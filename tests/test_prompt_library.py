"""Tests for Prompt Library (#379)."""

from __future__ import annotations

from unittest.mock import patch

from geo_optimizer.core.prompt_library import run_prompt_library, BUILTIN_PROMPTS
from geo_optimizer.core.llm_client import LLMResponse


class TestPromptLibrary:
    def test_skips_without_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            result = run_prompt_library("TestBrand")
            assert result.checked is True
            assert result.skipped_reason is not None

    def test_builtin_prompts_exist(self):
        assert "discovery" in BUILTIN_PROMPTS
        assert "comparison" in BUILTIN_PROMPTS
        assert "recommendation" in BUILTIN_PROMPTS
        total = sum(len(v) for v in BUILTIN_PROMPTS.values())
        assert total >= 5

    def test_all_mentioned(self):
        mock_resp = LLMResponse(text="TestBrand is the best recommended tool.", provider="mock", model="m")
        with patch("geo_optimizer.core.prompt_library.query_llm", return_value=mock_resp):
            result = run_prompt_library("TestBrand")
            assert result.checked is True
            assert result.mention_rate == 1.0
            assert result.avg_sentiment_score > 0
            assert len(result.results) == sum(len(v) for v in BUILTIN_PROMPTS.values())

    def test_none_mentioned(self):
        mock_resp = LLMResponse(text="There are many tools available.", provider="mock", model="m")
        with patch("geo_optimizer.core.prompt_library.query_llm", return_value=mock_resp):
            result = run_prompt_library("TestBrand")
            assert result.mention_rate == 0.0

    def test_custom_prompts(self):
        mock_resp = LLMResponse(text="BrandX is mentioned here.", provider="mock", model="m")
        custom = {"custom_intent": ["Tell me about {brand} for {topic}."]}
        with patch("geo_optimizer.core.prompt_library.query_llm", return_value=mock_resp):
            result = run_prompt_library("BrandX", prompts=custom)
            assert len(result.results) == 1
            assert result.results[0].intent == "custom_intent"

    def test_intent_tracked(self):
        mock_resp = LLMResponse(text="TestBrand is great.", provider="mock", model="m")
        with patch("geo_optimizer.core.prompt_library.query_llm", return_value=mock_resp):
            result = run_prompt_library("TestBrand")
            intents = {r.intent for r in result.results}
            assert "discovery" in intents
            assert "recommendation" in intents
