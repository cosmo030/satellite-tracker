"""Integration test setup: a real PostgreSQL database migrated with Alembic.

Set SATTRACK_TEST_DATABASE_URL to a disposable database. Tables are emptied after each test.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from sattrack.config import Settings
from sattrack.ingest import IngestService
from sattrack.main import create_app
from sattrack.shared.db import create_db_engine, create_session_factory

from ..conftest import FakeCatalogSource, MutableClock

BACKEND_DIR = Path(__file__).resolve().parents[2]
TEST_DATABASE_URL = os.environ.get("SATTRACK_TEST_DATABASE_URL")
TABLES = (
    "satellite_image",
    "satellite_about",
    "satellite_groups",
    "orbital_elements",
    "satellites",
    "groups",
    "fetch_log",
)

pytestmark = pytest.mark.integration

if not TEST_DATABASE_URL:
    pytest.skip(
        "SATTRACK_TEST_DATABASE_URL is not set; integration tests need PostgreSQL",
        allow_module_level=True,
    )


def _alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["database_url"] = database_url
    return config


@pytest.fixture(scope="session")
def database_url() -> str:
    assert TEST_DATABASE_URL is not None
    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
def engine(database_url: str) -> Iterator[Engine]:
    config = _alembic_config(database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = create_db_engine(database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> Iterator[sessionmaker[Session]]:
    yield create_session_factory(engine)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))


@pytest.fixture
def ingest_service(
    session_factory: sessionmaker[Session], fake_source: FakeCatalogSource, clock: MutableClock
) -> IngestService:
    return IngestService(
        source=fake_source,
        session_factory=session_factory,
        groups=("stations", "gps-ops"),
        clock=clock,
    )


@pytest.fixture
def api_client(
    database_url: str, session_factory: sessionmaker[Session], clock: MutableClock
) -> Iterator[TestClient]:
    settings = Settings(database_url=database_url)
    app = create_app(settings, clock=clock)
    app.state.session_factory = session_factory
    with TestClient(app) as client:
        yield client
