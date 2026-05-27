"""Agent Access Audit — unified check for AI agent accessibility.

Aggregates robots, CDN, JS rendering, noai meta, and AI discovery checks
into a single AgentAccessResult. Pure function — no I/O, no print.
"""

from __future__ import annotations

from geo_optimizer.core.audit_ai_discovery import audit_ai_discovery
from geo_optimizer.core.audit_cdn import audit_cdn_ai_crawler
from geo_optimizer.core.audit_js import audit_js_rendering
from geo_optimizer.core.audit_meta import audit_meta_tags
from geo_optimizer.core.audit_robots import audit_robots_txt
from geo_optimizer.models.results import AgentAccessResult
from geo_optimizer.utils.http import fetch_url


def run_agent_access_audit(base_url: str) -> AgentAccessResult:
    """Run a unified agent access audit for the given URL.

    Fetches the page once, then calls all relevant sub-audits.
    Returns AgentAccessResult with overall_status and actionable lists.
    Never raises — errors are captured in blocking_issues.
    """
    result = AgentAccessResult(url=base_url)

    # ── Fetch page (single HTTP call shared by JS + meta audits) ──────────────
    soup = None
    raw_html = ""
    try:
        resp, err = fetch_url(base_url)
        if resp is not None and not err:
            from bs4 import BeautifulSoup

            raw_html = resp.text or ""
            soup = BeautifulSoup(raw_html, "html.parser")
        elif err:
            result.blocking_issues.append(f"Page unreachable: {err}")
    except Exception as exc:  # noqa: BLE001
        result.blocking_issues.append(f"Fetch error: {exc}")

    # ── Robots.txt ─────────────────────────────────────────────────────────────
    try:
        robots = audit_robots_txt(base_url)
        result.robots_allows_citation_bots = robots.citation_bots_ok
        result.robots_blocks = list(robots.bots_blocked)
        if robots.bots_blocked:
            result.blocking_issues.append(f"robots.txt blocks: {', '.join(robots.bots_blocked)}")
        else:
            result.passing.append("robots.txt allows AI bots")
    except Exception as exc:  # noqa: BLE001
        result.warnings.append(f"robots.txt check failed: {exc}")

    # ── CDN / WAF challenge ────────────────────────────────────────────────────
    try:
        cdn = audit_cdn_ai_crawler(base_url)
        result.cdn_challenge_detected = cdn.any_blocked
        if cdn.any_blocked:
            blocked_bots = [r["bot"] for r in cdn.bot_results if r.get("blocked")]
            result.blocking_issues.append(f"CDN/WAF blocks AI bots: {', '.join(blocked_bots)}")
        else:
            result.passing.append("No CDN challenge detected for AI bots")
    except Exception as exc:  # noqa: BLE001
        result.warnings.append(f"CDN check failed: {exc}")

    # ── JS rendering ──────────────────────────────────────────────────────────
    if soup is not None:
        try:
            js = audit_js_rendering(soup, raw_html)
            result.js_required = js.js_dependent
            if js.js_dependent:
                result.warnings.append(
                    f"Page content requires JavaScript ({js.framework_detected or 'unknown framework'})"
                )
            else:
                result.passing.append("Content accessible without JavaScript")
        except Exception as exc:  # noqa: BLE001
            result.warnings.append(f"JS rendering check failed: {exc}")

    # ── noai / x-robots meta ──────────────────────────────────────────────────
    if soup is not None:
        try:
            meta = audit_meta_tags(soup, base_url)
            result.noai_meta_present = meta.has_noai
            result.x_robots_noindex = meta.x_robots_noindex
            # x_robots_noai: check if noai/noimageai appears in the x-robots-tag header
            x_robots_lower = meta.x_robots_tag.lower()
            result.x_robots_noai = "noai" in x_robots_lower or "noimageai" in x_robots_lower
            if meta.has_noai:
                result.warnings.append(f"noai/noimageai in meta robots: {meta.noai_value}")
            if result.x_robots_noai:
                result.warnings.append(f"X-Robots-Tag contains noai/noimageai: {meta.x_robots_tag}")
            if not meta.has_noai and not result.x_robots_noai:
                result.passing.append("No noai/noimageai directives found")
        except Exception as exc:  # noqa: BLE001
            result.warnings.append(f"Meta/noai check failed: {exc}")

    # ── AI discovery endpoints ────────────────────────────────────────────────
    try:
        discovery = audit_ai_discovery(base_url)
        result.ai_discovery_score = discovery.endpoints_found
        if discovery.endpoints_found == 0:
            result.warnings.append("No AI discovery endpoints found (ai.txt, ai/*.json)")
        elif discovery.endpoints_found < 3:
            result.warnings.append(f"Partial AI discovery: {discovery.endpoints_found}/4 endpoints")
        else:
            result.passing.append(f"AI discovery: {discovery.endpoints_found}/4 endpoints found")
    except Exception as exc:  # noqa: BLE001
        result.warnings.append(f"AI discovery check failed: {exc}")

    # ── Overall status ────────────────────────────────────────────────────────
    result.overall_status = _compute_overall_status(result)
    return result


def _compute_overall_status(result: AgentAccessResult) -> str:
    """Derive overall_status from blocking_issues and warnings."""
    if result.blocking_issues:
        # CDN blocks or robots blocks are hard blockers
        hard_blockers = [
            i for i in result.blocking_issues if "CDN" in i or "robots.txt blocks" in i or "unreachable" in i.lower()
        ]
        if hard_blockers:
            return "blocked"
        return "partial"
    if result.warnings:
        return "partial"
    if result.passing:
        return "accessible"
    return "unknown"
