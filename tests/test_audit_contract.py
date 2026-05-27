"""Contract tests for AuditResult JSON schema stability.

These tests freeze the set of expected top-level keys in AuditResult
and verify new fields are backward-compatible (optional, default values).
"""

from __future__ import annotations

import dataclasses

import pytest

from geo_optimizer.models.results import AuditResult

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
