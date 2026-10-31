from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from sattrack.catalog import OrbitalElements
from sattrack.catalog.models import OrbitalElementsRow, SatelliteGroupRow, SatelliteRow
from sattrack.ingest import IngestService
from sattrack.ingest.celestrak import (
    CelesTrakResponseError,
    CelesTrakUnavailableError,
    FetchResult,
)
from sattrack.ingest.models import FetchLogRow

from ..conftest import FakeCatalogSource, MutableClock


def count(session_factory: sessionmaker[Session], model: type) -> int:
    with session_factory() as session:
        return session.scalar(select(func.count()).select_from(model)) or 0


def test_first_run_stores_satellites_elements_groups_and_metadata(
    ingest_service: IngestService, session_factory: sessionmaker[Session]
) -> None:
    report = ingest_service.run_once()

    assert report.groups_refreshed == ["stations", "gps-ops"]
    assert report.elements_added == 3  # same three objects in both groups; stored once
    assert count(session_factory, SatelliteRow) == 3
    assert count(session_factory, SatelliteGroupRow) == 6
    with session_factory() as session:
        iss = session.get(SatelliteRow, 25544)
        assert iss is not None
        assert iss.orbit_class == "LEO"
        assert iss.country == "ISS"
        assert iss.launch_date == date(1998, 11, 20)
        assert session.get(SatelliteRow, 100173) is not None  # six-digit catalog number


def test_second_run_within_two_hours_makes_no_requests(
    ingest_service: IngestService, fake_source: FakeCatalogSource, clock: MutableClock
) -> None:
    ingest_service.run_once()
    fake_source.requests.clear()
    clock.advance(timedelta(hours=1, minutes=59))

    report = ingest_service.run_once()

    assert fake_source.requests == []
    assert report.groups_skipped == ["stations", "gps-ops"]


def test_run_after_two_hours_refetches_gp_but_not_daily_satcat(
    ingest_service: IngestService,
    fake_source: FakeCatalogSource,
    clock: MutableClock,
    session_factory: sessionmaker[Session],
) -> None:
    ingest_service.run_once()
    fake_source.requests.clear()
    clock.advance(timedelta(hours=2))

    report = ingest_service.run_once()

    assert fake_source.requests == [("gp", "stations"), ("gp", "gps-ops")]
    assert report.elements_added == 0  # same epochs: nothing new stored
    assert count(session_factory, OrbitalElementsRow) == 3


def test_unavailable_upstream_stops_the_run_and_is_logged(
    ingest_service: IngestService,
    fake_source: FakeCatalogSource,
    session_factory: sessionmaker[Session],
) -> None:
    fake_source.unavailable_groups = {"stations"}

    with pytest.raises(CelesTrakUnavailableError):
        ingest_service.run_once()

    assert fake_source.requests == [("gp", "stations")]  # gps-ops was never requested
    with session_factory() as session:
        log = session.scalars(select(FetchLogRow)).one()
    assert log.succeeded is False
    assert log.status_code == 503
    assert count(session_factory, SatelliteRow) == 0


def test_unusable_response_skips_group_and_continues(
    ingest_service: IngestService,
    fake_source: FakeCatalogSource,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = fake_source.fetch_group_elements

    def fetch(group: str) -> FetchResult[OrbitalElements]:
        if group == "stations":
            raise CelesTrakResponseError("https://celestrak.test", "body is not JSON")
        return original(group)

    monkeypatch.setattr(fake_source, "fetch_group_elements", fetch)

    report = ingest_service.run_once()

    assert report.failed_groups == ["stations"]
    assert report.groups_refreshed == ["gps-ops"]
    assert count(session_factory, SatelliteRow) == 3


def test_newer_epoch_is_stored_as_history_and_served_as_latest(
    ingest_service: IngestService,
    fake_source: FakeCatalogSource,
    clock: MutableClock,
    session_factory: sessionmaker[Session],
) -> None:
    ingest_service.run_once()
    iss = fake_source.elements[0]
    newer = replace(iss, epoch=iss.epoch + timedelta(hours=6))
    fake_source.elements = [newer, *fake_source.elements[1:]]
    clock.advance(timedelta(hours=2))

    report = ingest_service.run_once()

    assert report.elements_added == 1
    with session_factory() as session:
        epochs = session.scalars(
            select(OrbitalElementsRow.epoch).where(OrbitalElementsRow.norad_id == 25544)
        ).all()
    assert sorted(epochs) == [iss.epoch, newer.epoch]
