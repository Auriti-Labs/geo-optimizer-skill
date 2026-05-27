"""Tests for geo_optimizer.core.drift_detector — compute_semantic_drift()."""

from __future__ import annotations

from geo_optimizer.core.drift_detector import _classify_severity, compute_semantic_drift
from geo_optimizer.models.results import HistoryEntry, SemanticDriftDelta

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _entry(score: int, breakdown: dict | None = None) -> HistoryEntry:
    return HistoryEntry(
        url="https://example.com",
        timestamp="2026-01-01T00:00:00Z",
        score=score,
        score_breakdown=breakdown or {},
    )


# ─── Tests: score delta ───────────────────────────────────────────────────────


def test_no_drift_same_score():
    a = _entry(80, {"robots": 18, "llms": 15})
    b = _entry(80, {"robots": 18, "llms": 15})
    delta = compute_semantic_drift(a, b)
    assert delta.score_delta == 0
    assert delta.severity == "none"
    assert delta.category_deltas == {}


def test_info_small_score_drop():
    a = _entry(80)
    b = _entry(77)
    delta = compute_semantic_drift(a, b)
    assert delta.score_delta == -3
    assert delta.severity == "info"


def test_warning_score_drop_5():
    a = _entry(80)
    b = _entry(75)
    delta = compute_semantic_drift(a, b)
    assert delta.score_delta == -5
    assert delta.severity == "warning"


def test_critical_score_drop_15():
    a = _entry(80)
    b = _entry(65)
    delta = compute_semantic_drift(a, b)
    assert delta.score_delta == -15
    assert delta.severity == "critical"


def test_positive_score_no_drift():
    a = _entry(70)
    b = _entry(82)
    delta = compute_semantic_drift(a, b)
    assert delta.score_delta == 12
    assert delta.severity == "none"


# ─── Tests: category deltas ───────────────────────────────────────────────────


def test_category_delta_detected():
    a = _entry(80, {"robots": 18, "schema": 16})
    b = _entry(78, {"robots": 18, "schema": 14})
    delta = compute_semantic_drift(a, b)
    assert delta.category_deltas.get("schema") == -2
    assert "robots" not in delta.category_deltas


def test_schema_richness_degraded_flag():
    # Schema drop > 3 triggers schema_types_removed hint
    a = _entry(80, {"schema": 16})
    b = _entry(76, {"schema": 12})
    delta = compute_semantic_drift(a, b)
    assert "schema_richness_degraded" in delta.schema_types_removed
    assert delta.severity in ("warning", "critical")


# ─── Tests: crawlability proxy ────────────────────────────────────────────────


def test_robots_score_drops_to_zero_sets_hint():
    a = _entry(80, {"robots": 18})
    b = _entry(62, {"robots": 0})
    delta = compute_semantic_drift(a, b)
    assert delta.crawlable_before is True
    assert delta.crawlable_after is False
    assert "robots" in delta.blocking_issues_hint


def test_crawlable_both_positive():
    a = _entry(80, {"robots": 18})
    b = _entry(80, {"robots": 15})
    delta = compute_semantic_drift(a, b)
    assert delta.crawlable_before is True
    assert delta.crawlable_after is True


def test_crawlable_before_false_if_no_robots_score():
    a = _entry(70, {"robots": 0})
    b = _entry(70, {"robots": 0})
    delta = compute_semantic_drift(a, b)
    assert delta.crawlable_before is False
    assert delta.crawlable_after is False


# ─── Tests: severity classifier ───────────────────────────────────────────────


def test_severity_critical_crawlable_lost():
    delta = SemanticDriftDelta(
        crawlable_before=True,
        crawlable_after=False,
        score_delta=-2,
    )
    assert _classify_severity(delta, -2) == "critical"


def test_severity_warning_schema_removed():
    delta = SemanticDriftDelta(
        schema_types_removed=["FAQPage"],
        score_delta=-1,
    )
    assert _classify_severity(delta, -1) == "warning"


def test_severity_info_category_change():
    delta = SemanticDriftDelta(
        category_deltas={"llms": -2},
        score_delta=0,
    )
    assert _classify_severity(delta, 0) == "info"


def test_severity_none_no_changes():
    delta = SemanticDriftDelta()
    assert _classify_severity(delta, 0) == "none"


# ─── Tests: detected_at populated ────────────────────────────────────────────


def test_detected_at_is_set():
    a = _entry(80)
    b = _entry(75)
    delta = compute_semantic_drift(a, b)
    assert delta.detected_at != ""
    assert "T" in delta.detected_at  # ISO format
