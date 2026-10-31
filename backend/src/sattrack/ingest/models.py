"""ORM mapping for the fetch log, owned by the ingest module."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from sattrack.shared.db import Base


class FetchLogRow(Base):
    """One request to an upstream provider; proves we respect its usage policy."""

    __tablename__ = "fetch_log"
    __table_args__ = (
        Index("ix_fetch_log_source_group_started", "source", "group_slug", "started_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(20))
    group_slug: Mapped[str] = mapped_column(String(50))
    url: Mapped[str] = mapped_column(String(500))
    status_code: Mapped[int | None] = mapped_column(Integer)
    succeeded: Mapped[bool]
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
