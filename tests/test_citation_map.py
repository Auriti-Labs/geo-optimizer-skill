"""Tests for Cross-Platform Citation Map (#356)."""

from __future__ import annotations

from unittest.mock import patch

from geo_optimizer.core.audit_citation_map import _quick_sentiment, audit_citation_map
from geo_optimizer.core.llm_client import LLMResponse


class TestQuickSentiment:
    def test_positive(self):
        assert _quick_sentiment("This is the best and most recommended tool.") == "positive"

    def test_negative(self):
        assert _quick_sentiment("This tool lacks features and is limited.") == "negative"

    def test_neutral(self):
        assert _quick_sentiment("This is a tool that exists.") == "neutral"


class TestAuditCitationMap:
    def test_skips_without_provider(self):
        with patch.dict("os.environ", {}, clear=True):
            result = audit_citation_map("TestBrand")
            assert result.checked is True
            assert result.skipped_reason is not None

    def test_single_provider_all_mentioned(self):
        mock_resp = LLMResponse(text="TestBrand is the best recommended tool.", provider="mock", model="m")
        with patch("geo_optimizer.core.audit_citation_map.query_llm", return_value=mock_resp):
            result = audit_citation_map("TestBrand", providers=[("mock", "key")])
            assert result.checked is True
            assert result.platforms_citing == 1
            assert result.overall_visibility == 1.0
            assert len(result.entries) == 3  # 3 default queries
            assert all(e.brand_mentioned for e in result.entries)

    def test_single_provider_not_mentioned(self):
        mock_resp = LLMResponse(text="There are many tools available for this.", provider="mock", model="m")
        with patch("geo_optimizer.core.audit_citation_map.query_llm", return_value=mock_resp):
            result = audit_citation_map("TestBrand", providers=[("mock", "key")])
            assert result.platforms_citing == 0
            assert result.overall_visibility == 0.0

    def test_multiple_providers(self):
        responses = [
            LLMResponse(text="TestBrand is great.", provider="openai", model="m"),
            LLMResponse(text="TestBrand is recommended.", provider="openai", model="m"),
            LLMResponse(text="TestBrand is the best.", provider="openai", model="m"),
            LLMResponse(text="Other tools are available.", provider="anthropic", model="m"),
            LLMResponse(text="Consider alternatives.", provider="anthropic", model="m"),
            LLMResponse(text="Many options exist.", provider="anthropic", model="m"),
        ]
        with patch("geo_optimizer.core.audit_citation_map.query_llm", side_effect=responses):
            result = audit_citation_map(
                "TestBrand",
                providers=[("openai", "key1"), ("anthropic", "key2")],
            )
            assert result.platforms_tested == 2
            assert result.platforms_citing == 1  # only openai mentions
            assert result.overall_visibility == 0.5

    def test_custom_queries(self):
        mock_resp = LLMResponse(text="BrandX mentioned here.", provider="mock", model="m")
        with patch("geo_optimizer.core.audit_citation_map.query_llm", return_value=mock_resp):
            result = audit_citation_map("BrandX", providers=[("mock", "k")], queries=["Q1 {topic}", "Q2 {topic}"])
            assert len(result.entries) == 2
