"""Enrich use case: descriptions, purpose categories and images for catalogued objects.

Objects are processed in chunks of 200. A chunk's results are written in one transaction only
after every request for it succeeded, so a run that stops halfway never overwrites good data
with partial data. Each chunk holds the worker lock, so enrich never runs during ingest.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol
from urllib.parse import urlsplit

from sqlalchemy.orm import Session, sessionmaker

from sattrack.catalog import (
    AboutScope,
    AboutStatus,
    CatalogRepository,
    ImageCredit,
    ImageVariant,
    ImageWidth,
    MatchMethod,
    SatelliteAbout,
    SatelliteIdentity,
    SatelliteImage,
    SummarySource,
)
from sattrack.enrich.domain import (
    MAX_MANUFACTURERS,
    MAX_OPERATORS,
    MIN_ORIGINAL_WIDTH_PX,
    Category,
    WikidataItem,
    categories_for,
    choose_item,
    constellation_parent,
    constellation_title,
    image_alt_text,
    image_artist,
    is_allowed_license,
    is_cospar_id,
    summarize_extract,
    unique_labels,
    usable_wikidata_description,
)
from sattrack.enrich.sources import (
    COMMONS_BATCH,
    WIKIPEDIA_BATCH,
    Article,
    CommonsFile,
    class_category_query,
    commons_params,
    cospar_match_query,
    norad_match_query,
    parse_class_rows,
    parse_commons,
    parse_match_rows,
    parse_wikipedia,
    wikipedia_params,
)
from sattrack.enrich.wikimedia import IMAGE_HOSTS, Download, WikimediaUnavailableError
from sattrack.shared import Clock
from sattrack.shared.db import WORKER_LOCK_KEY, advisory_lock, transaction

logger = logging.getLogger(__name__)

CHUNK_SIZE = 200
CLASS_QUERY_BATCH = 200
_RASTER_THUMB_SUFFIXES = (".jpg", ".jpeg", ".png")


class EnrichMode(StrEnum):
    # New objects, objects whose last fetch failed, and those older than the refresh interval.
    DUE = "due"
    # Every object.
    FULL = "full"


class WikimediaApi(Protocol):
    """What the enrich service needs from Wikimedia (WikimediaClient in production)."""

    def sparql(self, query: str) -> list[dict[str, str]]: ...

    def wikipedia(self, params: Mapping[str, str]) -> dict[str, Any]: ...

    def commons(self, params: Mapping[str, str]) -> dict[str, Any]: ...

    def download_image(self, url: str) -> Download: ...


@dataclass(slots=True)
class EnrichReport:
    matched: int = 0
    descriptions: int = 0
    images: int = 0
    no_match: int = 0
    failed: int = 0
    processed: int = 0

    def add(self, results: Sequence[SatelliteAbout]) -> None:
        self.processed += len(results)
        self.matched += sum(1 for r in results if r.wikidata_qid is not None)
        self.descriptions += sum(1 for r in results if r.summary)
        self.images += sum(1 for r in results if r.image is not None)
        self.no_match += sum(1 for r in results if r.status is AboutStatus.NO_MATCH)


@dataclass(frozen=True, slots=True)
class _Match:
    item: WikidataItem
    method: MatchMethod


@dataclass(frozen=True, slots=True)
class _Text:
    scope: AboutScope = AboutScope.OBJECT
    title: str | None = None
    summary: str | None = None
    source: SummarySource | None = None
    url: str | None = None
    revised_at: datetime | None = None
    page_image: str | None = None


@dataclass(slots=True)
class _ChunkData:
    matches: dict[int, _Match] = field(default_factory=dict)
    texts: dict[int, _Text] = field(default_factory=dict)
    images: dict[int, SatelliteImage] = field(default_factory=dict)


class EnrichService:
    def __init__(
        self,
        client: WikimediaApi,
        session_factory: sessionmaker[Session],
        clock: Clock,
        refresh_interval: timedelta,
    ) -> None:
        self._client = client
        self._session_factory = session_factory
        self._clock = clock
        self._refresh_interval = refresh_interval
        self._class_categories: dict[str, frozenset[Category]] = {}

    def run(
        self, mode: EnrichMode = EnrichMode.DUE, stop: threading.Event | None = None
    ) -> EnrichReport:
        """Fetch descriptions for the objects that need them.

        Raises ``WikimediaUnavailableError`` when a request fails; chunks finished before that
        are kept, nothing else is changed.
        """
        started = self._clock()
        targets = self._targets(mode, started)
        report = EnrichReport()
        try:
            for chunk in _chunks(targets, CHUNK_SIZE):
                if stop is not None and stop.is_set():
                    break
                with advisory_lock(self._session_factory, WORKER_LOCK_KEY):
                    results = self._enrich_chunk(chunk)
                    with transaction(self._session_factory) as session:
                        repository = CatalogRepository(session)
                        for about in results:
                            repository.save_about(about)
                report.add(results)
        finally:
            report.failed = len(targets) - report.processed
            logger.info(
                "Enrich run finished matched=%d descriptions=%d images=%d no_match=%d "
                "failed=%d duration=%s",
                report.matched,
                report.descriptions,
                report.images,
                report.no_match,
                report.failed,
                self._clock() - started,
            )
        return report

    def _targets(self, mode: EnrichMode, now: datetime) -> list[SatelliteIdentity]:
        refresh_before = None if mode is EnrichMode.FULL else now - self._refresh_interval
        with self._session_factory() as session:
            return CatalogRepository(session).enrichment_targets(refresh_before)

    def _enrich_chunk(self, chunk: Sequence[SatelliteIdentity]) -> list[SatelliteAbout]:
        data = _ChunkData(matches=self._match(chunk))
        articles = self._fetch_articles(_article_titles(data.matches.values()))
        data.texts = {
            norad_id: _choose_text(match.item, articles) for norad_id, match in data.matches.items()
        }
        data.images = self._fetch_images(data)
        self._learn_classes(match.item for match in data.matches.values())
        now = self._clock()
        return [self._about(target.norad_id, data, now) for target in chunk]

    # --- Step 1: match on Wikidata ----------------------------------------------------------

    def _match(self, chunk: Sequence[SatelliteIdentity]) -> dict[int, _Match]:
        rows = self._client.sparql(norad_match_query(t.norad_id for t in chunk))
        by_norad = parse_match_rows(rows)
        matches: dict[int, _Match] = {}
        for target in chunk:
            item = choose_item(by_norad.get(str(target.norad_id), []))
            if item is not None:
                matches[target.norad_id] = _Match(item, MatchMethod.NORAD)
        rest = [
            t
            for t in chunk
            if t.norad_id not in matches and t.intl_designator and is_cospar_id(t.intl_designator)
        ]
        if rest:
            designators = [t.intl_designator for t in rest if t.intl_designator]
            by_cospar = parse_match_rows(self._client.sparql(cospar_match_query(designators)))
            for target in rest:
                item = choose_item(by_cospar.get(target.intl_designator or "", []))
                if item is not None:
                    matches[target.norad_id] = _Match(item, MatchMethod.COSPAR)
        return matches

    # --- Steps 2 and 3: descriptions from Wikipedia -----------------------------------------

    def _fetch_articles(self, titles: Sequence[str]) -> dict[str, Article]:
        articles: dict[str, Article] = {}
        for batch in _chunks(titles, WIKIPEDIA_BATCH):
            body = self._client.wikipedia(wikipedia_params(batch))
            articles.update(parse_wikipedia(body, batch))
        return articles

    # --- Step 4: images from Commons --------------------------------------------------------

    def _fetch_images(self, data: _ChunkData) -> dict[int, SatelliteImage]:
        candidates = {
            norad_id: _image_candidates(match.item, data.texts[norad_id])
            for norad_id, match in data.matches.items()
            if data.texts[norad_id].scope is AboutScope.OBJECT
        }
        files = sorted({name for names in candidates.values() for name in names})
        large = self._commons_files(files, ImageWidth.LARGE)
        small = self._commons_files(files, ImageWidth.SMALL)
        downloaded: dict[str, SatelliteImage] = {}
        images: dict[int, SatelliteImage] = {}
        for norad_id, names in candidates.items():
            name = next((n for n in names if _acceptable(large.get(n), small.get(n))), None)
            if name is None:
                continue
            if name not in downloaded:
                downloaded[name] = self._download(large[name], small[name])
            images[norad_id] = downloaded[name]
        return images

    def _commons_files(self, files: Sequence[str], width: ImageWidth) -> dict[str, CommonsFile]:
        found: dict[str, CommonsFile] = {}
        for batch in _chunks(files, COMMONS_BATCH):
            found.update(parse_commons(self._client.commons(commons_params(batch, width)), batch))
        return found

    def _download(self, large: CommonsFile, small: CommonsFile) -> SatelliteImage:
        small_file = self._client.download_image(small.thumb_url)
        large_file = self._client.download_image(large.thumb_url)
        if small_file.mime != large_file.mime:
            raise WikimediaUnavailableError(large.thumb_url, 200, "thumbnail formats differ")
        meta = large.metadata
        return SatelliteImage(
            small=ImageVariant(small_file.content, small.thumb_width, small.thumb_height),
            large=ImageVariant(large_file.content, large.thumb_width, large.thumb_height),
            mime=large_file.mime,
            sha256=hashlib.sha256(small_file.content + large_file.content).hexdigest(),
            credit=ImageCredit(
                source_file=large.title,
                source_url=large.page_url,
                artist=image_artist(meta.get("Artist"), meta.get("Credit")),
                license_short=" ".join(meta.get("LicenseShortName", "").split()),
                license_url=meta.get("LicenseUrl") or None,
                attribution_required=meta.get("AttributionRequired", "").lower() == "true",
                alt_text=image_alt_text(meta.get("ImageDescription")),
            ),
        )

    # --- Step 5: purpose categories ---------------------------------------------------------

    def _learn_classes(self, items: Iterable[WikidataItem]) -> None:
        """Map classes not seen yet in this run to categories (one query per 200 classes)."""
        unknown = sorted(
            {c for item in items for c in item.classes} - self._class_categories.keys()
        )
        for batch in _chunks(unknown, CLASS_QUERY_BATCH):
            mapping = parse_class_rows(self._client.sparql(class_category_query(batch)))
            for qid in batch:
                self._class_categories[qid] = mapping.get(qid, frozenset())

    # --- Result -----------------------------------------------------------------------------

    def _about(self, norad_id: int, data: _ChunkData, now: datetime) -> SatelliteAbout:
        match = data.matches.get(norad_id)
        if match is None:
            return SatelliteAbout(norad_id=norad_id, status=AboutStatus.NO_MATCH, fetched_at=now)
        item, text, image = match.item, data.texts[norad_id], data.images.get(norad_id)
        categories = categories_for(item.classes, self._class_categories)
        operators = unique_labels(item.operators, MAX_OPERATORS)
        manufacturers = unique_labels(item.manufacturers, MAX_MANUFACTURERS)
        has_content = bool(text.summary or image or categories or operators or manufacturers)
        return SatelliteAbout(
            norad_id=norad_id,
            # Matched but nothing to show: treated like no match, so the tile stays unchanged.
            status=AboutStatus.OK if has_content else AboutStatus.NO_MATCH,
            fetched_at=now,
            wikidata_qid=item.qid,
            match_method=match.method,
            scope=text.scope,
            title=text.title,
            summary=text.summary,
            summary_source=text.source,
            summary_url=text.url,
            summary_revision_at=text.revised_at,
            categories=categories,
            operators=operators,
            manufacturers=manufacturers,
            image=image,
        )


def _article_titles(matches: Iterable[_Match]) -> list[str]:
    titles: set[str] = set()
    for match in matches:
        parent = constellation_parent(match.item)
        title = match.item.article_title or (parent.article_title if parent else None)
        if title:
            titles.add(title)
    return sorted(titles)


def _choose_text(item: WikidataItem, articles: Mapping[str, Article]) -> _Text:
    """The object's own article, else its constellation's, else a Wikidata description."""
    article = articles.get(item.article_title) if item.article_title else None
    summary = summarize_extract(article.extract) if article else None
    if article and summary:
        return _Text(
            title=article.title,
            summary=summary,
            source=SummarySource.WIKIPEDIA,
            url=article.url,
            revised_at=article.revised_at,
            page_image=article.page_image,
        )
    parent = constellation_parent(item)
    parent_article = articles.get(parent.article_title) if parent and parent.article_title else None
    parent_summary = summarize_extract(parent_article.extract) if parent_article else None
    if parent_article and parent_summary:
        return _Text(
            scope=AboutScope.CONSTELLATION,
            title=constellation_title(parent_article.title),
            summary=parent_summary,
            source=SummarySource.WIKIPEDIA,
            url=parent_article.url,
            revised_at=parent_article.revised_at,
        )
    description = usable_wikidata_description(item.description)
    if description:
        return _Text(
            summary=description,
            source=SummarySource.WIKIDATA,
            url=f"https://www.wikidata.org/wiki/{item.qid}",
        )
    return _Text()


def _image_candidates(item: WikidataItem, text: _Text) -> list[str]:
    """Wikidata's image first, then the article's free page image."""
    names = [item.image_file, text.page_image]
    return list(dict.fromkeys(name for name in names if name))


def _acceptable(large: CommonsFile | None, small: CommonsFile | None) -> bool:
    """A Commons file with an allowlisted license, at least 320 px wide, with JPEG/PNG thumbs."""
    if large is None or small is None:
        return False
    meta = large.metadata
    non_free = meta.get("NonFree", "").strip().lower() in {"true", "1", "yes"}
    return (
        is_allowed_license(meta.get("LicenseShortName"), non_free=non_free)
        and large.original_width >= MIN_ORIGINAL_WIDTH_PX
        and _is_raster_thumb(large.thumb_url)
        and _is_raster_thumb(small.thumb_url)
    )


def _is_raster_thumb(url: str) -> bool:
    parts = urlsplit(url)
    return (
        parts.scheme == "https"
        and parts.hostname in IMAGE_HOSTS
        and parts.path.lower().endswith(_RASTER_THUMB_SUFFIXES)
    )


def _chunks[T](items: Sequence[T], size: int) -> Iterator[Sequence[T]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]
