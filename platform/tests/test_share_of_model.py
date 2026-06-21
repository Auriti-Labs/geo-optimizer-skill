"""Pure analysis / Share-of-Model / hallucination tests (no I/O)."""

from __future__ import annotations

from geoready_platform.services.probe import hallucination
from geoready_platform.services.probe.analysis import analyze_response
from geoready_platform.services.probe.share_of_model import AnalyzedResponse, compute_share_of_model


# ─── analysis ────────────────────────────────────────────────────────────────


def test_analyze_detects_brand_domain_and_competitors():
    sig = analyze_response(
        text="Acme is great. Competitors include Globex.",
        citations=["https://acme.com/about", "https://globex.com"],
        name="Acme",
        domain="acme.com",
    )
    assert sig.brand_mentioned is True
    assert sig.domain_cited is True
    assert "globex.com" in sig.competitor_domains
    assert "acme.com" not in sig.competitor_domains


def test_analyze_competitor_name_matching():
    sig = analyze_response(
        text="You should consider Globex instead.",
        citations=[],
        name="Acme",
        domain="acme.com",
        competitor_names=["Globex", "Initech"],
    )
    assert sig.competitor_names == ["Globex"]
    assert sig.brand_mentioned is False


# ─── share of model ──────────────────────────────────────────────────────────


def test_share_of_model_only_counts_share_categories():
    responses = [
        AnalyzedResponse(category="category_recommendation", answered=True, brand_mentioned=True),
        AnalyzedResponse(category="category_recommendation", answered=True, brand_mentioned=False),
        AnalyzedResponse(category="problem_solution", answered=True, brand_mentioned=True),
        # factual category must NOT affect share-of-model denominator
        AnalyzedResponse(category="factual_attributes", answered=True, brand_mentioned=False),
    ]
    som = compute_share_of_model(responses)
    assert som.share_denominator == 3
    assert som.recommended_count == 2
    assert som.share_of_model == round(2 / 3, 4)


def test_share_of_model_zero_when_no_answered_share_prompts():
    som = compute_share_of_model([AnalyzedResponse(category="factual_attributes", answered=True, brand_mentioned=True)])
    assert som.share_of_model == 0.0
    assert som.share_denominator == 0


def test_competitor_tally_aggregates():
    responses = [
        AnalyzedResponse(category="category_recommendation", answered=True, brand_mentioned=False,
                         competitor_domains=["globex.com"]),
        AnalyzedResponse(category="comparison", answered=True, brand_mentioned=False,
                         competitor_domains=["globex.com"], competitor_names=["Initech"]),
    ]
    som = compute_share_of_model(responses)
    tally = {c["name"]: c["mentions"] for c in som.competitors}
    assert tally["globex.com"] == 2
    assert tally["Initech"] == 1


# ─── hallucination ───────────────────────────────────────────────────────────


def test_flags_permanently_closed_high_severity():
    flags = hallucination.detect_flags(
        text="Acme is permanently closed as of last year.",
        category_key="factual_attributes",
        brand_mentioned=True,
        name="Acme",
        city="Austin",
        counts_for_factual=True,
    )
    types = {f.type: f.severity for f in flags}
    assert types.get("claims_closed") == "high"


def test_flags_brand_absent_on_factual_query():
    flags = hallucination.detect_flags(
        text="I don't have specific information, but here are general tips.",
        category_key="factual_attributes",
        brand_mentioned=False,
        name="Acme",
        city="Austin",
        counts_for_factual=True,
    )
    assert any(f.type == "brand_absent_on_factual_query" for f in flags)


def test_no_false_closed_flag_on_clean_answer():
    flags = hallucination.detect_flags(
        text="Acme is open Monday to Friday in Austin and offers plumbing services.",
        category_key="factual_attributes",
        brand_mentioned=True,
        name="Acme",
        city="Austin",
        counts_for_factual=True,
    )
    assert all(f.type != "claims_closed" for f in flags)
