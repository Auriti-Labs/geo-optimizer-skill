"""Hallucination / factual-mismatch flags (v1 heuristics). Pure, no I/O.

Flags are ADVISORY and evidence-bearing — never auto-acted. Each flag carries a
type, severity, and the text evidence that triggered it. Heuristics are
intentionally conservative; precision is refined in later phases.

Inputs are one AI answer plus the entity's name and intent category. v2 tuned
for precision: "closed" claims require the brand to be named and unnegated, the
former noisy "brand absent" flag is reclassified as a low-severity *visibility*
gap gated on substantive responses, and the weak city-mismatch flag was removed.
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


# A minimum response length below which "the brand isn't mentioned" is not
# meaningful (e.g. refusals, one-liners). Avoids flagging trivial answers.
_SUBSTANTIVE_MIN_CHARS = 120

# Negation cues immediately before a "closed" phrase that invert its meaning
# ("not permanently closed", "no longer closed", "never closed").
_NEGATION_BEFORE = re.compile(r"(?:\bnot\b|\bn't\b|\bnever\b|\bno longer\b)\s+\w*\s*$", re.IGNORECASE)


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
    city: str | None = None,  # retained for signature stability; no longer used
    counts_for_factual: bool,
) -> list[Flag]:
    """Return advisory, evidence-bearing flags. Tuned for precision over recall.

    Each flag explains a *specific* divergence and carries the text that
    triggered it. We deliberately favor fewer, higher-confidence flags: a noisy
    flag erodes trust faster than a missed one informs.
    """
    flags: list[Flag] = []
    text = text or ""

    # 1) "Permanently closed" / defunct claims — high severity, but ONLY when the
    #    answer actually names this business (otherwise the statement is about
    #    someone else) and is not negated ("not permanently closed").
    if brand_mentioned:
        for pat in _CLOSED_PATTERNS:
            m = re.search(pat, text, re.IGNORECASE)
            if m and not _NEGATION_BEFORE.search(text[: m.start()][-24:]):
                flags.append(Flag(type="claims_closed", severity="high", evidence=_snippet(text, m)))
                break

    # 2) Direct identity/factual question, a substantive answer, but the brand is
    #    never mentioned. This is a VISIBILITY gap (the model doesn't recognize
    #    the business), not a hallucination — low severity, clearly typed. Gated
    #    on response length so refusals/one-liners don't trip it.
    if (
        counts_for_factual
        and name
        and not brand_mentioned
        and len(text.strip()) >= _SUBSTANTIVE_MIN_CHARS
    ):
        flags.append(
            Flag(
                type="brand_not_recognized",
                severity="low",
                evidence=text[:160].strip(),
            )
        )

    return flags
