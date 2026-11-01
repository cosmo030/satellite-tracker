"""Enrich module: descriptions, purpose categories and images from Wikimedia.

The only code that calls Wikidata, Wikipedia and Wikimedia Commons. Writes to the catalog
through ``CatalogRepository``. Public interface: ``create_enrich_service`` for the worker and
the command line, ``EnrichMode``, ``run_enrich_forever`` and ``EnrichDisabledError``.
"""

from __future__ import annotations

from datetime import timedelta

import httpx
from sqlalchemy.orm import Session, sessionmaker

from sattrack.config import Settings
from sattrack.enrich.service import EnrichMode, EnrichReport, EnrichService
from sattrack.enrich.wikimedia import WikimediaClient, WikimediaUnavailableError, user_agent
from sattrack.enrich.worker import run_enrich_forever
from sattrack.shared import Clock


class EnrichDisabledError(Exception):
    """The enrich job must not run: switched off, or no contact for the User-Agent."""


def create_enrich_service(
    settings: Settings, http: httpx.Client, session_factory: sessionmaker[Session], clock: Clock
) -> EnrichService:
    """Build the enrich service; raises ``EnrichDisabledError`` when it must not start."""
    if not settings.enrich_enabled:
        raise EnrichDisabledError("SATTRACK_ENRICH_ENABLED is false; no Wikimedia requests")
    if not settings.enrich_contact:
        raise EnrichDisabledError(
            "SATTRACK_ENRICH_CONTACT is required: an email address or https URL that Wikimedia "
            "operators can use to reach you"
        )
    return EnrichService(
        client=WikimediaClient(http, user_agent(settings.enrich_contact)),
        session_factory=session_factory,
        clock=clock,
        refresh_interval=timedelta(hours=settings.enrich_interval_hours),
    )


__all__ = [
    "EnrichDisabledError",
    "EnrichMode",
    "EnrichReport",
    "EnrichService",
    "WikimediaUnavailableError",
    "create_enrich_service",
    "run_enrich_forever",
]
