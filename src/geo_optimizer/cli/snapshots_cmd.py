"""CLI command: geo snapshots."""

from __future__ import annotations

from pathlib import Path

import click

from geo_optimizer.cli.formatters import (
    format_citation_quality_json,
    format_citation_quality_text,
    format_snapshot_archive_json,
    format_snapshot_archive_text,
    format_snapshot_saved_text,
)
from geo_optimizer.core.citation_quality import analyze_snapshot_citation_quality
from geo_optimizer.core.snapshots import SnapshotStore
from geo_optimizer.models.config import DEFAULT_SNAPSHOT_LIMIT


@click.command(name="snapshots")
@click.option("--query", default="", help="Query text to filter or associate with the snapshot")
@click.option("--prompt", default="", help="Prompt used to produce the answer snapshot")
@click.option("--model", default="", help="Model/version used to generate the answer")
@click.option("--provider", default="", help="Provider name (OpenAI, Anthropic, Google, etc.)")
@click.option("--quality", "show_quality", is_flag=True, help="Analyze citation quality for an archived snapshot")
@click.option("--snapshot-id", default=None, type=int, help="Snapshot ID to inspect in quality mode")
@click.option("--target-domain", default="", help="Optional citation domain to focus on in quality mode")
@click.option("--answer-text", default=None, help="Answer text to archive directly")
@click.option("--answer-file", default=None, help="Path to a file containing the full answer text")
@click.option("--citation-url", "citation_urls", multiple=True, help="Extra cited URL to store explicitly")
@click.option("--timestamp", default=None, help="Snapshot timestamp (ISO 8601 or YYYY-MM-DD)")
@click.option("--from", "date_from", default=None, help="List snapshots from this date (YYYY-MM-DD or ISO 8601)")
@click.option("--to", "date_to", default=None, help="List snapshots until this date (YYYY-MM-DD or ISO 8601)")
@click.option(
    "--limit", default=DEFAULT_SNAPSHOT_LIMIT, show_default=True, type=int, help="Maximum snapshots to return"
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="Output format",
)
@click.option("--output", "output_file", default=None, help="Output file path (optional)")
@click.option("--snapshots-db", default=None, hidden=True, help="Override local snapshots DB path")
def snapshots(
    query,
    prompt,
    model,
    provider,
    show_quality,
    snapshot_id,
    target_domain,
    answer_text,
    answer_file,
    citation_urls,
    timestamp,
    date_from,
    date_to,
    limit,
    output_format,
    output_file,
    snapshots_db,
):
    """Archive or query saved AI answer snapshots."""
    if answer_text and answer_file:
        raise click.UsageError("Use either '--answer-text' or '--answer-file', not both")

    store = SnapshotStore(Path(snapshots_db) if snapshots_db else None)
    save_mode = bool(answer_text or answer_file)
    quality_mode = bool(show_quality)

    if quality_mode and save_mode:
        raise click.UsageError("'--quality' cannot be combined with snapshot save options")

    if quality_mode:
        if snapshot_id is None:
            raise click.UsageError("'--snapshot-id' is required in quality mode")
        snapshot = store.get_snapshot(snapshot_id)
        if snapshot is None:
            raise click.UsageError(f"Snapshot {snapshot_id} not found")
        report = analyze_snapshot_citation_quality(snapshot, target_domain=target_domain)
        output = (
            format_citation_quality_json(report) if output_format == "json" else format_citation_quality_text(report)
        )
    elif save_mode:
        if not query:
            raise click.UsageError("'--query' is required when saving a snapshot")
        if not model:
            raise click.UsageError("'--model' is required when saving a snapshot")
        if answer_file:
            answer_content = Path(answer_file).read_text(encoding="utf-8")
        else:
            answer_content = answer_text or ""
        if not answer_content.strip():
            raise click.UsageError("Answer text is empty")

        saved = store.save_snapshot(
            query=query,
            prompt=prompt,
            answer_text=answer_content,
            model=model,
            provider=provider,
            recorded_at=timestamp,
            citation_urls=list(citation_urls),
        )
        output = format_snapshot_archive_json(saved) if output_format == "json" else format_snapshot_saved_text(saved)
    else:
        archive = store.list_snapshots(
            query=query,
            date_from=date_from,
            date_to=date_to,
            model=model,
            limit=limit,
        )
        output = (
            format_snapshot_archive_json(archive) if output_format == "json" else format_snapshot_archive_text(archive)
        )

    if output_file:
        Path(output_file).write_text(output, encoding="utf-8")
        click.echo(f"✅ Report written to: {output_file}")
        return

    click.echo(output)
