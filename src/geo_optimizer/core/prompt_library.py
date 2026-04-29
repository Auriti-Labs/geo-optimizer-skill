"""
GEO Audit — Prompt Library (#379).

Curated prompt library organized by intent, with batch execution
against an LLM to track brand visibility across query types.
Requires LLM API key (opt-in).
"""

from __future__ import annotations

import logging
import re

from geo_optimizer.core.llm_client import query_llm
from geo_optimizer.models.results import PromptLibraryResult, PromptResult

logger = logging.getLogger(__name__)

_POSITIVE = frozenset({"best", "leading", "recommended", "excellent", "top", "great", "trusted", "popular"})
_NEGATIVE = frozenset({"lacks", "limited", "poor", "avoid", "outdated", "weak", "inferior"})

# Built-in prompt library organized by intent
BUILTIN_PROMPTS: dict[str, list[str]] = {
    "discovery": [
        "What is the best tool for {topic}?",
        "What tools exist for {topic}?",
    ],
    "comparison": [
        "Compare the top options for {topic}.",
    ],
    "recommendation": [
        "Which {topic} tool do you recommend?",
        "What would you suggest for {topic}?",
    ],
    "alternative": [
        "What are alternatives to {brand}?",
    ],
    "how_to": [
        "How do I get started with {topic}?",
    ],
}


def run_prompt_library(
    brand: str,
    topic: str = "",
    *,
    prompts: dict[str, list[str]] | None = None,
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> PromptLibraryResult:
    """Execute a prompt library and track brand mentions.

    Args:
        brand: Brand name to track.
        topic: Topic context (defaults to brand).
        prompts: Custom prompt library (defaults to BUILTIN_PROMPTS).
        provider: LLM provider override.
        api_key: API key override.
        model: Model override.

    Returns:
        PromptLibraryResult with per-prompt results and aggregate stats.
    """
    topic = topic or brand
    library = prompts or BUILTIN_PROMPTS

    results: list[PromptResult] = []
    resp_provider = ""
    resp_model = ""
    error_count = 0

    for intent, templates in library.items():
        for template in templates:
            prompt_text = template.format(topic=topic, brand=brand)
            response = query_llm(prompt_text, provider=provider, api_key=api_key, model=model)

            if response.error:
                # Fix H-6: skip errored prompts instead of aborting the entire batch.
                # A transient error on one prompt should not kill all results.
                logger.warning("Prompt library: skipping '%s' — %s", prompt_text[:60], response.error)
                error_count += 1
                continue

            resp_provider = response.provider
            resp_model = response.model
            mentions = len(re.findall(re.escape(brand), response.text, re.IGNORECASE))
            sentiment = _quick_sentiment(response.text)

            results.append(
                PromptResult(
                    intent=intent,
                    prompt=prompt_text,
                    brand_mentioned=mentions > 0,
                    mention_count=mentions,
                    sentiment=sentiment,
                    response_snippet=response.text[:200],
                )
            )

    # If ALL prompts failed, report as skipped
    if not results and error_count > 0:
        return PromptLibraryResult(checked=True, skipped_reason=f"All {error_count} prompts failed", brand=brand)

    mention_rate = sum(1 for r in results if r.brand_mentioned) / len(results) if results else 0.0
    avg_sentiment = _avg_sentiment(results)

    return PromptLibraryResult(
        checked=True,
        brand=brand,
        results=results,
        mention_rate=round(mention_rate, 2),
        avg_sentiment_score=round(avg_sentiment, 2),
        llm_provider=resp_provider,
        llm_model=resp_model,
    )


def _quick_sentiment(text: str) -> str:
    words = set(re.findall(r"\b[a-z]+\b", text.lower()))
    pos = len(_POSITIVE & words)
    neg = len(_NEGATIVE & words)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def _avg_sentiment(results: list[PromptResult]) -> float:
    if not results:
        return 0.0
    scores = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}
    total = sum(scores.get(r.sentiment, 0.0) for r in results)
    return total / len(results)
