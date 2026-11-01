"""Data access for the catalog tables. All catalog SQL lives here."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Select, delete, extract, func, or_, select, update
from sqlalchemy.dialects.postgresql import distinct_on, insert
from sqlalchemy.orm import Session

from sattrack.catalog.domain import (
    GroupInfo,
    OrbitalElements,
    OrbitClass,
    SatcatRecord,
    SatelliteFilters,
    SatelliteInfo,
)
from sattrack.catalog.models import GroupRow, OrbitalElementsRow, SatelliteGroupRow, SatelliteRow

# PostgreSQL limits a statement to 65535 bind parameters; batches stay well below it.
_INSERT_BATCH_SIZE = 1000


@dataclass(frozen=True, slots=True)
class GroupVersion:
    """Changes whenever the element sets served for a group change; used for HTTP ETags."""

    satellite_count: int
    last_fetched_at: datetime | None


class CatalogRepository:
    """Reads and writes satellites, element sets and group membership."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Reads -------------------------------------------------------------------------------

    def list_groups(self) -> list[GroupInfo]:
        member_count = func.count(SatelliteGroupRow.norad_id)
        stmt = (
            select(GroupRow.slug, GroupRow.name, member_count)
            .outerjoin(SatelliteGroupRow, SatelliteGroupRow.group_slug == GroupRow.slug)
            .group_by(GroupRow.slug, GroupRow.name)
            .order_by(GroupRow.slug)
        )
        return [
            GroupInfo(slug=slug, name=name, satellite_count=count)
            for slug, name, count in self._session.execute(stmt)
        ]

    def group_exists(self, slug: str) -> bool:
        return self._session.get(GroupRow, slug) is not None

    def search_satellites(
        self, filters: SatelliteFilters, limit: int, offset: int
    ) -> tuple[list[SatelliteInfo], int]:
        base = self._apply_filters(select(SatelliteRow), filters)
        total = self._session.scalar(select(func.count()).select_from(base.subquery())) or 0
        rows = self._session.scalars(
            base.order_by(SatelliteRow.name, SatelliteRow.norad_id).limit(limit).offset(offset)
        )
        return [_to_satellite_info(row) for row in rows], total

    def get_satellite(self, norad_id: int) -> SatelliteInfo | None:
        row = self._session.get(SatelliteRow, norad_id)
        return _to_satellite_info(row) if row else None

    def latest_elements(self, norad_id: int) -> OrbitalElements | None:
        stmt = (
            select(*OrbitalElementsRow.__table__.columns, SatelliteRow.name)
            .join(SatelliteRow, SatelliteRow.norad_id == OrbitalElementsRow.norad_id)
            .where(OrbitalElementsRow.norad_id == norad_id)
            .order_by(OrbitalElementsRow.epoch.desc())
            .limit(1)
        )
        row = self._session.execute(stmt).mappings().first()
        return _mapping_to_elements(row) if row else None

    def latest_elements_for_group(
        self, group: str, limit: int, offset: int
    ) -> list[OrbitalElements]:
        latest = (
            select(OrbitalElementsRow)
            .join(SatelliteGroupRow, SatelliteGroupRow.norad_id == OrbitalElementsRow.norad_id)
            .where(SatelliteGroupRow.group_slug == group)
            .ext(distinct_on(OrbitalElementsRow.norad_id))
            .order_by(OrbitalElementsRow.norad_id, OrbitalElementsRow.epoch.desc())
            .subquery()
        )
        stmt = (
            select(latest, SatelliteRow.name)
            .join(SatelliteRow, SatelliteRow.norad_id == latest.c.norad_id)
            .order_by(latest.c.norad_id)
            .limit(limit)
            .offset(offset)
        )
        return [_mapping_to_elements(row) for row in self._session.execute(stmt).mappings()]

    def group_version(self, group: str) -> GroupVersion:
        stmt = (
            select(
                func.count(func.distinct(SatelliteGroupRow.norad_id)),
                func.max(OrbitalElementsRow.fetched_at),
            )
            .select_from(SatelliteGroupRow)
            .outerjoin(
                OrbitalElementsRow, OrbitalElementsRow.norad_id == SatelliteGroupRow.norad_id
            )
            .where(SatelliteGroupRow.group_slug == group)
        )
        count, last_fetched = self._session.execute(stmt).one()
        return GroupVersion(satellite_count=count, last_fetched_at=last_fetched)

    # --- Writes (used by the ingest module) ----------------------------------------------------

    def upsert_group(self, slug: str, name: str) -> None:
        stmt = insert(GroupRow).values(slug=slug, name=name)
        self._session.execute(
            stmt.on_conflict_do_update(index_elements=[GroupRow.slug], set_={"name": name})
        )

    def upsert_satellites_from_elements(
        self, element_sets: Sequence[OrbitalElements], now: datetime
    ) -> None:
        """Create or update the satellite rows named by these element sets."""
        rows = [
            {
                "norad_id": e.norad_id,
                "name": e.object_name,
                "intl_designator": e.object_id,
                "orbit_class": e.orbit_class.value,
                "updated_at": now,
            }
            for e in _latest_per_satellite(element_sets)
        ]
        for batch in _batches(rows):
            stmt = insert(SatelliteRow).values(batch)
            self._session.execute(
                stmt.on_conflict_do_update(
                    index_elements=[SatelliteRow.norad_id],
                    set_={
                        "name": stmt.excluded.name,
                        "intl_designator": stmt.excluded.intl_designator,
                        "orbit_class": stmt.excluded.orbit_class,
                        "updated_at": stmt.excluded.updated_at,
                    },
                )
            )

    def add_elements(self, element_sets: Sequence[OrbitalElements], fetched_at: datetime) -> int:
        """Store element sets; an epoch already stored for a satellite is skipped.

        Returns the number of new element sets.
        """
        rows = [_elements_to_row_values(e, fetched_at) for e in element_sets]
        inserted = 0
        for batch in _batches(rows):
            stmt = (
                insert(OrbitalElementsRow)
                .values(batch)
                .on_conflict_do_nothing(constraint="uq_orbital_elements_norad_epoch")
                .returning(OrbitalElementsRow.id)
            )
            inserted += len(self._session.execute(stmt).all())
        return inserted

    def replace_group_members(self, slug: str, norad_ids: Iterable[int]) -> None:
        self._session.execute(delete(SatelliteGroupRow).where(SatelliteGroupRow.group_slug == slug))
        rows = [{"group_slug": slug, "norad_id": norad_id} for norad_id in sorted(set(norad_ids))]
        for batch in _batches(rows):
            self._session.execute(insert(SatelliteGroupRow).values(batch).on_conflict_do_nothing())

    def apply_satcat(self, records: Sequence[SatcatRecord], now: datetime) -> int:
        """Update metadata of satellites we already know. Returns the number updated."""
        updated = 0
        for record in records:
            result = self._session.execute(
                update(SatelliteRow)
                .where(SatelliteRow.norad_id == record.norad_id)
                .values(
                    object_type=record.object_type,
                    country=record.owner,
                    launch_date=record.launch_date,
                    updated_at=now,
                )
            )
            updated += result.rowcount  # type: ignore[attr-defined]  # CursorResult for UPDATE
        return updated

    # --- Helpers -------------------------------------------------------------------------------

    @staticmethod
    def _apply_filters(
        stmt: Select[SatelliteRow], filters: SatelliteFilters
    ) -> Select[SatelliteRow]:
        if filters.query:
            stmt = stmt.where(_matches_query(filters.query))
        if filters.group:
            stmt = stmt.join(
                SatelliteGroupRow, SatelliteGroupRow.norad_id == SatelliteRow.norad_id
            ).where(SatelliteGroupRow.group_slug == filters.group)
        if filters.orbit_class:
            stmt = stmt.where(SatelliteRow.orbit_class == filters.orbit_class.value)
        if filters.country:
            stmt = stmt.where(SatelliteRow.country == filters.country)
        if filters.launch_year:
            stmt = stmt.where(extract("year", SatelliteRow.launch_date) == filters.launch_year)
        return stmt


def _matches_query(query: str) -> Any:
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    name_match = SatelliteRow.name.ilike(f"%{escaped}%", escape="\\")
    if query.isdigit():
        return or_(name_match, SatelliteRow.norad_id == int(query))
    return name_match


def _latest_per_satellite(element_sets: Sequence[OrbitalElements]) -> list[OrbitalElements]:
    latest: dict[int, OrbitalElements] = {}
    for element_set in element_sets:
        current = latest.get(element_set.norad_id)
        if current is None or element_set.epoch > current.epoch:
            latest[element_set.norad_id] = element_set
    return list(latest.values())


def _batches(rows: list[dict[str, Any]]) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(rows), _INSERT_BATCH_SIZE):
        yield rows[start : start + _INSERT_BATCH_SIZE]


def _elements_to_row_values(e: OrbitalElements, fetched_at: datetime) -> dict[str, Any]:
    return {
        "norad_id": e.norad_id,
        "epoch": e.epoch,
        "mean_motion": e.mean_motion,
        "eccentricity": e.eccentricity,
        "inclination_deg": e.inclination_deg,
        "raan_deg": e.raan_deg,
        "arg_of_pericenter_deg": e.arg_of_pericenter_deg,
        "mean_anomaly_deg": e.mean_anomaly_deg,
        "bstar": e.bstar,
        "mean_motion_dot": e.mean_motion_dot,
        "mean_motion_ddot": e.mean_motion_ddot,
        "element_set_no": e.element_set_no,
        "rev_at_epoch": e.rev_at_epoch,
        "classification_type": e.classification_type,
        "ephemeris_type": e.ephemeris_type,
        "raw_omm": e.raw,
        "fetched_at": fetched_at,
    }


def _to_satellite_info(row: SatelliteRow) -> SatelliteInfo:
    return SatelliteInfo(
        norad_id=row.norad_id,
        name=row.name,
        intl_designator=row.intl_designator,
        object_type=row.object_type,
        country=row.country,
        launch_date=row.launch_date,
        orbit_class=OrbitClass(row.orbit_class) if row.orbit_class else None,
    )


def _mapping_to_elements(row: Any) -> OrbitalElements:
    """Build an element set from a result row holding the element columns plus ``name``."""
    raw: dict[str, Any] = row["raw_omm"]
    return OrbitalElements(
        norad_id=row["norad_id"],
        object_name=row["name"],
        object_id=raw.get("OBJECT_ID"),
        epoch=row["epoch"],
        mean_motion=row["mean_motion"],
        eccentricity=row["eccentricity"],
        inclination_deg=row["inclination_deg"],
        raan_deg=row["raan_deg"],
        arg_of_pericenter_deg=row["arg_of_pericenter_deg"],
        mean_anomaly_deg=row["mean_anomaly_deg"],
        bstar=row["bstar"],
        mean_motion_dot=row["mean_motion_dot"],
        mean_motion_ddot=row["mean_motion_ddot"],
        element_set_no=row["element_set_no"],
        rev_at_epoch=row["rev_at_epoch"],
        classification_type=row["classification_type"],
        ephemeris_type=row["ephemeris_type"],
        raw=raw,
    )
