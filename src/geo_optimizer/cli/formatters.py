"""
Output formatters for the CLI.

Handles text and JSON output for audit results.
"""

import json
from dataclasses import asdict

from geo_optimizer.models.results import AuditResult


def format_audit_json(result: AuditResult) -> str:
    """Format AuditResult as JSON string."""
    data = {
        "url": result.url,
        "timestamp": result.timestamp,
        "score": result.score,
        "band": result.band,
        "checks": {
            "robots_txt": {
                "score": _robots_score(result),
                "max": 20,
                "passed": result.robots.citation_bots_ok,
                "details": asdict(result.robots),
            },
            "llms_txt": {
                "score": _llms_score(result),
                "max": 20,
                "passed": result.llms.found and result.llms.has_h1,
                "details": asdict(result.llms),
            },
            "schema_jsonld": {
                "score": _schema_score(result),
                "max": 25,
                "passed": result.schema.has_website,
                "details": {
                    "has_website": result.schema.has_website,
                    "has_webapp": result.schema.has_webapp,
                    "has_faq": result.schema.has_faq,
                    "found_types": result.schema.found_types,
                },
            },
            "meta_tags": {
                "score": _meta_score(result),
                "max": 20,
                "passed": result.meta.has_title and result.meta.has_description,
                "details": asdict(result.meta),
            },
            "content": {
                "score": _content_score(result),
                "max": 15,
                "passed": result.content.has_h1,
                "details": asdict(result.content),
            },
        },
        "recommendations": result.recommendations,
    }
    return json.dumps(data, indent=2)


def format_audit_text(result: AuditResult) -> str:
    """Format AuditResult as human-readable text."""
    lines = []

    lines.append("")
    lines.append("🔍 " * 20)
    lines.append(f"  GEO AUDIT — {result.url}")
    lines.append("  github.com/auriti-web-design/geo-optimizer-skill")
    lines.append("🔍 " * 20)
    lines.append("")
    lines.append(f"   Status: {result.http_status} | Size: {result.page_size:,} bytes")

    # Robots
    lines.append("")
    lines.append(_section_header("1. ROBOTS.TXT — AI Bot Access"))
    if not result.robots.found:
        lines.append("  ❌ robots.txt not found")
    else:
        lines.append("  ✅ robots.txt found")
        for bot in result.robots.bots_allowed:
            lines.append(f"  ✅ {bot} allowed ✓")
        for bot in result.robots.bots_blocked:
            lines.append(f"  ⚠️  {bot} blocked")
        for bot in result.robots.bots_missing:
            lines.append(f"  ⚠️  {bot} not configured")
        if result.robots.citation_bots_ok:
            lines.append("  ✅ All critical CITATION bots are correctly configured")

    # llms.txt
    lines.append("")
    lines.append(_section_header("2. LLMS.TXT — AI Index File"))
    if not result.llms.found:
        lines.append("  ❌ llms.txt not found — essential for AI indexing!")
    else:
        lines.append(f"  ✅ llms.txt found (~{result.llms.word_count} words)")
        if result.llms.has_h1:
            lines.append("  ✅ H1 present")
        else:
            lines.append("  ❌ H1 missing")
        if result.llms.has_sections:
            lines.append("  ✅ H2 sections present")
        if result.llms.has_links:
            lines.append("  ✅ Links found")

    # Schema
    lines.append("")
    lines.append(_section_header("3. SCHEMA JSON-LD — Structured Data"))
    if not result.schema.found_types:
        lines.append("  ❌ No JSON-LD schema found on homepage")
    else:
        for t in result.schema.found_types:
            lines.append(f"  ✅ {t} schema ✓")
        if not result.schema.has_website:
            lines.append("  ❌ WebSite schema missing")
        if not result.schema.has_faq:
            lines.append("  ⚠️  FAQPage schema missing")

    # Meta
    lines.append("")
    lines.append(_section_header("4. META TAGS — SEO & Open Graph"))
    if result.meta.has_title:
        lines.append(f"  ✅ Title: {result.meta.title_text}")
    else:
        lines.append("  ❌ Title missing")
    if result.meta.has_description:
        lines.append(f"  ✅ Meta description ({result.meta.description_length} chars) ✓")
    else:
        lines.append("  ❌ Meta description missing")
    if result.meta.has_canonical:
        lines.append(f"  ✅ Canonical: {result.meta.canonical_url}")
    if result.meta.has_og_title:
        lines.append("  ✅ og:title ✓")
    if result.meta.has_og_description:
        lines.append("  ✅ og:description ✓")
    if result.meta.has_og_image:
        lines.append("  ✅ og:image ✓")

    # Content
    lines.append("")
    lines.append(_section_header("5. CONTENT QUALITY — GEO Best Practices"))
    if result.content.has_h1:
        lines.append(f"  ✅ H1: {result.content.h1_text}")
    else:
        lines.append("  ⚠️  H1 missing on homepage")
    lines.append(f"  {'✅' if result.content.heading_count >= 3 else '⚠️ '} {result.content.heading_count} headings")
    if result.content.has_numbers:
        lines.append(f"  ✅ {result.content.numbers_count} numbers/statistics found ✓")
    else:
        lines.append("  ⚠️  Few numerical data points")
    lines.append(f"  {'✅' if result.content.word_count >= 300 else '⚠️ '} ~{result.content.word_count} words")
    if result.content.has_links:
        lines.append(f"  ✅ {result.content.external_links_count} external links ✓")
    else:
        lines.append("  ⚠️  No external source links")

    # Score
    lines.append("")
    lines.append(_section_header("📊 FINAL GEO SCORE"))
    bar_filled = int(result.score / 5)
    bar_empty = 20 - bar_filled
    bar = "█" * bar_filled + "░" * bar_empty
    lines.append(f"\n  [{bar}] {result.score}/100")

    band_labels = {
        "excellent": "🏆 EXCELLENT — Site is well optimized for AI search engines!",
        "good": "✅ GOOD — Core optimizations in place, fine-tune content and schema",
        "foundation": "⚠️  FOUNDATION — Core elements missing, implement priority fixes below",
        "critical": "❌ CRITICAL — Site is not visible to AI search engines",
    }
    lines.append(f"\n  {band_labels.get(result.band, result.band)}")
    lines.append("\n  Score bands: 0–40 = critical | 41–70 = foundation | 71–90 = good | 91–100 = excellent")

    # Recommendations
    lines.append("\n  📋 NEXT PRIORITY STEPS:")
    if not result.recommendations:
        lines.append("  🎉 Great! All main optimizations are implemented.")
    else:
        for i, action in enumerate(result.recommendations, 1):
            lines.append(f"  {i}. {action}")

    lines.append("")
    return "\n".join(lines)


def _section_header(text: str) -> str:
    width = 60
    return f"{'=' * width}\n  {text}\n{'=' * width}"


def _robots_score(r: AuditResult) -> int:
    if r.robots.citation_bots_ok:
        return 20
    if r.robots.bots_allowed:
        return 13
    if r.robots.found:
        return 5
    return 0


def _llms_score(r: AuditResult) -> int:
    s = 10 if r.llms.found else 0
    s += 3 if r.llms.has_h1 else 0
    s += 4 if r.llms.has_sections else 0
    s += 3 if r.llms.has_links else 0
    return s


def _schema_score(r: AuditResult) -> int:
    s = 10 if r.schema.has_website else 0
    s += 10 if r.schema.has_faq else 0
    s += 5 if r.schema.has_webapp else 0
    return s


def _meta_score(r: AuditResult) -> int:
    s = 5 if r.meta.has_title else 0
    s += 8 if r.meta.has_description else 0
    s += 3 if r.meta.has_canonical else 0
    s += 4 if (r.meta.has_og_title and r.meta.has_og_description) else 0
    return s


def _content_score(r: AuditResult) -> int:
    s = 4 if r.content.has_h1 else 0
    s += 6 if r.content.has_numbers else 0
    s += 5 if r.content.has_links else 0
    return s
