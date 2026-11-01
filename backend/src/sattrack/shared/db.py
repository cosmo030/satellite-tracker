"""Database engine, session factory and the declarative base shared by all ORM models."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Deterministic constraint names keep Alembic migrations reviewable and reversible.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for every table; one metadata object for migrations."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def create_db_engine(database_url: str) -> Engine:
    """Create the SQLAlchemy engine. ``pool_pre_ping`` survives database restarts.

    Sessions use UTC so timestamps come back in UTC whatever the server's time zone is.
    """
    return create_engine(
        database_url, pool_pre_ping=True, connect_args={"options": "-c timezone=UTC"}
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def transaction(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Open a session for one business operation: commit on success, roll back on error."""
    with session_factory() as session, session.begin():
        yield session
