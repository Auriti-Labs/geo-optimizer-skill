"""Tests for the shared JSON-LD walker (utils/jsonld.py, #535-cleanup).

Consolidates what used to be three independent @graph-unpacking implementations
(citability.py, audit_schema.py, schema_injector.py). These tests pin the
combined behavior directly, independent of any one caller.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from geo_optimizer.utils.jsonld import iter_jsonld_objects


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


class TestIterJsonldObjects:
    def test_plain_object(self):
        soup = _soup('<script type="application/ld+json">{"@type":"WebSite","name":"T"}</script>')
        objs = list(iter_jsonld_objects(soup))
        assert objs == [{"@type": "WebSite", "name": "T"}]

    def test_top_level_array(self):
        soup = _soup('<script type="application/ld+json">[{"@type":"WebSite"},{"@type":"Organization"}]</script>')
        objs = list(iter_jsonld_objects(soup))
        assert [o["@type"] for o in objs] == ["WebSite", "Organization"]

    def test_single_level_graph(self):
        soup = _soup(
            '<script type="application/ld+json">'
            '{"@context":"https://schema.org","@graph":['
            '{"@type":"WebSite"},{"@type":"Organization"}]}'
            "</script>"
        )
        objs = list(iter_jsonld_objects(soup))
        assert [o["@type"] for o in objs] == ["WebSite", "Organization"]

    def test_nested_graph(self):
        soup = _soup(
            '<script type="application/ld+json">'
            '{"@graph":[{"@graph":[{"@type":"Person","name":"A"}]},{"@type":"WebSite"}]}'
            "</script>"
        )
        objs = list(iter_jsonld_objects(soup))
        assert {o["@type"] for o in objs} == {"Person", "WebSite"}

    def test_context_and_id_propagated_to_children(self):
        soup = _soup(
            '<script type="application/ld+json">'
            '{"@context":"https://schema.org","@id":"https://example.com/#root",'
            '"@graph":[{"@type":"WebSite"}]}'
            "</script>"
        )
        (obj,) = list(iter_jsonld_objects(soup))
        assert obj["@context"] == "https://schema.org"
        assert obj["@id"] == "https://example.com/#root"

    def test_child_own_context_not_overwritten(self):
        soup = _soup(
            '<script type="application/ld+json">'
            '{"@context":"https://schema.org","@graph":['
            '{"@type":"WebSite","@context":"https://custom.example/"}]}'
            "</script>"
        )
        (obj,) = list(iter_jsonld_objects(soup))
        assert obj["@context"] == "https://custom.example/"

    def test_malformed_json_skipped_without_dropping_siblings(self):
        soup = _soup(
            '<script type="application/ld+json">{not valid json}</script>'
            '<script type="application/ld+json">{"@type":"WebSite"}</script>'
        )
        objs = list(iter_jsonld_objects(soup))
        assert objs == [{"@type": "WebSite"}]

    def test_on_parse_error_called_once_per_bad_script(self):
        soup = _soup(
            '<script type="application/ld+json">{bad one}</script>'
            '<script type="application/ld+json">{bad two}</script>'
            '<script type="application/ld+json">{"@type":"WebSite"}</script>'
        )
        errors = []
        objs = list(iter_jsonld_objects(soup, on_parse_error=errors.append))
        assert len(errors) == 2
        assert len(objs) == 1

    def test_oversized_script_skipped(self):
        big_name = "x" * 1000
        soup = _soup(f'<script type="application/ld+json">{{"@type":"Thing","name":"{big_name}"}}</script>')
        objs = list(iter_jsonld_objects(soup, max_bytes=100))
        assert objs == []

    def test_non_dict_items_in_array_skipped(self):
        soup = _soup('<script type="application/ld+json">[{"@type":"WebSite"}, "not an object", 42]</script>')
        objs = list(iter_jsonld_objects(soup))
        assert objs == [{"@type": "WebSite"}]

    def test_empty_script_skipped(self):
        soup = _soup('<script type="application/ld+json"></script>')
        assert list(iter_jsonld_objects(soup)) == []

    def test_no_scripts_yields_nothing(self):
        soup = _soup("<html><body><p>No JSON-LD here.</p></body></html>")
        assert list(iter_jsonld_objects(soup)) == []

    def test_document_order_preserved_across_scripts(self):
        soup = _soup(
            '<script type="application/ld+json">{"@type":"A"}</script>'
            '<script type="application/ld+json">{"@graph":[{"@type":"B"},{"@type":"C"}]}</script>'
            '<script type="application/ld+json">{"@type":"D"}</script>'
        )
        objs = list(iter_jsonld_objects(soup))
        assert [o["@type"] for o in objs] == ["A", "B", "C", "D"]
