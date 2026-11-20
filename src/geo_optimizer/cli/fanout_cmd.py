"""CLI command: geo fanout: which commercial sub-intents a page speaks to, for one topic.

Fixed templates, lexical match, no language model, no network beyond the page. The families are a checklist of
common follow-up questions, not what an answer engine issues: see FanoutResult.disclaimer.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import click

from geo_optimizer.core.fanout import analyze_fanout
from geo_optimizer.utils.validators import normalize_url_scheme, validate_public_url

_ICONS = {"covered": "✅", "partial": "🟡", "uncovered": "❌"}


@click.command(name="fanout")
@click.option("--url", required=True, help="Page to measure")
@click.option("--topic", required=True, help="The seed topic or product, e.g. 'roof repair' or 'CRM software'")
@click.option(
    "--format", "output_format", type=click.Choice(["text", "json"]), default="text", show_default=True, help="Output"
)
@click.option("--output", "output_file", default=None, help="Write output to file")
def fanout(url: str, topic: str, output_format: str, output_file: str | None) -> None:
    """Check which usual follow-up questions (price, comparison, reviews, how-to, fit, trust, free options) the page covers.

    The topic is expanded with fixed templates and each query is scored against the page text, as in ``geo align``.
    A family is as covered as the mean of its queries. A checklist for finding gaps, not a prediction.
    """
    if not topic.strip():
        click.echo("\n❌ --topic is empty", err=True)
        sys.exit(1)
    safe, reason = validate_public_url(normalize_url_scheme(url))
    if not safe:
        click.echo(f"\n❌ Unsafe URL: {reason}", err=True)
        sys.exit(1)

    result = analyze_fanout(url, topic)
    if result.error:
        if output_format == "json":
            click.echo(json.dumps({"error": result.error, "url": result.url}, indent=2))
        else:
            click.echo(f"\n❌ Unable to measure sub-intents: {result.error}", err=True)
        sys.exit(1)

    output = (
        json.dumps(asdict(result), indent=2, ensure_ascii=False) if output_format == "json" else _format_text(result)
    )
    if output_file:
        Path(output_file).write_text(output, encoding="utf-8")
        click.echo(f"✅ Report written to: {output_file}")
        return
    click.echo(output)


def _format_text(result) -> str:
    lines = ["", f"🧭 SUB-INTENT COVERAGE — {result.url}", "=" * 60, f"topic: {result.seed}"]
    lines.append(
        f"{len(result.families)} families · {result.covered} covered · {result.partial} partial · {result.uncovered} uncovered"
    )
    lines.append("")
    for family in result.families:
        lines.append(f"{_ICONS[family.status]} {family.mean_score:.2f}  {family.family.replace('_', ' ')}")
        for item in family.items:
            lines.append(f"      {item.score:.2f}  {item.prompt}")
            if item.missing_terms:
                lines.append(f"            nowhere on the page: {', '.join(item.missing_terms)}")
    lines += ["", result.disclaimer, ""]
    return "\n".join(lines)
