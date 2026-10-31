from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from sattrack.catalog import OrbitClass
from sattrack.ingest.celestrak import (
    USER_AGENT,
    CelesTrakClient,
    CelesTrakResponseError,
    CelesTrakUnavailableError,
    parse_omm_record,
    parse_satcat_record,
)

from ..conftest import load_fixture

BASE_URL = "https://celestrak.test"
OmmFactory = Callable[..., dict[str, Any]]


def make_client(handler: Callable[[httpx.Request], httpx.Response]) -> CelesTrakClient:
    return CelesTrakClient(httpx.Client(transport=httpx.MockTransport(handler)), BASE_URL)


def test_parse_omm_record_maps_fields_and_assumes_utc_epoch(omm_record: OmmFactory) -> None:
    elements = parse_omm_record(omm_record())

    assert elements.norad_id == 25544
    assert elements.object_name == "ISS (ZARYA)"
    assert elements.epoch == datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
    assert elements.raan_deg == pytest.approx(247.4627)
    assert elements.orbit_class is OrbitClass.LEO
    assert elements.raw["OBJECT_ID"] == "1998-067A"


def test_parse_omm_record_accepts_six_digit_catalog_numbers(omm_record: OmmFactory) -> None:
    # Five-digit catalog numbers ran out on 2026-07-11.
    assert parse_omm_record(omm_record(NORAD_CAT_ID=100173)).norad_id == 100173


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("MEAN_MOTION", 0),
        ("ECCENTRICITY", 1.0),
        ("INCLINATION", 181),
        ("NORAD_CAT_ID", 0),
        ("EPOCH", "not-a-date"),
        ("OBJECT_NAME", ""),
    ],
)
def test_parse_omm_record_rejects_invalid_values(
    omm_record: OmmFactory, field: str, value: object
) -> None:
    with pytest.raises(ValidationError):
        parse_omm_record(omm_record(**{field: value}))


def test_parse_omm_record_rejects_missing_required_field(omm_record: OmmFactory) -> None:
    record = omm_record()
    del record["MEAN_MOTION"]
    with pytest.raises(ValidationError):
        parse_omm_record(record)


def test_parse_satcat_record_treats_blank_values_as_missing() -> None:
    record = parse_satcat_record(
        {"OBJECT_NAME": "DEB", "NORAD_CAT_ID": 99999, "OWNER": "", "LAUNCH_DATE": ""}
    )
    assert record.owner is None
    assert record.launch_date is None


def test_parse_satcat_record_parses_launch_date() -> None:
    record = parse_satcat_record(load_fixture("satcat_sample.json")[0])
    assert record.launch_date == date(1998, 11, 20)
    assert record.owner == "ISS"
    assert record.object_type == "PAY"


def test_fetch_group_elements_requests_json_explicitly_with_user_agent() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=load_fixture("gp_sample.json"))

    result = make_client(handler).fetch_group_elements("stations")

    assert len(result.records) == 3
    assert result.rejected_count == 0
    assert seen[0].url.params["FORMAT"] == "JSON"
    assert seen[0].url.params["GROUP"] == "stations"
    assert seen[0].headers["User-Agent"] == USER_AGENT


def test_fetch_group_elements_skips_invalid_records_and_counts_them(
    omm_record: OmmFactory,
) -> None:
    body = [omm_record(), omm_record(ECCENTRICITY=2.0), "not an object"]
    result = make_client(lambda _r: httpx.Response(200, json=body)).fetch_group_elements("x")

    assert [e.norad_id for e in result.records] == [25544]
    assert result.rejected_count == 2


@pytest.mark.parametrize("status_code", [301, 403, 404, 500, 503])
def test_non_200_response_raises_unavailable_with_status(status_code: int) -> None:
    client = make_client(lambda _r: httpx.Response(status_code))

    with pytest.raises(CelesTrakUnavailableError) as excinfo:
        client.fetch_group_elements("stations")

    assert excinfo.value.status_code == status_code


def test_network_error_raises_unavailable_without_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    with pytest.raises(CelesTrakUnavailableError) as excinfo:
        make_client(handler).fetch_group_satcat("stations")

    assert excinfo.value.status_code is None


def test_plain_text_body_raises_response_error() -> None:
    client = make_client(lambda _r: httpx.Response(200, text="No GP data found"))

    with pytest.raises(CelesTrakResponseError, match="body is not JSON"):
        client.fetch_group_elements("unknown")


def test_json_object_body_raises_response_error() -> None:
    client = make_client(lambda _r: httpx.Response(200, content=json.dumps({"error": "x"})))

    with pytest.raises(CelesTrakResponseError, match="expected a JSON list"):
        client.fetch_group_satcat("stations")
