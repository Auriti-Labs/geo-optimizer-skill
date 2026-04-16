"""Tests for Multi-Turn Persistence (#376)."""

from __future__ import annotations

from unittest.mock import patch, call

from geo_optimizer.core.audit_persistence import audit_multi_turn_persistence, _count_mentions, _compute_persistence
from geo_optimizer.core.llm_client import LLMResponse
from geo_optimizer.models.results import TurnResult


class TestCountMentions:
    def test_counts_case_insensitive(self):
        assert _count_mentions("GEO Optimizer is great. geo optimizer rocks.", "GEO Optimizer") == 2

    def test_zero_mentions(self):
        assert _count_mentions("This tool is useful.", "BrandX") == 0


class TestComputePersistence:
    def test_all_mentioned(self):
        turns = [TurnResult(turn=i, brand_mentioned=True) for i in range(1, 6)]
        assert _compute_persistence(turns, 5) == 100

    def test_none_mentioned(self):
        turns = [TurnResult(turn=i, brand_mentioned=False) for i in range(1, 6)]
        assert _compute_persistence(turns, 5) == 0

    def test_partial(self):
        turns = [TurnResult(turn=1, brand_mentioned=True), TurnResult(turn=2, brand_mentioned=False)]
        assert _compute_persistence(turns, 2) == 50

    def test_empty(self):
        assert _compute_persistence([], 0) == 0


class TestAuditMultiTurnPersistence:
    def test_skips_without_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            result = audit_multi_turn_persistence("TestBrand")
            assert result.checked is True
            assert result.skipped_reason is not None

    def test_with_mocked_llm_all_mentioned(self):
        mock_resp = LLMResponse(
            text="TestBrand is a great tool. I recommend TestBrand for this use case.",
            provider="mock",
            model="mock-1",
        )
        with patch("geo_optimizer.core.audit_persistence.query_llm", return_value=mock_resp):
            result = audit_multi_turn_persistence("TestBrand")
            assert result.checked is True
            assert result.persistence_score == 100
            assert result.last_mentioned_turn == 5
            assert len(result.turns) == 5

    def test_with_mocked_llm_partial_mention(self):
        responses = [
            LLMResponse(text="TestBrand is a tool for optimization.", provider="mock", model="m"),
            LLMResponse(text="There are several alternatives available.", provider="mock", model="m"),
            LLMResponse(text="I recommend TestBrand among others.", provider="mock", model="m"),
            LLMResponse(text="The options vary by use case.", provider="mock", model="m"),
            LLMResponse(text="Consider your specific needs.", provider="mock", model="m"),
        ]
        with patch("geo_optimizer.core.audit_persistence.query_llm", side_effect=responses):
            result = audit_multi_turn_persistence("TestBrand")
            assert result.persistence_score == 40  # 2/5
            assert result.last_mentioned_turn == 3

    def test_custom_turns(self):
        mock_resp = LLMResponse(text="BrandX is mentioned here.", provider="mock", model="m")
        with patch("geo_optimizer.core.audit_persistence.query_llm", return_value=mock_resp):
            result = audit_multi_turn_persistence("BrandX", turns=["Q1 about {topic}", "Q2 about {topic}"])
            assert result.total_turns == 2
