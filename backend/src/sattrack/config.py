"""Central configuration: every setting is loaded and validated here, once, at startup.

Other modules receive a ``Settings`` instance; nothing else reads environment variables.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]

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
