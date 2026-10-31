"""Load a synthetic demo catalog into the local database (run via `make seed`).

Useful when celestrak.org is unreachable or you do not want to download data while
developing. The objects are made up (NORAD IDs 900001+), with epochs at the current time.
Runs through the real ingest service, so the fetch log and health endpoint behave normally.
"""

from __future__ import annotations

import logging
import sys
from datetime import UTC, date, datetime
from typing import Any

from sattrack.catalog import OrbitalElements, SatcatRecord
from sattrack.config import load_settings
from sattrack.ingest import IngestService
from sattrack.ingest.celestrak import FetchResult, parse_omm_record, parse_satcat_record
from sattrack.shared import utc_now
from sattrack.shared.db import create_db_engine, create_session_factory
from sattrack.shared.logging import configure_logging

FIRST_DEMO_NORAD_ID = 900_001


def _constellation(
    prefix: str, planes: int, per_plane: int, mean_motion: float, inclination: float
) -> list[dict[str, Any]]:
    """Evenly spaced circular orbits: ``planes`` RAAN slots, ``per_plane`` phase slots."""
    shells = []
    for plane in range(planes):
        for slot in range(per_plane):
            shells.append(
                {
                    "OBJECT_NAME": f"{prefix}-{plane + 1:02d}{slot + 1:02d}",
                    "MEAN_MOTION": mean_motion,
                    "ECCENTRICITY": 0.0001,
                    "INCLINATION": inclination,
                    "RA_OF_ASC_NODE": 360.0 * plane / planes,
                    "MEAN_ANOMALY": (360.0 * slot / per_plane + 7.5 * plane) % 360,
                }
            )
    return shells


DEMO_GROUPS: dict[str, list[dict[str, Any]]] = {
    "demo-leo": _constellation(
        "DEMO LEO", planes=6, per_plane=12, mean_motion=15.05, inclination=53.0
    ),
    "demo-meo": _constellation(
        "DEMO MEO", planes=3, per_plane=8, mean_motion=2.0056, inclination=55.0
    ),
    "demo-geo": _constellation(
        "DEMO GEO", planes=1, per_plane=12, mean_motion=1.0027, inclination=0.05
    ),
}


class SyntheticSource:
    """A ``CatalogSource`` that returns the demo groups instead of calling CelesTrak."""

    def __init__(self, epoch: datetime) -> None:
        self._epoch = epoch
        self._records: dict[str, list[dict[str, Any]]] = {}
        next_id = FIRST_DEMO_NORAD_ID
        for group, shells in DEMO_GROUPS.items():
            self._records[group] = []
            for shell in shells:
                self._records[group].append({**self._omm_defaults(next_id), **shell})
                next_id += 1

    def fetch_group_elements(self, group: str) -> FetchResult[OrbitalElements]:
        records = [parse_omm_record(r) for r in self._records[group]]
        return FetchResult(url=f"synthetic://{group}", records=records, rejected_count=0)

    def fetch_group_satcat(self, group: str) -> FetchResult[SatcatRecord]:
        records = [
            parse_satcat_record(
                {
                    "OBJECT_NAME": r["OBJECT_NAME"],
                    "NORAD_CAT_ID": r["NORAD_CAT_ID"],
                    "OBJECT_TYPE": "PAY",
                    "OWNER": "DEMO",
                    "LAUNCH_DATE": date(2020 + r["NORAD_CAT_ID"] % 7, 1, 15).isoformat(),
                }
            )
            for r in self._records[group]
        ]
        return FetchResult(url=f"synthetic://{group}/satcat", records=records, rejected_count=0)

    def _omm_defaults(self, norad_id: int) -> dict[str, Any]:
        return {
            "OBJECT_ID": f"2026-9{norad_id % 100:02d}A",
            "EPOCH": self._epoch.replace(tzinfo=None).isoformat(),
            "ARG_OF_PERICENTER": 0.0,
            "EPHEMERIS_TYPE": 0,
            "CLASSIFICATION_TYPE": "U",
            "NORAD_CAT_ID": norad_id,
            "ELEMENT_SET_NO": 1,
            "REV_AT_EPOCH": 1,
            "BSTAR": 0.0,
            "MEAN_MOTION_DOT": 0.0,
            "MEAN_MOTION_DDOT": 0.0,
        }


def main() -> int:
    settings = load_settings()
    configure_logging(settings.log_level)
    engine = create_db_engine(str(settings.database_url))
    service = IngestService(
        source=SyntheticSource(datetime.now(UTC)),
        session_factory=create_session_factory(engine),
        groups=tuple(DEMO_GROUPS),
        clock=utc_now,
    )
    report = service.run_once()
    engine.dispose()
    logging.getLogger("seed").info("Seeded %d synthetic element sets", report.elements_added)
    return 0


if __name__ == "__main__":
    sys.exit(main())
