"""Shared test helpers: fixture loading, a fixed clock and a fake CelesTrak source."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from sattrack.catalog import OrbitalElements, SatcatRecord
from sattrack.ingest.celestrak import (
    CelesTrakUnavailableError,
    FetchResult,
    parse_omm_record,
    parse_satcat_record,
)

FIXTURES = Path(__file__).parent / "fixtures"
FIXED_NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)


def load_fixture(name: str) -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = json.loads((FIXTURES / name).read_text())
    return data


class MutableClock:
    """A clock tests can move forward."""

    def __init__(self, now: datetime = FIXED_NOW) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta) -> None:
        self.now += delta


class FakeCatalogSource:
    """Stands in for CelesTrak. Serves fixture data or raises configured errors per group."""

    def __init__(self) -> None:
        self.elements = [parse_omm_record(r) for r in load_fixture("gp_sample.json")]
        self.satcat = [parse_satcat_record(r) for r in load_fixture("satcat_sample.json")]
        self.unavailable_groups: set[str] = set()
        self.requests: list[tuple[str, str]] = []

    def fetch_group_elements(self, group: str) -> FetchResult[OrbitalElements]:
        self.requests.append(("gp", group))
        url = f"https://celestrak.test/gp?GROUP={group}"
        if group in self.unavailable_groups:
            raise CelesTrakUnavailableError(url, 503, "HTTP 503")
        return FetchResult(url=url, records=list(self.elements), rejected_count=0)

    def fetch_group_satcat(self, group: str) -> FetchResult[SatcatRecord]:
        self.requests.append(("satcat", group))
        url = f"https://celestrak.test/satcat?GROUP={group}"
        return FetchResult(url=url, records=list(self.satcat), rejected_count=0)


@pytest.fixture
def clock() -> MutableClock:
    return MutableClock()


@pytest.fixture
def fake_source() -> FakeCatalogSource:
    return FakeCatalogSource()


@pytest.fixture
def omm_record() -> Callable[..., dict[str, Any]]:
    """Factory for a valid OMM record with selected fields overridden."""

    def build(**overrides: Any) -> dict[str, Any]:
        record = dict(load_fixture("gp_sample.json")[0])
        record.update(overrides)
        return record

    return build
