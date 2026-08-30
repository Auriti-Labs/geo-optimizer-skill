"""CLI command: geo diff."""

from __future__ import annotations

import sys

import click

from geo_optimizer.cli.formatters import format_audit_diff_json, format_audit_diff_text
from geo_optimizer.core.diffing import run_diff_audit
from geo_optimizer.utils.validators import normalize_url_scheme, validate_public_url


@click.command()
@click.option("--before", "before_url", required=True, help="Baseline URL before optimization")
@click.option("--after", "after_url", required=True, help="Candidate URL after optimization")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="Output format for the A/B comparison",
)
@click.option("--output", "output_file", default=None, help="Output file path (optional)")
@click.option("--cache", is_flag=True, help="Use local HTTP cache for faster repeated audits")
@click.option("--config", "config_file", default=None, help="Path to .geo-optimizer.yml config file")
def diff(before_url, after_url, output_format, output_file, cache, config_file):
    """Compare two pages or sites with a GEO A/B diff."""
    from geo_optimizer.models.project_config import load_config

    config_path = None
    if config_file:
        from pathlib import Path

        config_path = Path(config_file)

    project_config = load_config(config_path)

    for label, url in (("before", before_url), ("after", after_url)):
        safe, reason = validate_public_url(normalize_url_scheme(url))
        if not safe:
            click.echo(f"\n❌ Unsafe {label} URL: {reason}", err=True)
            sys.exit(1)

    try:
        if output_format != "json":
            click.echo("⏳ Running GEO diff...", err=True)
            click.echo("⏳ Auditing baseline and candidate URLs...", err=True)
        result = run_diff_audit(before_url, after_url, use_cache=cache, project_config=project_config)
        if output_format != "json":
            click.echo("✅ Diff complete.\n", err=True)
    except Exception as e:
        if output_format == "json":
            import json

            error_msg = type(e).__name__ if not str(e) else str(e).split("\n")[0][:200]
            click.echo(json.dumps({"error": error_msg, "before_url": before_url, "after_url": after_url}, indent=2))
        else:
            click.echo(f"\n❌ ERROR: {type(e).__name__}", err=True)
        sys.exit(1)

    if output_format == "json":
        output = format_audit_diff_json(result)
    else:
        output = format_audit_diff_text(result)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)
        click.echo(f"✅ Report written to: {output_file}")
    else:
        click.echo(output)

    return result.score_delta
