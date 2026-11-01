"""Data access for the fetch log."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sattrack.ingest.models import FetchLogRow


class FetchSource(StrEnum):
    GP = "gp"
    SATCAT = "satcat"


@dataclass(frozen=True, slots=True)
class FetchAttempt:
    source: FetchSource
    group: str
    url: str
    status_code: int | None
    succeeded: bool
    record_count: int
    rejected_count: int
    error: str | None
    started_at: datetime
    finished_at: datetime


class FetchLogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(self, attempt: FetchAttempt) -> None:
        self._session.add(
            FetchLogRow(
                source=attempt.source.value,
                group_slug=attempt.group,
                url=attempt.url,
                status_code=attempt.status_code,
                succeeded=attempt.succeeded,
                record_count=attempt.record_count,
                rejected_count=attempt.rejected_count,
                error=attempt.error,
                started_at=attempt.started_at,
                finished_at=attempt.finished_at,
            )
        )

    def last_success(self, source: FetchSource, group: str) -> datetime | None:
        return self._session.scalar(
            select(func.max(FetchLogRow.finished_at)).where(
                FetchLogRow.source == source.value,
                FetchLogRow.group_slug == group,
                FetchLogRow.succeeded.is_(True),
            )
        )

    def last_success_any(self, source: FetchSource) -> datetime | None:
        return self._session.scalar(
            select(func.max(FetchLogRow.finished_at)).where(
                FetchLogRow.source == source.value,
                FetchLogRow.succeeded.is_(True),
            )
        )
