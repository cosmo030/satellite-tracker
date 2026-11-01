"""One enrich run from the command line: ``python -m sattrack.enrich --once [--full]``.

The worker (``python -m sattrack.ingest``) runs the same job daily on its own.
"""

from __future__ import annotations

import argparse
import logging
import sys

import httpx

from sattrack.config import load_settings
from sattrack.enrich import (
    EnrichDisabledError,
    EnrichMode,
    WikimediaUnavailableError,
    create_enrich_service,
)
from sattrack.shared import utc_now
from sattrack.shared.db import create_db_engine, create_session_factory
from sattrack.shared.logging import configure_logging

logger = logging.getLogger("sattrack.enrich")

EXIT_FAILED = 1
EXIT_NOT_CONFIGURED = 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch descriptions and images from Wikimedia.")
    parser.add_argument("--once", action="store_true", help="run one pass and exit (default)")
    parser.add_argument(
        "--full", action="store_true", help="refresh every object, not only those due"
    )
    args = parser.parse_args(argv)

    settings = load_settings()
    configure_logging(settings.log_level)
    engine = create_db_engine(str(settings.database_url))
    try:
        with httpx.Client(timeout=settings.http_timeout_seconds) as http:
            service = create_enrich_service(
                settings, http, create_session_factory(engine), clock=utc_now
            )
            service.run(EnrichMode.FULL if args.full else EnrichMode.DUE)
    except EnrichDisabledError as exc:
        if not settings.enrich_enabled:
            logger.info("Enrich not started: %s", exc)
            return 0
        logger.error("Enrich not started: %s", exc)
        return EXIT_NOT_CONFIGURED
    except WikimediaUnavailableError as exc:
        logger.error("Enrich run stopped: %s", exc)
        return EXIT_FAILED
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
