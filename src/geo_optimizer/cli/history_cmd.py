"""CLI command: geo history."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from geo_optimizer.cli.formatters import format_history_json, format_history_text
from geo_optimizer.core.history import HistoryStore
from geo_optimizer.models.config import DEFAULT_HISTORY_LIMIT, DEFAULT_HISTORY_RETENTION_DAYS
from geo_optimizer.utils.validators import normalize_url_scheme, validate_public_url


@click.command(name="history")
@click.option("--url", required=True, help="URL for which to show the saved GEO trend")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="Output format for the saved history",
)
@click.option("--output", "output_file", default=None, help="Output file path (optional)")
@click.option("--limit", default=DEFAULT_HISTORY_LIMIT, show_default=True, type=int, help="Maximum snapshots to show")
@click.option(
    "--retention-days",
    default=DEFAULT_HISTORY_RETENTION_DAYS,
    show_default=True,
    type=int,
    help="Retention window for local snapshots",
)
@click.option("--history-db", default=None, hidden=True, help="Override local tracking DB path")
def history(url, output_format, output_file, limit, retention_days, history_db):
    """Show the saved GEO score trend for a URL."""
    normalized_url = normalize_url_scheme(url)
    safe, reason = validate_public_url(normalized_url)
    if not safe:
        click.echo(f"\n❌ Unsafe URL: {reason}", err=True)
        sys.exit(1)

    store = HistoryStore(Path(history_db) if history_db else None)
    result = store.build_history_result(normalized_url, limit=limit, retention_days=retention_days)
    output = format_history_json(result) if output_format == "json" else format_history_text(result)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)
        click.echo(f"✅ Report written to: {output_file}")
        return

    click.echo(output)
