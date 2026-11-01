"""Entry point of the worker: ``python -m sattrack.ingest [--once]``.

Runs the CelesTrak ingest every 2 hours and, unless disabled, the Wikimedia enrich job daily
in a second thread. ``--once`` runs a single ingest pass only.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
from types import FrameType

import httpx
from sqlalchemy.orm import Session, sessionmaker

from sattrack.config import Settings, load_settings
from sattrack.enrich import EnrichDisabledError, create_enrich_service, run_enrich_forever
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
    session_factory = create_session_factory(engine)
    with (
        httpx.Client(timeout=settings.http_timeout_seconds) as http,
        httpx.Client(timeout=settings.http_timeout_seconds) as enrich_http,
    ):
        service = IngestService(
            source=CelesTrakClient(http, settings.celestrak_base_url),
            session_factory=session_factory,
            groups=settings.ingest_groups,
            clock=utc_now,
        )
        if args.once:
            return _run_single(service)
        stop = threading.Event()
        _stop_on_signals(stop)
        enrich_thread = _start_enrich_job(settings, enrich_http, session_factory, stop)
        logger.info("Ingest worker started groups=%s", ",".join(settings.ingest_groups))
        run_forever(service, stop)
        if enrich_thread is not None:
            enrich_thread.join()
    engine.dispose()
    logger.info("Ingest worker stopped")
    return 0


def _start_enrich_job(
    settings: Settings,
    http: httpx.Client,
    session_factory: sessionmaker[Session],
    stop: threading.Event,
) -> threading.Thread | None:
    """Run the Wikimedia enrich job alongside ingest, in its own thread (it shares the lock)."""
    try:
        enrich = create_enrich_service(settings, http, session_factory, clock=utc_now)
    except EnrichDisabledError as exc:
        log = logger.info if not settings.enrich_enabled else logger.error
        log("Enrich job not started: %s", exc)
        return None
    thread = threading.Thread(
        target=run_enrich_forever, args=(enrich, stop), name="enrich", daemon=True
    )
    thread.start()
    logger.info("Enrich job started refresh_interval_hours=%d", settings.enrich_interval_hours)
    return thread


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
