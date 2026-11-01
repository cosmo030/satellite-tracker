"""Response types of the catalog API. Built explicitly from domain objects."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from sattrack.catalog.domain import (
    AboutInfo,
    AboutScope,
    GroupInfo,
    ImageInfo,
    ImageWidth,
    OrbitalElements,
    OrbitClass,
    SatelliteInfo,
    SummarySource,
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
    has_about: bool = Field(description="A description is available at .../about")
    has_image: bool = Field(description="An image is available at .../image")


# Licenses of the description text, by source (Wikipedia text is CC BY-SA 4.0, Wikidata CC0).
SUMMARY_LICENSES = {SummarySource.WIKIPEDIA: "CC BY-SA 4.0", SummarySource.WIKIDATA: "CC0"}


class AboutImageOut(BaseModel):
    """A Wikimedia Commons image, served from this API; always shown with its credit."""

    url_480: str = Field(examples=["/api/v1/satellites/25544/image?w=480"])
    url_960: str = Field(examples=["/api/v1/satellites/25544/image?w=960"])
    width_480: int = Field(examples=[480])
    height_480: int = Field(examples=[320])
    artist: str = Field(examples=["NASA"])
    license_short: str = Field(examples=["Public domain"])
    license_url: str | None
    source_url: str = Field(description="Wikimedia Commons file page")
    alt_text: str = Field(description="Empty when the file has no description")


class AboutOut(BaseModel):
    """What Wikimedia says about an object, with the attribution its licenses require."""

    norad_id: int = Field(examples=[25544])
    scope: AboutScope = Field(
        description="object: the text describes this object; constellation: its constellation"
    )
    title: str | None = Field(examples=["International Space Station"])
    summary: str | None
    summary_source: SummarySource | None
    summary_url: str | None
    summary_license: str | None = Field(examples=["CC BY-SA 4.0"])
    categories: list[str] = Field(examples=[["space_station", "crewed"]])
    operators: list[str] = Field(examples=[["NASA", "Roscosmos"]])
    manufacturers: list[str]
    image: AboutImageOut | None
    fetched_at: datetime

    @classmethod
    def from_domain(cls, info: AboutInfo, image_path: str) -> AboutOut:
        about = info.about
        return cls(
            norad_id=about.norad_id,
            scope=about.scope or AboutScope.OBJECT,
            title=about.title,
            summary=about.summary,
            summary_source=about.summary_source,
            summary_url=about.summary_url,
            summary_license=SUMMARY_LICENSES[about.summary_source]
            if about.summary_source
            else None,
            categories=list(about.categories),
            operators=list(about.operators),
            manufacturers=list(about.manufacturers),
            image=_image_out(info.image, image_path) if info.image else None,
            fetched_at=about.fetched_at,
        )


def _image_out(image: ImageInfo, image_path: str) -> AboutImageOut:
    credit = image.credit
    return AboutImageOut(
        url_480=f"{image_path}?w={ImageWidth.SMALL.value}",
        url_960=f"{image_path}?w={ImageWidth.LARGE.value}",
        width_480=image.width_small,
        height_480=image.height_small,
        artist=credit.artist,
        license_short=credit.license_short,
        license_url=credit.license_url,
        source_url=credit.source_url,
        alt_text=credit.alt_text,
    )
