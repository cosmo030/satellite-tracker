from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from sattrack.enrich.wikimedia import (
    WikimediaClient,
    WikimediaUnavailableError,
    retry_after_seconds,
    user_agent,
)

from ..wikimedia_fake import placeholder_png

Handler = Callable[[httpx.Request], httpx.Response]


class Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def monotonic(self) -> float:
        return self.now


def client(handler: Handler, clock: Clock | None = None) -> WikimediaClient:
    clock = clock or Clock()
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return WikimediaClient(http, "agent/1", sleep=clock.sleep, monotonic=clock.monotonic)


def test_user_agent_names_the_project_and_the_contact() -> None:
    assert user_agent("ops@example.test") == (
        "SatelliteTracker/0.1.0 (+https://github.com/cosmo030/satellite-tracker; ops@example.test)"
    )


def test_requests_to_one_host_are_at_least_250_ms_apart() -> None:
    clock = Clock()
    api = client(lambda _: httpx.Response(200, json={"query": {}}), clock)

    api.wikipedia({"a": "1"})
    clock.now += 0.1
    api.wikipedia({"a": "2"})
    api.commons({"a": "3"})  # another host: no wait

    assert clock.sleeps == [pytest.approx(0.15)]


def test_429_waits_for_retry_after_then_succeeds() -> None:
    responses = iter(
        [httpx.Response(429, headers={"Retry-After": "30"}), httpx.Response(200, json={})]
    )
    clock = Clock()

    client(lambda _: next(responses), clock).commons({})

    assert 30.0 in clock.sleeps


def test_429_retry_after_is_capped_and_retried_three_times_at_most() -> None:
    clock = Clock()
    api = client(lambda _: httpx.Response(429, headers={"Retry-After": "9999"}), clock)

    with pytest.raises(WikimediaUnavailableError) as error:
        api.commons({})

    assert error.value.status_code == 429
    assert [s for s in clock.sleeps if s > 1] == [120.0, 120.0, 120.0]


@pytest.mark.parametrize(
    "response",
    [httpx.Response(503), httpx.Response(404), httpx.Response(200, text="not json")],
)
def test_server_errors_and_unexpected_responses_stop(response: httpx.Response) -> None:
    with pytest.raises(WikimediaUnavailableError):
        client(lambda _: response).wikipedia({})


def test_network_errors_stop() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout", request=request)

    with pytest.raises(WikimediaUnavailableError):
        client(fail).wikipedia({})


def test_api_error_bodies_stop() -> None:
    with pytest.raises(WikimediaUnavailableError):
        client(lambda _: httpx.Response(200, json={"error": {"code": "x"}})).commons({})


def test_images_come_only_from_wikimedia_image_hosts() -> None:
    api = client(
        lambda _: httpx.Response(
            200, content=placeholder_png(), headers={"Content-Type": "image/png"}
        )
    )

    assert api.download_image("https://upload.wikimedia.org/thumb/a.png").mime == "image/png"
    assert api.download_image("https://thumb.wikimedia.org/thumb/a.png").mime == "image/png"
    with pytest.raises(WikimediaUnavailableError):
        api.download_image("https://example.com/a.png")
    with pytest.raises(WikimediaUnavailableError):
        api.download_image("http://upload.wikimedia.org/thumb/a.png")


def test_images_must_really_be_jpeg_or_png() -> None:
    api = client(
        lambda _: httpx.Response(200, content=b"<svg/>", headers={"Content-Type": "image/png"})
    )
    with pytest.raises(WikimediaUnavailableError):
        api.download_image("https://upload.wikimedia.org/thumb/a.png")


@pytest.mark.parametrize(
    ("header", "seconds"),
    [("12", 12.0), ("500", 120.0), (None, 5.0), ("garbage", 5.0), ("-3", 0.0)],
)
def test_retry_after_parsing(header: str | None, seconds: float) -> None:
    assert retry_after_seconds(header) == seconds
