"""A stand-in for Wikimedia that serves the recorded fixtures in tests/fixtures/wikimedia.

The fixtures are synthetic (made-up objects, text and image); no real Wikipedia text or
Commons file is stored in the repository.
"""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import httpx

FIXTURES = Path(__file__).parent / "fixtures" / "wikimedia"


def placeholder_png(width: int = 2, height: int = 2) -> bytes:
    """A tiny valid PNG (grey pixels), generated so no real image lives in the repository."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    rows = b"".join(b"\x00" + b"\x80" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return data


class FakeWikimedia:
    """Routes requests by host; failures can be switched on per host."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.fail_hosts: dict[str, int] = {}
        self.rate_limited: dict[str, int] = {}
        self.retry_after = "7"
        self.image = placeholder_png()

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def hosts(self) -> list[str]:
        return [request.url.host for request in self.requests]

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        host = request.url.host
        if host in self.fail_hosts:
            return httpx.Response(self.fail_hosts[host])
        if self.rate_limited.get(host, 0) > 0:
            self.rate_limited[host] -= 1
            return httpx.Response(429, headers={"Retry-After": self.retry_after})
        if host == "query.wikidata.org":
            return httpx.Response(200, json=self._sparql(request))
        if host == "en.wikipedia.org":
            return httpx.Response(200, json=load("wikipedia.json"))
        if host == "commons.wikimedia.org":
            width = request.url.params.get("iiurlwidth", "960")
            return httpx.Response(200, json=load(f"commons_{width}.json"))
        if host in {"upload.wikimedia.org", "thumb.wikimedia.org"}:
            return httpx.Response(200, content=self.image, headers={"Content-Type": "image/png"})
        return httpx.Response(404)

    @staticmethod
    def _sparql(request: httpx.Request) -> dict[str, Any]:
        query = parse_qs(request.content.decode())["query"][0]
        if "VALUES ?class" in query:
            return load("wikidata_classes.json")
        if "wdt:P247" in query:
            return load("wikidata_cospar.json")
        return load("wikidata_norad.json")
