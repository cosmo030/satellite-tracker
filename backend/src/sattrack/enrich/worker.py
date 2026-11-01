"""Daily loop of the enrich job inside the worker process."""

from __future__ import annotations

import logging
import threading
from datetime import timedelta
from typing import Protocol

from sattrack.enrich.service import EnrichMode, EnrichReport
from sattrack.enrich.wikimedia import WikimediaUnavailableError

logger = logging.getLogger(__name__)

# New objects are picked up once a day; each object is refreshed when it is older than the
# configured interval (7 days by default), so a daily check covers both.
CHECK_INTERVAL = timedelta(days=1)


class _Runnable(Protocol):
    def run(self, mode: EnrichMode = ..., stop: threading.Event | None = ...) -> EnrichReport: ...


def run_enrich_forever(service: _Runnable, stop: threading.Event) -> None:
    """Run the due enrichment once a day until ``stop`` is set."""
    while not stop.is_set():
        try:
            service.run(EnrichMode.DUE, stop=stop)
        except WikimediaUnavailableError as exc:
            logger.error(
                "Wikimedia unavailable; enrich run stopped status=%s retry_in=%s",
                exc.status_code,
                CHECK_INTERVAL,
            )
        stop.wait(CHECK_INTERVAL.total_seconds())
