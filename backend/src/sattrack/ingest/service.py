"""Ingest use case: refresh catalog data from CelesTrak while respecting its usage policy.

Policy (https://celestrak.org/usage-policy.php): GP data updates once every 2 hours, so each
group is downloaded at most once per update; any non-200 response stops all further queries.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol

from sqlalchemy.orm import Session, sessionmaker

from sattrack.catalog import CatalogRepository, OrbitalElements, SatcatRecord, group_display_name
from sattrack.ingest.celestrak import CelesTrakResponseError, CelesTrakUnavailableError, FetchResult
from sattrack.ingest.repository import FetchAttempt, FetchLogRepository, FetchSource
from sattrack.shared import Clock
from sattrack.shared.db import transaction

logger = logging.getLogger(__name__)

GP_REFRESH_INTERVAL = timedelta(hours=2)
SATCAT_REFRESH_INTERVAL = timedelta(hours=24)
# Three missed GP updates in a row means the served data is getting old.
DATA_STALE_AFTER = timedelta(hours=6)
MAX_RETRY_DELAY = timedelta(hours=24)


class CatalogSource(Protocol):
    """What the ingest service needs from an upstream provider (CelesTrak in production)."""

    def fetch_group_elements(self, group: str) -> FetchResult[OrbitalElements]: ...

    def fetch_group_satcat(self, group: str) -> FetchResult[SatcatRecord]: ...


def is_due(last_success: datetime | None, now: datetime, interval: timedelta) -> bool:
    """True when a refresh is allowed: never fetched, or the previous success is old enough."""
    return last_success is None or now - last_success >= interval


def retry_delay(consecutive_failures: int) -> timedelta:
    """Back-off after failed runs: 2 h, 4 h, 8 h, ... capped at 24 h."""
    if consecutive_failures < 1:
        return GP_REFRESH_INTERVAL
    exponent = min(consecutive_failures - 1, 10)
    return min(GP_REFRESH_INTERVAL * (1 << exponent), MAX_RETRY_DELAY)


class DataState(StrEnum):
    OK = "ok"
    STALE = "stale"
    NO_DATA = "no_data"


@dataclass(frozen=True, slots=True)
class DataStatus:
    state: DataState
    last_success_at: datetime | None
    age_seconds: int | None


def data_status(last_success: datetime | None, now: datetime) -> DataStatus:
    if last_success is None:
        return DataStatus(DataState.NO_DATA, None, None)
    age = now - last_success
    state = DataState.STALE if age > DATA_STALE_AFTER else DataState.OK
    return DataStatus(state, last_success, int(age.total_seconds()))


def get_data_status(session: Session, now: datetime) -> DataStatus:
    """Freshness of the served element sets, based on the last successful GP download."""
    return data_status(FetchLogRepository(session).last_success_any(FetchSource.GP), now)


@dataclass(slots=True)
class IngestReport:
    groups_refreshed: list[str] = field(default_factory=list)
    groups_skipped: list[str] = field(default_factory=list)
    elements_added: int = 0
    satcat_updated: int = 0
    failed_groups: list[str] = field(default_factory=list)


class IngestService:
    def __init__(
        self,
        source: CatalogSource,
        session_factory: sessionmaker[Session],
        groups: tuple[str, ...],
        clock: Clock,
    ) -> None:
        self._source = source
        self._session_factory = session_factory
        self._groups = groups
        self._clock = clock

    def run_once(self) -> IngestReport:
        """Refresh every configured group that is due.

        Raises ``CelesTrakUnavailableError`` on the first non-200 response or network error;
        no further requests are made in this run.
        """
        report = IngestReport()
        for group in self._groups:
            self._refresh_elements_if_due(group, report)
            self._refresh_satcat_if_due(group, report)
        logger.info(
            "Ingest run finished refreshed=%s skipped=%s elements_added=%d "
            "satcat_updated=%d failed=%s",
            report.groups_refreshed,
            report.groups_skipped,
            report.elements_added,
            report.satcat_updated,
            report.failed_groups,
        )
        return report

    def _refresh_elements_if_due(self, group: str, report: IngestReport) -> None:
        if not self._is_due(FetchSource.GP, group, GP_REFRESH_INTERVAL):
            report.groups_skipped.append(group)
            return
        result = self._fetch(FetchSource.GP, group, self._source.fetch_group_elements, report)
        if result is None:
            return
        now = self._clock()
        with transaction(self._session_factory) as session:
            catalog = CatalogRepository(session)
            catalog.upsert_group(group, group_display_name(group))
            catalog.upsert_satellites_from_elements(result.records, now)
            report.elements_added += catalog.add_elements(result.records, now)
            catalog.replace_group_members(group, (e.norad_id for e in result.records))
        report.groups_refreshed.append(group)

    def _refresh_satcat_if_due(self, group: str, report: IngestReport) -> None:
        if not self._is_due(FetchSource.SATCAT, group, SATCAT_REFRESH_INTERVAL):
            return
        result = self._fetch(FetchSource.SATCAT, group, self._source.fetch_group_satcat, report)
        if result is None:
            return
        with transaction(self._session_factory) as session:
            report.satcat_updated += CatalogRepository(session).apply_satcat(
                result.records, self._clock()
            )

    def _is_due(self, source: FetchSource, group: str, interval: timedelta) -> bool:
        with self._session_factory() as session:
            last = FetchLogRepository(session).last_success(source, group)
        return is_due(last, self._clock(), interval)

    def _fetch[T](
        self,
        source: FetchSource,
        group: str,
        fetch: _Fetch[T],
        report: IngestReport,
    ) -> FetchResult[T] | None:
        """Run one upstream request and record it in the fetch log.

        Returns None when the body was unusable (logged, run continues). Re-raises
        ``CelesTrakUnavailableError`` so the caller stops querying.
        """
        started = self._clock()
        try:
            result = fetch(group)
        except CelesTrakUnavailableError as exc:
            self._record_failure(source, group, exc.url, exc.status_code, str(exc), started)
            report.failed_groups.append(group)
            raise
        except CelesTrakResponseError as exc:
            self._record_failure(source, group, exc.url, 200, str(exc), started)
            report.failed_groups.append(group)
            logger.error("Skipping group after unusable response group=%s error=%s", group, exc)
            return None
        self._record(
            FetchAttempt(
                source=source,
                group=group,
                url=result.url,
                status_code=200,
                succeeded=True,
                record_count=len(result.records),
                rejected_count=result.rejected_count,
                error=None,
                started_at=started,
                finished_at=self._clock(),
            )
        )
        return result

    def _record_failure(
        self,
        source: FetchSource,
        group: str,
        url: str,
        status_code: int | None,
        error: str,
        started: datetime,
    ) -> None:
        self._record(
            FetchAttempt(
                source=source,
                group=group,
                url=url,
                status_code=status_code,
                succeeded=False,
                record_count=0,
                rejected_count=0,
                error=error,
                started_at=started,
                finished_at=self._clock(),
            )
        )

    def _record(self, attempt: FetchAttempt) -> None:
        # Own transaction, so the attempt is logged even if storing the data fails later.
        with transaction(self._session_factory) as session:
            FetchLogRepository(session).record(attempt)


class _Fetch[T](Protocol):
    def __call__(self, group: str, /) -> FetchResult[T]: ...
