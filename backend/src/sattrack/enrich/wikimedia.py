"""Adapter for Wikimedia (Wikidata, English Wikipedia, Commons): the only code that calls them.

Etiquette, as for CelesTrak: identify ourselves, one request at a time with a pause between
requests to the same host, honour 429 Retry-After, and stop on anything unexpected.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from importlib.metadata import version
from typing import Any
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)

WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
# Commons serves rendered thumbnails from these hosts; downloads go nowhere else.
IMAGE_HOSTS = frozenset({"upload.wikimedia.org", "thumb.wikimedia.org"})
ALLOWED_HOSTS = frozenset(
    {"query.wikidata.org", "en.wikipedia.org", "commons.wikimedia.org", *IMAGE_HOSTS}
)

MIN_INTERVAL_SECONDS = 0.25
MAX_RETRIES_ON_429 = 3
MAX_RETRY_AFTER_SECONDS = 120.0
DEFAULT_RETRY_AFTER_SECONDS = 5.0
MAX_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_SIGNATURES = {"image/jpeg": b"\xff\xd8\xff", "image/png": b"\x89PNG\r\n\x1a\n"}


def user_agent(contact: str) -> str:
    return (
        f"SatelliteTracker/{version('sattrack')} "
        f"(+https://github.com/cosmo030/satellite-tracker; {contact})"
    )


class WikimediaUnavailableError(Exception):
    """Wikimedia could not be reached, refused us, or answered unexpectedly. Stop the run."""

    def __init__(self, url: str, status_code: int | None, reason: str) -> None:
        super().__init__(f"Wikimedia request failed ({reason}): {url}")
        self.url = url
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class Download:
    content: bytes
    mime: str


class WikimediaClient:
    """Rate-limited, identified HTTP access to the Wikimedia APIs."""

    def __init__(
        self,
        http: httpx.Client,
        user_agent: str,
        *,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._http = http
        self._headers = {"User-Agent": user_agent}
        self._sleep = sleep
        self._monotonic = monotonic
        self._last_request: dict[str, float] = {}

    def sparql(self, query: str) -> list[dict[str, str]]:
        """Run a SPARQL query; returns the result rows as {variable: value}."""
        body = self._json(
            "POST",
            WIKIDATA_SPARQL_URL,
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
        )
        try:
            bindings = body["results"]["bindings"]
            return [{name: cell["value"] for name, cell in row.items()} for row in bindings]
        except (KeyError, TypeError) as exc:
            raise WikimediaUnavailableError(WIKIDATA_SPARQL_URL, 200, "unexpected body") from exc

    def wikipedia(self, params: Mapping[str, str]) -> dict[str, Any]:
        return self._json("GET", WIKIPEDIA_API_URL, params=params)

    def commons(self, params: Mapping[str, str]) -> dict[str, Any]:
        return self._json("GET", COMMONS_API_URL, params=params)

    def download_image(self, url: str) -> Download:
        """A rendered thumbnail from a Wikimedia image host: JPEG or PNG, at most 5 MB."""
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.hostname not in IMAGE_HOSTS:
            raise WikimediaUnavailableError(
                url, None, "image URL outside the Wikimedia image hosts"
            )
        response = self._send("GET", url)
        mime = response.headers.get("content-type", "").split(";")[0].strip().lower()
        signature = IMAGE_SIGNATURES.get(mime)
        content = response.content
        if signature is None or not content.startswith(signature):
            raise WikimediaUnavailableError(url, 200, f"not a JPEG or PNG image ({mime})")
        if len(content) > MAX_IMAGE_BYTES:
            raise WikimediaUnavailableError(url, 200, "image larger than 5 MB")
        return Download(content=content, mime=mime)

    def _json(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        response = self._send(method, url, **kwargs)
        try:
            body = response.json()
        except ValueError as exc:
            raise WikimediaUnavailableError(url, 200, "body is not JSON") from exc
        if not isinstance(body, dict):
            raise WikimediaUnavailableError(url, 200, "expected a JSON object")
        if "error" in body:
            raise WikimediaUnavailableError(url, 200, f"API error {body['error']!r:.100}")
        return body

    def _send(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        headers = {**self._headers, **kwargs.pop("headers", {})}
        for attempt in range(MAX_RETRIES_ON_429 + 1):
            self._wait_turn(url)
            try:
                response = self._http.request(method, url, headers=headers, **kwargs)
            except httpx.HTTPError as exc:
                raise WikimediaUnavailableError(url, None, type(exc).__name__) from exc
            if response.status_code == httpx.codes.OK:
                return response
            if response.status_code != httpx.codes.TOO_MANY_REQUESTS:
                raise WikimediaUnavailableError(
                    url, response.status_code, f"HTTP {response.status_code}"
                )
            if attempt == MAX_RETRIES_ON_429:
                break
            delay = retry_after_seconds(response.headers.get("retry-after"))
            logger.warning("Wikimedia rate limit url=%s retry_in=%.0fs", _host(url), delay)
            self._sleep(delay)
        raise WikimediaUnavailableError(url, 429, "HTTP 429 after retries")

    def _wait_turn(self, url: str) -> None:
        """At least MIN_INTERVAL_SECONDS between two requests to the same host."""
        host = _host(url)
        if host not in ALLOWED_HOSTS:
            raise WikimediaUnavailableError(url, None, "host is not a Wikimedia API")
        previous = self._last_request.get(host)
        if previous is not None:
            wait = MIN_INTERVAL_SECONDS - (self._monotonic() - previous)
            if wait > 0:
                self._sleep(wait)
        self._last_request[host] = self._monotonic()


def retry_after_seconds(header: str | None) -> float:
    """Seconds to wait from a Retry-After header (seconds or HTTP date), capped at 120 s."""
    if not header:
        return DEFAULT_RETRY_AFTER_SECONDS
    try:
        seconds = float(header)
    except ValueError:
        try:
            when = parsedate_to_datetime(header)
        except (TypeError, ValueError):
            return DEFAULT_RETRY_AFTER_SECONDS
        seconds = when.timestamp() - time.time()
    return min(max(seconds, 0.0), MAX_RETRY_AFTER_SECONDS)


def _host(url: str) -> str:
    return urlsplit(url).hostname or ""
