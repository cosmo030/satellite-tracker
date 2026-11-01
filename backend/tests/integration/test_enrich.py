from __future__ import annotations

from datetime import timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from sattrack.catalog.models import SatelliteAboutRow, SatelliteImageRow
from sattrack.enrich import EnrichMode, EnrichService, WikimediaUnavailableError
from sattrack.enrich.wikimedia import WikimediaClient, user_agent
from sattrack.ingest import IngestService

from ..conftest import MutableClock
from ..wikimedia_fake import FakeWikimedia

ISS = 25544
NAV = 100173  # matched on COSPAR ID, described by its constellation
GEO = 45001  # not on Wikidata


@pytest.fixture
def wikimedia() -> FakeWikimedia:
    return FakeWikimedia()


@pytest.fixture
def sleeps() -> list[float]:
    return []


@pytest.fixture
def enrich_service(
    ingest_service: IngestService,
    session_factory: sessionmaker[Session],
    clock: MutableClock,
    wikimedia: FakeWikimedia,
    sleeps: list[float],
) -> EnrichService:
    ingest_service.run_once()
    http = httpx.Client(transport=wikimedia.transport())
    client = WikimediaClient(
        http, user_agent("ops@example.test"), sleep=sleeps.append, monotonic=lambda: 1000.0
    )
    return EnrichService(client, session_factory, clock, refresh_interval=timedelta(days=7))


def _about_rows(session_factory: sessionmaker[Session]) -> dict[int, SatelliteAboutRow]:
    with session_factory() as session:
        return {row.norad_id: row for row in session.scalars(select(SatelliteAboutRow))}


def test_full_run_populates_descriptions_and_images(
    enrich_service: EnrichService, session_factory: sessionmaker[Session]
) -> None:
    report = enrich_service.run()

    assert (report.matched, report.descriptions, report.images, report.no_match) == (2, 2, 1, 1)
    rows = _about_rows(session_factory)
    iss = rows[ISS]
    assert iss.status == "ok"
    assert iss.wikidata_qid == "Q900001"  # the station, not its module (more sitelinks)
    assert iss.match_method == "norad"
    assert iss.scope == "object"
    assert iss.summary == (
        "The Synthetic Station is a made-up orbital station used only in tests. "
        "It has four modules. It was assembled by two made-up agencies."
    )
    assert iss.summary_source == "wikipedia"
    assert iss.categories == ["space_station", "crewed"]
    assert iss.operators == ["Agency A", "Agency B"]

    nav = rows[NAV]
    assert (nav.match_method, nav.scope, nav.title) == (
        "cospar",
        "constellation",
        "Testnet constellation",
    )
    assert nav.categories == ["navigation"]
    assert rows[GEO].status == "no_match"

    with session_factory() as session:
        images = {row.norad_id: row for row in session.scalars(select(SatelliteImageRow))}
    assert set(images) == {ISS}  # never the constellation's or a constellation member's image
    image = images[ISS]
    assert image.mime == "image/png"
    assert (image.width_480, image.height_480, image.width_960) == (480, 320, 960)
    assert image.artist == "Example Photographer"
    assert image.license_short == "CC BY-SA 4.0"
    assert image.attribution_required is True
    assert image.alt_text == "The made-up station seen from a departing test vehicle"
    assert image.source_url == "https://commons.wikimedia.org/wiki/File:Synthetic_station.jpg"


def test_every_request_identifies_us_and_goes_to_wikimedia(
    enrich_service: EnrichService, wikimedia: FakeWikimedia
) -> None:
    enrich_service.run()

    assert set(wikimedia.hosts()) == {
        "query.wikidata.org",
        "en.wikipedia.org",
        "commons.wikimedia.org",
        "upload.wikimedia.org",
        "thumb.wikimedia.org",
    }
    downloads = [str(r.url) for r in wikimedia.requests if r.url.host == "thumb.wikimedia.org"]
    assert downloads and all("utm_" not in url for url in downloads)
    agents = {request.headers["User-Agent"] for request in wikimedia.requests}
    assert agents == {
        "SatelliteTracker/0.1.0 (+https://github.com/cosmo030/satellite-tracker; ops@example.test)"
    }


def test_rate_limit_is_honoured_with_retry_after(
    enrich_service: EnrichService, wikimedia: FakeWikimedia, sleeps: list[float]
) -> None:
    wikimedia.rate_limited["en.wikipedia.org"] = 2

    report = enrich_service.run()

    assert report.descriptions == 2
    assert sleeps.count(7.0) == 2


def test_server_error_stops_the_run_and_keeps_existing_rows(
    enrich_service: EnrichService,
    session_factory: sessionmaker[Session],
    wikimedia: FakeWikimedia,
    clock: MutableClock,
) -> None:
    enrich_service.run()
    before = _about_rows(session_factory)
    clock.advance(timedelta(days=8))
    wikimedia.fail_hosts["commons.wikimedia.org"] = 503
    wikimedia.requests.clear()

    with pytest.raises(WikimediaUnavailableError):
        enrich_service.run(EnrichMode.FULL)

    after = _about_rows(session_factory)
    assert {n: (r.summary, r.fetched_at) for n, r in after.items()} == {
        n: (r.summary, r.fetched_at) for n, r in before.items()
    }
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(SatelliteImageRow)) == 1
    # No request after the failure.
    assert {"upload.wikimedia.org", "thumb.wikimedia.org"}.isdisjoint(wikimedia.hosts())


def test_due_run_skips_objects_fetched_recently(
    enrich_service: EnrichService, wikimedia: FakeWikimedia, clock: MutableClock
) -> None:
    enrich_service.run()
    wikimedia.requests.clear()
    clock.advance(timedelta(days=1))

    report = enrich_service.run(EnrichMode.DUE)

    assert report.processed == 0
    assert wikimedia.requests == []


def test_about_and_image_endpoints(enrich_service: EnrichService, api_client: TestClient) -> None:
    enrich_service.run()

    detail = api_client.get(f"/api/v1/satellites/{ISS}").json()
    assert (detail["has_about"], detail["has_image"]) == (True, True)
    about = api_client.get(f"/api/v1/satellites/{ISS}/about").json()
    assert about["scope"] == "object"
    assert about["summary_license"] == "CC BY-SA 4.0"
    assert about["categories"] == ["space_station", "crewed"]
    assert about["image"]["url_480"] == f"/api/v1/satellites/{ISS}/image?w=480"
    assert about["image"]["width_480"] == 480

    image = api_client.get(f"/api/v1/satellites/{ISS}/image", params={"w": 960})
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.headers["cache-control"] == "public, max-age=604800"
    assert image.content.startswith(b"\x89PNG")
    etag = image.headers["etag"]
    cached = api_client.get(
        f"/api/v1/satellites/{ISS}/image", params={"w": 960}, headers={"If-None-Match": etag}
    )
    assert cached.status_code == 304


def test_about_and_image_are_404_without_data(
    enrich_service: EnrichService, api_client: TestClient
) -> None:
    enrich_service.run()

    detail = api_client.get(f"/api/v1/satellites/{GEO}").json()
    assert (detail["has_about"], detail["has_image"]) == (False, False)
    assert api_client.get(f"/api/v1/satellites/{GEO}/about").status_code == 404
    assert api_client.get(f"/api/v1/satellites/{GEO}/image", params={"w": 480}).status_code == 404
    constellation = api_client.get(f"/api/v1/satellites/{NAV}/about").json()
    assert constellation["scope"] == "constellation"
    assert constellation["image"] is None
    assert api_client.get(f"/api/v1/satellites/{ISS}/image", params={"w": 500}).status_code == 422
