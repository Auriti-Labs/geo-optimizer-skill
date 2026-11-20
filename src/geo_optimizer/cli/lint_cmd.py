"""CLI command: geo lint: epistemic lint of a page's claims.

Deterministic text heuristics (statistics with no source, badges with no link, repeated blocks, absolute promises
with no qualifier). No language model, no network beyond fetching the page. Findings are questions to ask about a
sentence, never verdicts: see LintResult.disclaimer.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import click

from geo_optimizer.core.epistemic_lint import analyze_lint
from geo_optimizer.utils.validators import normalize_url_scheme, validate_public_url

_LABELS = {
    "authority_laundering": "AUTHORITY WITHOUT EVIDENCE",
    "relevance_flooding": "REPETITION",
    "caveat_omission": "PROMISE WITHOUT CAVEAT",
}


@click.command(name="lint")
@click.option("--url", required=True, help="Page to lint")
@click.option(
    "--format", "output_format", type=click.Choice(["text", "json"]), default="text", show_default=True, help="Output"
)
@click.option("--output", "output_file", default=None, help="Write output to file")
def lint(url: str, output_format: str, output_file: str | None) -> None:
    """List sentences that claim more than the page supports.

    Checks three families: a statistic with no source, date or sample; a badge or superlative with no link; the same
    block repeated or a block that is only a long keyword list; an absolute promise ("guaranteed", "always") with no
    qualifier. A finding is a question to ask, not a verdict.
    """
    safe, reason = validate_public_url(normalize_url_scheme(url))
    if not safe:
        click.echo(f"\n❌ Unsafe URL: {reason}", err=True)
        sys.exit(1)

    result = analyze_lint(url)
    if result.error:
        if output_format == "json":
            click.echo(json.dumps({"error": result.error, "url": result.url}, indent=2))
        else:
            click.echo(f"\n❌ Unable to lint: {result.error}", err=True)
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
    lines = ["", f"🔎 EPISTEMIC LINT — {result.url}", "=" * 60]
    lines.append(f"{result.blocks_checked} text blocks checked · {sum(result.counts.values())} findings")
    if not result.findings:
        lines.append("Nothing to ask.")
    current = ""
    for finding in result.findings:
        if finding.family != current:
            current = finding.family
            lines += ["", f"{_LABELS[current]}"]
        lines.append(f"  [{finding.rule}] {finding.excerpt}")
        lines.append(f"      {finding.why}")
    if result.truncated:
        lines += ["", f"(listing cut at {len(result.findings)} findings; counts above are complete)"]
    lines += ["", result.disclaimer, ""]
    return "\n".join(lines)
