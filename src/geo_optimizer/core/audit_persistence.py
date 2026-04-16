"""
GEO Audit — Multi-Turn Persistence (#376).

Simulates a multi-turn conversation to measure how long a brand
persists in the LLM's conversational context.
Requires LLM API key (opt-in).
"""

from __future__ import annotations

import re

from geo_optimizer.core.llm_client import query_llm
from geo_optimizer.models.results import MultiTurnResult, TurnResult

_DEFAULT_TURNS = [
    "What is {topic}?",
    "How does it compare to alternatives?",
    "Which tools do you recommend for this?",
    "What are the pros and cons of the top options?",
    "If I had to choose one, what would you suggest?",
]


def audit_multi_turn_persistence(
    brand: str,
    topic: str = "",
    *,
    turns: list[str] | None = None,
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> MultiTurnResult:
    """Simulate multi-turn conversation and track brand persistence.

    Args:
        brand: Brand name to track across turns.
        topic: Topic context (defaults to brand name).
        turns: Custom turn queries (defaults to _DEFAULT_TURNS).
        provider: LLM provider override.
        api_key: API key override.
        model: Model override.

    Returns:
        MultiTurnResult with per-turn mention tracking and persistence score.
    """
    topic = topic or brand
    turn_queries = [t.format(topic=topic) for t in (turns or _DEFAULT_TURNS)]

    conversation_context = ""
    turn_results: list[TurnResult] = []
    last_mentioned = 0
    resp_provider = ""
    resp_model = ""

    for i, query_text in enumerate(turn_queries, 1):
        prompt = query_text
        if conversation_context:
            prompt = f"Previous context:\n{conversation_context}\n\nNew question: {query_text}"

        response = query_llm(
            prompt,
            system="You are a helpful technology advisor. Be specific and mention tools by name.",
            provider=provider,
            api_key=api_key,
            model=model,
        )

        if response.error:
            return MultiTurnResult(checked=True, skipped_reason=response.error, brand=brand)

        resp_provider = response.provider
        resp_model = response.model
        mentioned = _count_mentions(response.text, brand)

        turn_results.append(
            TurnResult(
                turn=i,
                query=query_text,
                brand_mentioned=mentioned > 0,
                mention_count=mentioned,
                response_snippet=response.text[:200],
            )
        )

        if mentioned > 0:
            last_mentioned = i

        conversation_context += f"\nQ: {query_text}\nA: {response.text[:500]}\n"

    total = len(turn_results)
    persistence = _compute_persistence(turn_results, total)

    return MultiTurnResult(
        checked=True,
        brand=brand,
        turns=turn_results,
        persistence_score=persistence,
        last_mentioned_turn=last_mentioned,
        total_turns=total,
        llm_provider=resp_provider,
        llm_model=resp_model,
    )


def _count_mentions(text: str, brand: str) -> int:
    """Count case-insensitive mentions of brand in text."""
    return len(re.findall(re.escape(brand), text, re.IGNORECASE))


def _compute_persistence(turns: list[TurnResult], total: int) -> int:
    """Compute persistence score (0-100)."""
    if not turns or total == 0:
        return 0
    mentioned_turns = sum(1 for t in turns if t.brand_mentioned)
    return int((mentioned_turns / total) * 100)
