from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from sattrack.ingest import IngestService

from ..conftest import FakeCatalogSource, MutableClock


@pytest.fixture
def seeded(ingest_service: IngestService) -> None:
    ingest_service.run_once()


@pytest.mark.usefixtures("seeded")
def test_groups_lists_ingested_groups_with_counts(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/groups")

    assert response.status_code == 200
    assert response.json() == [
        {"slug": "gps-ops", "name": "GPS operational", "satellite_count": 3},
        {"slug": "stations", "name": "Space stations", "satellite_count": 3},
    ]


@pytest.mark.usefixtures("seeded")
def test_search_matches_name_case_insensitively(api_client: TestClient) -> None:
    body = api_client.get("/api/v1/satellites", params={"q": "zarya"}).json()

    assert body["total"] == 1
    assert body["items"][0]["norad_id"] == 25544
    assert body["items"][0]["orbit_class"] == "LEO"


@pytest.mark.usefixtures("seeded")
def test_search_matches_norad_id(api_client: TestClient) -> None:
    body = api_client.get("/api/v1/satellites", params={"q": "100173"}).json()
    assert [item["name"] for item in body["items"]] == ["TESTSAT NAV-1"]


@pytest.mark.usefixtures("seeded")
def test_search_treats_wildcards_in_query_literally(api_client: TestClient) -> None:
    body = api_client.get("/api/v1/satellites", params={"q": "%"}).json()
    assert body["total"] == 0


@pytest.mark.usefixtures("seeded")
@pytest.mark.parametrize(
    ("params", "expected_ids"),
    [
        ({"orbit_class": "GEO"}, [45001]),
        ({"orbit_class": "MEO"}, [100173]),
        ({"country": "US"}, [45001]),
        ({"launch_year": 1998}, [25544]),
        ({"group": "stations", "orbit_class": "LEO"}, [25544]),
    ],
)
def test_search_filters(
    api_client: TestClient, params: dict[str, object], expected_ids: list[int]
) -> None:
    body = api_client.get("/api/v1/satellites", params=params).json()
    assert [item["norad_id"] for item in body["items"]] == expected_ids


@pytest.mark.usefixtures("seeded")
def test_search_paginates_in_name_order(api_client: TestClient) -> None:
    body = api_client.get("/api/v1/satellites", params={"limit": 2, "offset": 1}).json()

    assert body["total"] == 3
    assert body["limit"] == 2
    assert [item["name"] for item in body["items"]] == ["TESTSAT GEO-2", "TESTSAT NAV-1"]


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 201},
        {"offset": -1},
        {"orbit_class": "LOW"},
        {"group": "Bad Group"},
        {"country": "us"},
        {"launch_year": 1900},
        {"q": "x" * 101},
    ],
)
def test_search_rejects_invalid_parameters(
    api_client: TestClient, params: dict[str, object]
) -> None:
    assert api_client.get("/api/v1/satellites", params=params).status_code == 422


@pytest.mark.usefixtures("seeded")
def test_satellite_detail_includes_latest_elements(api_client: TestClient) -> None:
    body = api_client.get("/api/v1/satellites/25544").json()

    assert body["satellite"]["name"] == "ISS (ZARYA)"
    assert body["satellite"]["launch_date"] == "1998-11-20"
    elements = body["latest_elements"]
    assert elements["epoch"] == "2026-10-30T12:00:00Z"
    assert elements["period_minutes"] == pytest.approx(92.897, abs=1e-3)


@pytest.mark.usefixtures("seeded")
def test_satellite_detail_returns_404_for_unknown_id(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/satellites/424242")
    assert response.status_code == 404
    assert response.json() == {"detail": "No satellite with NORAD ID 424242"}


@pytest.mark.usefixtures("seeded")
def test_elements_returns_group_with_cache_headers(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/elements", params={"group": "stations"})

    assert response.status_code == 200
    assert [e["norad_id"] for e in response.json()] == [25544, 45001, 100173]
    assert response.headers["cache-control"] == "public, max-age=300"
    assert response.headers["etag"].startswith('"')


@pytest.mark.usefixtures("seeded")
def test_elements_returns_304_when_etag_matches(api_client: TestClient) -> None:
    etag = api_client.get("/api/v1/elements", params={"group": "stations"}).headers["etag"]

    response = api_client.get(
        "/api/v1/elements", params={"group": "stations"}, headers={"If-None-Match": etag}
    )

    assert response.status_code == 304
    assert response.content == b""
    assert response.headers["etag"] == etag


@pytest.mark.usefixtures("seeded")
def test_elements_etag_is_stable_when_refetch_brings_no_new_epochs(
    api_client: TestClient, ingest_service: IngestService, clock: MutableClock
) -> None:
    first = api_client.get("/api/v1/elements", params={"group": "stations"}).headers["etag"]
    clock.advance(timedelta(hours=2))
    ingest_service.run_once()

    second = api_client.get("/api/v1/elements", params={"group": "stations"}).headers["etag"]

    assert first == second


@pytest.mark.usefixtures("seeded")
def test_elements_etag_changes_when_a_newer_epoch_arrives(
    api_client: TestClient,
    ingest_service: IngestService,
    fake_source: FakeCatalogSource,
    clock: MutableClock,
) -> None:
    first = api_client.get("/api/v1/elements", params={"group": "stations"}).headers["etag"]
    iss = fake_source.elements[0]
    fake_source.elements[0] = replace(iss, epoch=iss.epoch + timedelta(hours=3))
    clock.advance(timedelta(hours=2))
    ingest_service.run_once()

    response = api_client.get("/api/v1/elements", params={"group": "stations"})

    assert response.headers["etag"] != first
    assert response.json()[0]["epoch"] == "2026-10-30T15:00:00Z"


def test_elements_returns_404_for_unknown_group(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/elements", params={"group": "nope"})
    assert response.status_code == 404


def test_health_reports_no_data_before_first_ingest(api_client: TestClient) -> None:
    body = api_client.get("/api/v1/health").json()
    assert body == {
        "status": "ok",
        "data_state": "no_data",
        "last_successful_fetch_at": None,
        "data_age_seconds": None,
    }


@pytest.mark.usefixtures("seeded")
def test_health_reports_stale_data_after_six_hours(
    api_client: TestClient, clock: MutableClock
) -> None:
    assert api_client.get("/api/v1/health").json()["data_state"] == "ok"
    clock.advance(timedelta(hours=7))
    assert api_client.get("/api/v1/health").json()["data_state"] == "stale"


def test_health_returns_503_when_database_fails(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing_status(*_args: object, **_kwargs: object) -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    monkeypatch.setattr("sattrack.health.api.get_data_status", failing_status)

    response = api_client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"


def test_responses_carry_security_headers(api_client: TestClient) -> None:
    headers = api_client.get("/api/v1/health").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"


def test_unexpected_errors_return_generic_message_with_correlation_id(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr("sattrack.catalog.repository.CatalogRepository.list_groups", broken)
    client = TestClient(api_client.app, raise_server_exceptions=False)

    response = client.get("/api/v1/groups")

    assert response.status_code == 500
    body = response.json()
    assert body["detail"] == "Internal server error"
    assert "secret" not in response.text
    assert len(body["correlation_id"]) == 32
