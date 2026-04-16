"""Tests for LLM client and Brand Sentiment Analysis (#378)."""

from __future__ import annotations

from unittest.mock import patch

from geo_optimizer.core.llm_client import LLMResponse, detect_provider, query_llm
from geo_optimizer.core.audit_sentiment import audit_brand_sentiment, _analyze_response


# ─── LLM Client ──────────────────────────────────────────────────────────────


class TestDetectProvider:
    def test_no_env_returns_none(self):
        with patch.dict("os.environ", {}, clear=True):
            provider, key = detect_provider()
            assert provider is None
            assert key is None

    def test_explicit_provider(self):
        with patch.dict("os.environ", {"GEO_LLM_PROVIDER": "openai", "GEO_LLM_API_KEY": "sk-test"}):
            provider, key = detect_provider()
            assert provider == "openai"
            assert key == "sk-test"

    def test_auto_detect_openai(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-auto"}, clear=True):
            provider, key = detect_provider()
            assert provider == "openai"
            assert key == "sk-auto"

    def test_auto_detect_anthropic(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "ant-auto"}, clear=True):
            provider, key = detect_provider()
            assert provider == "anthropic"
            assert key == "ant-auto"


class TestQueryLLM:
    def test_no_provider_returns_error(self):
        with patch.dict("os.environ", {}, clear=True):
            resp = query_llm("test prompt")
            assert resp.error is not None
            assert "No LLM provider" in resp.error

    def test_unknown_provider_returns_error(self):
        resp = query_llm("test", provider="unknown_provider", api_key="key")
        assert resp.error is not None
        assert "Unknown provider" in resp.error

    def test_openai_import_error(self):
        with patch.dict("sys.modules", {"openai": None}):
            resp = query_llm("test", provider="openai", api_key="sk-test")
            assert resp.error is not None
            assert "not installed" in resp.error

    def test_anthropic_import_error(self):
        with patch.dict("sys.modules", {"anthropic": None}):
            resp = query_llm("test", provider="anthropic", api_key="ant-test")
            assert resp.error is not None
            assert "not installed" in resp.error


# ─── Brand Sentiment ─────────────────────────────────────────────────────────


class TestAnalyzeResponse:
    def test_positive_response(self):
        resp = LLMResponse(
            text="GEO Optimizer is a leading, recommended, and excellent tool for SEO. It is trusted and popular.",
            provider="openai",
            model="gpt-4o-mini",
        )
        result = _analyze_response("GEO Optimizer", resp)
        assert result.sentiment == "positive"
        assert result.overall_score > 0
        assert len(result.positive_phrases) > 0

    def test_negative_response(self):
        resp = LLMResponse(
            text="This tool lacks features, is limited and outdated. It has poor performance and is unreliable.",
            provider="openai",
            model="gpt-4o-mini",
        )
        result = _analyze_response("TestBrand", resp)
        assert result.sentiment == "negative"
        assert result.overall_score < 0
        assert len(result.negative_phrases) > 0

    def test_neutral_response(self):
        resp = LLMResponse(
            text="This is a tool that exists. It does things. Some people use it.",
            provider="openai",
            model="gpt-4o-mini",
        )
        result = _analyze_response("TestBrand", resp)
        assert result.sentiment == "neutral"

    def test_recommendation_strength_strong(self):
        resp = LLMResponse(text="I would strongly recommend this tool for anyone.", provider="test", model="test")
        result = _analyze_response("Brand", resp)
        assert result.recommendation_strength == "strongly_recommended"

    def test_recommendation_strength_warned(self):
        resp = LLMResponse(text="I would not recommend this tool due to issues.", provider="test", model="test")
        result = _analyze_response("Brand", resp)
        assert result.recommendation_strength == "warned_against"


class TestAuditBrandSentiment:
    def test_skips_without_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            result = audit_brand_sentiment("TestBrand")
            assert result.checked is True
            assert result.skipped_reason is not None
            assert result.brand == "TestBrand"

    def test_with_mocked_llm(self):
        mock_resp = LLMResponse(
            text="TestBrand is a leading and recommended solution. Highly trusted.",
            provider="mock",
            model="mock-1",
        )
        with patch("geo_optimizer.core.audit_sentiment.query_llm", return_value=mock_resp):
            result = audit_brand_sentiment("TestBrand")
            assert result.checked is True
            assert result.skipped_reason is None
            assert result.sentiment == "positive"
            assert result.brand == "TestBrand"
            assert result.llm_provider == "mock"
