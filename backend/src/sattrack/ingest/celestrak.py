"""Adapter for CelesTrak: the only code that talks to celestrak.org.

Translates HTTP responses into catalog domain types and CelesTrak failures into our own
errors. Usage policy: https://celestrak.org/usage-policy.php
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from sattrack.catalog import OrbitalElements, SatcatRecord

logger = logging.getLogger(__name__)

USER_AGENT = "satellite-tracker/0.1 (+https://github.com/cosmo030/satellite-tracker)"


class CelesTrakUnavailableError(Exception):
    """CelesTrak could not be reached or answered with a non-200 status.

    The policy requires clients to stop querying on any non-200 response.
    """

    def __init__(self, url: str, status_code: int | None, reason: str) -> None:
        super().__init__(f"CelesTrak request failed ({reason}): {url}")
        self.url = url
        self.status_code = status_code


class CelesTrakResponseError(Exception):
    """CelesTrak answered 200 but the body is not the expected JSON list."""

    def __init__(self, url: str, reason: str) -> None:
        super().__init__(f"Unexpected CelesTrak response ({reason}): {url}")
        self.url = url


@dataclass(frozen=True, slots=True)
class FetchResult[T]:
    url: str
    records: list[T]
    rejected_count: int


class _OmmRecord(BaseModel):
    """One record of CelesTrak's GP data in OMM JSON format."""

    model_config = ConfigDict(extra="ignore")

    OBJECT_NAME: str = Field(min_length=1, max_length=100)
    OBJECT_ID: str | None = Field(default=None, max_length=20)
    EPOCH: datetime
    MEAN_MOTION: float = Field(gt=0, lt=20)
    ECCENTRICITY: float = Field(ge=0, lt=1)
    INCLINATION: float = Field(ge=0, le=180)
    RA_OF_ASC_NODE: float = Field(ge=0, le=360)
    ARG_OF_PERICENTER: float = Field(ge=0, le=360)
    MEAN_ANOMALY: float = Field(ge=0, le=360)
    EPHEMERIS_TYPE: int = 0
    CLASSIFICATION_TYPE: str = Field(default="U", min_length=1, max_length=1)
    NORAD_CAT_ID: int = Field(ge=1, le=999_999_999)
    ELEMENT_SET_NO: int | None = None
    REV_AT_EPOCH: int | None = None
    BSTAR: float
    MEAN_MOTION_DOT: float
    MEAN_MOTION_DDOT: float

    @field_validator("EPOCH")
    @classmethod
    def _assume_utc(cls, epoch: datetime) -> datetime:
        # CelesTrak publishes epochs in UTC without an offset.
        return epoch.replace(tzinfo=UTC) if epoch.tzinfo is None else epoch.astimezone(UTC)


class _SatcatRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    OBJECT_NAME: str = Field(min_length=1, max_length=100)
    NORAD_CAT_ID: int = Field(ge=1, le=999_999_999)
    OBJECT_TYPE: str | None = Field(default=None, max_length=10)
    OWNER: str | None = Field(default=None, max_length=10)
    LAUNCH_DATE: date | None = None

    @field_validator("OBJECT_TYPE", "OWNER", "LAUNCH_DATE", mode="before")
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        return None if value == "" else value


def parse_omm_record(record: dict[str, Any]) -> OrbitalElements:
    """Validate one OMM JSON record; raises ``pydantic.ValidationError`` when invalid."""
    omm = _OmmRecord.model_validate(record)
    return OrbitalElements(
        norad_id=omm.NORAD_CAT_ID,
        object_name=omm.OBJECT_NAME.strip(),
        object_id=omm.OBJECT_ID,
        epoch=omm.EPOCH,
        mean_motion=omm.MEAN_MOTION,
        eccentricity=omm.ECCENTRICITY,
        inclination_deg=omm.INCLINATION,
        raan_deg=omm.RA_OF_ASC_NODE,
        arg_of_pericenter_deg=omm.ARG_OF_PERICENTER,
        mean_anomaly_deg=omm.MEAN_ANOMALY,
        bstar=omm.BSTAR,
        mean_motion_dot=omm.MEAN_MOTION_DOT,
        mean_motion_ddot=omm.MEAN_MOTION_DDOT,
        element_set_no=omm.ELEMENT_SET_NO,
        rev_at_epoch=omm.REV_AT_EPOCH,
        classification_type=omm.CLASSIFICATION_TYPE,
        ephemeris_type=omm.EPHEMERIS_TYPE,
        raw=record,
    )


def parse_satcat_record(record: dict[str, Any]) -> SatcatRecord:
    """Validate one SATCAT JSON record; raises ``pydantic.ValidationError`` when invalid."""
    satcat = _SatcatRecord.model_validate(record)
    return SatcatRecord(
        norad_id=satcat.NORAD_CAT_ID,
        object_name=satcat.OBJECT_NAME.strip(),
        object_type=satcat.OBJECT_TYPE,
        owner=satcat.OWNER,
        launch_date=satcat.LAUNCH_DATE,
    )


class CelesTrakClient:
    """Fetches GP element sets and SATCAT metadata for CelesTrak groups."""

    def __init__(self, http: httpx.Client, base_url: str) -> None:
        self._http = http
        self._base_url = base_url

    def gp_url(self, group: str) -> str:
        # FORMAT is always explicit: the default changed to CSV on 2026-05-09.
        return f"{self._base_url}/NORAD/elements/gp.php?GROUP={group}&FORMAT=JSON"

    def satcat_url(self, group: str) -> str:
        return f"{self._base_url}/satcat/records.php?GROUP={group}&FORMAT=JSON"

    def fetch_group_elements(self, group: str) -> FetchResult[OrbitalElements]:
        url = self.gp_url(group)
        return _parse_all(url, self._get_json_list(url), parse_omm_record)

    def fetch_group_satcat(self, group: str) -> FetchResult[SatcatRecord]:
        url = self.satcat_url(group)
        return _parse_all(url, self._get_json_list(url), parse_satcat_record)

    def _get_json_list(self, url: str) -> list[Any]:
        try:
            response = self._http.get(url, headers={"User-Agent": USER_AGENT})
        except httpx.HTTPError as exc:
            raise CelesTrakUnavailableError(url, None, type(exc).__name__) from exc
        if response.status_code != httpx.codes.OK:
            raise CelesTrakUnavailableError(
                url, response.status_code, f"HTTP {response.status_code}"
            )
        try:
            body = response.json()
        except ValueError as exc:
            # CelesTrak answers 200 with a plain-text message such as "No GP data found".
            raise CelesTrakResponseError(url, "body is not JSON") from exc
        if not isinstance(body, list):
            raise CelesTrakResponseError(url, "expected a JSON list")
        return body


def _parse_all[T](
    url: str, body: list[Any], parse: Callable[[dict[str, Any]], T]
) -> FetchResult[T]:
    records: list[T] = []
    rejected = 0
    for item in body:
        try:
            if not isinstance(item, dict):
                raise TypeError("record is not an object")
            records.append(parse(item))
        except (ValidationError, TypeError) as exc:
            rejected += 1
            logger.warning(
                "Rejected invalid CelesTrak record url=%s error=%s", url, _first_line(exc)
            )
    return FetchResult(url=url, records=records, rejected_count=rejected)


def _first_line(exc: Exception) -> str:
    return str(exc).splitlines()[0] if str(exc) else type(exc).__name__
