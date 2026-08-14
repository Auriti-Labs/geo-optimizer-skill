"""CLI command: geo authority — site-level topical authority analysis."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict

import click

from geo_optimizer.core.topic_authority import run_topic_authority
from geo_optimizer.utils.validators import validate_public_url


@click.command(name="authority")
@click.option("--sitemap", required=True, help="Sitemap URL to analyze for topical authority")
@click.option("--max-pages", default=20, show_default=True, help="Maximum pages to analyze")
@click.option("--brand", default="", help="Brand name to exclude from topic clustering")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="Output format",
)
def authority(sitemap: str, max_pages: int, brand: str, output_format: str) -> None:
    """Measure entity-based topical authority across your site.

    AI engines map entities and multi-page topic coverage: five interlinked
    pages covering a topic from different angles beat one strong page.
    Groups your pages into topic clusters and scores depth, interlinking,
    and pillar-page presence (0-100).
    """
    ok, err = validate_public_url(sitemap)
    if not ok:
        click.echo(f"❌ Invalid sitemap URL: {err}", err=True)
        sys.exit(1)

    result = run_topic_authority(sitemap, max_pages=max_pages, brand=brand)

    if output_format == "json":
        click.echo(json.dumps(asdict(result), indent=2, ensure_ascii=False))
    else:
        _print_text(result)

    if result.skipped_reason:
        sys.exit(1)


def _print_text(result) -> None:
    """Format topic authority result as human-readable text."""
    click.echo("")
    click.echo("🏛  TOPIC AUTHORITY ANALYSIS")
    click.echo("=" * 60)

    if result.skipped_reason:
        click.echo(f"⚠️  Skipped: {result.skipped_reason}")
        return

    click.echo(f"Pages analyzed:  {result.pages_analyzed}")
    click.echo(f"Authority score: {result.authority_score}/100")

    if result.clusters:
        click.echo(f"\nTopic clusters ({len(result.clusters)}):")
        for cluster in result.clusters:
            pillar = "📌 pillar" if cluster.pillar_url else "no pillar"
            click.echo(
                f"  • {cluster.topic} — {cluster.pages_count} pages, "
                f"{int(cluster.interlink_ratio * 100)}% interlinked, {pillar}"
            )

    if result.orphan_pages:
        click.echo(f"\n⚠️  Orphan pages ({len(result.orphan_pages)}, no inbound internal links):")
        for url in result.orphan_pages[:10]:
            click.echo(f"  • {url}")
        if len(result.orphan_pages) > 10:
            click.echo(f"  … +{len(result.orphan_pages) - 10} more")

    if result.recommendations:
        click.echo("\nRecommendations:")
        for rec in result.recommendations:
            click.echo(f"  → {rec}")

    click.echo("")
    click.echo("Entity authority is built over time — track it with https://geoready.dev")
