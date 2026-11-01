from __future__ import annotations

import pytest
from pydantic import ValidationError

from sattrack.config import DEFAULT_INGEST_GROUPS, Settings

DB_URL = "postgresql+psycopg://user:password-not-real@localhost:5432/app"


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ignore SATTRACK_* variables set in the developer's shell.
    for name in (
        "DATABASE_URL",
        "INGEST_GROUPS",
        "CORS_ALLOWED_ORIGINS",
        "CELESTRAK_BASE_URL",
        "ENRICH_ENABLED",
        "ENRICH_CONTACT",
        "ENRICH_INTERVAL_HOURS",
    ):
        monkeypatch.delenv(f"SATTRACK_{name}", raising=False)


def test_settings_require_database_url() -> None:
    with pytest.raises(ValidationError, match="database_url"):
        Settings()


def test_settings_use_safe_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SATTRACK_DATABASE_URL", DB_URL)
    settings = Settings()

    assert settings.ingest_groups == DEFAULT_INGEST_GROUPS
    assert settings.cors_allowed_origins == ()
    assert settings.celestrak_base_url == "https://celestrak.org"
    assert settings.log_level == "INFO"


def test_settings_parse_comma_separated_lists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SATTRACK_DATABASE_URL", DB_URL)
    monkeypatch.setenv("SATTRACK_INGEST_GROUPS", " stations, gps-ops ,")
    monkeypatch.setenv("SATTRACK_CORS_ALLOWED_ORIGINS", "https://a.example,https://b.example")
    settings = Settings()

    assert settings.ingest_groups == ("stations", "gps-ops")
    assert settings.cors_allowed_origins == ("https://a.example", "https://b.example")


@pytest.mark.parametrize("groups", ["", "stations,bad group", "../etc"])
def test_settings_reject_invalid_groups(monkeypatch: pytest.MonkeyPatch, groups: str) -> None:
    monkeypatch.setenv("SATTRACK_DATABASE_URL", DB_URL)
    monkeypatch.setenv("SATTRACK_INGEST_GROUPS", groups)
    with pytest.raises(ValidationError, match="ingest_groups"):
        Settings()


def test_settings_reject_non_https_celestrak_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SATTRACK_DATABASE_URL", DB_URL)
    monkeypatch.setenv("SATTRACK_CELESTRAK_BASE_URL", "http://celestrak.org")
    with pytest.raises(ValidationError, match="must use https"):
        Settings()


def test_settings_reject_non_postgres_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SATTRACK_DATABASE_URL", "sqlite:///local.db")
    with pytest.raises(ValidationError, match="database_url"):
        Settings()


def test_enrich_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SATTRACK_DATABASE_URL", DB_URL)
    settings = Settings()

    assert settings.enrich_enabled is True
    assert settings.enrich_contact is None
    assert settings.enrich_interval_hours == 168


@pytest.mark.parametrize(
    "contact", ["ops@example.test", "https://example.test/contact", "  https://example.test  "]
)
def test_enrich_contact_accepts_email_or_https_url(
    monkeypatch: pytest.MonkeyPatch, contact: str
) -> None:
    monkeypatch.setenv("SATTRACK_DATABASE_URL", DB_URL)
    monkeypatch.setenv("SATTRACK_ENRICH_CONTACT", contact)

    assert Settings().enrich_contact == contact.strip()


@pytest.mark.parametrize(
    "contact", ["not an address", "http://example.test", "a@b.test\r\nX-Injected: 1", "a@b"]
)
def test_enrich_contact_rejects_anything_else(
    monkeypatch: pytest.MonkeyPatch, contact: str
) -> None:
    monkeypatch.setenv("SATTRACK_DATABASE_URL", DB_URL)
    monkeypatch.setenv("SATTRACK_ENRICH_CONTACT", contact)
    with pytest.raises(ValidationError, match="enrich_contact"):
        Settings()
