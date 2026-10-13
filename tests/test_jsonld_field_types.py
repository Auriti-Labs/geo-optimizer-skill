"""Regressione: campi JSON-LD con tipi inattesi non devono far fallire l'audit.

Il JSON-LD arriva da pagine di terzi. Un fuzzing su run_full_audit (un campo
alla volta sostituito con numero, stringa, null, lista mista, oggetto, booleano)
ha trovato 10 punti in cui un solo campo malformato sollevava AttributeError,
TypeError o KeyError e faceva fallire l'intero audit (errore 500 sul web).
I casi qui sotto sono quelli che sollevavano su main.
"""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest

from geo_optimizer.core.audit import run_full_audit
from geo_optimizer.utils.jsonld import first_object, schema_types, string_list

_URL = "https://example.com"


def _audit(jsonld: object, title: str = "Acme", h1: str = "Acme"):
    """Esegue run_full_audit su una homepage con il JSON-LD indicato, senza rete."""
    html = (
        f'<html lang="en"><head><title>{title}</title><meta name="description" content="Acme bakery">'
        f'<script type="application/ld+json">{json.dumps(jsonld)}</script></head>'
        f"<body><h1>{h1}</h1><p>Fresh bread every day.</p></body></html>"
    )

    def fake_fetch(url, *args, **kwargs):
        if url.rstrip("/") == _URL:
            return Mock(status_code=200, text=html, content=html.encode(), headers={}), None
        return None, "Not found"

    with (
        patch("geo_optimizer.core.audit.fetch_url", side_effect=fake_fetch),
        patch("geo_optimizer.core.audit.check_markdown_negotiation", return_value=False),
    ):
        return run_full_audit(_URL)


def _node(schema_type: str = "Organization", **fields) -> dict:
    return {"@context": "https://schema.org", "@type": schema_type, "name": "Acme", **fields}


# ─── Helper condivisi ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Product", ["Product"]),
        (["Thing", "LocalBusiness"], ["Thing", "LocalBusiness"]),
        ([1, "Product", None, {"x": 1}, ""], ["Product"]),
        (123, []),
        (None, []),
        ({"@type": "Product"}, []),
    ],
)
def test_jsonld_schema_types_keeps_only_strings(value, expected):
    assert schema_types(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ({"price": "1"}, {"price": "1"}),
        (["$10", {"price": "2"}], {"price": "2"}),
        ("$10", {}),
        ([], {}),
        (None, {}),
    ],
)
def test_jsonld_first_object_returns_a_dict(value, expected):
    assert first_object(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://a.example", ["https://a.example"]),
        (["https://a.example", 3, None, " "], ["https://a.example"]),
        ({"x": 1}, []),
        (123, []),
    ],
)
def test_jsonld_string_list_returns_strings(value, expected):
    assert string_list(value) == expected


# ─── Audit completo: nessuna eccezione ───────────────────────────────────────


@pytest.mark.parametrize(
    "jsonld",
    [
        pytest.param(_node(**{"@type": 123}), id="type-number"),
        pytest.param(_node(**{"@type": {"x": 1}}), id="type-object"),
        pytest.param(_node(**{"@type": ["Organization", None]}), id="type-list-with-null"),
        pytest.param(_node(**{"@type": [{"@type": 5}]}), id="type-list-of-objects"),
        pytest.param(_node("Product", offers="$10"), id="offers-string"),
        pytest.param(_node("Product", offers=["$10"]), id="offers-list-of-strings"),
        pytest.param(_node("Product", aggregateRating="4.5"), id="aggregaterating-string"),
        pytest.param(_node("Product", aggregateRating=[]), id="aggregaterating-empty-list"),
        pytest.param(_node(sameAs=123), id="sameas-number"),
        pytest.param(_node(sameAs={"x": 1}), id="sameas-object"),
        pytest.param(_node(sameAs=[1, "https://a.example", None]), id="sameas-mixed-list"),
        pytest.param(_node("WebSite", potentialAction={"@type": ["SearchAction", 3]}), id="action-type-list"),
        pytest.param({"@context": "https://schema.org", "@graph": None}, id="graph-null"),
        pytest.param({"@context": "https://schema.org", "@graph": [5, None]}, id="graph-scalars"),
        pytest.param([1, None, "x"], id="top-level-list-of-scalars"),
    ],
)
def test_full_audit_malformed_jsonld_field_does_not_raise(jsonld):
    result = _audit(jsonld)

    assert result.http_status == 200
    assert 0 <= result.score <= 100


def test_full_audit_aggregaterating_string_is_not_counted_as_rating():
    from bs4 import BeautifulSoup

    from geo_optimizer.core.citability import detect_shopping_readiness

    product = _node("Product", offers={"price": "1", "availability": "InStock"}, aggregateRating="4.5")
    soup = BeautifulSoup(f'<script type="application/ld+json">{json.dumps(product)}</script>', "html.parser")

    result = detect_shopping_readiness(soup)

    assert result.score == 1  # solo prezzo + disponibilita'
    assert result.details["has_rating"] is False


# ─── Brand: sottotipi di Organization ────────────────────────────────────────


def test_brand_localbusiness_name_counts_for_name_consistency():
    """Prima il nome contava solo con @type "Organization" letterale."""
    result = _audit(_node("LocalBusiness", name="Acme Bakery"), title="Acme Bakery | Fresh bread", h1="Baked daily")

    assert result.brand_entity.brand_name_consistent is True


def test_brand_organization_name_consistency_unchanged():
    result = _audit(_node("Organization", name="Acme Bakery"), title="Acme Bakery | Fresh bread", h1="Baked daily")

    assert result.brand_entity.brand_name_consistent is True


def test_brand_contact_info_with_type_list():
    """@type ["Thing", "LocalBusiness"]: prima si guardava solo il primo tipo."""
    result = _audit(_node(**{"@type": ["Thing", "LocalBusiness"], "telephone": "+39 06 000000"}))

    assert result.brand_entity.has_contact_info is True
