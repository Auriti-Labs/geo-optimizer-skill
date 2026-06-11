"""CLI command: geo drift — semantic drift between the last two saved snapshots.

MVP B (Quiet Glass): compares the two most recent local history entries for a
URL and reports what changed — score, per-category deltas, crawlability, and
schema degradation — with a severity verdict. One-shot and local by design;
continuous drift monitoring with alerts lives in the platform.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import click

from geo_optimizer.core.drift_detector import compute_semantic_drift
from geo_optimizer.core.history import HistoryStore, canonicalize_history_url

_SEVERITY_RANK = {"none": 0, "info": 1, "warning": 2, "critical": 3}
_SEVERITY_ICON = {"none": "✅", "info": "ℹ️", "warning": "🟡", "critical": "❌"}


def _format_text(delta, before, after) -> str:
    lines: list[str] = []
    lines.append("")
    lines.append("📉 SEMANTIC DRIFT")
    lines.append("=" * 60)
    lines.append(f"Compared:  {before.timestamp}  →  {after.timestamp}")
    sign = "+" if delta.score_delta > 0 else ""
    lines.append(f"Score:     {before.score} → {after.score} ({sign}{delta.score_delta})")
    lines.append(f"Severity:  {_SEVERITY_ICON.get(delta.severity, '')} {delta.severity.upper()}")

    if delta.category_deltas:
        lines.append("")
        lines.append("Category changes:")
        for category, value in sorted(delta.category_deltas.items(), key=lambda kv: kv[1]):
            sign = "+" if value > 0 else ""
            lines.append(f"  {'▼' if value < 0 else '▲'} {category}: {sign}{value}")

    if delta.blocking_issues_hint:
        lines.append("")
        lines.append(f"⚠️  {delta.blocking_issues_hint}")
    if delta.schema_types_removed:
        lines.append("⚠️  Schema richness degraded since the previous snapshot")

    if delta.severity == "none":
        lines.append("")
        lines.append("No significant drift between the last two snapshots.")

    lines.append("")
    lines.append("One-shot comparison. Continuous drift monitoring with email")
    lines.append("alerts runs on every plan with monitoring → https://geoready.dev")
    return "\n".join(lines)


@click.command(name="drift")
@click.option("--url", required=True, help="URL whose saved history to compare")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="Output format",
)
@click.option(
    "--fail-on",
    type=click.Choice(["info", "warning", "critical"]),
    default=None,
    help="Exit non-zero if drift severity reaches this level (for CI)",
)
@click.option("--history-db", default=None, hidden=True, help="Override local tracking DB path")
def drift(url: str, output_format: str, fail_on: str | None, history_db: str | None) -> None:
    """Detect semantic drift between the last two saved audit snapshots.

    Requires at least two history entries for the URL — create them with:

      geo audit --url URL --save-history
    """
    store = HistoryStore(Path(history_db) if history_db else None)
    result = store.build_history_result(canonicalize_history_url(url), limit=2)

    if len(result.entries) < 2:
        click.echo(
            f"\n❌ Need at least 2 saved snapshots for {url} "
            f"(found {len(result.entries)}).\n"
            "   Create them with: geo audit --url URL --save-history",
            err=True,
        )
        sys.exit(1)

    # Entries are newest-first: entries[1] is the older snapshot.
    after, before = result.entries[0], result.entries[1]
    delta = compute_semantic_drift(before, after)

    if output_format == "json":
        payload = {
            "url": result.url,
            "before": {"timestamp": before.timestamp, "score": before.score},
            "after": {"timestamp": after.timestamp, "score": after.score},
            "drift": asdict(delta),
        }
        click.echo(json.dumps(payload, indent=2))
    else:
        click.echo(_format_text(delta, before, after))

    if fail_on and _SEVERITY_RANK[delta.severity] >= _SEVERITY_RANK[fail_on]:
        sys.exit(2)
