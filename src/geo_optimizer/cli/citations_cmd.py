"""CLI command: geo citations — one-shot AI citation check (BYO API key)."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict

import click

from geo_optimizer.core.citations import normalize_domain, resolve_provider, run_citation_check

_VERDICT_LINES = {
    "strong": "🏆 STRONG — AI engines cite {domain} as a source in most answers.",
    "cited": "✅ CITED — {domain} appears among AI answer sources, but not consistently.",
    "mentioned_only": "🟡 MENTIONED ONLY — AI knows the brand but never cites {domain} as a source.",
    "invisible": "❌ INVISIBLE — AI answers neither mention {brand} nor cite {domain}.",
}

_VERDICT_ADVICE = {
    "strong": "Keep your content fresh and monitor for regressions.",
    "cited": "Strengthen citability: statistics, quotable passages, llms.txt depth (run: geo audit).",
    "mentioned_only": "AI learned about you from third parties. Make your own pages the citable source (run: geo audit).",
    "invisible": "Start with the basics: geo audit --url https://{domain} and fix the HIGH recommendations first.",
}


def _format_text(result) -> str:
    lines: list[str] = []
    lines.append("")
    lines.append(f"🔎 AI Citation Check — {result.brand} ({result.domain})")
    lines.append("=" * 60)

    if result.skipped_reason:
        lines.append(f"⚠️  Skipped: {result.skipped_reason}")
        return "\n".join(lines)

    for entry in result.entries:
        lines.append("")
        lines.append(f'Q: "{entry.query}"  [{entry.platform}]')
        if entry.error:
            lines.append(f"   ⚠️ error: {entry.error}")
            continue
        lines.append(f"   Brand mentioned: {'✅' if entry.brand_mentioned else '❌'}")
        lines.append(f"   Domain cited:    {'✅' if entry.domain_cited else '❌'}")
        if entry.cited_sources:
            shown = ", ".join(entry.cited_sources[:3])
            extra = len(entry.cited_sources) - 3
            lines.append(f"   Sources: {shown}{f' (+{extra} more)' if extra > 0 else ''}")

    lines.append("")
    lines.append("-" * 60)
    lines.append(f"Answers analyzed:     {result.queries_run}")
    lines.append(f"Brand mention rate:   {int(result.brand_mention_rate * 100)}%")
    lines.append(f"Domain citation rate: {int(result.domain_citation_rate * 100)}%")
    if result.top_cited_domains:
        competitors = ", ".join(f"{d} ({n})" for d, n in result.top_cited_domains)
        lines.append(f"Cited instead of you: {competitors}")
    lines.append("")
    lines.append(_VERDICT_LINES[result.verdict].format(brand=result.brand, domain=result.domain))
    lines.append(f"→ {_VERDICT_ADVICE[result.verdict].format(domain=result.domain)}")
    lines.append("")
    lines.append("One-shot check. Track citations over time with alerts → https://geoready.dev")
    return "\n".join(lines)


@click.command(name="citations")
@click.option("--brand", required=True, help="Brand name to look for in AI answers")
@click.option("--domain", required=True, help="Your domain (e.g. example.com) to look for among cited sources")
@click.option("--topic", default="", help="Topic for the default queries (defaults to brand)")
@click.option("--query", "queries", multiple=True, help="Custom query to ask (repeatable, overrides defaults)")
@click.option(
    "--provider",
    type=click.Choice(["perplexity", "openai", "anthropic", "groq"]),
    default=None,
    help="AI provider (default: perplexity if PERPLEXITY_API_KEY is set, else auto-detect)",
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
def citations(brand, domain, topic, queries, provider, output_format, output_file):
    """Check if AI answer engines mention your brand and cite your domain.

    Bring your own API key: PERPLEXITY_API_KEY is recommended because
    Perplexity grounds answers in live web search and returns real source
    URLs. Parametric providers (OpenAI/Anthropic/Groq) only reveal whether
    the model knows your brand.

    \b
    Examples:
      geo citations --brand "GeoReady" --domain geoready.dev --topic "GEO audit tools"
      geo citations --brand "Acme" --domain acme.com --query "best CRM for startups"
    """
    resolved_provider, resolved_key = resolve_provider(provider)
    if not resolved_provider or not resolved_key:
        click.echo(
            "\n❌ No AI provider configured.\n"
            "   Set PERPLEXITY_API_KEY (recommended: real web citations from Sonar)\n"
            "   or OPENAI_API_KEY / ANTHROPIC_API_KEY / GROQ_API_KEY.",
            err=True,
        )
        sys.exit(1)

    result = run_citation_check(
        brand,
        normalize_domain(domain),
        topic=topic,
        queries=list(queries) if queries else None,
        provider=resolved_provider,
        api_key=resolved_key,
    )

    if output_format == "json":
        rendered = json.dumps(asdict(result), indent=2, ensure_ascii=False)
    else:
        rendered = _format_text(result)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as fh:
            fh.write(rendered + "\n")
        click.echo(f"Report written to {output_file}")
    else:
        click.echo(rendered)

    if result.skipped_reason:
        sys.exit(1)
