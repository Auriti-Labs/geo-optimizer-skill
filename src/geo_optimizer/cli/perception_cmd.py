"""CLI command: geo perception — deterministic AI perception snapshot (MVP C).

Aggregates brand, schema, citability, trust, and factual signals from a full
audit into what an AI/retrieval system would likely extract from the page.
Deterministic (mode="deterministic"): no LLM calls, no extra network beyond
the audit itself. Always labeled as simulated perception, not real AI system
output — see PerceptionSnapshot.disclaimer. For a real model's answer, use
`geo citations` instead.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict

import click

from geo_optimizer.core.audit import run_full_audit
from geo_optimizer.core.perception_extractor import extract_perception
from geo_optimizer.utils.validators import validate_public_url


@click.command(name="perception")
@click.option("--url", required=True, help="URL to extract a simulated AI perception snapshot from")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="Output format",
)
@click.option("--output", "output_file", default=None, help="Write output to file")
@click.option("--cache", is_flag=True, help="Use local HTTP cache for the underlying audit")
def perception(url: str, output_format: str, output_file: str | None, cache: bool) -> None:
    """Extract a deterministic AI perception snapshot from a page.

    Runs a full audit and aggregates its signals into what an AI/retrieval
    system would likely extract: brand entity, schema types, citability
    grade, trust score, supported vs. unsupported claims, and missing
    authority signals. Deterministic and disclosed as simulated — not a
    call to a real AI model.
    """
    target = url if url.startswith(("http://", "https://")) else f"https://{url}"
    safe, reason = validate_public_url(target)
    if not safe:
        click.echo(f"\n❌ Unsafe URL: {reason}", err=True)
        sys.exit(1)

    audit_result = run_full_audit(url, use_cache=cache)
    snapshot = extract_perception(audit_result)

    output = _format_json(snapshot) if output_format == "json" else _format_text(snapshot)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)
        click.echo(f"✅ Report written to: {output_file}")
        return

    click.echo(output)


def _format_json(snapshot) -> str:
    return json.dumps(asdict(snapshot), indent=2, ensure_ascii=False)


def _format_text(snapshot) -> str:
    lines: list[str] = []
    lines.append("")
    lines.append(f"🧠 AI PERCEPTION SNAPSHOT — {snapshot.url}")
    lines.append("=" * 60)
    lines.append(f"⚠️  {snapshot.disclaimer}")

    if snapshot.ai_readable_summary:
        lines.append("")
        lines.append(f"Summary: {snapshot.ai_readable_summary}")

    lines.append("")
    if snapshot.brand_name:
        entity = f" ({snapshot.brand_entity_type})" if snapshot.brand_entity_type else ""
        lines.append(f"Brand:            {snapshot.brand_name}{entity}")
    if snapshot.citability_grade:
        lines.append(f"Citability grade: {snapshot.citability_grade}")
    if snapshot.trust_score is not None:
        lines.append(f"Trust score:      {snapshot.trust_score:.0f}/100")
    if snapshot.schema_types_present:
        lines.append(f"Schema types:     {', '.join(snapshot.schema_types_present)}")

    if snapshot.citation_worthy_facts:
        lines.append("")
        lines.append("✅ Citation-worthy signals:")
        for fact in snapshot.citation_worthy_facts:
            lines.append(f"   • {fact}")

    if snapshot.supported_claims:
        lines.append("")
        lines.append("✅ Supported claims:")
        for claim in snapshot.supported_claims:
            lines.append(f"   • {claim}")

    if snapshot.unsupported_claims:
        lines.append("")
        lines.append("⚠️  Unsupported claims (no on-page evidence found):")
        for claim in snapshot.unsupported_claims:
            lines.append(f"   • {claim}")

    if snapshot.missing_authority_signals:
        lines.append("")
        lines.append("🚫 Missing authority signals:")
        for signal in snapshot.missing_authority_signals:
            lines.append(f"   • {signal}")

    lines.append("")
    lines.append("Deterministic extraction from on-page signals — not a live model call.")
    lines.append("Want a real answer engine's take instead? → geo citations")
    lines.append("")
    return "\n".join(lines)
