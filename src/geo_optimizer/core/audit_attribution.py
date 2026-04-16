"""
GEO Audit — Citation Attribution Chain (#375).

Queries an LLM about a topic, then compares the response with the
original page content to measure faithfulness of reformulation.
Requires LLM API key (opt-in).
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from geo_optimizer.core.llm_client import query_llm
from geo_optimizer.models.results import AttributionSegment, CitationAttributionResult

_QUERY_TEMPLATE = "Tell me about {topic}. What are the key facts and details?"

_FAITHFUL_THRESHOLD = 0.6
_PARAPHRASED_THRESHOLD = 0.35


def audit_citation_attribution(
    page_text: str,
    topic: str,
    *,
    query: str | None = None,
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> CitationAttributionResult:
    """Query an LLM and compare response with source content.

    Args:
        page_text: Original page text content.
        topic: Topic to query the LLM about.
        query: Custom query (defaults to template).
        provider: LLM provider override.
        api_key: API key override.
        model: Model override.

    Returns:
        CitationAttributionResult with faithfulness analysis.
    """
    if not page_text.strip():
        return CitationAttributionResult(checked=True, skipped_reason="No page content")

    query_text = query or _QUERY_TEMPLATE.format(topic=topic)

    response = query_llm(
        query_text,
        system="Answer factually and specifically. Cite details when possible.",
        provider=provider,
        api_key=api_key,
        model=model,
    )

    if response.error:
        return CitationAttributionResult(checked=True, skipped_reason=response.error, query=query_text)

    return _analyze_attribution(page_text, response.text, query_text, response.provider, response.model)


def _analyze_attribution(
    source: str, llm_text: str, query: str, provider: str, model: str
) -> CitationAttributionResult:
    """Compare LLM response sentences against source content."""
    source_sentences = _split_sentences(source)
    llm_sentences = _split_sentences(llm_text)

    if not llm_sentences:
        return CitationAttributionResult(checked=True, query=query, llm_provider=provider, llm_model=model)

    segments: list[AttributionSegment] = []
    faithful_count = 0

    for llm_sent in llm_sentences:
        best_match, best_score = _find_best_match(llm_sent, source_sentences)
        faithfulness = _classify_faithfulness(best_score)
        if faithfulness == "faithful" or faithfulness == "paraphrased":
            faithful_count += 1
        segments.append(
            AttributionSegment(
                llm_text=llm_sent[:200],
                source_text=best_match[:200] if best_match else "",
                similarity=round(best_score, 4),
                faithfulness=faithfulness,
            )
        )

    faithfulness_score = faithful_count / len(segments) if segments else 0.0

    # Details analysis
    details_lost = [s[:100] for s in source_sentences[:50] if not _has_match(s, llm_sentences)][:5]
    details_added = [seg.llm_text[:100] for seg in segments if seg.faithfulness == "hallucinated"][:5]

    return CitationAttributionResult(
        checked=True,
        query=query,
        segments=segments[:20],
        faithfulness_score=round(faithfulness_score, 4),
        details_lost=details_lost,
        details_added=details_added,
        llm_provider=provider,
        llm_model=model,
    )


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences (simple heuristic)."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 15]


def _find_best_match(sentence: str, candidates: list[str]) -> tuple[str, float]:
    """Find the most similar candidate sentence."""
    best = ""
    best_score = 0.0
    sent_lower = sentence.lower()
    for cand in candidates:
        score = SequenceMatcher(None, sent_lower, cand.lower()).ratio()
        if score > best_score:
            best_score = score
            best = cand
    return best, best_score


def _has_match(sentence: str, candidates: list[str], threshold: float = 0.3) -> bool:
    """Check if a sentence has any match above threshold."""
    sent_lower = sentence.lower()
    return any(SequenceMatcher(None, sent_lower, c.lower()).ratio() >= threshold for c in candidates)


def _classify_faithfulness(score: float) -> str:
    """Classify similarity score into faithfulness category."""
    if score >= _FAITHFUL_THRESHOLD:
        return "faithful"
    if score >= _PARAPHRASED_THRESHOLD:
        return "paraphrased"
    if score >= 0.15:
        return "altered"
    return "hallucinated"
