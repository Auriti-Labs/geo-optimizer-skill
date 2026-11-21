"""CLI command: geo fidelity: do the pages an AI answer cites carry the words of its sentences?

Lexical, no language model, no network beyond the cited pages. It does not decide whether a claim is true: see
FidelityResult.disclaimer.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import click

from geo_optimizer.core.fidelity import analyze_fidelity
from geo_optimizer.models.config import FIDELITY_MAX_ANSWER_CHARS, FIDELITY_MAX_SOURCES
from geo_optimizer.utils.validators import normalize_url_scheme, validate_public_url

_ICONS = {"supported": "✅", "partial": "🟡", "unsupported": "❌"}


@click.command(name="fidelity")
@click.option(
    "--answer",
    "answer_file",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Text file with the AI answer",
)
@click.option("--source", "sources", multiple=True, required=True, help="A page the answer cites (repeatable)")
@click.option(
    "--format", "output_format", type=click.Choice(["text", "json"]), default="text", show_default=True, help="Output"
)
@click.option("--output", "output_file", default=None, help="Write output to file")
def fidelity(answer_file: Path, sources: tuple[str, ...], output_format: str, output_file: str | None) -> None:
    """Check each sentence of an AI answer against the pages the answer cites.

    For every sentence, the share of its words (and any figure in it) found on the best cited page. A claim whose
    words are on no cited page is the first one to read by hand. It does not tell you whether a claim is true.
    """
    if answer_file.stat().st_size > FIDELITY_MAX_ANSWER_CHARS * 4:
        click.echo(f"\n❌ Answer file over {FIDELITY_MAX_ANSWER_CHARS * 4} bytes", err=True)
        sys.exit(1)
    if len(sources) > FIDELITY_MAX_SOURCES:
        click.echo(f"\n❌ At most {FIDELITY_MAX_SOURCES} --source pages", err=True)
        sys.exit(1)
    for source in sources:
        safe, reason = validate_public_url(normalize_url_scheme(source))
        if not safe:
            click.echo(f"\n❌ Unsafe URL {source}: {reason}", err=True)
            sys.exit(1)

    result = analyze_fidelity(answer_file.read_text(encoding="utf-8-sig", errors="replace"), list(sources))
    if result.error:
        if output_format == "json":
            click.echo(json.dumps({"error": result.error, "unreachable_sources": result.unreachable_sources}, indent=2))
        else:
            click.echo(f"\n❌ Unable to check fidelity: {result.error}", err=True)
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
    lines = ["", "🔎 CITATION FIDELITY", "=" * 60]
    lines.append(
        f"{len(result.claims)} claims · {result.supported} supported · {result.partial} partial · "
        f"{result.unsupported} unsupported ({result.support_rate:.0%} supported)"
    )
    if result.unreachable_sources:
        lines.append(f"not readable: {', '.join(result.unreachable_sources)}")
    lines.append("")
    for claim in result.claims:
        lines.append(f"{_ICONS[claim.status]} {claim.score:.2f}  {claim.claim}")
        if claim.best_source:
            lines.append(f"      best page: {claim.best_source}")
        if claim.missing_numbers:
            lines.append(f"      figures not on that page: {', '.join(claim.missing_numbers)}")
        if claim.missing_terms:
            lines.append(f"      on no cited page: {', '.join(claim.missing_terms)}")
    lines += ["", result.disclaimer, ""]
    return "\n".join(lines)
