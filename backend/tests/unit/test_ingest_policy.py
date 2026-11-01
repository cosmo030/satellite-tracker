from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sattrack.ingest.service import DataState, data_status, is_due, retry_delay

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
TWO_HOURS = timedelta(hours=2)


def test_is_due_when_never_fetched() -> None:
    assert is_due(None, NOW, TWO_HOURS) is True


def test_is_not_due_before_interval_has_passed() -> None:
    assert is_due(NOW - timedelta(hours=1, minutes=59), NOW, TWO_HOURS) is False


def test_is_due_exactly_at_interval() -> None:
    assert is_due(NOW - TWO_HOURS, NOW, TWO_HOURS) is True


@pytest.mark.parametrize(
    ("failures", "expected_hours"),
    [(0, 2), (1, 2), (2, 4), (3, 8), (4, 16), (5, 24), (50, 24)],
)
def test_retry_delay_doubles_and_caps_at_24_hours(failures: int, expected_hours: int) -> None:
    assert retry_delay(failures) == timedelta(hours=expected_hours)


def test_data_status_without_any_fetch_is_no_data() -> None:
    status = data_status(None, NOW)
    assert status.state is DataState.NO_DATA
    assert status.age_seconds is None


def test_data_status_is_ok_within_six_hours() -> None:
    status = data_status(NOW - timedelta(hours=6), NOW)
    assert status.state is DataState.OK
    assert status.age_seconds == 6 * 3600


def test_data_status_is_stale_after_six_hours() -> None:
    assert data_status(NOW - timedelta(hours=6, seconds=1), NOW).state is DataState.STALE
