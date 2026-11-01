from __future__ import annotations

from sattrack.enrich.domain import Category, PartOf
from sattrack.enrich.sources import (
    class_category_query,
    cospar_match_query,
    norad_match_query,
    normalize_file_title,
    parse_class_rows,
    parse_commons,
    parse_match_rows,
    parse_wikipedia,
    wikipedia_params,
)

from ..wikimedia_fake import load


def _rows(name: str) -> list[dict[str, str]]:
    bindings = load(name)["results"]["bindings"]
    return [{key: cell["value"] for key, cell in row.items()} for row in bindings]


def test_norad_query_matches_on_the_satellite_catalog_number() -> None:
    query = norad_match_query([25544, 43013])
    assert 'VALUES ?id { "25544" "43013" }' in query
    assert "wdt:P377 ?id" in query


def test_cospar_query_only_includes_valid_designators() -> None:
    query = cospar_match_query(["1998-067A", 'bad" } DROP', "2026-101AB"])
    assert 'VALUES ?id { "1998-067A" "2026-101AB" }' in query
    assert "DROP" not in query


def test_class_query_follows_subclass_of_up_to_four_steps() -> None:
    query = class_category_query(["Q900100", "not-a-qid"])
    assert "VALUES ?class { wd:Q900100 }" in query
    assert "wdt:P279?/wdt:P279?/wdt:P279?/wdt:P279?" in query
    assert "wd:Q25956" in query


def test_parse_match_rows_groups_items_by_matched_id() -> None:
    matches = parse_match_rows(_rows("wikidata_norad.json"))

    station, module = matches["25544"]
    assert station.qid == "Q900001"
    assert station.article_title == "Synthetic Station"
    assert station.image_file == "File:Synthetic station.jpg"
    assert station.classes == ("Q900100",)
    assert station.operators == ("Agency B", "Agency A")
    assert module.parts == (PartOf("Q900001", "Synthetic Station"),)


def test_parse_class_rows_maps_classes_to_categories() -> None:
    mapping = parse_class_rows(_rows("wikidata_classes.json"))
    assert mapping["Q900100"] == frozenset({Category.SPACE_STATION, Category.CREWED})
    assert mapping["Q1285444"] == frozenset({Category.NAVIGATION})


def test_parse_wikipedia_drops_missing_and_disambiguation_pages() -> None:
    body = {
        "query": {
            "redirects": [{"from": "Old name", "to": "Real page"}],
            "pages": [
                {
                    "title": "Real page",
                    "extract": "Text.",
                    "fullurl": "https://en.wikipedia.org/wiki/Real_page",
                    "touched": "2026-10-20T08:00:00Z",
                    "pageimage": "Pic_one.jpg",
                },
                {"title": "Gone", "missing": True},
                {
                    "title": "Mercury",
                    "extract": "May refer to.",
                    "fullurl": "u",
                    "pageprops": {"disambiguation": ""},
                },
            ],
        }
    }

    articles = parse_wikipedia(body, ["Old name", "Gone", "Mercury"])

    assert set(articles) == {"Old name"}
    assert articles["Old name"].page_image == "File:Pic one.jpg"
    assert articles["Old name"].revised_at is not None


def test_wikipedia_request_asks_for_plain_intros_and_free_page_images() -> None:
    params = wikipedia_params(["A", "B"])
    assert params["titles"] == "A|B"
    assert (params["exintro"], params["explaintext"], params["pilicense"]) == ("1", "1", "free")


def test_parse_commons_keeps_only_files_hosted_on_commons() -> None:
    body = load("commons_960.json")
    body["query"]["pages"].append({"title": "File:Local only.jpg", "imagerepository": "shared"})

    files = parse_commons(body, ["File:Synthetic station.jpg", "File:Local only.jpg"])

    assert set(files) == {"File:Synthetic station.jpg"}
    station = files["File:Synthetic station.jpg"]
    assert (station.original_width, station.thumb_width, station.thumb_height) == (2400, 960, 640)
    assert station.metadata["LicenseShortName"] == "CC BY-SA 4.0"
    assert station.thumb_url == (
        "https://thumb.wikimedia.org/wikipedia/commons/thumb/0/0a/"
        "Synthetic_station.jpg/960px-Synthetic_station.jpg"
    )


def test_file_titles_are_normalized() -> None:
    assert normalize_file_title("iss_2021.jpg") == "File:Iss 2021.jpg"
    assert normalize_file_title("File:ISS 2021.jpg") == "File:ISS 2021.jpg"
