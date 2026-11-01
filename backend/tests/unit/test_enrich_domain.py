from __future__ import annotations

from collections.abc import Mapping

import pytest

from sattrack.enrich.domain import (
    CATEGORY_CLASSES,
    P_COSPAR_ID,
    P_IMAGE,
    P_INSTANCE_OF,
    P_MANUFACTURER,
    P_NORAD_ID,
    P_OPERATOR,
    P_PART_OF,
    P_SUBCLASS_OF,
    SUMMARY_MAX_CHARS,
    Category,
    PartOf,
    WikidataItem,
    categories_for,
    choose_item,
    clean_extract,
    constellation_parent,
    constellation_title,
    image_alt_text,
    image_artist,
    is_allowed_license,
    strip_html,
    summarize_extract,
    trim_summary,
    unique_labels,
    usable_wikidata_description,
)


def item(
    qid: str, sitelinks: int = 1, article: str | None = None, **kwargs: object
) -> WikidataItem:
    return WikidataItem(
        qid=qid,
        sitelinks=sitelinks,
        article_title=article,
        description=None,
        image_file=None,
        **kwargs,  # type: ignore[arg-type]
    )


def test_wikidata_property_ids_are_pinned() -> None:
    # Verified on Wikidata on 2026-11-01; a change here must be checked there again.
    assert (P_NORAD_ID, P_COSPAR_ID, P_INSTANCE_OF, P_SUBCLASS_OF) == (
        "P377",
        "P247",
        "P31",
        "P279",
    )
    assert (P_OPERATOR, P_MANUFACTURER, P_PART_OF, P_IMAGE) == ("P137", "P176", "P361", "P18")
    assert CATEGORY_CLASSES[Category.SPACE_STATION] == ("Q25956",)
    assert CATEGORY_CLASSES[Category.CUBESAT] == ("Q1142930",)


class TestChooseItem:
    def test_prefers_an_item_with_an_english_article(self) -> None:
        chosen = choose_item([item("Q1", sitelinks=90), item("Q2", sitelinks=3, article="Station")])
        assert chosen is not None and chosen.qid == "Q2"

    def test_then_the_most_sitelinks(self) -> None:
        station = item("Q25271", sitelinks=136, article="International Space Station")
        module = item("Q331785", sitelinks=37, article="Zarya (ISS module)")
        chosen = choose_item([module, station])
        assert chosen is not None and chosen.qid == "Q25271"

    def test_then_the_lowest_qid_number(self) -> None:
        chosen = choose_item([item("Q900", 5, "A"), item("Q12", 5, "B"), item("Q100", 5, "C")])
        assert chosen is not None and chosen.qid == "Q12"

    def test_none_without_candidates(self) -> None:
        assert choose_item([]) is None


class TestConstellation:
    def test_uses_a_parent_with_an_article_when_the_item_has_none(self) -> None:
        member = item("Q5", parts=(PartOf("Q9", None), PartOf("Q7", "Starlink")))
        assert constellation_parent(member) == PartOf("Q7", "Starlink")

    def test_not_used_when_the_item_has_its_own_article(self) -> None:
        member = item("Q5", article="Own article", parts=(PartOf("Q7", "Starlink"),))
        assert constellation_parent(member) is None

    @pytest.mark.parametrize(
        ("title", "expected"),
        [
            ("Starlink", "Starlink constellation"),
            ("Iridium satellite constellation", "Iridium satellite constellation"),
            ("Global Positioning System", "Global Positioning System"),
            ("Testnet (satellite navigation system)", "Testnet constellation"),
            ("B-chain (satellite constellation)", "B-chain constellation"),
        ],
    )
    def test_heading_title(self, title: str, expected: str) -> None:
        assert constellation_title(title) == expected


class TestSummary:
    def test_cleans_whitespace_pronunciations_and_empty_parentheses(self) -> None:
        text = "The  Station (/STAY-shun/; listen) is   big ( ; ) and old . Really."
        assert clean_extract(text) == "The Station is big and old. Really."

    def test_keeps_at_most_three_sentences(self) -> None:
        text = "One is here. Two is here. Three is here. Four is here."
        assert trim_summary(text) == "One is here. Two is here. Three is here."

    def test_stops_before_a_sentence_that_would_pass_420_characters(self) -> None:
        first = "A" + "a" * 199 + "."
        second = "B" + "b" * 249 + "."
        assert trim_summary(f"{first} {second}") == first

    def test_cuts_a_very_long_first_sentence_at_a_word_boundary(self) -> None:
        text = ("word " * 120).strip() + "."
        result = trim_summary(text)
        assert result is not None
        assert len(result) <= SUMMARY_MAX_CHARS
        assert result.endswith("word…")

    def test_does_not_split_after_initials(self) -> None:
        text = "It is operated by the U.S. Navy. Second. Third. Fourth."
        assert trim_summary(text) == "It is operated by the U.S. Navy. Second. Third."

    def test_empty_extract_gives_nothing(self) -> None:
        assert summarize_extract("   ") is None

    @pytest.mark.parametrize(
        "description", ["satellite", "Artificial satellite", "spacecraft", "CubeSat", "space probe"]
    )
    def test_generic_wikidata_descriptions_are_rejected(self, description: str) -> None:
        assert usable_wikidata_description(description) is None

    def test_short_wikidata_descriptions_are_rejected(self) -> None:
        assert usable_wikidata_description("Russian satellite") is None

    def test_specific_wikidata_descriptions_are_kept_and_capitalized(self) -> None:
        assert (
            usable_wikidata_description("american weather satellite")
            == "American weather satellite"
        )


class TestLicense:
    @pytest.mark.parametrize(
        "name",
        [
            "Public domain",
            "PD-USGov-NASA",
            "CC0",
            "CC0 1.0",
            "CC BY 4.0",
            "CC BY-SA 3.0",
            "CC BY-SA 2.0 de",
            "CC BY-SA 3.0 igo",
            "cc-by-sa-4.0",
        ],
    )
    def test_allowlisted(self, name: str) -> None:
        assert is_allowed_license(name, non_free=False)

    @pytest.mark.parametrize(
        "name", ["GFDL", "CC BY-NC 2.0", "CC BY-ND 4.0", "Copyrighted free use", "", None]
    )
    def test_rejected(self, name: str | None) -> None:
        assert not is_allowed_license(name, non_free=False)

    def test_anything_marked_non_free_is_rejected(self) -> None:
        assert not is_allowed_license("CC BY 4.0", non_free=True)


class TestCredit:
    def test_strips_html_and_collapses_whitespace(self) -> None:
        html = '<a href="//commons.wikimedia.org/wiki/User:X">Jane   Doe</a> &amp; <i>NASA</i>'
        assert strip_html(html) == "Jane Doe & NASA"

    def test_artist_falls_back_to_credit_then_to_commons(self) -> None:
        assert image_artist(None, "<span>ESA</span>") == "ESA"
        assert image_artist("  ", None) == "Wikimedia Commons"

    def test_artist_and_alt_text_are_truncated(self) -> None:
        assert len(image_artist("x" * 300, None)) == 120
        assert len(image_alt_text("<p>" + "y" * 300 + "</p>")) == 200
        assert image_alt_text(None) == ""


CLASS_CATEGORIES: Mapping[str, frozenset[Category]] = {
    "Q100": frozenset({Category.SPACE_STATION, Category.CREWED}),
    "Q200": frozenset({Category.SCIENCE}),
    "Q300": frozenset({Category.CUBESAT}),
    "Q400": frozenset({Category.COMMUNICATIONS, Category.MILITARY}),
}


class TestCategories:
    def test_maps_classes_in_priority_order_with_two_chips_at_most(self) -> None:
        assert categories_for(["Q200", "Q100"], CLASS_CATEGORIES) == ("space_station", "crewed")

    def test_cubesat_is_the_second_chip(self) -> None:
        assert categories_for(["Q300", "Q400"], CLASS_CATEGORIES) == ("communications", "cubesat")
        assert categories_for(["Q300"], CLASS_CATEGORIES) == ("cubesat",)

    def test_unmapped_classes_give_no_chip(self) -> None:
        assert categories_for(["Q999"], CLASS_CATEGORIES) == ()


def test_unique_labels_are_sorted_distinct_and_capped() -> None:
    assert unique_labels(["NASA", " NASA", "ESA", "", "JAXA"], 2) == ("ESA", "JAXA")
