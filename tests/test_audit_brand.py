from __future__ import annotations

from bs4 import BeautifulSoup

from geo_optimizer.core.audit_brand import audit_brand_entity
from geo_optimizer.core.citability import _TITLE_SEPARATOR_RE
from geo_optimizer.models.results import ContentResult, MetaResult, SchemaResult


def _html(title: str, og: str | None = None, h1: str | None = None, schema_json: str | None = None):
    og_tag = f'<meta property="og:title" content="{og}">' if og else ""
    ld = f'<script type="application/ld+json">{schema_json}</script>' if schema_json else ""
    h1_tag = f"<h1>{h1}</h1>" if h1 else ""
    return BeautifulSoup(
        f"<html><head><title>{title}</title>{og_tag}{ld}</head><body>{h1_tag}</body></html>",
        "html.parser",
    )


def _audit(soup, schema_result: SchemaResult | None = None):
    return audit_brand_entity(
        soup, schema_result or SchemaResult(), MetaResult(title_text=soup.title.get_text()), ContentResult()
    )


def test_non_string_schema_name_does_not_crash():
    soup = _html("Acme", schema_json='{"@type":"Organization","name":{"@value":"Acme"}}')
    result = _audit(soup, SchemaResult(raw_schemas=[{"@type": "Organization", "name": {"@value": "Acme"}}]))

    assert {"@value": "Acme"} not in result.names_found


def test_title_and_identical_og_title_are_one_source():
    soup = _html("Acme | Home", og="Acme | Home")

    assert _audit(soup).brand_name_consistent is False


def test_title_plus_schema_is_consistent():
    soup = _html("Acme | Home", schema_json='{"@type":"Organization","name":"Acme"}')
    schema = SchemaResult(raw_schemas=[{"@type": "Organization", "name": "Acme"}])

    assert _audit(soup, schema).brand_name_consistent is True


def test_hyphenated_brand_is_not_split():
    assert _TITLE_SEPARATOR_RE.split("Coca-Cola | Home")[0] == "Coca-Cola"
    assert _TITLE_SEPARATOR_RE.split("Acme - Home")[0] == "Acme"
