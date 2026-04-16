"""
GEO Audit — Content Decay Predictor (#383).

Detects content that will become stale:
- Temporal: explicit years/dates ("In 2026, ...")
- Statistical: numeric claims ("42% of users...")
- Version: software versions ("Python 3.11")
- Event: recency language ("recently", "just launched")
- Price: monetary values ("$99/month")
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from geo_optimizer.models.results import ContentDecayResult, DecaySignal

# ─── Patterns ────────────────────────────────────────────────────────────────

_YEAR_RE = re.compile(r"\b(20[2-3]\d)\b")
_STAT_RE = re.compile(r"\b(\d{1,3}(?:\.\d+)?%)\s+(?:of|increase|decrease|growth|decline|more|less)\b", re.IGNORECASE)
_VERSION_RE = re.compile(
    r"\b(?:Python|Node|Java|PHP|Ruby|Go|Rust|React|Angular|Vue|Next\.?js|Django|Laravel|Rails|Swift|Kotlin|TypeScript)"
    r"\s+(\d+(?:\.\d+)+)"
    r"|\bv(?:ersion)?\s*(\d+\.\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)
_EVENT_RE = re.compile(
    r"\b(recently|just\s+(?:launched|released|announced|updated)|this\s+(?:month|quarter|year)"
    r"|last\s+(?:month|quarter|week)|the\s+(?:latest|newest|current)\s+(?:version|release|update))\b",
    re.IGNORECASE,
)
_PRICE_RE = re.compile(r"[\$€£]\s*\d[\d,]*(?:\.\d{2})?(?:\s*/\s*(?:mo(?:nth)?|yr|year|annual))?", re.IGNORECASE)

_DECAY_DAYS = {
    "temporal": 365,
    "statistical": 540,
    "version": 365,
    "event": 180,
    "price": 180,
}

_SUGGESTIONS = {
    "temporal": "Use relative time or add dateModified schema for freshness signals",
    "statistical": "Add source attribution with date; consider 'as of [date]' pattern",
    "version": "Use 'latest version' or add a last-updated note",
    "event": "Replace recency language with specific dates",
    "price": "Add 'pricing as of [date]' or link to live pricing page",
}


def audit_content_decay(soup, clean_text: str | None = None) -> ContentDecayResult:
    """Predict content decay from temporal patterns in page text.

    Args:
        soup: BeautifulSoup of the HTML document.
        clean_text: Optional pre-extracted body text.

    Returns:
        ContentDecayResult with decay signals and evergreen score.
    """
    if clean_text is None:
        body = soup.find("body") if soup else None
        clean_text = body.get_text(separator=" ", strip=True) if body else ""

    if not clean_text:
        return ContentDecayResult(checked=True)

    signals: list[DecaySignal] = []
    now_year = datetime.now(timezone.utc).year

    # Temporal: explicit years
    for m in _YEAR_RE.finditer(clean_text):
        year = int(m.group(1))
        if year <= now_year:
            days = (now_year - year + 1) * 365
            ctx = clean_text[max(0, m.start() - 30) : m.end() + 30].strip()
            signals.append(DecaySignal("temporal", ctx, days, _SUGGESTIONS["temporal"]))

    # Statistical
    for m in _STAT_RE.finditer(clean_text):
        ctx = clean_text[max(0, m.start() - 30) : m.end() + 30].strip()
        signals.append(DecaySignal("statistical", ctx, _DECAY_DAYS["statistical"], _SUGGESTIONS["statistical"]))

    # Version
    for m in _VERSION_RE.finditer(clean_text):
        ctx = clean_text[max(0, m.start() - 20) : m.end() + 20].strip()
        signals.append(DecaySignal("version", ctx, _DECAY_DAYS["version"], _SUGGESTIONS["version"]))

    # Event / recency language
    for m in _EVENT_RE.finditer(clean_text):
        ctx = clean_text[max(0, m.start() - 20) : m.end() + 30].strip()
        signals.append(DecaySignal("event", ctx, _DECAY_DAYS["event"], _SUGGESTIONS["event"]))

    # Price
    for m in _PRICE_RE.finditer(clean_text):
        ctx = clean_text[max(0, m.start() - 20) : m.end() + 20].strip()
        signals.append(DecaySignal("price", ctx, _DECAY_DAYS["price"], _SUGGESTIONS["price"]))

    # Dedupe by text (keep first occurrence)
    seen: set[str] = set()
    unique: list[DecaySignal] = []
    for s in signals:
        key = s.text[:60]
        if key not in seen:
            seen.add(key)
            unique.append(s)
    signals = unique[:20]

    earliest = min((s.estimated_stale_days for s in signals), default=None)
    risk = _compute_risk(signals)
    evergreen = _compute_evergreen(signals)

    return ContentDecayResult(
        checked=True,
        signals=signals,
        earliest_decay_days=earliest,
        decay_risk=risk,
        evergreen_score=evergreen,
    )


def _compute_risk(signals: list[DecaySignal]) -> str:
    """Classify decay risk based on signal count and types."""
    if not signals:
        return "low"
    high_types = {"temporal", "event"}
    high_count = sum(1 for s in signals if s.decay_type in high_types)
    if high_count >= 3 or len(signals) >= 6:
        return "high"
    if high_count >= 1 or len(signals) >= 3:
        return "medium"
    return "low"


def _compute_evergreen(signals: list[DecaySignal]) -> int:
    """Compute evergreen score: 100 minus penalties per signal."""
    score = 100
    for s in signals:
        if s.decay_type in {"temporal", "event"}:
            score -= 8
        elif s.decay_type == "statistical":
            score -= 5
        else:
            score -= 3
    return max(score, 0)
