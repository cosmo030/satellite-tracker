"""Cross-cutting infrastructure used by several modules (database, logging, clock)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

Clock = Callable[[], datetime]
"""Returns the current time as an aware UTC datetime; injected so tests are deterministic."""


def utc_now() -> datetime:
    return datetime.now(UTC)
