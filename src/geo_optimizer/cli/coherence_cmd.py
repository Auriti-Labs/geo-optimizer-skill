"""CLI command: geo coherence."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict

import click

from geo_optimizer.core.site_coherence import run_site_coherence
from geo_optimizer.utils.validators import validate_public_url


@click.command(name="coherence")
@click.option("--sitemap", required=True, help="Sitemap URL to analyze for cross-page coherence")
@click.option("--max-pages", default=20, show_default=True, help="Maximum pages to analyze")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="Output format",
)
def coherence(sitemap: str, max_pages: int, output_format: str) -> None:
    """Analyze terminology consistency across site pages."""
    ok, err = validate_public_url(sitemap)
    if not ok:
        click.echo(f"❌ Invalid sitemap URL: {err}", err=True)
        sys.exit(1)

    result = run_site_coherence(sitemap, max_pages=max_pages)

    if output_format == "json":
        click.echo(json.dumps(asdict(result), indent=2))
    else:
        _print_text(result)

    if result.issues:
        sys.exit(1)


def _print_text(result) -> None:
    """Format coherence result as human-readable text."""
    click.echo("")
    click.echo("🔍 " * 20)
    click.echo("  SEMANTIC COHERENCE ANALYSIS")
    click.echo("🔍 " * 20)
    click.echo(f"\n  Pages analyzed: {result.pages_analyzed}")
    click.echo(f"  Coherence score: {result.coherence_score}/100")
    click.echo(f"  Language consistency: {result.language_consistency:.0%}")

    if not result.issues:
        click.echo("\n  ✅ No coherence issues found.")
        return

    click.echo(f"\n  ⚠️  {len(result.issues)} issue(s) found:\n")
    for issue in result.issues:
        icon = {"high": "🔴", "medium": "🟡", "low": "🔵"}.get(issue.severity, "⚪")
        click.echo(f"  {icon} [{issue.severity.upper()}] {issue.description}")
        for page in issue.pages[:3]:
            click.echo(f"     → {page}")
