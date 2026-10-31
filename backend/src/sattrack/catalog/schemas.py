"""Response types of the catalog API. Built explicitly from domain objects."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from sattrack.catalog.domain import (
    GroupInfo,
    OrbitalElements,
    OrbitClass,
    SatelliteInfo,
    period_minutes,
)


class GroupOut(BaseModel):
    slug: str = Field(examples=["stations"])
    name: str = Field(examples=["Space stations"])
    satellite_count: int = Field(examples=[12])

    @classmethod
    def from_domain(cls, group: GroupInfo) -> GroupOut:
        return cls(slug=group.slug, name=group.name, satellite_count=group.satellite_count)


class SatelliteOut(BaseModel):
    norad_id: int = Field(examples=[25544])
    name: str = Field(examples=["ISS (ZARYA)"])
    intl_designator: str | None = Field(examples=["1998-067A"])
    object_type: str | None = Field(description="PAY, R/B, DEB or UNK", examples=["PAY"])
    country: str | None = Field(description="CelesTrak owner code", examples=["ISS"])
    launch_date: date | None = Field(examples=["1998-11-20"])
    orbit_class: OrbitClass | None

    @classmethod
    def from_domain(cls, satellite: SatelliteInfo) -> SatelliteOut:
        return cls(
            norad_id=satellite.norad_id,
            name=satellite.name,
            intl_designator=satellite.intl_designator,
            object_type=satellite.object_type,
            country=satellite.country,
            launch_date=satellite.launch_date,
            orbit_class=satellite.orbit_class,
        )


class SatellitePageOut(BaseModel):
    items: list[SatelliteOut]
    total: int
    limit: int
    offset: int


class ElementSetOut(BaseModel):
    """Mean orbital elements for SGP4 propagation, in CCSDS OMM units."""

    norad_id: int = Field(examples=[25544])
    object_name: str = Field(examples=["ISS (ZARYA)"])
    object_id: str | None = Field(examples=["1998-067A"])
    epoch: datetime = Field(description="UTC epoch of the element set")
    mean_motion: float = Field(description="Revolutions per day", examples=[15.5])
    eccentricity: float = Field(examples=[0.0004])
    inclination_deg: float = Field(examples=[51.64])
    raan_deg: float = Field(description="Right ascension of the ascending node, degrees")
    arg_of_pericenter_deg: float
    mean_anomaly_deg: float
    bstar: float = Field(description="Drag term, 1/earth radii")
    mean_motion_dot: float
    mean_motion_ddot: float
    element_set_no: int | None
    rev_at_epoch: int | None
    classification_type: str = Field(examples=["U"])
    ephemeris_type: int = Field(examples=[0])
    period_minutes: float = Field(examples=[92.9])
    orbit_class: OrbitClass

    @classmethod
    def from_domain(cls, e: OrbitalElements) -> ElementSetOut:
        return cls(
            norad_id=e.norad_id,
            object_name=e.object_name,
            object_id=e.object_id,
            epoch=e.epoch,
            mean_motion=e.mean_motion,
            eccentricity=e.eccentricity,
            inclination_deg=e.inclination_deg,
            raan_deg=e.raan_deg,
            arg_of_pericenter_deg=e.arg_of_pericenter_deg,
            mean_anomaly_deg=e.mean_anomaly_deg,
            bstar=e.bstar,
            mean_motion_dot=e.mean_motion_dot,
            mean_motion_ddot=e.mean_motion_ddot,
            element_set_no=e.element_set_no,
            rev_at_epoch=e.rev_at_epoch,
            classification_type=e.classification_type,
            ephemeris_type=e.ephemeris_type,
            period_minutes=period_minutes(e.mean_motion),
            orbit_class=e.orbit_class,
        )


class SatelliteDetailOut(BaseModel):
    satellite: SatelliteOut
    latest_elements: ElementSetOut | None
