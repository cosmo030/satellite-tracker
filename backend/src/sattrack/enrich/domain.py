"""Rules for turning Wikimedia data into object descriptions. Pure functions; no I/O.

Spec: docs/adr/0006-wikimedia-descriptions-and-images.md.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from html.parser import HTMLParser

# Wikidata properties, verified on Wikidata on 2026-11-01 (pinned by a unit test).
P_NORAD_ID = "P377"  # Satellite Catalog Number (SCN), as a string without leading zeros
P_COSPAR_ID = "P247"  # International designator, e.g. "1998-067A" (CelesTrak OBJECT_ID)
P_INSTANCE_OF = "P31"
P_SUBCLASS_OF = "P279"
P_OPERATOR = "P137"
P_MANUFACTURER = "P176"
P_PART_OF = "P361"
P_IMAGE = "P18"  # Always a Wikimedia Commons file

# Classes are mapped to categories by following "subclass of" up to this many steps.
MAX_SUBCLASS_DEPTH = 4


class Category(StrEnum):
    """Purpose categories, in display priority order."""

    SPACE_STATION = "space_station"
    CREWED = "crewed"
    TELESCOPE = "telescope"
    EARTH_OBSERVATION = "earth_observation"
    WEATHER = "weather"
    NAVIGATION = "navigation"
    COMMUNICATIONS = "communications"
    SCIENCE = "science"
    TECHNOLOGY = "technology"
    AMATEUR = "amateur"
    MILITARY = "military"
    CUBESAT = "cubesat"


# Wikidata classes that put an object in a category (verified 2026-11-01).
CATEGORY_CLASSES: Mapping[Category, tuple[str, ...]] = {
    Category.SPACE_STATION: ("Q25956",),  # space station
    Category.CREWED: ("Q7217761",),  # crewed spacecraft
    Category.TELESCOPE: ("Q148578",),  # space telescope (alias: space observatory)
    Category.EARTH_OBSERVATION: (
        "Q854845",  # Earth observation satellite
        "Q60963420",  # remote sensing satellite
        "Q466421",  # reconnaissance satellite
    ),
    Category.WEATHER: ("Q209363",),  # weather satellite
    Category.NAVIGATION: ("Q1285444",),  # navigation satellite (alias: GNSS satellite)
    Category.COMMUNICATIONS: ("Q149918",),  # communications satellite
    Category.SCIENCE: ("Q105839698",),  # research satellite
    Category.TECHNOLOGY: ("Q95945728",),  # technology demonstration spacecraft
    Category.AMATEUR: ("Q455647",),  # amateur radio satellite
    Category.MILITARY: ("Q973887",),  # military satellite
    Category.CUBESAT: ("Q1142930",),  # CubeSat
}
CATEGORY_BY_CLASS: Mapping[str, Category] = {
    qid: category for category, qids in CATEGORY_CLASSES.items() for qid in qids
}

MAX_CATEGORIES = 2
MAX_OPERATORS = 5
MAX_MANUFACTURERS = 3
SUMMARY_MAX_SENTENCES = 3
SUMMARY_MAX_CHARS = 420
ARTIST_MAX_CHARS = 120
ALT_TEXT_MAX_CHARS = 200
MIN_ORIGINAL_WIDTH_PX = 320
ELLIPSIS = "…"

# Descriptions too generic to be worth showing ("artificial satellite" says nothing new).
GENERIC_DESCRIPTIONS = frozenset(
    {"satellite", "artificial satellite", "spacecraft", "space probe", "cubesat"}
)
MIN_DESCRIPTION_WORDS = 3

_QID = re.compile(r"Q[1-9][0-9]{0,11}")
_COSPAR = re.compile(r"[0-9]{4}-[0-9]{3}[A-Z]{1,3}")


@dataclass(frozen=True, slots=True)
class PartOf:
    """An item this item is part of (constellation or series), with its English article."""

    qid: str
    article_title: str | None


@dataclass(frozen=True, slots=True)
class WikidataItem:
    """One Wikidata item matched to a catalogued object."""

    qid: str
    sitelinks: int
    article_title: str | None
    description: str | None
    image_file: str | None
    classes: tuple[str, ...] = ()
    operators: tuple[str, ...] = ()
    manufacturers: tuple[str, ...] = ()
    parts: tuple[PartOf, ...] = ()


def is_qid(value: str) -> bool:
    return _QID.fullmatch(value) is not None


def is_cospar_id(value: str) -> bool:
    return _COSPAR.fullmatch(value) is not None


def qid_number(qid: str) -> int:
    return int(qid[1:])


def choose_item(items: Sequence[WikidataItem]) -> WikidataItem | None:
    """Pick one item when several match an object (a station and one of its modules, say).

    Prefer an item with an English Wikipedia article, then the most sitelinks, then the
    lowest QID number.
    """
    if not items:
        return None
    return min(items, key=lambda i: (i.article_title is None, -i.sitelinks, qid_number(i.qid)))


def constellation_parent(item: WikidataItem) -> PartOf | None:
    """The constellation or series to describe instead, when the item has no article."""
    if item.article_title is not None:
        return None
    with_article = [part for part in item.parts if part.article_title]
    return min(with_article, key=lambda p: qid_number(p.qid)) if with_article else None


_CONSTELLATION_WORDS = ("constellation", "satellites", "system", "program", "programme", "series")
# Wikipedia's disambiguation suffix, as in "Galileo (satellite navigation system)".
_DISAMBIGUATION = re.compile(r"\s*\([^()]*\)$")


def constellation_title(article_title: str) -> str:
    """How a constellation is named in the heading: "About the Starlink constellation"."""
    name = _DISAMBIGUATION.sub("", article_title) or article_title
    if name.lower().endswith(_CONSTELLATION_WORDS):
        return name
    return f"{name} constellation"


# --- Description text -----------------------------------------------------------------------

_WHITESPACE = re.compile(r"\s+")
# Parentheses holding a pronunciation: IPA between slashes, "pronounced", "listen".
_PRONUNCIATION = re.compile(
    r"\s*\((?:[^()]*?(?:/[^/()]+/|\bpronounced\b|\blisten\b)[^()]*?)\)", re.IGNORECASE
)
# Parentheses left empty (or with only punctuation) once the pronunciation is gone.
_EMPTY_PARENS = re.compile(r"\s*\(\s*[;,:]?\s*\)")
_SPACE_BEFORE_PUNCTUATION = re.compile(r"\s+([,.;:!?])")
# A sentence ends at . ! ? followed by a space and a capital, digit or quote; not after a
# single capital (initials such as "U.S.").
_OPENING_QUOTES = '"' + chr(0x201C) + chr(0x2018)  # straight, curly double, curly single
_SENTENCE_BREAK = re.compile(
    r"(?<=[.!?])(?<!\b[A-Z]\.)\s+(?=[A-Z0-9" + re.escape(_OPENING_QUOTES) + "(])"
)


def clean_extract(text: str) -> str:
    """Tidy a plain-text Wikipedia intro: whitespace, pronunciations, empty parentheses."""
    text = _WHITESPACE.sub(" ", text)
    text = _PRONUNCIATION.sub("", text)
    text = _EMPTY_PARENS.sub("", text)
    text = _SPACE_BEFORE_PUNCTUATION.sub(r"\1", text)
    return text.strip()


def trim_summary(text: str) -> str | None:
    """At most 3 sentences and 420 characters, cut at a sentence boundary.

    A first sentence longer than 420 characters is cut at the last word boundary before the
    limit and ends with an ellipsis.
    """
    text = text.strip()
    if not text:
        return None
    kept: list[str] = []
    for sentence in _SENTENCE_BREAK.split(text)[:SUMMARY_MAX_SENTENCES]:
        if len(" ".join([*kept, sentence])) > SUMMARY_MAX_CHARS:
            break
        kept.append(sentence)
    if kept:
        return " ".join(kept)
    cut = text[: SUMMARY_MAX_CHARS - len(ELLIPSIS)]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,;:") + ELLIPSIS


def summarize_extract(extract: str) -> str | None:
    return trim_summary(clean_extract(extract))


def usable_wikidata_description(description: str | None) -> str | None:
    """A Wikidata description worth showing: three words or more and not generic."""
    if not description:
        return None
    text = _WHITESPACE.sub(" ", description).strip()
    if text.lower() in GENERIC_DESCRIPTIONS or len(text.split()) < MIN_DESCRIPTION_WORDS:
        return None
    return text[0].upper() + text[1:]


# --- Image credit and license -----------------------------------------------------------------


class _TextOnly(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def strip_html(value: str) -> str:
    """Plain text from an HTML fragment (Commons metadata), with whitespace collapsed."""
    parser = _TextOnly()
    parser.feed(value)
    parser.close()
    return _WHITESPACE.sub(" ", "".join(parser.parts)).strip()


def truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - len(ELLIPSIS)].rstrip() + ELLIPSIS


def image_artist(artist_html: str | None, credit_html: str | None) -> str:
    """Credit line author: Artist, else Credit, else "Wikimedia Commons"."""
    for value in (artist_html, credit_html):
        text = strip_html(value) if value else ""
        if text:
            return truncate(text, ARTIST_MAX_CHARS)
    return "Wikimedia Commons"


def image_alt_text(description_html: str | None) -> str:
    return truncate(strip_html(description_html), ALT_TEXT_MAX_CHARS) if description_html else ""


# Allowlist: public domain marks, CC0, and CC BY / CC BY-SA in any version or port.
_CC_BY = re.compile(r"cc[ -]by(?:-sa)?(?:[ -]\d+(?:\.\d+)?)?(?:[ -][a-z]{2,4})*")


def is_allowed_license(license_short_name: str | None, *, non_free: bool) -> bool:
    if non_free or not license_short_name:
        return False
    name = _WHITESPACE.sub(" ", license_short_name).strip().lower()
    if name == "pd" or name.startswith(("pd-", "pd ", "public domain")):
        return True
    if name.startswith(("cc0", "cc-zero", "cc zero")):
        return True
    return _CC_BY.fullmatch(name) is not None


# --- Purpose categories -------------------------------------------------------------------


def categories_for(
    classes: Iterable[str], class_categories: Mapping[str, frozenset[Category]]
) -> tuple[str, ...]:
    """Up to two category keys for an object's classes, in priority order.

    CubeSat is a form factor, so it is shown as the second chip next to the object's purpose.
    """
    found: set[Category] = set()
    for qid in classes:
        found |= class_categories.get(qid, frozenset())
    ordered = [category for category in Category if category in found]
    if Category.CUBESAT in found:
        purpose = [c for c in ordered if c is not Category.CUBESAT][: MAX_CATEGORIES - 1]
        ordered = [*purpose, Category.CUBESAT]
    return tuple(category.value for category in ordered[:MAX_CATEGORIES])


def unique_labels(labels: Iterable[str], limit: int) -> tuple[str, ...]:
    """Distinct non-empty labels in a stable (alphabetical) order, at most ``limit``."""
    cleaned = {_WHITESPACE.sub(" ", label).strip() for label in labels}
    return tuple(sorted(label for label in cleaned if label))[:limit]
