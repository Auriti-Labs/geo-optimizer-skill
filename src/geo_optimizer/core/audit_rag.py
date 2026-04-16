"""
GEO Audit — RAG Chunk Readiness sub-audit (#353).

Analyzes whether page content is well-segmented for RAG chunking:
- Sections of 100-150 words (optimal for 4.7x citation rate per SE Ranking 2026)
- Definition pattern in the first 150 characters
- Headings as chunk boundaries
- Anchor sentences (self-contained, citable statements)
"""

from __future__ import annotations

import re

from geo_optimizer.models.results import RagChunkResult

_OPTIMAL_MIN_WORDS = 100
_OPTIMAL_MAX_WORDS = 150

# Patterns that indicate a definition-style opening (e.g. "X is ...", "X refers to ...")
_DEFINITION_RE = re.compile(
    r"^[A-Z][^.]{5,60}\b(?:is|are|refers?\s+to|means?|describes?|represents?)\b",
    re.MULTILINE,
)

# Anchor sentence: a self-contained factual statement (ends with period, 10-40 words)
_ANCHOR_RE = re.compile(r"(?<=[.!?]\s)[A-Z][^.!?]{30,200}[.!?]")


def audit_rag_readiness(soup, soup_clean=None) -> RagChunkResult:
    """Analyze content segmentation for RAG retrieval readiness.

    Args:
        soup: BeautifulSoup of the full HTML document.
        soup_clean: Optional pre-cleaned soup (scripts/styles removed).

    Returns:
        RagChunkResult with chunk readiness metrics.
    """
    body = soup_clean.find("body") if soup_clean else soup.find("body")
    if not body:
        return RagChunkResult(checked=True)

    headings = body.find_all(re.compile(r"^h[1-6]$"))
    sections = _split_by_headings(body, headings)

    total = len(sections)
    if total == 0:
        return RagChunkResult(checked=True)

    word_counts = [len(s.split()) for s in sections]
    in_range = sum(1 for wc in word_counts if _OPTIMAL_MIN_WORDS <= wc <= _OPTIMAL_MAX_WORDS)
    avg_words = sum(word_counts) / total

    # Definition opening: check first 150 chars of body text
    body_text = body.get_text(separator=" ", strip=True)
    has_definition = bool(_DEFINITION_RE.search(body_text[:150]))

    # Heading-as-boundary ratio: how many sections start after a heading
    heading_ratio = len(headings) / total if total > 0 else 0.0

    # Anchor sentences: self-contained citable statements
    anchors = len(_ANCHOR_RE.findall(body_text))

    # Score: 0-100
    score = _compute_score(total, in_range, avg_words, has_definition, heading_ratio, anchors)

    return RagChunkResult(
        checked=True,
        total_sections=total,
        sections_in_range=in_range,
        avg_section_words=round(avg_words, 1),
        has_definition_opening=has_definition,
        heading_as_boundary_ratio=round(heading_ratio, 2),
        anchor_sentences=anchors,
        chunk_readiness_score=score,
    )


def _split_by_headings(body, headings) -> list[str]:
    """Split body text into sections delimited by headings."""
    if not headings:
        text = body.get_text(separator=" ", strip=True)
        return [text] if text else []

    headings_set = set(headings)
    sections: list[str] = []
    for heading in headings:
        text_parts: list[str] = []
        for sibling in heading.next_siblings:
            if sibling in headings_set:
                break
            t = sibling.get_text(separator=" ", strip=True) if hasattr(sibling, "get_text") else str(sibling).strip()
            if t:
                text_parts.append(t)
        combined = " ".join(text_parts)
        if combined:
            sections.append(combined)
    return sections


def _compute_score(
    total: int,
    in_range: int,
    avg_words: float,
    has_definition: bool,
    heading_ratio: float,
    anchors: int,
) -> int:
    """Compute RAG chunk readiness score (0-100)."""
    score = 0

    # Section count (max 25): having multiple sections is good
    if total >= 5:
        score += 25
    elif total >= 3:
        score += 15
    elif total >= 1:
        score += 5

    # Sections in optimal range (max 30)
    if total > 0:
        ratio = in_range / total
        score += int(ratio * 30)

    # Average section length (max 15): penalize too short or too long
    if _OPTIMAL_MIN_WORDS <= avg_words <= _OPTIMAL_MAX_WORDS:
        score += 15
    elif 50 <= avg_words <= 250:
        score += 8

    # Definition opening (max 10)
    if has_definition:
        score += 10

    # Heading boundaries (max 10)
    if heading_ratio >= 0.8:
        score += 10
    elif heading_ratio >= 0.5:
        score += 5

    # Anchor sentences (max 10)
    if anchors >= 5:
        score += 10
    elif anchors >= 2:
        score += 5

    return min(score, 100)
