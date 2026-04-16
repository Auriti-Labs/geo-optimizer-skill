"""
GEO Audit — Brand Sentiment Analysis (#378).

Queries an LLM about a brand and analyzes the sentiment of the response.
Requires LLM API key (opt-in). Graceful skip if not configured.
"""

from __future__ import annotations

import re

from geo_optimizer.core.llm_client import LLMResponse, query_llm
from geo_optimizer.models.results import BrandSentimentResult

_POSITIVE_WORDS = frozenset(
    {
        "leading",
        "best",
        "recommended",
        "excellent",
        "popular",
        "trusted",
        "powerful",
        "comprehensive",
        "innovative",
        "reliable",
        "top",
        "great",
        "outstanding",
        "superior",
        "well-known",
        "widespread",
        "acclaimed",
    }
)

_NEGATIVE_WORDS = frozenset(
    {
        "lacks",
        "limited",
        "however",
        "drawback",
        "weakness",
        "expensive",
        "outdated",
        "complex",
        "difficult",
        "poor",
        "slow",
        "unreliable",
        "criticized",
        "controversial",
        "inferior",
        "disappointing",
        "warning",
    }
)

_PROMPT_TEMPLATE = (
    "What do you know about {brand}? Is it good? What are its strengths and weaknesses? Would you recommend it?"
)


def audit_brand_sentiment(
    brand: str,
    *,
    use_case: str = "",
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> BrandSentimentResult:
    """Query an LLM about a brand and analyze sentiment.

    Args:
        brand: Brand or product name to analyze.
        use_case: Optional context (e.g. "for SEO optimization").
        provider: LLM provider override.
        api_key: API key override.
        model: Model override.

    Returns:
        BrandSentimentResult with sentiment score and analysis.
    """
    prompt = _PROMPT_TEMPLATE.format(brand=brand)
    if use_case:
        prompt += f" Specifically for {use_case}."

    response = query_llm(
        prompt,
        system="You are a knowledgeable technology analyst. Be balanced and specific.",
        provider=provider,
        api_key=api_key,
        model=model,
    )

    if response.error:
        return BrandSentimentResult(
            checked=True,
            skipped_reason=response.error,
            brand=brand,
        )

    return _analyze_response(brand, response)


def _analyze_response(brand: str, response: LLMResponse) -> BrandSentimentResult:
    """Analyze LLM response text for sentiment signals."""
    text = response.text.lower()
    words = set(re.findall(r"\b[a-z]+(?:-[a-z]+)*\b", text))

    positive = sorted(_POSITIVE_WORDS & words)
    negative = sorted(_NEGATIVE_WORDS & words)

    pos_count = len(positive)
    neg_count = len(negative)
    total = pos_count + neg_count

    if total == 0:
        score = 0
        sentiment = "neutral"
    else:
        score = int(((pos_count - neg_count) / total) * 100)
        if score >= 30:
            sentiment = "positive"
        elif score <= -30:
            sentiment = "negative"
        else:
            sentiment = "neutral"

    strength = _classify_strength(text)

    return BrandSentimentResult(
        checked=True,
        brand=brand,
        overall_score=score,
        sentiment=sentiment,
        positive_phrases=positive,
        negative_phrases=negative,
        recommendation_strength=strength,
        llm_provider=response.provider,
        llm_model=response.model,
        raw_response=response.text[:2000],
    )


def _classify_strength(text: str) -> str:
    """Classify how strongly the LLM recommends the brand."""
    if any(p in text for p in ["strongly recommend", "highly recommend", "definitely recommend"]):
        return "strongly_recommended"
    if any(p in text for p in ["would not recommend", "do not recommend", "avoid", "warned against"]):
        return "warned_against"
    if any(p in text for p in ["recommend", "suggest", "worth"]):
        return "mentioned"
    return "neutral"
