"""Contract tests for AuditResult JSON schema stability.

These tests freeze the set of expected top-level keys in AuditResult
and verify new fields are backward-compatible (optional, default values).
Also verifies _audit_result_to_dict() output (web API contract v1).
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from geo_optimizer.models.results import AuditResult

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "audit_result_v1.json"

# Expected core keys that must always be present in AuditResult
_REQUIRED_KEYS = {
    "url",
    "timestamp",
    "score",
    "band",
    "robots",
    "llms",
    "schema",
    "meta",
    "content",
    "recommendations",
    "http_status",
    "citability",
    "signals",
    "ai_discovery",
    "score_breakdown",
    "error",
    "cdn_check",
    "js_rendering",
    "brand_entity",
    "negative_signals",
    "trust_stack",
}


def test_audit_result_has_required_fields():
    """All expected keys present in AuditResult dataclass."""
    result = AuditResult(url="https://example.com")
    result_dict = dataclasses.asdict(result)
    missing = _REQUIRED_KEYS - set(result_dict.keys())
    assert missing == set(), f"Missing keys in AuditResult: {missing}"


def test_audit_result_url_required():
    """url field is required (no default)."""
    with pytest.raises(TypeError):
        AuditResult()  # type: ignore[call-arg]


def test_audit_result_defaults_safe():
    """All non-url fields have safe defaults — no None unless explicit."""
    result = AuditResult(url="https://example.com")
    assert result.score == 0
    assert result.band == "critical"
    assert result.error is None
    assert isinstance(result.recommendations, list)
    assert isinstance(result.score_breakdown, dict)


def test_audit_result_agent_access_optional():
    """agent_access is NOT a field of AuditResult — new features stay in separate dataclasses."""
    result = AuditResult(url="https://example.com")
    result_dict = dataclasses.asdict(result)
    # agent_access lives in AgentAccessResult, not inline in AuditResult
    assert "agent_access" not in result_dict


def test_new_dataclasses_importable():
    """AgentAccessResult, SemanticDriftDelta, PerceptionSnapshot are importable."""
    from geo_optimizer.models.results import (
        AgentAccessResult,
        PerceptionSnapshot,
        SemanticDriftDelta,
    )

    assert AgentAccessResult is not None
    assert SemanticDriftDelta is not None
    assert PerceptionSnapshot is not None


def test_agent_access_result_defaults():
    from geo_optimizer.models.results import AgentAccessResult

    r = AgentAccessResult()
    assert r.overall_status == "unknown"
    assert r.url == ""
    assert r.blocking_issues == []
    assert r.passing == []
    assert r.warnings == []


def test_semantic_drift_delta_defaults():
    from geo_optimizer.models.results import SemanticDriftDelta

    d = SemanticDriftDelta()
    assert d.severity == "none"
    assert d.score_delta == 0
    assert d.schema_types_removed == []
    assert d.blocking_issues_hint == ""


def test_perception_snapshot_disclaimer_default():
    from geo_optimizer.models.results import PerceptionSnapshot

    p = PerceptionSnapshot()
    assert "Simulated" in p.disclaimer or "simulated" in p.disclaimer.lower()
    assert p.mode == "deterministic"


# ─── Web API contract v1 (_audit_result_to_dict) ──────────────────────────────


def _make_minimal_audit_result():
    """AuditResult with all sub-results populated to default instances."""
    from geo_optimizer.models.results import (
        AiDiscoveryResult,
        BrandEntityResult,
        ContentResult,
        LlmsTxtResult,
        MetaResult,
        RobotsResult,
        SchemaResult,
        SignalsResult,
    )

    return AuditResult(
        url="https://example.com",
        robots=RobotsResult(),
        llms=LlmsTxtResult(),
        schema=SchemaResult(),
        meta=MetaResult(),
        content=ContentResult(),
        signals=SignalsResult(),
        ai_discovery=AiDiscoveryResult(),
        brand_entity=BrandEntityResult(),
    )


def _call_audit_result_to_dict(result):
    """Import and call _audit_result_to_dict from web app."""
    import importlib
    import os

    # Dipendenza opzionale: il web app richiede FastAPI (extra [web]).
    # In CI si installa solo [dev], quindi skip se FastAPI non c'è.
    pytest.importorskip("fastapi", reason="FastAPI non installato (pip install geo-optimizer-skill[web])")

    os.environ.setdefault("GEO_STATIC_DIR", str(Path(__file__).parent.parent / "frontend/dist"))
    app_module = importlib.import_module("geo_optimizer.web.app")
    return app_module._audit_result_to_dict(result)


def test_web_api_llms_exposes_blocked_by_cdn():
    """`checks.llms_txt` must expose blocked_by_cdn and validation_warnings.

    The SaaS platform consumes this serialization to decide the llms.txt
    recommendation; a CDN/WAF block (v4.18.3) must be visible so the platform
    does not tell the user to "create" a file that may already exist behind
    the WAF.
    """
    from geo_optimizer.models.results import LlmsTxtResult

    result = _make_minimal_audit_result()
    result.llms = LlmsTxtResult(
        found=False,
        blocked_by_cdn=True,
        validation_warnings=["llms.txt may exist but CDN/WAF returned 403"],
    )

    data = _call_audit_result_to_dict(result)
    llms_txt = data["checks"]["llms_txt"]
    assert llms_txt["blocked_by_cdn"] is True
    assert "CDN/WAF" in llms_txt["validation_warnings"][0]


def test_web_api_has_schema_version():
    """Web API JSON response must include schema_version: 1."""
    result = _make_minimal_audit_result()
    data = _call_audit_result_to_dict(result)
    assert "schema_version" in data, "schema_version missing from web API response"
    assert data["schema_version"] == 1


def test_web_api_required_top_level_keys():
    """Web API must include all required top-level keys from fixture contract."""
    fixture = json.loads(_FIXTURE_PATH.read_text())
    required = set(fixture["required_top_level_keys"])

    result = _make_minimal_audit_result()
    data = _call_audit_result_to_dict(result)
    missing = required - set(data.keys())
    assert missing == set(), f"Missing top-level keys in web API response: {missing}"


def test_web_api_score_breakdown_has_eight_categories():
    """score_breakdown must contain all 8 scoring categories."""
    fixture = json.loads(_FIXTURE_PATH.read_text())
    required = set(fixture["required_score_breakdown_keys"])

    result = _make_minimal_audit_result()
    data = _call_audit_result_to_dict(result)
    breakdown = data.get("score_breakdown", {})
    missing = required - set(breakdown.keys())
    assert missing == set(), f"Missing score_breakdown categories: {missing}"


def test_web_api_checks_has_alias_keys():
    """checks dict must include alias keys used by platform consumers."""
    fixture = json.loads(_FIXTURE_PATH.read_text())
    required_checks = set(fixture["required_checks_keys"])

    result = _make_minimal_audit_result()
    data = _call_audit_result_to_dict(result)
    checks = data.get("checks", {})
    missing = required_checks - set(checks.keys())
    assert missing == set(), f"Missing checks keys (platform consumers broken): {missing}"


def test_web_api_checks_alias_values_match_source():
    """Alias keys in checks must equal their source field values."""
    from geo_optimizer.models.results import LlmsTxtResult, RobotsResult

    result = _make_minimal_audit_result()
    result.robots = RobotsResult(citation_bots_ok=True)
    result.llms = LlmsTxtResult(found=True, has_full=True)

    data = _call_audit_result_to_dict(result)
    checks = data["checks"]

    assert checks["robots_citation_ok"] is True
    assert checks["llms_found"] is True
    assert checks["llms_full"] is True


def test_web_api_checks_alias_false_by_default():
    """Alias keys default to False when sub-results are default."""
    result = _make_minimal_audit_result()
    data = _call_audit_result_to_dict(result)
    checks = data["checks"]

    assert checks["robots_citation_ok"] is False
    assert checks["llms_found"] is False
    assert checks["llms_full"] is False


def test_web_api_checks_signals_section_present():
    """checks must include signals section (was missing before v1)."""
    result = _make_minimal_audit_result()
    data = _call_audit_result_to_dict(result)
    checks = data["checks"]

    assert "signals" in checks
    assert "has_lang" in checks["signals"]
    assert "has_rss" in checks["signals"]


def test_web_api_checks_ai_discovery_section_present():
    """checks must include ai_discovery section (was missing before v1)."""
    result = _make_minimal_audit_result()
    data = _call_audit_result_to_dict(result)
    checks = data["checks"]

    assert "ai_discovery" in checks
    assert "has_well_known_ai" in checks["ai_discovery"]
    assert "endpoints_found" in checks["ai_discovery"]


def test_web_api_checks_brand_entity_section_present():
    """checks must include brand_entity section (was missing before v1)."""
    result = _make_minimal_audit_result()
    data = _call_audit_result_to_dict(result)
    checks = data["checks"]

    assert "brand_entity" in checks
    assert "brand_name_consistent" in checks["brand_entity"]


def test_web_api_band_is_valid_value():
    """band must be one of the four valid values."""
    fixture = json.loads(_FIXTURE_PATH.read_text())
    valid_bands = set(fixture["band_values"])

    result = _make_minimal_audit_result()
    data = _call_audit_result_to_dict(result)
    assert data["band"] in valid_bands, f"Invalid band value: {data['band']}"


def test_fixture_file_exists():
    """Fixture file must exist and be valid JSON."""
    assert _FIXTURE_PATH.exists(), f"Fixture not found: {_FIXTURE_PATH}"
    fixture = json.loads(_FIXTURE_PATH.read_text())
    assert fixture["_contract_version"] == 1


def test_web_api_score_breakdown_follows_result_rubric_version():
    """Un risultato v2 espone google_ai nel breakdown e i massimi v2 in score_max."""
    from geo_optimizer.models.config import CATEGORY_MAX_V2

    result = _make_minimal_audit_result()
    result.score_version = 2
    result.score_max = dict(CATEGORY_MAX_V2)
    result.score_breakdown = {"google_ai": 15, "robots": 10}
    data = _call_audit_result_to_dict(result)
    assert data["score_breakdown"]["google_ai"] == 15
    assert set(data["score_breakdown"]) == set(CATEGORY_MAX_V2)
    assert data["score_max"] == CATEGORY_MAX_V2
