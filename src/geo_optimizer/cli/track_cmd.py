"""CLI command: geo track."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from geo_optimizer.cli.formatters import (
    format_history_json,
    format_history_report_html,
    format_history_text,
    format_tracking_json,
    format_tracking_text,
)
from geo_optimizer.core.audit import run_full_audit
from geo_optimizer.core.history import HistoryStore
from geo_optimizer.models.config import DEFAULT_HISTORY_LIMIT, DEFAULT_HISTORY_RETENTION_DAYS
from geo_optimizer.models.project_config import load_config
from geo_optimizer.utils.validators import validate_public_url


@click.command(name="track")
@click.option("--url", required=True, help="URL to audit and store in local GEO tracking")
@click.option("--history", "show_history", is_flag=True, help="Show saved history instead of running a new audit")
@click.option("--report", is_flag=True, help="Generate an HTML report after saving the new snapshot")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="Output format",
)
@click.option("--output", "output_file", default=None, help="Output file path (optional)")
@click.option("--cache", is_flag=True, help="Use local HTTP cache for the audit step")
@click.option("--config", "config_file", default=None, help="Path to .geo-optimizer.yml config file")
@click.option("--limit", default=DEFAULT_HISTORY_LIMIT, show_default=True, type=int, help="Maximum snapshots to show")
@click.option(
    "--retention-days",
    default=DEFAULT_HISTORY_RETENTION_DAYS,
    show_default=True,
    type=int,
    help="Retention window for local snapshots",
)
@click.option("--history-db", default=None, hidden=True, help="Override local tracking DB path")
def track(url, show_history, report, output_format, output_file, cache, config_file, limit, retention_days, history_db):
    """Run GEO monitoring with local tracking and trend reports."""
    if show_history and report:
        raise click.UsageError("Use either '--history' or '--report', not both")

    normalized_url = url if url.startswith(("http://", "https://")) else f"https://{url}"
    safe, reason = validate_public_url(normalized_url)
    if not safe:
        click.echo(f"\n❌ Unsafe URL: {reason}", err=True)
        sys.exit(1)

    config_path = Path(config_file) if config_file else None
    project_config = load_config(config_path)
    store = HistoryStore(Path(history_db) if history_db else None)

    if show_history:
        history_result = store.build_history_result(normalized_url, limit=limit, retention_days=retention_days)
        output = format_history_json(history_result) if output_format == "json" else format_history_text(history_result)
    else:
        audit_result = run_full_audit(normalized_url, use_cache=cache, project_config=project_config)
        if audit_result.error:
            click.echo(f"\n❌ Audit failed, snapshot not saved: {audit_result.error}", err=True)
            sys.exit(1)
        store.save_audit_result(audit_result, retention_days=retention_days)
        history_result = store.build_history_result(normalized_url, limit=limit, retention_days=retention_days)

        if report:
            output = format_history_report_html(history_result)
            output_file = output_file or "geo-track-report.html"
        elif output_format == "json":
            output = format_tracking_json(audit_result, history_result)
        else:
            output = format_tracking_text(audit_result, history_result)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)
        click.echo(f"✅ Report written to: {output_file}")
        return

    click.echo(output)
