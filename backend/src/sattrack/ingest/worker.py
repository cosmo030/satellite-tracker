"""Long-running loop that triggers ingest runs on CelesTrak's update cycle."""

from __future__ import annotations

import logging
import threading
from typing import Protocol

from sattrack.ingest.celestrak import CelesTrakUnavailableError
from sattrack.ingest.service import GP_REFRESH_INTERVAL, IngestReport, retry_delay

logger = logging.getLogger(__name__)


class _Runnable(Protocol):
    def run_once(self) -> IngestReport: ...


def run_forever(service: _Runnable, stop: threading.Event) -> None:
    """Run ingest every 2 hours until ``stop`` is set; back off after upstream failures."""
    consecutive_failures = 0
    while not stop.is_set():
        try:
            service.run_once()
            consecutive_failures = 0
            delay = GP_REFRESH_INTERVAL
        except CelesTrakUnavailableError as exc:
            consecutive_failures += 1
            delay = retry_delay(consecutive_failures)
            logger.error(
                "CelesTrak unavailable; pausing all requests status=%s failures=%d retry_in=%s",
                exc.status_code,
                consecutive_failures,
                delay,
            )
        logger.info("Next ingest run in %s", delay)
        stop.wait(delay.total_seconds())
