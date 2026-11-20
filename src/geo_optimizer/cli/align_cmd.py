"""CLI command: geo align: how well a page's text covers the prompts you care about.

Deterministic lexical alignment between a list of prompts (or search queries) and one page. No language model, no
embedding, no network beyond fetching the page. It is a measure of your content against your own list, never what an
AI system would answer: see AlignResult.disclaimer.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import click

from geo_optimizer.core.align import analyze_alignment, parse_prompts
from geo_optimizer.models.config import ALIGN_MAX_PROMPT_FILE_BYTES
from geo_optimizer.utils.validators import normalize_url_scheme, validate_public_url

_ICONS = {"covered": "✅", "partial": "🟡", "uncovered": "❌"}


@click.command(name="align")
@click.option("--url", required=True, help="Page to measure")
@click.option(
    "--prompts",
    "prompts_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Text file with one prompt per line, or a CSV export with a query column (Search Console, Bing)",
)
@click.option("--prompt", "prompt_args", multiple=True, help="A prompt on the command line (repeatable)")
@click.option(
    "--format", "output_format", type=click.Choice(["text", "json"]), default="text", show_default=True, help="Output"
)
@click.option("--output", "output_file", default=None, help="Write output to file")
def align(
    url: str, prompts_file: Path | None, prompt_args: tuple[str, ...], output_format: str, output_file: str | None
) -> None:
    """Measure how much of each prompt the page's own text covers.

    For every prompt, the share of its terms found together in one surface of the page (title, h1, meta
    description, a heading, a passage), weighted by prominence. Terms that appear nowhere on the page are listed:
    they are the content to write.
    """
    raw = ""
    if prompts_file is not None:
        if prompts_file.stat().st_size > ALIGN_MAX_PROMPT_FILE_BYTES:
            click.echo(f"\n❌ Prompt file over {ALIGN_MAX_PROMPT_FILE_BYTES} bytes", err=True)
            sys.exit(1)
        raw = prompts_file.read_text(encoding="utf-8", errors="replace")
    raw = "\n".join([raw, *prompt_args])
    prompts, skipped = parse_prompts(raw)
    if not prompts:
        click.echo("\n❌ No prompts: pass --prompts FILE or --prompt TEXT", err=True)
        sys.exit(1)

    safe, reason = validate_public_url(normalize_url_scheme(url))
    if not safe:
        click.echo(f"\n❌ Unsafe URL: {reason}", err=True)
        sys.exit(1)

    result = analyze_alignment(url, prompts, skipped)
    if result.error:
        if output_format == "json":
            click.echo(json.dumps({"error": result.error, "url": result.url}, indent=2))
        else:
            click.echo(f"\n❌ Unable to measure alignment: {result.error}", err=True)
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
    lines = ["", f"🎯 PROMPT ALIGNMENT — {result.url}", "=" * 60]
    lines.append(
        f"{result.prompts} prompts · {result.covered} covered · {result.partial} partial · "
        f"{result.uncovered} uncovered · mean {result.mean_score:.2f}"
    )
    if result.skipped_prompts:
        lines.append(f"{result.skipped_prompts} skipped (empty, duplicate, too long or over the limit)")
    lines.append("")
    for item in result.items:
        where = f" in {item.surface}" if item.surface else ""
        lines.append(f"{_ICONS[item.status]} {item.score:.2f}  {item.prompt}{where}")
        if item.missing_terms:
            lines.append(f"      nowhere on the page: {', '.join(item.missing_terms)}")
    lines += ["", result.disclaimer, ""]
    return "\n".join(lines)
