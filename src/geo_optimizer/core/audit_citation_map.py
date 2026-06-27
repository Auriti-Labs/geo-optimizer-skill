"""
GEO Audit — Cross-Platform Citation Map (#356).

Queries multiple LLM providers with the same prompts and aggregates
which platform cites the brand, with what sentiment and faithfulness.
Requires at least one LLM API key.
"""

from __future__ import annotations

import re

from geo_optimizer.core.llm_client import detect_provider, query_llm
from geo_optimizer.models.results import CitationMapEntry, CitationMapResult
from geo_optimizer.utils.brand_match import brand_matches

_QUERIES = [
    "What is the best tool for {topic}?",
    "Compare the top options for {topic}.",
    "What do you recommend for {topic}?",
]

_POSITIVE = frozenset({"best", "leading", "recommended", "excellent", "top", "great", "trusted"})
_NEGATIVE = frozenset({"lacks", "limited", "poor", "avoid", "outdated", "weak"})


def audit_citation_map(
    brand: str,
    topic: str = "",
    *,
    providers: list[tuple[str, str]] | None = None,
    queries: list[str] | None = None,
) -> CitationMapResult:
    """Query multiple LLM providers and build a citation map.

    Args:
        brand: Brand name to track.
        topic: Topic context (defaults to brand).
        providers: List of (provider, api_key) tuples. Auto-detected if None.
        queries: Custom queries (defaults to _QUERIES).

    Returns:
        CitationMapResult with per-query, per-platform entries.
    """
    topic = topic or brand
    query_templates = queries or _QUERIES

    if providers is None:
        detected_provider, detected_key = detect_provider()
        if not detected_provider or not detected_key:
            return CitationMapResult(checked=True, skipped_reason="No LLM provider configured", brand=brand)
        providers = [(detected_provider, detected_key)]

    entries: list[CitationMapEntry] = []
    platforms_citing: set[str] = set()

    for provider_name, api_key in providers:
        for template in query_templates:
            query_text = template.format(topic=topic)
            response = query_llm(query_text, provider=provider_name, api_key=api_key)

            if response.error:
                continue

            mentioned = brand_matches(response.text, brand)
            sentiment = _quick_sentiment(response.text)

            if mentioned:
                platforms_citing.add(provider_name)

            entries.append(
                CitationMapEntry(
                    query=query_text,
                    platform=provider_name,
                    brand_mentioned=mentioned,
                    sentiment=sentiment,
                    snippet=response.text[:200],
                )
            )

    total_platforms = len({p for p, _ in providers})
    visibility = len(platforms_citing) / total_platforms if total_platforms else 0.0

    return CitationMapResult(
        checked=True,
        brand=brand,
        entries=entries,
        platforms_tested=total_platforms,
        platforms_citing=len(platforms_citing),
        overall_visibility=round(visibility, 2),
    )


def _quick_sentiment(text: str) -> str:
    """Quick keyword-based sentiment classification."""
    words = set(re.findall(r"\b[a-z]+\b", text.lower()))
    pos = len(_POSITIVE & words)
    neg = len(_NEGATIVE & words)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"
