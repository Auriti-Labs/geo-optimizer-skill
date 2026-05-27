"""Tests for geo_optimizer.core.agent_access — run_agent_access_audit()."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from geo_optimizer.core.agent_access import _compute_overall_status, run_agent_access_audit
from geo_optimizer.models.results import AgentAccessResult

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_robots(citation_ok=True, blocked=None):
    r = MagicMock()
    r.citation_bots_ok = citation_ok
    r.bots_blocked = blocked or []
    return r


def _make_cdn(any_blocked=False, bot_results=None):
    c = MagicMock()
    c.any_blocked = any_blocked
    c.bot_results = bot_results or []
    return c


def _make_js(js_dependent=False, framework_detected=None):
    j = MagicMock()
    j.js_dependent = js_dependent
    j.framework_detected = framework_detected
    return j


def _make_meta(has_noai=False, x_robots_tag="", x_robots_noindex=False, noai_value=""):
    m = MagicMock()
    m.has_noai = has_noai
    m.x_robots_tag = x_robots_tag
    m.x_robots_noindex = x_robots_noindex
    m.noai_value = noai_value
    return m


def _make_discovery(endpoints_found=2):
    d = MagicMock()
    d.endpoints_found = endpoints_found
    return d


def _make_resp(text="<html><body>content</body></html>"):
    r = MagicMock()
    r.text = text
    return r


# ─── Patch helper ─────────────────────────────────────────────────────────────

_PATCHES = {
    "fetch": "geo_optimizer.core.agent_access.fetch_url",
    "robots": "geo_optimizer.core.agent_access.audit_robots_txt",
    "cdn": "geo_optimizer.core.agent_access.audit_cdn_ai_crawler",
    "js": "geo_optimizer.core.agent_access.audit_js_rendering",
    "meta": "geo_optimizer.core.agent_access.audit_meta_tags",
    "discovery": "geo_optimizer.core.agent_access.audit_ai_discovery",
}


# ─── Tests: status outcomes ───────────────────────────────────────────────────


def test_status_accessible_all_passing():
    with (
        patch(_PATCHES["fetch"], return_value=(_make_resp(), None)),
        patch(_PATCHES["robots"], return_value=_make_robots()),
        patch(_PATCHES["cdn"], return_value=_make_cdn()),
        patch(_PATCHES["js"], return_value=_make_js()),
        patch(_PATCHES["meta"], return_value=_make_meta()),
        patch(_PATCHES["discovery"], return_value=_make_discovery(endpoints_found=4)),
    ):
        result = run_agent_access_audit("https://example.com")

    assert result.overall_status == "accessible"
    assert result.blocking_issues == []
    assert result.url == "https://example.com"


def test_status_blocked_by_cdn():
    cdn = _make_cdn(any_blocked=True, bot_results=[{"bot": "GPTBot", "blocked": True}])
    with (
        patch(_PATCHES["fetch"], return_value=(_make_resp(), None)),
        patch(_PATCHES["robots"], return_value=_make_robots()),
        patch(_PATCHES["cdn"], return_value=cdn),
        patch(_PATCHES["js"], return_value=_make_js()),
        patch(_PATCHES["meta"], return_value=_make_meta()),
        patch(_PATCHES["discovery"], return_value=_make_discovery()),
    ):
        result = run_agent_access_audit("https://example.com")

    assert result.overall_status == "blocked"
    assert result.cdn_challenge_detected is True
    assert any("CDN" in issue for issue in result.blocking_issues)


def test_status_blocked_by_robots():
    with (
        patch(_PATCHES["fetch"], return_value=(_make_resp(), None)),
        patch(_PATCHES["robots"], return_value=_make_robots(citation_ok=False, blocked=["GPTBot", "ClaudeBot"])),
        patch(_PATCHES["cdn"], return_value=_make_cdn()),
        patch(_PATCHES["js"], return_value=_make_js()),
        patch(_PATCHES["meta"], return_value=_make_meta()),
        patch(_PATCHES["discovery"], return_value=_make_discovery()),
    ):
        result = run_agent_access_audit("https://example.com")

    assert result.overall_status == "blocked"
    assert result.robots_allows_citation_bots is False
    assert "GPTBot" in result.robots_blocks


def test_status_partial_js_required():
    with (
        patch(_PATCHES["fetch"], return_value=(_make_resp(), None)),
        patch(_PATCHES["robots"], return_value=_make_robots()),
        patch(_PATCHES["cdn"], return_value=_make_cdn()),
        patch(_PATCHES["js"], return_value=_make_js(js_dependent=True, framework_detected="React")),
        patch(_PATCHES["meta"], return_value=_make_meta()),
        patch(_PATCHES["discovery"], return_value=_make_discovery()),
    ):
        result = run_agent_access_audit("https://example.com")

    assert result.overall_status == "partial"
    assert result.js_required is True
    assert any("JavaScript" in w for w in result.warnings)


def test_status_partial_noai_meta():
    with (
        patch(_PATCHES["fetch"], return_value=(_make_resp(), None)),
        patch(_PATCHES["robots"], return_value=_make_robots()),
        patch(_PATCHES["cdn"], return_value=_make_cdn()),
        patch(_PATCHES["js"], return_value=_make_js()),
        patch(_PATCHES["meta"], return_value=_make_meta(has_noai=True, noai_value="noai")),
        patch(_PATCHES["discovery"], return_value=_make_discovery()),
    ):
        result = run_agent_access_audit("https://example.com")

    assert result.noai_meta_present is True
    assert any("noai" in w for w in result.warnings)


def test_status_unknown_on_fetch_error():
    with (
        patch(_PATCHES["fetch"], return_value=(None, "Connection refused")),
        patch(_PATCHES["robots"], return_value=_make_robots()),
        patch(_PATCHES["cdn"], return_value=_make_cdn()),
        patch(_PATCHES["discovery"], return_value=_make_discovery()),
    ):
        result = run_agent_access_audit("https://unreachable.example.com")

    # No soup → js and meta checks skipped; fetch error in blocking_issues
    assert any("unreachable" in i.lower() or "Page unreachable" in i for i in result.blocking_issues)


def test_sub_audit_exception_does_not_raise():
    """Any sub-audit exception must be caught; function never raises."""
    with (
        patch(_PATCHES["fetch"], side_effect=RuntimeError("network error")),
        patch(_PATCHES["robots"], return_value=_make_robots()),
        patch(_PATCHES["cdn"], return_value=_make_cdn()),
        patch(_PATCHES["discovery"], return_value=_make_discovery()),
    ):
        result = run_agent_access_audit("https://example.com")

    assert isinstance(result, AgentAccessResult)


# ─── Tests: _compute_overall_status ───────────────────────────────────────────


def test_compute_status_no_issues_no_warnings():
    r = AgentAccessResult(url="https://x.com", passing=["robots ok"])
    assert _compute_overall_status(r) == "accessible"


def test_compute_status_hard_blocker():
    r = AgentAccessResult(url="https://x.com", blocking_issues=["CDN/WAF blocks AI bots: GPTBot"])
    assert _compute_overall_status(r) == "blocked"


def test_compute_status_soft_blocker():
    r = AgentAccessResult(url="https://x.com", blocking_issues=["Some unknown issue"])
    assert _compute_overall_status(r) == "partial"


def test_compute_status_warnings_only():
    r = AgentAccessResult(url="https://x.com", warnings=["JS required"])
    assert _compute_overall_status(r) == "partial"


def test_compute_status_nothing():
    r = AgentAccessResult(url="https://x.com")
    assert _compute_overall_status(r) == "unknown"


# ─── Tests: x_robots_noai detection ──────────────────────────────────────────


def test_x_robots_noai_detected_in_header():
    with (
        patch(_PATCHES["fetch"], return_value=(_make_resp(), None)),
        patch(_PATCHES["robots"], return_value=_make_robots()),
        patch(_PATCHES["cdn"], return_value=_make_cdn()),
        patch(_PATCHES["js"], return_value=_make_js()),
        patch(_PATCHES["meta"], return_value=_make_meta(x_robots_tag="noai, noindex")),
        patch(_PATCHES["discovery"], return_value=_make_discovery()),
    ):
        result = run_agent_access_audit("https://example.com")

    assert result.x_robots_noai is True
    assert any("noai" in w for w in result.warnings)
