"""ORM mappings for the catalog tables. Only the catalog repository uses these."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Double,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sattrack.shared.db import Base


class SatelliteRow(Base):
    __tablename__ = "satellites"

    # BIGINT: catalog numbers passed 99999 in 2026 and the OMM format allows 9 digits.
    norad_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(100))
    intl_designator: Mapped[str | None] = mapped_column(String(20))
    object_type: Mapped[str | None] = mapped_column(String(10))
    country: Mapped[str | None] = mapped_column(String(10), index=True)
    launch_date: Mapped[date | None] = mapped_column(Date, index=True)
    orbit_class: Mapped[str | None] = mapped_column(String(10), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OrbitalElementsRow(Base):
    __tablename__ = "orbital_elements"
    __table_args__ = (
        UniqueConstraint("norad_id", "epoch", name="uq_orbital_elements_norad_epoch"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Lookups by norad_id use the (norad_id, epoch) unique constraint's index.
    norad_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("satellites.norad_id", ondelete="CASCADE")
    )
    epoch: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    mean_motion: Mapped[float] = mapped_column(Double)
    eccentricity: Mapped[float] = mapped_column(Double)
    inclination_deg: Mapped[float] = mapped_column(Double)
    raan_deg: Mapped[float] = mapped_column(Double)
    arg_of_pericenter_deg: Mapped[float] = mapped_column(Double)
    mean_anomaly_deg: Mapped[float] = mapped_column(Double)
    bstar: Mapped[float] = mapped_column(Double)
    mean_motion_dot: Mapped[float] = mapped_column(Double)
    mean_motion_ddot: Mapped[float] = mapped_column(Double)
    element_set_no: Mapped[int | None] = mapped_column(Integer)
    rev_at_epoch: Mapped[int | None] = mapped_column(Integer)
    classification_type: Mapped[str] = mapped_column(String(1))
    ephemeris_type: Mapped[int] = mapped_column(Integer)
    # The provider's record as received, so a format change never loses data.
    raw_omm: Mapped[dict[str, Any]] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GroupRow(Base):
    __tablename__ = "groups"

    slug: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))


class SatelliteGroupRow(Base):
    __tablename__ = "satellite_groups"

    group_slug: Mapped[str] = mapped_column(
        String(50), ForeignKey("groups.slug", ondelete="CASCADE"), primary_key=True
    )
    norad_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("satellites.norad_id", ondelete="CASCADE"), primary_key=True
    )
