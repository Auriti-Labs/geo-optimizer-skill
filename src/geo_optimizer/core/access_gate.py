"""Access gate (rubric v6): can AI crawlers read this page at all?

A page can score well on markup and still be unreadable: the server refuses it, a CDN blocks the AI user agents,
every citation bot is disallowed, a ``noindex`` is set, or the raw HTML is an empty shell that needs JavaScript.
The gate reads signals the audit already collected and adds no request. ``blocked`` caps the score
(``ACCESS_GATE_SCORE_CAP``); ``warn`` lists a restriction that does not block every crawler; ``pass`` means nothing
found. ``core/`` does not print.
"""

from __future__ import annotations

from geo_optimizer.core.scoring import get_score_band
from geo_optimizer.models.config import ACCESS_GATE_SCORE_CAP, CITATION_BOTS, JS_CRITICAL_WORDS
from geo_optimizer.models.results import AccessGate, AuditResult


def evaluate_access_gate(result: AuditResult) -> AccessGate:
    """The gate for ``result``: reasons that block, warnings that restrict, otherwise pass."""
    reasons: list[str] = []
    warnings: list[str] = []

    if result.http_status >= 400:
        reasons.append(f"The page answers HTTP {result.http_status}")
    if result.cdn_check.checked and result.cdn_check.block_pattern == "blanket":
        reasons.append("A CDN or firewall blocks every AI crawler tested")
    elif result.cdn_check.checked and result.cdn_check.any_blocked:
        warnings.append("A CDN or firewall blocks some AI crawlers")
    if result.meta.x_robots_noindex:
        reasons.append("X-Robots-Tag: noindex")
    blocked_citation = sorted(CITATION_BOTS.intersection(result.robots.bots_blocked))
    if result.robots.found and blocked_citation and len(blocked_citation) == len(CITATION_BOTS):
        reasons.append("robots.txt disallows every citation bot")
    elif blocked_citation:
        warnings.append("robots.txt disallows some citation bots: " + ", ".join(blocked_citation))
    js = result.js_rendering
    if js.checked and js.js_dependent and js.raw_word_count < JS_CRITICAL_WORDS:
        reasons.append(f"Script-dependent page with {js.raw_word_count} words in the raw HTML")
    elif js.checked and js.js_dependent:
        warnings.append("The page needs JavaScript to render part of its content")
    if result.meta.has_noai:
        warnings.append("meta robots asks AI engines not to use the content (noai)")

    status = "blocked" if reasons else "warn" if warnings else "pass"
    return AccessGate(status=status, reasons=reasons, warnings=warnings)


def gate_for_http_status(status: int) -> AccessGate:
    """The gate of an audit that stopped at the first request because the page answered ``status`` (anything other
    than 200 or 203). The audit scores such a page 0 and never reaches the checks above; the gate still says why."""
    return AccessGate(status="blocked", reasons=[f"The page answers HTTP {status}"])


def apply_access_gate(result: AuditResult) -> None:
    """Set ``result.access_gate`` and, when blocked, cap the score and recompute the band."""
    gate = evaluate_access_gate(result)
    if gate.status == "blocked" and result.score > ACCESS_GATE_SCORE_CAP:
        gate.score_before_cap = result.score
        result.score = ACCESS_GATE_SCORE_CAP
        result.band = get_score_band(result.score)
    result.access_gate = gate
