"""Catalog business rules: orbital element sets, satellite metadata and orbit classification.

Plain data and functions only; no framework, database or network code.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import IntEnum, StrEnum
from typing import Any

MINUTES_PER_DAY = 1440.0

# Orbit regime thresholds, following the definitions Space-Track uses for its
# catalog filters. Mean motion is in revolutions per day.
LEO_MIN_MEAN_MOTION_REV_PER_DAY = 11.25
GEO_MIN_MEAN_MOTION_REV_PER_DAY = 0.99
GEO_MAX_MEAN_MOTION_REV_PER_DAY = 1.01
GEO_MAX_ECCENTRICITY = 0.01
HEO_MIN_ECCENTRICITY = 0.25


class OrbitClass(StrEnum):
    LEO = "LEO"
    MEO = "MEO"
    GEO = "GEO"
    HEO = "HEO"
    OTHER = "OTHER"


def classify_orbit(mean_motion_rev_per_day: float, eccentricity: float) -> OrbitClass:
    """Classify an orbit into a regime from its mean motion and eccentricity."""
    if eccentricity >= HEO_MIN_ECCENTRICITY:
        return OrbitClass.HEO
    if mean_motion_rev_per_day > LEO_MIN_MEAN_MOTION_REV_PER_DAY:
        return OrbitClass.LEO
    is_geo_period = (
        GEO_MIN_MEAN_MOTION_REV_PER_DAY
        <= mean_motion_rev_per_day
        <= GEO_MAX_MEAN_MOTION_REV_PER_DAY
    )
    if is_geo_period and eccentricity < GEO_MAX_ECCENTRICITY:
        return OrbitClass.GEO
    if mean_motion_rev_per_day > GEO_MAX_MEAN_MOTION_REV_PER_DAY:
        return OrbitClass.MEO
    return OrbitClass.OTHER


def period_minutes(mean_motion_rev_per_day: float) -> float:
    """Orbital period in minutes for a mean motion in revolutions per day."""
    if mean_motion_rev_per_day <= 0:
        raise ValueError(f"mean motion must be positive, got {mean_motion_rev_per_day}")
    return MINUTES_PER_DAY / mean_motion_rev_per_day


@dataclass(frozen=True, slots=True)
class OrbitalElements:
    """One general-perturbations element set (CCSDS OMM mean elements for SGP4)."""

    norad_id: int
    object_name: str
    object_id: str | None
    epoch: datetime
    mean_motion: float
    eccentricity: float
    inclination_deg: float
    raan_deg: float
    arg_of_pericenter_deg: float
    mean_anomaly_deg: float
    bstar: float
    mean_motion_dot: float
    mean_motion_ddot: float
    element_set_no: int | None
    rev_at_epoch: int | None
    classification_type: str
    ephemeris_type: int
    raw: dict[str, Any]

    @property
    def orbit_class(self) -> OrbitClass:
        return classify_orbit(self.mean_motion, self.eccentricity)


@dataclass(frozen=True, slots=True)
class SatcatRecord:
    """Catalog metadata for one object (CelesTrak SATCAT)."""

    norad_id: int
    object_name: str
    object_type: str | None
    owner: str | None
    launch_date: date | None


@dataclass(frozen=True, slots=True)
class SatelliteInfo:
    """What the application knows about one catalogued object."""

    norad_id: int
    name: str
    intl_designator: str | None
    object_type: str | None
    country: str | None
    launch_date: date | None
    orbit_class: OrbitClass | None


@dataclass(frozen=True, slots=True)
class GroupInfo:
    slug: str
    name: str
    satellite_count: int


@dataclass(frozen=True, slots=True)
class SatelliteFilters:
    """Search criteria; ``None`` means "do not filter on this field"."""

    query: str | None = None
    group: str | None = None
    orbit_class: OrbitClass | None = None
    country: str | None = None
    launch_year: int | None = None


@dataclass(frozen=True, slots=True)
class SatelliteIdentity:
    """The identifiers other catalogues use to refer to an object."""

    norad_id: int
    intl_designator: str | None


# --- Descriptions and images from Wikimedia (written by the enrich module) -------------------


class AboutStatus(StrEnum):
    OK = "ok"
    # Nothing usable was found; retried on the next periodic refresh.
    NO_MATCH = "no_match"
    ERROR = "error"


class MatchMethod(StrEnum):
    NORAD = "norad"
    COSPAR = "cospar"


class AboutScope(StrEnum):
    # The text describes this object.
    OBJECT = "object"
    # The text describes the constellation or series the object belongs to.
    CONSTELLATION = "constellation"


class SummarySource(StrEnum):
    WIKIPEDIA = "wikipedia"
    WIKIDATA = "wikidata"


class ImageWidth(IntEnum):
    SMALL = 480
    LARGE = 960


@dataclass(frozen=True, slots=True)
class ImageCredit:
    """Who made an image and under which license; always shown with the image."""

    source_file: str
    source_url: str
    artist: str
    license_short: str
    license_url: str | None
    attribution_required: bool
    alt_text: str


@dataclass(frozen=True, slots=True)
class ImageVariant:
    data: bytes
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class SatelliteImage:
    """An object's image in the two stored widths, with its credit."""

    small: ImageVariant
    large: ImageVariant
    mime: str
    sha256: str
    credit: ImageCredit


@dataclass(frozen=True, slots=True)
class SatelliteAbout:
    """What Wikimedia says about an object. Content fields are empty unless status is OK."""

    norad_id: int
    status: AboutStatus
    fetched_at: datetime
    wikidata_qid: str | None = None
    match_method: MatchMethod | None = None
    scope: AboutScope | None = None
    title: str | None = None
    summary: str | None = None
    summary_source: SummarySource | None = None
    summary_url: str | None = None
    summary_revision_at: datetime | None = None
    categories: tuple[str, ...] = ()
    operators: tuple[str, ...] = ()
    manufacturers: tuple[str, ...] = ()
    image: SatelliteImage | None = None


@dataclass(frozen=True, slots=True)
class ImageInfo:
    """Image metadata for the about response (no bytes)."""

    width_small: int
    height_small: int
    credit: ImageCredit


@dataclass(frozen=True, slots=True)
class AboutInfo:
    """A stored description, as served by the API."""

    about: SatelliteAbout
    image: ImageInfo | None


@dataclass(frozen=True, slots=True)
class ImageFile:
    data: bytes
    mime: str
    sha256: str


# Display names for the CelesTrak groups we know; unknown slugs fall back to the slug.
GROUP_DISPLAY_NAMES = {
    "stations": "Space stations",
    "visual": "Brightest (visual)",
    "gps-ops": "GPS operational",
    "galileo": "Galileo",
    "weather": "Weather",
    "science": "Science",
    "starlink": "Starlink",
    "active": "All active",
    # Synthetic groups loaded by scripts/seed_dev_data.py for local development.
    "demo-leo": "Demo LEO (synthetic)",
    "demo-meo": "Demo MEO (synthetic)",
    "demo-geo": "Demo GEO (synthetic)",
}


def group_display_name(slug: str) -> str:
    return GROUP_DISPLAY_NAMES.get(slug, slug)
