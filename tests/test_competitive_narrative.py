"""Tests for Competitive Narrative Analysis.

Tests the core functions to extract and analyze competitor narratives using LLMs.
Uses heavy mocking to avoid real API calls and network interactions.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from geo_optimizer.core.competitive_narrative import (
    CompetitiveNarrativeResult,
    CompetitorNarrative,
    extract_competitor_narrative,
    format_competitive_narrative,
    run_competitive_narrative_analysis,
)
from geo_optimizer.core.llm_client import LLMResponse
from geo_optimizer.models.results import AuditResult, BrandEntityResult, ContentResult, MetaResult, SignalsResult

# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_audit_result() -> AuditResult:
    """Minimal AuditResult for competitor extraction."""
    return AuditResult(
        url="https://example.com",
        score=85,
        band="good",
        meta=MetaResult(title_text="Test Brand", description_text="Description"),
        content=ContentResult(word_count=1200, h1_text="Test Brand"),
        brand_entity=BrandEntityResult(names_found=["Test Brand"]),
        signals=SignalsResult(has_rss=True),
    )


@pytest.fixture
def llm_success_response() -> LLMResponse:
    """Valid LLM response with JSON."""
    return LLMResponse(
        text='{"dominant_adjectives":["enterprise"],"key_frames":["AI-first"],"positioning":"AI-first platform","credibility_signals":["certifications"],"content_gaps":["sustainability"],"confidence":0.9}',
        provider="openai",
        model="gpt-4o-mini",
        error=None,
    )


@pytest.fixture
def llm_error_response() -> LLMResponse:
    """LLM error response."""
    return LLMResponse(
        text="",
        error="API rate limit exceeded",
        provider="openai",
        model="gpt-4o-mini",
    )


@pytest.fixture
def llm_invalid_json_response() -> LLMResponse:
    """LLM response with invalid JSON."""
    return LLMResponse(
        text="{invalid json}",
        error=None,
        provider="openai",
        model="gpt-4o-mini",
    )


# ─── Tests ────────────────────────────────────────────────────────────────────


class TestExtractCompetitorNarrative:
    """Tests for extract_competitor_narrative()."""

    def test_extract_competitor_narrative_success(
        self, mock_audit_result: AuditResult, llm_success_response: LLMResponse
    ):
        """LLM returns valid JSON with full narrative."""
        with patch("geo_optimizer.core.competitive_narrative.query_llm", return_value=llm_success_response):
            result = extract_competitor_narrative("https://competitor.com", mock_audit_result)

        assert isinstance(result, CompetitorNarrative)
        assert result.url == "https://competitor.com"
        assert result.brand_name == "Test Brand"
        assert result.positioning == "AI-first platform"
        assert result.dominant_adjectives == ["enterprise"]
        assert result.content_gaps == ["sustainability"]
        assert result.confidence == 0.9

    def test_extract_competitor_narrative_llm_error(
        self, mock_audit_result: AuditResult, llm_error_response: LLMResponse
    ):
        """LLM error triggers fallback message."""
        with patch("geo_optimizer.core.competitive_narrative.query_llm", return_value=llm_error_response):
            result = extract_competitor_narrative("https://competitor.com", mock_audit_result)

        assert result.positioning == "Unable to analyze - LLM unavailable"
        assert result.confidence == 0.0

    def test_extract_competitor_narrative_json_parse_error(
        self, mock_audit_result: AuditResult, llm_invalid_json_response: LLMResponse
    ):
        """Malformed JSON triggers fallback values."""
        with patch("geo_optimizer.core.competitive_narrative.query_llm", return_value=llm_invalid_json_response):
            result = extract_competitor_narrative("https://competitor.com", mock_audit_result)

        assert result.positioning == "Unable to parse analysis"
        assert result.confidence == 0.0


class TestRunCompetitiveNarrativeAnalysis:
    """Tests for run_competitive_narrative_analysis()."""

    def test_run_competitive_narrative_analysis_success(
        self, mock_audit_result: AuditResult, llm_success_response: LLMResponse
    ):
        """Full competitive analysis with one competitor."""
        target_url = "https://target.com"
        competitors = ["https://competitor.com"]

        with (
            patch(
                "geo_optimizer.core.competitive_narrative.run_full_audit",
                side_effect=[mock_audit_result, mock_audit_result],
            ),
            patch("geo_optimizer.utils.validators.validate_public_url", return_value=(True, "")),
            patch("geo_optimizer.core.competitive_narrative.query_llm", return_value=llm_success_response),
        ):
            result = run_competitive_narrative_analysis(target_url, competitors)

        assert isinstance(result, CompetitiveNarrativeResult)
        assert result.target_url == target_url
        assert len(result.competitors) == 1
        assert result.summary != ""

    def test_run_competitive_narrative_analysis_invalid_target_url(self):
        """Invalid target URL returns early with error."""
        target_url = "invalid-url"
        competitors = ["https://competitor.com"]

        with patch("geo_optimizer.utils.validators.validate_public_url", return_value=(False, "Invalid URL format")):
            result = run_competitive_narrative_analysis(target_url, competitors)

        assert result.summary.startswith("Error:")
        assert len(result.competitors) == 0


class TestFormatCompetitiveNarrative:
    """Tests for format_competitive_narrative()."""

    def test_format_competitive_narrative(self):
        """Format valid result to dict."""
        mock_audit = Mock()
        mock_audit.score = 85
        mock_audit.band = "good"

        result = CompetitiveNarrativeResult(
            target_url="https://target.com",
            target_audit=mock_audit,
            competitors=[
                CompetitorNarrative(
                    url="https://competitor.com",
                    brand_name="Brand",
                    dominant_adjectives=["A"],
                    key_frames=["B"],
                    positioning="C",
                    credibility_signals=["D"],
                    content_gaps=["E"],
                    confidence=0.9,
                )
            ],
            competitive_gaps=[],
            summary="Test summary",
        )

        formatted = format_competitive_narrative(result)

        assert isinstance(formatted, dict)
        assert formatted["target_url"] == "https://target.com"
        assert formatted["target_score"] == 85
        assert formatted["target_band"] == "good"
        assert len(formatted["competitors"]) == 1
        assert formatted["competitors"][0]["brand_name"] == "Brand"
        assert formatted["summary"] == "Test summary"
