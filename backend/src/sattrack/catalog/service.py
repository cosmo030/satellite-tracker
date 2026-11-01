"""Catalog use cases served by the API: groups, search, satellite details and element sets."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from sattrack.catalog.domain import (
    AboutInfo,
    GroupInfo,
    ImageFile,
    ImageWidth,
    OrbitalElements,
    SatelliteFilters,
    SatelliteInfo,
)
from sattrack.catalog.repository import CatalogRepository


class GroupNotFoundError(LookupError):
    def __init__(self, group: str) -> None:
        super().__init__(f"Unknown group {group!r}")
        self.group = group


class SatelliteNotFoundError(LookupError):
    def __init__(self, norad_id: int) -> None:
        super().__init__(f"No satellite with NORAD ID {norad_id}")
        self.norad_id = norad_id


@dataclass(frozen=True, slots=True)
class SatellitePage:
    items: list[SatelliteInfo]
    total: int
    limit: int
    offset: int


class AboutNotFoundError(LookupError):
    def __init__(self, norad_id: int) -> None:
        super().__init__(f"No description for NORAD ID {norad_id}")
        self.norad_id = norad_id


class ImageNotFoundError(LookupError):
    def __init__(self, norad_id: int) -> None:
        super().__init__(f"No image for NORAD ID {norad_id}")
        self.norad_id = norad_id


@dataclass(frozen=True, slots=True)
class SatelliteDetail:
    satellite: SatelliteInfo
    latest_elements: OrbitalElements | None
    has_about: bool
    has_image: bool


class CatalogService:
    def __init__(self, repository: CatalogRepository) -> None:
        self._repository = repository

    def list_groups(self) -> list[GroupInfo]:
        return self._repository.list_groups()

    def search_satellites(
        self, filters: SatelliteFilters, limit: int, offset: int
    ) -> SatellitePage:
        items, total = self._repository.search_satellites(filters, limit, offset)
        return SatellitePage(items=items, total=total, limit=limit, offset=offset)

    def get_satellite(self, norad_id: int) -> SatelliteDetail:
        satellite = self._repository.get_satellite(norad_id)
        if satellite is None:
            raise SatelliteNotFoundError(norad_id)
        has_about, has_image = self._repository.about_flags(norad_id)
        return SatelliteDetail(
            satellite=satellite,
            latest_elements=self._repository.latest_elements(norad_id),
            has_about=has_about,
            has_image=has_image,
        )

    def get_about(self, norad_id: int) -> AboutInfo:
        about = self._repository.get_about(norad_id)
        if about is None:
            raise AboutNotFoundError(norad_id)
        return about

    def get_image(self, norad_id: int, width: ImageWidth) -> ImageFile:
        image = self._repository.get_image(norad_id, width)
        if image is None:
            raise ImageNotFoundError(norad_id)
        return image

    def group_elements_etag(self, group: str, limit: int, offset: int) -> str:
        """Entity tag for a page of a group's element sets.

        Cheap to compute, so clients that already hold the current data get a 304 without
        the element sets being loaded.
        """
        if not self._repository.group_exists(group):
            raise GroupNotFoundError(group)
        version = self._repository.group_version(group)
        fetched = version.last_fetched_at.isoformat() if version.last_fetched_at else "never"
        fingerprint = f"{group}|{version.satellite_count}|{fetched}|{limit}|{offset}"
        return hashlib.sha256(fingerprint.encode()).hexdigest()[:32]

    def group_elements(self, group: str, limit: int, offset: int) -> list[OrbitalElements]:
        if not self._repository.group_exists(group):
            raise GroupNotFoundError(group)
        return self._repository.latest_elements_for_group(group, limit, offset)
