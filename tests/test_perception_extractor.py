"""Tests for geo_optimizer.core.perception_extractor — extract_perception()."""

from __future__ import annotations

from unittest.mock import MagicMock

from geo_optimizer.core.perception_extractor import extract_perception
from geo_optimizer.models.results import AuditResult

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_brand(names=None, has_about=True, has_contact=True, kg_count=1):
    b = MagicMock()
    b.names_found = names if names is not None else ["Acme Corp"]
    b.has_about_link = has_about
    b.has_contact_info = has_contact
    b.kg_pillar_count = kg_count
    return b


def _make_schema(found_types=None, has_faq=True, has_article=True, ecommerce_signals=None):
    s = MagicMock()
    s.found_types = found_types if found_types is not None else ["Organization", "WebSite"]
    s.has_faq = has_faq
    s.has_article = has_article
    s.ecommerce_signals = ecommerce_signals if ecommerce_signals is not None else []
    return s


def _make_citability(grade="A", methods=None):
    c = MagicMock()
    c.grade = grade
    c.methods = methods or []
    return c


def _make_trust(composite_score=0.85):
    t = MagicMock()
    t.composite_score = composite_score
    return t


def _make_factual(supported=None, unsupported=None):
    f = MagicMock()
    f.supported_claims = supported or []
    f.unsupported_claims = unsupported or []
    return f


def _make_audit(**kwargs) -> AuditResult:
    audit = MagicMock()
    audit.url = kwargs.get("url", "https://example.com")
    audit.brand_entity = kwargs.get("brand_entity", _make_brand())
    audit.schema = kwargs.get("schema", _make_schema())
    audit.citability = kwargs.get("citability", _make_citability())
    audit.trust_stack = kwargs.get("trust_stack", _make_trust())
    audit.factual_accuracy = kwargs.get("factual_accuracy", _make_factual())
    return audit


# ─── Tests: disclaimer always present ─────────────────────────────────────────


def test_disclaimer_always_populated():
    audit = _make_audit()
    snap = extract_perception(audit)
    assert snap.disclaimer != ""
    assert "Simulated" in snap.disclaimer or "simulated" in snap.disclaimer.lower()


# ─── Tests: brand entity extraction ──────────────────────────────────────────


def test_brand_name_extracted():
    audit = _make_audit(brand_entity=_make_brand(names=["GEO Optimizer"]))
    snap = extract_perception(audit)
    assert snap.brand_name == "GEO Optimizer"


def test_brand_name_empty_when_no_names():
    audit = _make_audit(brand_entity=_make_brand(names=[]))
    snap = extract_perception(audit)
    assert snap.brand_name is None


def test_brand_entity_type_organization():
    audit = _make_audit(schema=_make_schema(found_types=["Organization", "WebSite"]))
    snap = extract_perception(audit)
    assert snap.brand_entity_type == "Organization"


def test_brand_entity_type_product():
    audit = _make_audit(schema=_make_schema(found_types=["SoftwareApplication"]))
    snap = extract_perception(audit)
    assert snap.brand_entity_type == "SoftwareApplication"


# ─── Tests: schema types ─────────────────────────────────────────────────────


def test_schema_types_present():
    audit = _make_audit(schema=_make_schema(found_types=["Organization", "FAQPage"]))
    snap = extract_perception(audit)
    assert "Organization" in snap.schema_types_present
    assert "FAQPage" in snap.schema_types_present


def test_schema_types_empty_when_no_schema():
    audit = _make_audit()
    audit.schema = None
    snap = extract_perception(audit)
    assert snap.schema_types_present == []


# ─── Tests: citability ────────────────────────────────────────────────────────


def test_citability_grade_extracted():
    audit = _make_audit(citability=_make_citability(grade="B+"))
    snap = extract_perception(audit)
    assert snap.citability_grade == "B+"


def test_citation_worthy_facts_high_score():
    m1 = MagicMock()
    m1.name = "has_statistics"
    m1.score = 8
    m1.max_score = 10
    m2 = MagicMock()
    m2.name = "has_citations"
    m2.score = 3
    m2.max_score = 10
    audit = _make_audit(citability=_make_citability(grade="A", methods=[m1, m2]))
    snap = extract_perception(audit)
    assert "has_statistics" in snap.citation_worthy_facts
    assert "has_citations" not in snap.citation_worthy_facts


# ─── Tests: trust ─────────────────────────────────────────────────────────────


def test_trust_score_extracted():
    audit = _make_audit(trust_stack=_make_trust(composite_score=0.72))
    snap = extract_perception(audit)
    assert abs(snap.trust_score - 0.72) < 0.001


def test_trust_score_none_when_missing():
    audit = _make_audit()
    audit.trust_stack = None
    snap = extract_perception(audit)
    assert snap.trust_score is None


# ─── Tests: factual claims ────────────────────────────────────────────────────


def test_supported_claims_extracted():
    audit = _make_audit(factual_accuracy=_make_factual(supported=["claim A", "claim B"]))
    snap = extract_perception(audit)
    assert "claim A" in snap.supported_claims


def test_unsupported_claims_extracted():
    audit = _make_audit(factual_accuracy=_make_factual(unsupported=["unverified claim"]))
    snap = extract_perception(audit)
    assert "unverified claim" in snap.unsupported_claims


# ─── Tests: missing authority signals ─────────────────────────────────────────


def test_missing_about_link():
    audit = _make_audit(brand_entity=_make_brand(has_about=False))
    snap = extract_perception(audit)
    assert any("/about" in s for s in snap.missing_authority_signals)


def test_missing_kg_pillars():
    audit = _make_audit(brand_entity=_make_brand(kg_count=0))
    snap = extract_perception(audit)
    assert any("Knowledge Graph" in s for s in snap.missing_authority_signals)


def test_missing_faq_schema():
    audit = _make_audit(schema=_make_schema(has_faq=False))
    snap = extract_perception(audit)
    assert any("FAQ" in s for s in snap.missing_authority_signals)


# ─── Tests: None sub-results handled gracefully ───────────────────────────────


def test_all_none_sub_results():
    audit = _make_audit(
        brand_entity=None,
        schema=None,
        citability=None,
        trust_stack=None,
        factual_accuracy=None,
    )

    snap = extract_perception(audit)

    assert snap.url == "https://example.com"
    assert snap.brand_name is None
    assert snap.schema_types_present == []
    assert snap.trust_score is None
    assert snap.disclaimer != ""


# ─── Tests: ai_readable_summary ───────────────────────────────────────────────


def test_ai_readable_summary_built():
    audit = _make_audit(
        brand_entity=_make_brand(names=["Acme"]),
        schema=_make_schema(found_types=["Organization"]),
        citability=_make_citability(grade="A"),
    )
    snap = extract_perception(audit)
    assert snap.ai_readable_summary is not None
    assert "Acme" in snap.ai_readable_summary


def test_ai_readable_summary_none_when_no_signals():
    audit = _make_audit(
        brand_entity=_make_brand(names=[]),
        schema=_make_schema(found_types=[]),
        citability=_make_citability(grade=None),
        trust_stack=None,
        factual_accuracy=None,
    )
    snap = extract_perception(audit)
    assert snap.ai_readable_summary is None
