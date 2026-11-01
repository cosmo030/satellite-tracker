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
    AboutInfo,
    AboutScope,
    AboutStatus,
    GroupInfo,
    ImageCredit,
    ImageFile,
    ImageInfo,
    ImageWidth,
    MatchMethod,
    OrbitalElements,
    OrbitClass,
    SatcatRecord,
    SatelliteAbout,
    SatelliteFilters,
    SatelliteIdentity,
    SatelliteImage,
    SatelliteInfo,
    SummarySource,
)
from sattrack.catalog.models import (
    GroupRow,
    OrbitalElementsRow,
    SatelliteAboutRow,
    SatelliteGroupRow,
    SatelliteImageRow,
    SatelliteRow,
)

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

    # --- Descriptions and images (written by the enrich module) -------------------------------

    def enrichment_targets(self, refresh_before: datetime | None) -> list[SatelliteIdentity]:
        """Objects to fetch descriptions for, by NORAD ID.

        With ``refresh_before``: objects never fetched, whose last fetch failed, or fetched
        before that time. Without it: every object.
        """
        stmt = (
            select(SatelliteRow.norad_id, SatelliteRow.intl_designator)
            .outerjoin(SatelliteAboutRow, SatelliteAboutRow.norad_id == SatelliteRow.norad_id)
            .order_by(SatelliteRow.norad_id)
        )
        if refresh_before is not None:
            stmt = stmt.where(
                or_(
                    SatelliteAboutRow.norad_id.is_(None),
                    SatelliteAboutRow.status == AboutStatus.ERROR.value,
                    SatelliteAboutRow.fetched_at < refresh_before,
                )
            )
        return [
            SatelliteIdentity(norad_id=norad_id, intl_designator=designator)
            for norad_id, designator in self._session.execute(stmt)
        ]

    def save_about(self, about: SatelliteAbout) -> None:
        """Replace an object's description and image with the result of a completed fetch."""
        values = _about_row_values(about)
        stmt = insert(SatelliteAboutRow).values(values)
        self._session.execute(
            stmt.on_conflict_do_update(
                index_elements=[SatelliteAboutRow.norad_id],
                set_={name: stmt.excluded[name] for name in values if name != "norad_id"},
            )
        )
        self._session.execute(
            delete(SatelliteImageRow).where(SatelliteImageRow.norad_id == about.norad_id)
        )
        if about.image is not None:
            self._session.execute(
                insert(SatelliteImageRow).values(
                    _image_row_values(about.norad_id, about.image, about.fetched_at)
                )
            )

    def get_about(self, norad_id: int) -> AboutInfo | None:
        """The stored description of an object, if one was found (status OK)."""
        about_row = self._session.get(SatelliteAboutRow, norad_id)
        if about_row is None or about_row.status != AboutStatus.OK.value:
            return None
        image_stmt = select(
            SatelliteImageRow.width_480,
            SatelliteImageRow.height_480,
            *_IMAGE_CREDIT_COLUMNS,
        ).where(SatelliteImageRow.norad_id == norad_id)
        image_row = self._session.execute(image_stmt).mappings().first()
        image = (
            ImageInfo(
                width_small=image_row["width_480"],
                height_small=image_row["height_480"],
                credit=_to_image_credit(image_row),
            )
            if image_row
            else None
        )
        return AboutInfo(about=_to_about(about_row), image=image)

    def get_image(self, norad_id: int, width: ImageWidth) -> ImageFile | None:
        column = (
            SatelliteImageRow.image_480
            if width is ImageWidth.SMALL
            else SatelliteImageRow.image_960
        )
        stmt = select(column, SatelliteImageRow.mime, SatelliteImageRow.sha256).where(
            SatelliteImageRow.norad_id == norad_id
        )
        row = self._session.execute(stmt).first()
        return ImageFile(data=row[0], mime=row[1], sha256=row[2]) if row else None

    def about_flags(self, norad_id: int) -> tuple[bool, bool]:
        """Whether an object has a description and whether it has an image."""
        has_about = select(SatelliteAboutRow.norad_id).where(
            SatelliteAboutRow.norad_id == norad_id,
            SatelliteAboutRow.status == AboutStatus.OK.value,
        )
        has_image = select(SatelliteImageRow.norad_id).where(SatelliteImageRow.norad_id == norad_id)
        about, image = self._session.execute(select(has_about.exists(), has_image.exists())).one()
        return bool(about), bool(image)

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


_IMAGE_CREDIT_COLUMNS = (
    SatelliteImageRow.source_file,
    SatelliteImageRow.source_url,
    SatelliteImageRow.artist,
    SatelliteImageRow.license_short,
    SatelliteImageRow.license_url,
    SatelliteImageRow.attribution_required,
    SatelliteImageRow.alt_text,
)


def _about_row_values(about: SatelliteAbout) -> dict[str, Any]:
    return {
        "norad_id": about.norad_id,
        "status": about.status.value,
        "wikidata_qid": about.wikidata_qid,
        "match_method": about.match_method.value if about.match_method else None,
        "scope": about.scope.value if about.scope else None,
        "title": about.title,
        "summary": about.summary,
        "summary_source": about.summary_source.value if about.summary_source else None,
        "summary_url": about.summary_url,
        "summary_revision_at": about.summary_revision_at,
        "categories": list(about.categories),
        "operators": list(about.operators),
        "manufacturers": list(about.manufacturers),
        "fetched_at": about.fetched_at,
    }


def _image_row_values(norad_id: int, image: SatelliteImage, fetched_at: datetime) -> dict[str, Any]:
    credit = image.credit
    return {
        "norad_id": norad_id,
        "image_480": image.small.data,
        "image_960": image.large.data,
        "mime": image.mime,
        "width_480": image.small.width,
        "height_480": image.small.height,
        "width_960": image.large.width,
        "height_960": image.large.height,
        "sha256": image.sha256,
        "source_file": credit.source_file,
        "source_url": credit.source_url,
        "artist": credit.artist,
        "license_short": credit.license_short,
        "license_url": credit.license_url,
        "attribution_required": credit.attribution_required,
        "alt_text": credit.alt_text,
        "fetched_at": fetched_at,
    }


def _to_about(row: SatelliteAboutRow) -> SatelliteAbout:
    return SatelliteAbout(
        norad_id=row.norad_id,
        status=AboutStatus(row.status),
        fetched_at=row.fetched_at,
        wikidata_qid=row.wikidata_qid,
        match_method=MatchMethod(row.match_method) if row.match_method else None,
        scope=AboutScope(row.scope) if row.scope else None,
        title=row.title,
        summary=row.summary,
        summary_source=SummarySource(row.summary_source) if row.summary_source else None,
        summary_url=row.summary_url,
        summary_revision_at=row.summary_revision_at,
        categories=tuple(row.categories),
        operators=tuple(row.operators),
        manufacturers=tuple(row.manufacturers),
    )


def _to_image_credit(row: Any) -> ImageCredit:
    return ImageCredit(
        source_file=row["source_file"],
        source_url=row["source_url"],
        artist=row["artist"],
        license_short=row["license_short"],
        license_url=row["license_url"],
        attribution_required=row["attribution_required"],
        alt_text=row["alt_text"],
    )


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
