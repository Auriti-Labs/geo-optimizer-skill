"""CLI command: geo access — unified AI agent access audit."""

from __future__ import annotations

import json
import sys

import click

from geo_optimizer.core.agent_access import run_agent_access_audit
from geo_optimizer.utils.validators import validate_public_url

_STATUS_EMOJI = {
    "accessible": "✅",
    "partial": "⚠️",
    "blocked": "🚫",
    "unknown": "❓",
}


@click.command(name="access")
@click.option("--url", required=True, help="URL to audit for AI agent access")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="Output format",
)
@click.option("--output", "output_file", default=None, help="Write output to file")
def access(url, output_format, output_file):
    """Audit how AI agents can access a URL.

    Checks robots.txt, CDN/WAF challenges, JS rendering requirements,
    noai/noimageai meta directives, and AI discovery endpoints.
    Returns an overall status: accessible | partial | blocked | unknown.
    """
    safe, reason = validate_public_url(url)
    if not safe:
        click.echo(f"\n❌ Unsafe URL: {reason}", err=True)
        sys.exit(1)

    result = run_agent_access_audit(url)

    if output_format == "json":
        output = _format_json(result)
    else:
        output = _format_text(result)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)
        click.echo(f"✅ Report written to: {output_file}")
        return

    click.echo(output)


def _format_text(result) -> str:
    lines = []
    emoji = _STATUS_EMOJI.get(result.overall_status, "❓")
    lines.append(f"\n{emoji}  Agent Access Audit: {result.url}")
    lines.append(f"   Status: {result.overall_status.upper()}\n")

    if result.blocking_issues:
        lines.append("🚫 Blocking issues:")
        for issue in result.blocking_issues:
            lines.append(f"   • {issue}")

    if result.warnings:
        lines.append("\n⚠️  Warnings:")
        for warn in result.warnings:
            lines.append(f"   • {warn}")

    if result.passing:
        lines.append("\n✅ Passing:")
        for p in result.passing:
            lines.append(f"   • {p}")

    lines.append(f"\n   AI Discovery score: {result.ai_discovery_score}/4")
    lines.append("")
    return "\n".join(lines)


def _format_json(result) -> str:
    data = {
        "url": result.url,
        "overall_status": result.overall_status,
        "robots_allows_citation_bots": result.robots_allows_citation_bots,
        "robots_blocks": result.robots_blocks,
        "cdn_challenge_detected": result.cdn_challenge_detected,
        "js_required": result.js_required,
        "noai_meta_present": result.noai_meta_present,
        "x_robots_noai": result.x_robots_noai,
        "x_robots_noindex": result.x_robots_noindex,
        "ai_discovery_score": result.ai_discovery_score,
        "blocking_issues": result.blocking_issues,
        "warnings": result.warnings,
        "passing": result.passing,
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
