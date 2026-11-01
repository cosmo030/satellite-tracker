"""Central configuration: every setting is loaded and validated here, once, at startup.

Other modules receive a ``Settings`` instance; nothing else reads environment variables.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,24}")
_HTTPS_URL = re.compile(r"https://[A-Za-z0-9.-]{1,190}(?:/[A-Za-z0-9._~%/-]{0,200})?")

# Groups ingested when SATTRACK_INGEST_GROUPS is not set. Kept small on purpose:
# CelesTrak enforces limits on the large "active" and "starlink" sets.
DEFAULT_INGEST_GROUPS = ("stations", "visual", "gps-ops", "galileo", "weather", "science")


class Settings(BaseSettings):
    """Application settings, read from ``SATTRACK_*`` environment variables.

    The Makefile and docker-compose load the repository's ``.env`` file into the environment.
    """

    model_config = SettingsConfigDict(env_prefix="SATTRACK_", extra="ignore")

    database_url: PostgresDsn = Field(
        description="SQLAlchemy URL of the PostgreSQL database (postgresql+psycopg://...).",
    )
    log_level: LogLevel = "INFO"
    celestrak_base_url: str = "https://celestrak.org"
    http_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    ingest_groups: Annotated[tuple[str, ...], NoDecode] = DEFAULT_INGEST_GROUPS
    cors_allowed_origins: Annotated[tuple[str, ...], NoDecode] = ()
    # Descriptions and images from Wikimedia (sattrack.enrich). The contact is checked when the
    # enrich job starts, not here, so the API runs without it.
    enrich_enabled: bool = True
    enrich_contact: str | None = Field(
        default=None,
        description="Email or https URL put in the User-Agent of every Wikimedia request.",
    )
    enrich_interval_hours: int = Field(default=168, ge=24, le=24 * 90)

    @field_validator("enrich_contact", mode="before")
    @classmethod
    def _blank_contact_is_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("enrich_contact")
    @classmethod
    def _validate_contact(cls, contact: str | None) -> str | None:
        if contact is None:
            return None
        contact = contact.strip()
        # Goes into an HTTP header: allow only an email address or an https URL.
        if not (_EMAIL.fullmatch(contact) or _HTTPS_URL.fullmatch(contact)):
            raise ValueError("must be an email address or an https:// URL")
        return contact

    @field_validator("ingest_groups", "cors_allowed_origins", mode="before")
    @classmethod
    def _split_comma_separated(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(item.strip() for item in value.split(",") if item.strip())
        return value

    @field_validator("ingest_groups")
    @classmethod
    def _validate_groups(cls, groups: tuple[str, ...]) -> tuple[str, ...]:
        if not groups:
            raise ValueError("at least one group is required")
        for group in groups:
            if not group.replace("-", "").isalnum():
                raise ValueError(f"invalid group name {group!r}: use CelesTrak group slugs")
        return groups

    @field_validator("celestrak_base_url")
    @classmethod
    def _require_https(cls, url: str) -> str:
        if not url.startswith("https://"):
            raise ValueError("must use https://")
        return url.rstrip("/")


def load_settings() -> Settings:
    """Load settings from the environment; raises ``pydantic.ValidationError`` when invalid."""
    return Settings()
