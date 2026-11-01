"""Requests to and responses from Wikidata, Wikipedia and Commons, as plain data.

Builders only put validated identifiers into queries (NORAD numbers, COSPAR IDs, QIDs), so
catalog data can never change a query's meaning.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import unquote, urlsplit

from sattrack.enrich.domain import (
    CATEGORY_BY_CLASS,
    MAX_SUBCLASS_DEPTH,
    P_COSPAR_ID,
    P_IMAGE,
    P_INSTANCE_OF,
    P_MANUFACTURER,
    P_NORAD_ID,
    P_OPERATOR,
    P_PART_OF,
    P_SUBCLASS_OF,
    Category,
    PartOf,
    WikidataItem,
    is_cospar_id,
    is_qid,
)

WIKIPEDIA_BATCH = 20
COMMONS_BATCH = 50
_LIST_SEPARATOR = "|"

# --- Wikidata -------------------------------------------------------------------------------

_MATCH_QUERY = """
SELECT ?item ?id
  (SAMPLE(?links) AS ?sitelinks) (SAMPLE(?article) AS ?enwiki)
  (SAMPLE(?desc) AS ?description) (SAMPLE(?image) AS ?p18)
  (GROUP_CONCAT(DISTINCT STRAFTER(STR(?class), "entity/"); separator="|") AS ?classes)
  (GROUP_CONCAT(DISTINCT ?operatorLabel; separator="|") AS ?operators)
  (GROUP_CONCAT(DISTINCT ?manufacturerLabel; separator="|") AS ?manufacturers)
  (GROUP_CONCAT(DISTINCT CONCAT(STRAFTER(STR(?part), "entity/"), " ",
     COALESCE(STR(?partArticle), "")); separator="|") AS ?parts)
WHERE {
  VALUES ?id { $values }
  ?item wdt:$property ?id ; wikibase:sitelinks ?links .
  OPTIONAL { ?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> }
  OPTIONAL { ?item schema:description ?desc FILTER(LANG(?desc) = "en") }
  OPTIONAL { ?item wdt:$image ?image }
  OPTIONAL { ?item wdt:$instance_of ?class }
  OPTIONAL { ?item wdt:$operator ?operator .
             ?operator rdfs:label ?operatorLabel FILTER(LANG(?operatorLabel) = "en") }
  OPTIONAL { ?item wdt:$manufacturer ?manufacturer .
             ?manufacturer rdfs:label ?manufacturerLabel FILTER(LANG(?manufacturerLabel) = "en") }
  OPTIONAL { ?item wdt:$part_of ?part .
             OPTIONAL { ?partArticle schema:about ?part ;
                                     schema:isPartOf <https://en.wikipedia.org/> } }
}
GROUP BY ?item ?id
"""

_CLASS_QUERY = """
SELECT DISTINCT ?class ?target WHERE {
  VALUES ?class { $classes }
  VALUES ?target { $targets }
  ?class $path ?target .
}
"""


def _match_query(property_id: str, literals: Iterable[str]) -> str:
    values = " ".join(f'"{literal}"' for literal in literals)
    return (
        _MATCH_QUERY.replace("$values", values)
        .replace("$property", property_id)
        .replace("$image", P_IMAGE)
        .replace("$instance_of", P_INSTANCE_OF)
        .replace("$operator", P_OPERATOR)
        .replace("$manufacturer", P_MANUFACTURER)
        .replace("$part_of", P_PART_OF)
    )


def norad_match_query(norad_ids: Iterable[int]) -> str:
    """Items whose Satellite Catalog Number is one of these (Wikidata stores it as a string)."""
    return _match_query(P_NORAD_ID, (str(int(norad_id)) for norad_id in norad_ids))


def cospar_match_query(designators: Iterable[str]) -> str:
    valid = [d for d in designators if is_cospar_id(d)]
    return _match_query(P_COSPAR_ID, valid)


def class_category_query(classes: Iterable[str]) -> str:
    """Which category classes each class reaches through up to four "subclass of" steps."""
    path = "/".join([f"wdt:{P_SUBCLASS_OF}?"] * MAX_SUBCLASS_DEPTH)
    return (
        _CLASS_QUERY.replace("$classes", " ".join(f"wd:{q}" for q in classes if is_qid(q)))
        .replace("$targets", " ".join(f"wd:{q}" for q in CATEGORY_BY_CLASS))
        .replace("$path", path)
    )


def parse_match_rows(rows: Sequence[Mapping[str, str]]) -> dict[str, list[WikidataItem]]:
    """Matched items, keyed by the identifier they matched (NORAD number or COSPAR ID)."""
    matches: dict[str, list[WikidataItem]] = {}
    for row in rows:
        qid = _entity_id(row.get("item", ""))
        matched = row.get("id", "")
        if not is_qid(qid) or not matched:
            continue
        matches.setdefault(matched, []).append(
            WikidataItem(
                qid=qid,
                sitelinks=_int(row.get("sitelinks")),
                article_title=_article_title(row.get("enwiki")),
                description=row.get("description") or None,
                image_file=_commons_file_name(row.get("p18")),
                classes=tuple(q for q in _split(row.get("classes")) if is_qid(q)),
                operators=tuple(_split(row.get("operators"))),
                manufacturers=tuple(_split(row.get("manufacturers"))),
                parts=tuple(_parse_parts(row.get("parts"))),
            )
        )
    return matches


def parse_class_rows(rows: Sequence[Mapping[str, str]]) -> dict[str, frozenset[Category]]:
    found: dict[str, set[Category]] = {}
    for row in rows:
        target = CATEGORY_BY_CLASS.get(_entity_id(row.get("target", "")))
        if target is not None:
            found.setdefault(_entity_id(row.get("class", "")), set()).add(target)
    return {qid: frozenset(categories) for qid, categories in found.items()}


def _parse_parts(value: str | None) -> Iterable[PartOf]:
    for entry in _split(value):
        qid, _, article = entry.partition(" ")
        if is_qid(qid):
            yield PartOf(qid=qid, article_title=_article_title(article))


def _split(value: str | None) -> list[str]:
    return [part for part in (value or "").split(_LIST_SEPARATOR) if part.strip()]


def _entity_id(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def _int(value: str | None) -> int:
    try:
        return int(value or 0)
    except ValueError:
        return 0


def _article_title(url: str | None) -> str | None:
    """ "https://en.wikipedia.org/wiki/International_Space_Station" -> the article title."""
    if not url:
        return None
    parts = urlsplit(url)
    if parts.hostname != "en.wikipedia.org" or not parts.path.startswith("/wiki/"):
        return None
    return unquote(parts.path[len("/wiki/") :]).replace("_", " ") or None


def _commons_file_name(url: str | None) -> str | None:
    """P18 values are Special:FilePath URLs; returns "File:Name.jpg"."""
    if not url:
        return None
    name = unquote(urlsplit(url).path.rsplit("/", 1)[-1]).replace("_", " ")
    return normalize_file_title(name) if name else None


def normalize_file_title(name: str) -> str:
    """A Commons file title the way the API spells it: "File:Name with spaces.jpg"."""
    name = name.removeprefix("File:").replace("_", " ").strip()
    return f"File:{name[:1].upper()}{name[1:]}"


# --- Wikipedia -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Article:
    title: str
    extract: str
    url: str
    revised_at: datetime | None
    page_image: str | None


def wikipedia_params(titles: Sequence[str]) -> dict[str, str]:
    return {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "redirects": "1",
        "prop": "extracts|pageimages|pageprops|info",
        "exintro": "1",
        "explaintext": "1",
        "exlimit": str(WIKIPEDIA_BATCH),
        "piprop": "name",
        "pilicense": "free",
        "ppprop": "disambiguation",
        "inprop": "url",
        "titles": "|".join(titles),
    }


def parse_wikipedia(body: Mapping[str, Any], requested: Sequence[str]) -> dict[str, Article]:
    """Usable articles keyed by the requested title. Missing pages and disambiguations are left
    out; redirects and normalized titles are followed back to the requested title."""
    query = body.get("query") or {}
    renamed = _renames(query.get("normalized"), query.get("redirects"))
    pages = {page.get("title"): page for page in query.get("pages") or []}
    articles: dict[str, Article] = {}
    for title in requested:
        page = pages.get(_follow(title, renamed))
        article = _to_article(page) if page else None
        if article is not None:
            articles[title] = article
    return articles


def _to_article(page: Mapping[str, Any]) -> Article | None:
    if page.get("missing") or "disambiguation" in (page.get("pageprops") or {}):
        return None
    extract = page.get("extract")
    url = page.get("fullurl")
    if not isinstance(extract, str) or not extract.strip() or not isinstance(url, str):
        return None
    page_image = page.get("pageimage")
    return Article(
        title=str(page.get("title")),
        extract=extract,
        url=url,
        revised_at=_timestamp(page.get("touched")),
        page_image=normalize_file_title(page_image) if isinstance(page_image, str) else None,
    )


def _renames(*lists: Any) -> dict[str, str]:
    renames: dict[str, str] = {}
    for items in lists:
        for item in items or []:
            if isinstance(item, dict) and "from" in item and "to" in item:
                renames[str(item["from"])] = str(item["to"])
    return renames


def _follow(title: str, renamed: Mapping[str, str]) -> str:
    for _ in range(3):  # normalized, then redirected
        if title not in renamed:
            break
        title = renamed[title]
    return title


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


# --- Commons -------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CommonsFile:
    title: str
    page_url: str
    original_width: int
    thumb_url: str
    thumb_width: int
    thumb_height: int
    metadata: Mapping[str, str]


def commons_params(files: Sequence[str], width: int) -> dict[str, str]:
    return {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "prop": "imageinfo",
        "iiprop": "url|mime|size|extmetadata",
        "iiurlwidth": str(width),
        "titles": "|".join(files),
    }


def parse_commons(body: Mapping[str, Any], requested: Sequence[str]) -> dict[str, CommonsFile]:
    """Files found on Commons itself, keyed by the requested title."""
    query = body.get("query") or {}
    renamed = _renames(query.get("normalized"))
    pages = {page.get("title"): page for page in query.get("pages") or []}
    files: dict[str, CommonsFile] = {}
    for title in requested:
        page = pages.get(_follow(title, renamed))
        commons_file = _to_commons_file(page) if page else None
        if commons_file is not None:
            files[title] = commons_file
    return files


def _to_commons_file(page: Mapping[str, Any]) -> CommonsFile | None:
    # Files that live on Commons are "local" here; anything else (missing, shared from another
    # repository) is not hosted on Commons.
    if page.get("missing") or page.get("imagerepository") != "local":
        return None
    info = (page.get("imageinfo") or [None])[0]
    if not isinstance(info, dict) or not isinstance(info.get("thumburl"), str):
        return None
    metadata = {
        key: str(value.get("value", ""))
        for key, value in (info.get("extmetadata") or {}).items()
        if isinstance(value, dict)
    }
    return CommonsFile(
        title=str(page.get("title")),
        page_url=str(info.get("descriptionurl", "")),
        original_width=_int(str(info.get("width", 0))),
        # Commons appends utm_* tracking parameters to thumbnail URLs; the path alone is the file.
        thumb_url=urlsplit(info["thumburl"])._replace(query="", fragment="").geturl(),
        thumb_width=_int(str(info.get("thumbwidth", 0))),
        thumb_height=_int(str(info.get("thumbheight", 0))),
        metadata=metadata,
    )
