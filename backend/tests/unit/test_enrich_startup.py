from __future__ import annotations

import httpx
import pytest
from sqlalchemy.orm import sessionmaker

from sattrack.config import Settings
from sattrack.enrich import EnrichDisabledError, create_enrich_service
from sattrack.enrich.__main__ import EXIT_NOT_CONFIGURED, main

from ..conftest import MutableClock

DB_URL = "postgresql+psycopg://user:password-not-real@localhost:5432/app"


def _no_network(request: httpx.Request) -> httpx.Response:
    raise AssertionError(f"unexpected request to {request.url}")


@pytest.mark.parametrize(
    ("enabled", "contact", "message"),
    [
        (True, None, "SATTRACK_ENRICH_CONTACT is required"),
        (False, "ops@example.test", "SATTRACK_ENRICH_ENABLED is false"),
    ],
)
def test_enrich_refuses_to_start(enabled: bool, contact: str | None, message: str) -> None:
    settings = Settings(database_url=DB_URL, enrich_enabled=enabled, enrich_contact=contact)
    http = httpx.Client(transport=httpx.MockTransport(_no_network))

    with pytest.raises(EnrichDisabledError, match=message):
        create_enrich_service(settings, http, sessionmaker(), MutableClock())


def test_command_exits_with_an_error_without_contact(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SATTRACK_DATABASE_URL", DB_URL)
    monkeypatch.delenv("SATTRACK_ENRICH_CONTACT", raising=False)
    monkeypatch.delenv("SATTRACK_ENRICH_ENABLED", raising=False)

    assert main(["--once"]) == EXIT_NOT_CONFIGURED


def test_command_does_nothing_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SATTRACK_DATABASE_URL", DB_URL)
    monkeypatch.setenv("SATTRACK_ENRICH_ENABLED", "false")

    assert main(["--once"]) == 0
