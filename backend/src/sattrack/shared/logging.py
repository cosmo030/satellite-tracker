"""Logging setup used by the API and the ingest worker."""

from __future__ import annotations

import logging

LOG_FORMAT = "%(asctime)s level=%(levelname)s logger=%(name)s %(message)s"


def configure_logging(level: str) -> None:
    """Configure the root logger once per process."""
    logging.basicConfig(level=level, format=LOG_FORMAT, force=True)
