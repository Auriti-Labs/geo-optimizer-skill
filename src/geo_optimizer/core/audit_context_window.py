"""
GEO Audit — Context Window Optimization sub-audit (#370).

Analyzes how effectively page content utilizes LLM context windows:
- Token estimation (word count × 1.3 heuristic)
- Front-loading ratio: key info in the first 30% of content
- Filler/boilerplate ratio
- Truncation risk per platform (RAG ~300 words, Perplexity, ChatGPT, Claude)
- Context efficiency score (0-100)

Informational check — does not affect GEO score.
"""

from __future__ import annotations

import re

from geo_optimizer.models.results import ContextWindowResult

# Token estimation: ~1.3 tokens per English word (OpenAI tokenizer average)
_TOKENS_PER_WORD = 1.3

# Platform context windows (in tokens)
_PLATFORMS = {
    "rag_chunk": 400,       # ~300 words, typical RAG chunk
    "perplexity": 4000,     # Perplexity answer context
    "chatgpt": 128000,      # GPT-4o
    "claude": 200000,       # Claude 3.5+
}

# Filler patterns: navigation, boilerplate, repetitive CTAs
_FILLER_RE = re.compile(
    r"\b(?:click here|read more|subscribe|sign up|cookie|privacy policy|"
    r"all rights reserved|terms of service|copyright|©|menu|navigation|"
    r"skip to content|back to top|share this|follow us)\b",
    re.IGNORECASE,
)

# Key info patterns: definitions, statistics, facts, answers
_KEY_INFO_RE = re.compile(
    r"(?:"
    r"\b\d+(?:\.\d+)?%"                          # percentages
    r"|\b\d{4}\b"                                 # years
    r"|\$\d+"                                     # dollar amounts
    r"|\b(?:is|are|means?|refers?\s+to)\b"        # definitions
    r"|\b(?:according to|study|research|data)\b"  # citations
    r"|\b(?:step \d|first|second|third)\b"        # structured info
    r")",
    re.IGNORECASE,
)


def audit_context_window(soup, soup_clean=None) -> ContextWindowResult:
    """Analyze content for context window utilization efficiency.

    Args:
        soup: BeautifulSoup of the full HTML document.
        soup_clean: Optional pre-cleaned soup (scripts/styles removed).

    Returns:
        ContextWindowResult with efficiency metrics.
    """
    body = (soup_clean or soup).find("body") if soup else None
    if not body:
        return ContextWindowResult(checked=True)

    text = body.get_text(separator=" ", strip=True)
    words = text.split()
    total_words = len(words)

    if total_words == 0:
        return ContextWindowResult(checked=True)

    total_tokens = int(total_words * _TOKENS_PER_WORD)

    # Front-loading: key info density in first 30% vs rest
    split_point = max(1, int(total_words * 0.3))
    front_text = " ".join(words[:split_point])
    back_text = " ".join(words[split_point:])

    front_key = len(_KEY_INFO_RE.findall(front_text))
    back_key = len(_KEY_INFO_RE.findall(back_text))
    total_key = front_key + back_key

    front_loaded_ratio = front_key / total_key if total_key > 0 else 0.0

    # Key info tokens: estimate tokens containing key information
    key_info_tokens = int(total_key * 15 * _TOKENS_PER_WORD)  # ~15 words per key info match
    key_info_tokens = min(key_info_tokens, total_tokens)

    # Filler ratio
    filler_matches = len(_FILLER_RE.findall(text))
    filler_words = filler_matches * 5  # ~5 words per filler match context
    filler_ratio = min(filler_words / total_words, 1.0) if total_words > 0 else 0.0

    # Optimal platforms: content fits within context window
    optimal_for = [name for name, limit in _PLATFORMS.items() if total_tokens <= limit]

    # Truncation risk
    truncation_risk = _compute_truncation_risk(total_tokens)

    # Context efficiency score
    score = _compute_score(front_loaded_ratio, filler_ratio, truncation_risk, total_key, total_words)

    return ContextWindowResult(
        checked=True,
        total_words=total_words,
        total_tokens_estimate=total_tokens,
        front_loaded_ratio=round(front_loaded_ratio, 2),
        key_info_tokens=key_info_tokens,
        filler_ratio=round(filler_ratio, 2),
        optimal_for=optimal_for,
        truncation_risk=truncation_risk,
        context_efficiency_score=score,
    )


def _compute_truncation_risk(total_tokens: int) -> str:
    """Determine truncation risk based on token count vs RAG chunk sizes."""
    if total_tokens <= 400:
        return "none"
    if total_tokens <= 2000:
        return "low"
    if total_tokens <= 8000:
        return "medium"
    return "high"


def _compute_score(
    front_loaded_ratio: float,
    filler_ratio: float,
    truncation_risk: str,
    total_key: int,
    total_words: int,
) -> int:
    """Compute context efficiency score (0-100)."""
    score = 0

    # Front-loading quality (max 35): key info concentrated in first 30%
    if front_loaded_ratio >= 0.5:
        score += 35
    elif front_loaded_ratio >= 0.3:
        score += 20
    elif front_loaded_ratio > 0:
        score += 10

    # Low filler ratio (max 25): less boilerplate = better
    if filler_ratio <= 0.02:
        score += 25
    elif filler_ratio <= 0.05:
        score += 15
    elif filler_ratio <= 0.10:
        score += 8

    # Truncation risk (max 20): lower risk = better
    risk_scores = {"none": 20, "low": 15, "medium": 8, "high": 0}
    score += risk_scores.get(truncation_risk, 0)

    # Key info density (max 20): more key info per word = better
    if total_words > 0:
        density = total_key / total_words
        if density >= 0.02:
            score += 20
        elif density >= 0.01:
            score += 12
        elif density > 0:
            score += 5

    return min(score, 100)
