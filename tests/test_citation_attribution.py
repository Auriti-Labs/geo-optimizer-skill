"""Tests for Citation Attribution Chain (#375)."""

from __future__ import annotations

from unittest.mock import patch

from geo_optimizer.core.audit_attribution import (
    audit_citation_attribution,
    _analyze_attribution,
    _classify_faithfulness,
    _split_sentences,
)
from geo_optimizer.core.llm_client import LLMResponse


class TestSplitSentences:
    def test_splits_on_period(self):
        result = _split_sentences("First sentence is here. Second sentence is here. Third sentence is here.")
        assert len(result) == 3

    def test_skips_short(self):
        result = _split_sentences("Short. Also short. This is a longer sentence that should be kept.")
        assert len(result) == 1


class TestClassifyFaithfulness:
    def test_faithful(self):
        assert _classify_faithfulness(0.7) == "faithful"

    def test_paraphrased(self):
        assert _classify_faithfulness(0.4) == "paraphrased"

    def test_altered(self):
        assert _classify_faithfulness(0.2) == "altered"

    def test_hallucinated(self):
        assert _classify_faithfulness(0.1) == "hallucinated"


class TestAnalyzeAttribution:
    def test_faithful_content(self):
        source = "GEO Optimizer scores websites from 0 to 100. It analyzes robots.txt and schema markup."
        llm = "GEO Optimizer scores websites from 0 to 100. It checks robots.txt and schema markup."
        result = _analyze_attribution(source, llm, "test query", "mock", "mock-1")
        assert result.checked is True
        assert result.faithfulness_score > 0.5
        assert any(s.faithfulness in ("faithful", "paraphrased") for s in result.segments)

    def test_hallucinated_content(self):
        source = "GEO Optimizer is a Python tool for SEO analysis."
        llm = "The weather in Tokyo is sunny today. Quantum computing advances rapidly."
        result = _analyze_attribution(source, llm, "test query", "mock", "mock-1")
        assert result.faithfulness_score < 0.5

    def test_details_lost(self):
        source = "The algorithm processes data in three stages. Authentication uses JWT tokens with rotation. Database queries are optimized with connection pooling."
        llm = "The algorithm processes data in three stages."
        result = _analyze_attribution(source, llm, "test", "mock", "mock-1")
        assert len(result.details_lost) > 0

    def test_empty_response(self):
        result = _analyze_attribution("Some source text here.", "", "test", "mock", "mock-1")
        assert result.checked is True
        assert result.faithfulness_score == 0.0


class TestAuditCitationAttribution:
    def test_skips_without_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            result = audit_citation_attribution("Some page text.", "test topic")
            assert result.checked is True
            assert result.skipped_reason is not None

    def test_skips_empty_content(self):
        result = audit_citation_attribution("", "test topic")
        assert result.skipped_reason == "No page content"

    def test_with_mocked_llm(self):
        mock_resp = LLMResponse(
            text="GEO Optimizer is a tool that scores websites for AI visibility.",
            provider="mock",
            model="mock-1",
        )
        with patch("geo_optimizer.core.audit_attribution.query_llm", return_value=mock_resp):
            result = audit_citation_attribution(
                "GEO Optimizer scores websites from 0 to 100 for AI search visibility.",
                "GEO Optimizer",
            )
            assert result.checked is True
            assert result.skipped_reason is None
            assert len(result.segments) > 0
            assert result.llm_provider == "mock"
