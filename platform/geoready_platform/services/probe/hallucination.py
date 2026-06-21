"""Hallucination / factual-mismatch flags (v1 heuristics). Pure, no I/O.

Flags are ADVISORY and evidence-bearing — never auto-acted. Each flag carries a
type, severity, and the text evidence that triggered it. Heuristics are
intentionally conservative; precision is refined in later phases.

Inputs are one AI answer plus the entity's known ground-truth (name, category,
city, domain). Flags compare what AI said against those facts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Phrases suggesting the business is defunct — high-impact false claims.
_CLOSED_PATTERNS = (
    r"permanently closed",
    r"no longer (?:in business|operating|exists)",
    r"out of business",
    r"has shut down",
    r"is closed down",
)


@dataclass
class Flag:
    type: str
    severity: str  # high | medium | low
    evidence: str


def _snippet(text: str, match: re.Match, width: int = 80) -> str:
    start = max(0, match.start() - width)
    end = min(len(text), match.end() + width)
    return text[start:end].strip()


def detect_flags(
    *,
    text: str,
    category_key: str,
    brand_mentioned: bool,
    name: str,
    city: str | None = None,
    counts_for_factual: bool,
) -> list[Flag]:
    flags: list[Flag] = []
    text = text or ""

    # 1) "Permanently closed" / defunct claims — always high severity.
    for pat in _CLOSED_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            flags.append(Flag(type="claims_closed", severity="high", evidence=_snippet(text, m)))
            break

    # 2) Factual-intent question but the brand isn't mentioned at all — the
    #    model likely doesn't know the business (knowledge gap / possible
    #    confabulation about a different entity).
    if counts_for_factual and name and not brand_mentioned and text.strip():
        flags.append(
            Flag(
                type="brand_absent_on_factual_query",
                severity="medium",
                evidence=text[:160].strip(),
            )
        )

    # 3) City contradiction: a factual answer names the brand but the known city
    #    never appears — weak signal, low severity.
    if counts_for_factual and brand_mentioned and city and city.lower() not in text.lower():
        flags.append(
            Flag(
                type="city_not_confirmed",
                severity="low",
                evidence=f"Known city '{city}' not present in answer.",
            )
        )

    return flags
