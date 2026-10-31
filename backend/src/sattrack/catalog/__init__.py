"""Catalog module: satellites, orbital element sets and groups.

Public interface for other modules: the domain types, ``CatalogRepository`` (used by the
ingest module to write data) and the HTTP ``router``.
"""

from sattrack.catalog.api import router
from sattrack.catalog.domain import (
    OrbitalElements,
    OrbitClass,
    SatcatRecord,
    classify_orbit,
    group_display_name,
)
from sattrack.catalog.repository import CatalogRepository

__all__ = [
    "CatalogRepository",
    "OrbitClass",
    "OrbitalElements",
    "SatcatRecord",
    "classify_orbit",
    "group_display_name",
    "router",
]
