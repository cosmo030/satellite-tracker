"""Catalog module: satellites, orbital element sets, groups, and their descriptions and images.

Public interface for other modules: the domain types, ``CatalogRepository`` (used by the
ingest and enrich modules to write data) and the HTTP ``router``.
"""

from sattrack.catalog.api import router
from sattrack.catalog.domain import (
    AboutScope,
    AboutStatus,
    ImageCredit,
    ImageVariant,
    ImageWidth,
    MatchMethod,
    OrbitalElements,
    OrbitClass,
    SatcatRecord,
    SatelliteAbout,
    SatelliteIdentity,
    SatelliteImage,
    SummarySource,
    classify_orbit,
    group_display_name,
)
from sattrack.catalog.repository import CatalogRepository

__all__ = [
    "AboutScope",
    "AboutStatus",
    "CatalogRepository",
    "ImageCredit",
    "ImageVariant",
    "ImageWidth",
    "MatchMethod",
    "OrbitClass",
    "OrbitalElements",
    "SatcatRecord",
    "SatelliteAbout",
    "SatelliteIdentity",
    "SatelliteImage",
    "SummarySource",
    "classify_orbit",
    "group_display_name",
    "router",
]
