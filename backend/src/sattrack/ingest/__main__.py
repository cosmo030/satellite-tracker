"""Entry point of the ingest worker: ``python -m sattrack.ingest [--once]``."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
from types import FrameType

import httpx

from sattrack.config import load_settings
from sattrack.ingest.celestrak import CelesTrakClient, CelesTrakUnavailableError
from sattrack.ingest.service import IngestService
from sattrack.ingest.worker import run_forever
from sattrack.shared import utc_now
from sattrack.shared.db import create_db_engine, create_session_factory
from sattrack.shared.logging import configure_logging

logger = logging.getLogger("sattrack.ingest")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh satellite data from CelesTrak.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="run a single ingest pass and exit (for cron or manual runs)",
    )
    args = parser.parse_args(argv)

    settings = load_settings()
    configure_logging(settings.log_level)
    engine = create_db_engine(str(settings.database_url))
    with httpx.Client(timeout=settings.http_timeout_seconds) as http:
        service = IngestService(
            source=CelesTrakClient(http, settings.celestrak_base_url),
            session_factory=create_session_factory(engine),
            groups=settings.ingest_groups,
            clock=utc_now,
        )
        if args.once:
            return _run_single(service)
        stop = threading.Event()
        _stop_on_signals(stop)
        logger.info("Ingest worker started groups=%s", ",".join(settings.ingest_groups))
        run_forever(service, stop)
    engine.dispose()
    logger.info("Ingest worker stopped")
    return 0


def _run_single(service: IngestService) -> int:
    try:
        report = service.run_once()
    except CelesTrakUnavailableError as exc:
        logger.error("Ingest aborted: %s", exc)
        return 1
    return 1 if report.failed_groups else 0


def _stop_on_signals(stop: threading.Event) -> None:
    def handle(signum: int, _frame: FrameType | None) -> None:
        logger.info("Received signal %d, stopping", signum)
        stop.set()

    signal.signal(signal.SIGTERM, handle)
    signal.signal(signal.SIGINT, handle)


if __name__ == "__main__":
    sys.exit(main())
