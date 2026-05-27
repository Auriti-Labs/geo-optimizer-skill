"""Semantic Drift Detector — compares two GEO audit snapshots.

Detects structural and signal changes between two HistoryEntry snapshots.
Pure function — no I/O, no print.
"""

from __future__ import annotations

from datetime import datetime, timezone

from geo_optimizer.models.results import HistoryEntry, SemanticDriftDelta

# Thresholds for severity classification
_SCORE_DROP_CRITICAL = 15
_SCORE_DROP_WARNING = 5


def compute_semantic_drift(
    entry_before: HistoryEntry,
    entry_after: HistoryEntry,
) -> SemanticDriftDelta:
    """Compute the semantic drift delta between two GEO audit snapshots.

    Returns SemanticDriftDelta with severity 'none' if no significant change.
    Severity: 'critical' > 'warning' > 'info' > 'none'
    """
    delta = SemanticDriftDelta(
        detected_at=datetime.now(timezone.utc).isoformat(),
    )

    score_delta = entry_after.score - entry_before.score
    delta.score_delta = score_delta

    # Category-level deltas
    for category, before_val in entry_before.score_breakdown.items():
        after_val = entry_after.score_breakdown.get(category, 0)
        cat_delta = after_val - before_val
        if cat_delta != 0:
            delta.category_deltas[category] = cat_delta

    # Schema types: detect removed types via category score drop
    # (full schema type list not in HistoryEntry — flag via schema category drop)
    schema_drop = delta.category_deltas.get("schema", 0)
    if schema_drop < -3:
        delta.schema_types_removed = ["schema_richness_degraded"]

    # Crawlability proxy: robots category score dropped to 0
    robots_before = entry_before.score_breakdown.get("robots", 0)
    robots_after = entry_after.score_breakdown.get("robots", 0)
    delta.crawlable_before = robots_before > 0
    delta.crawlable_after = robots_after > 0
    if delta.crawlable_before and not delta.crawlable_after:
        delta.blocking_issues_hint = "robots score dropped to 0 — AI bots may be blocked"

    # Severity
    delta.severity = _classify_severity(delta, score_delta)
    return delta


def _classify_severity(delta: SemanticDriftDelta, score_delta: int) -> str:
    """Classify drift severity based on score drop and structural changes."""
    if score_delta <= -_SCORE_DROP_CRITICAL:
        return "critical"
    if score_delta <= -_SCORE_DROP_WARNING:
        return "warning"
    if delta.schema_types_removed:
        return "warning"
    if not delta.crawlable_after and delta.crawlable_before:
        return "critical"
    if delta.category_deltas:
        return "info"
    if score_delta < 0:
        return "info"
    return "none"
