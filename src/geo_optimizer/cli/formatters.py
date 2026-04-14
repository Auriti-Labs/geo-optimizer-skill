"""
Output formatters for the CLI.

Handles text and JSON output of audit results.
Fix #127: _() imported for future use (full localization in v3.2.0).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from html import escape

from geo_optimizer.cli.scoring_helpers import (
    brand_entity_score as _brand_entity_score,
)
from geo_optimizer.cli.scoring_helpers import (
    content_score as _content_score,
)
from geo_optimizer.cli.scoring_helpers import (
    llms_score as _llms_score,
)
from geo_optimizer.cli.scoring_helpers import (
    meta_score as _meta_score,
)
from geo_optimizer.cli.scoring_helpers import (
    robots_score as _robots_score,
)
from geo_optimizer.cli.scoring_helpers import (
    schema_score as _schema_score,
)
from geo_optimizer.cli.scoring_helpers import (
    signals_score as _signals_score,
)
from geo_optimizer.models.config import SCORE_BANDS, SCORING
from geo_optimizer.models.results import (
    AnswerSnapshot,
    AnswerSnapshotArchive,
    AuditDiffResult,
    AuditResult,
    BatchAuditResult,
    HistoryResult,
    MonitorResult,
)

# Fix #409: max scores computed dynamically from SCORING (not hardcoded)
_MAX_ROBOTS = sum(v for k, v in SCORING.items() if k.startswith("robots_"))
_MAX_LLMS = sum(v for k, v in SCORING.items() if k.startswith("llms_"))
_MAX_SCHEMA = sum(v for k, v in SCORING.items() if k.startswith("schema_"))
_MAX_META = sum(v for k, v in SCORING.items() if k.startswith("meta_"))
_MAX_CONTENT = sum(v for k, v in SCORING.items() if k.startswith("content_"))
_MAX_SIGNALS = sum(v for k, v in SCORING.items() if k.startswith("signals_"))
_MAX_AI_DISC = sum(v for k, v in SCORING.items() if k.startswith("ai_discovery_"))
_MAX_BRAND = sum(v for k, v in SCORING.items() if k.startswith("brand_"))


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
                "max": _MAX_ROBOTS,
                "passed": result.robots.citation_bots_ok,
                "details": asdict(result.robots),
            },
            "llms_txt": {
                "score": _llms_score(result),
                "max": _MAX_LLMS,
                "passed": result.llms.found and result.llms.has_h1,
                "details": asdict(result.llms),
            },
            "schema_jsonld": {
                "score": _schema_score(result),
                "max": _MAX_SCHEMA,
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
                "max": _MAX_META,
                "passed": result.meta.has_title and result.meta.has_description,
                "details": asdict(result.meta),
            },
            "content": {
                "score": _content_score(result),
                "max": _MAX_CONTENT,
                "passed": result.content.has_h1,
                "details": asdict(result.content),
            },
            "signals": {
                "score": _signals_score(result),
                "max": _MAX_SIGNALS,
                "passed": bool(result.signals and result.signals.has_lang),
                "details": asdict(result.signals) if result.signals else {},
            },
            "ai_discovery": {
                "score": result.score_breakdown.get("ai_discovery", 0),
                "max": _MAX_AI_DISC,
                "passed": bool(result.ai_discovery and result.ai_discovery.endpoints_found >= 1),
                "details": asdict(result.ai_discovery) if result.ai_discovery else {},
            },
            "brand_entity": {
                "score": _brand_entity_score(result),
                "max": _MAX_BRAND,
                "passed": bool(result.brand_entity and result.brand_entity.brand_name_consistent),
                "details": asdict(result.brand_entity) if result.brand_entity else {},
            },
        },
        "score_breakdown": result.score_breakdown,
        "recommendations": result.recommendations,
    }

    # WebMCP Readiness (#233) — separate informational section
    if hasattr(result, "webmcp") and result.webmcp.checked:
        data["webmcp"] = {
            "readiness_level": result.webmcp.readiness_level,
            "agent_ready": result.webmcp.agent_ready,
            "has_register_tool": result.webmcp.has_register_tool,
            "has_tool_attributes": result.webmcp.has_tool_attributes,
            "tool_count": result.webmcp.tool_count,
            "has_potential_action": result.webmcp.has_potential_action,
            "potential_actions": result.webmcp.potential_actions,
            "has_labeled_forms": result.webmcp.has_labeled_forms,
            "labeled_forms_count": result.webmcp.labeled_forms_count,
            "has_openapi": result.webmcp.has_openapi,
        }

    # Negative Signals (v4.3) — separate informational section
    if hasattr(result, "negative_signals") and result.negative_signals.checked:
        data["negative_signals"] = {
            "severity": result.negative_signals.severity,
            "signals_found": result.negative_signals.signals_found,
            "cta_density_high": result.negative_signals.cta_density_high,
            "cta_count": result.negative_signals.cta_count,
            "has_popup_signals": result.negative_signals.has_popup_signals,
            "is_thin_content": result.negative_signals.is_thin_content,
            "broken_links_count": result.negative_signals.broken_links_count,
            "has_keyword_stuffing": result.negative_signals.has_keyword_stuffing,
            "has_author_signal": result.negative_signals.has_author_signal,
            "boilerplate_ratio": result.negative_signals.boilerplate_ratio,
            "has_mixed_signals": result.negative_signals.has_mixed_signals,
        }

    # Fix #451: CDN AI Crawler check
    if hasattr(result, "cdn_check") and result.cdn_check and result.cdn_check.checked:
        data["cdn_check"] = asdict(result.cdn_check)

    # Fix #451: JS Rendering check
    if hasattr(result, "js_rendering") and result.js_rendering and result.js_rendering.checked:
        data["js_rendering"] = asdict(result.js_rendering)

    # Fix #451: Trust Stack score
    if hasattr(result, "trust_stack") and result.trust_stack:
        data["trust_stack"] = asdict(result.trust_stack)

    # Fix #451: Prompt Injection detection
    if hasattr(result, "prompt_injection") and result.prompt_injection and result.prompt_injection.checked:
        data["prompt_injection"] = asdict(result.prompt_injection)

    # Metadata
    data["http_status"] = result.http_status
    data["page_size"] = result.page_size

    return json.dumps(data, indent=2)


def format_audit_text(result: AuditResult) -> str:
    """Format AuditResult as human-readable text."""
    lines = []

    lines.append("")
    lines.append("🔍 " * 20)
    lines.append(f"  GEO AUDIT — {result.url}")
    lines.append("  github.com/auriti-labs/geo-optimizer-skill")
    lines.append("🔍 " * 20)
    lines.append("")
    lines.append(f"   Status: {result.http_status} | Size: {result.page_size:,} bytes")

    # Robots.txt
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
            lines.append(f"  ✅ Schema {t} ✓")
        if not result.schema.has_website:
            lines.append("  ❌ WebSite schema missing")
        if not result.schema.has_faq:
            lines.append("  ⚠️  FAQPage schema missing")

    # Meta
    lines.append("")
    lines.append(_section_header("4. META TAG — SEO & Open Graph"))
    if result.meta.has_title:
        lines.append(f"  ✅ Title: {result.meta.title_text}")
    else:
        lines.append("  ❌ Title missing")
    if result.meta.has_description:
        lines.append(f"  ✅ Meta description ({result.meta.description_length} characters) ✓")
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
        lines.append("  ⚠️  Few numerical data")
    lines.append(f"  {'✅' if result.content.word_count >= 300 else '⚠️ '} ~{result.content.word_count} words")
    if result.content.has_links:
        lines.append(f"  ✅ {result.content.external_links_count} external links ✓")
    else:
        lines.append("  ⚠️  No links to external sources")

    # Signals (v4.0)
    if result.signals:
        lines.append("")
        lines.append(_section_header("6. TECHNICAL SIGNALS"))
        if result.signals.has_lang:
            lines.append(f"  ✅ Language: {result.signals.lang_value}")
        else:
            lines.append("  ⚠️  Missing <html lang> attribute")
        if result.signals.has_rss:
            lines.append("  ✅ RSS/Atom feed found")
        else:
            lines.append("  ⚠️  No RSS/Atom feed")
        if result.signals.has_freshness:
            lines.append(f"  ✅ Freshness signal: {result.signals.freshness_date}")
        else:
            lines.append("  ⚠️  No dateModified signal")

    # AI Discovery
    if result.ai_discovery:
        lines.append("")
        lines.append(_section_header("7. AI DISCOVERY ENDPOINTS"))
        if result.ai_discovery.has_well_known_ai:
            lines.append("  ✅ /.well-known/ai.txt found")
        else:
            lines.append("  ⚠️  /.well-known/ai.txt missing")
        if result.ai_discovery.has_summary and result.ai_discovery.summary_valid:
            lines.append("  ✅ /ai/summary.json valid")
        else:
            lines.append("  ⚠️  /ai/summary.json missing or invalid")
        if result.ai_discovery.has_faq:
            lines.append(f"  ✅ /ai/faq.json ({result.ai_discovery.faq_count} FAQs)")
        else:
            lines.append("  ⚠️  /ai/faq.json missing")

    # Brand & Entity Signals
    if result.brand_entity:
        lines.append("")
        lines.append(_section_header("8. BRAND & ENTITY SIGNALS"))
        be = result.brand_entity
        be_pts = _brand_entity_score(result)
        bar_filled = int(be_pts / 2)
        bar_empty = 5 - bar_filled
        bar = "█" * bar_filled + "░" * bar_empty
        lines.append(f"  [{bar}] {be_pts}/10")
        if be.brand_name_consistent:
            names = ", ".join(be.names_found[:3]) if be.names_found else ""
            lines.append(f"  ✅ Brand name coerente{f' ({names})' if names else ''}")
        else:
            lines.append("  ⚠️  Brand name incoerente tra schema, meta e contenuto")
        if be.kg_pillar_count > 0:
            lines.append(f"  ✅ {be.kg_pillar_count}/4 Knowledge Graph pillars")
        else:
            lines.append("  ⚠️  Nessun link a Knowledge Graph (Wikipedia, Wikidata, LinkedIn)")
        if be.has_about_link:
            lines.append("  ✅ About page collegata")
        else:
            lines.append("  ⚠️  About page non rilevata")
        if be.has_contact_info:
            lines.append("  ✅ Informazioni di contatto presenti")
        else:
            lines.append("  ⚠️  Informazioni di contatto mancanti")
        if be.faq_depth > 0:
            lines.append(f"  ✅ {be.faq_depth} FAQ trovate")
        if be.has_recent_articles:
            lines.append("  ✅ Articoli con dateModified trovati")

    # CDN Check
    if result.cdn_check and result.cdn_check.checked:
        lines.append("")
        lines.append(_section_header("9. CDN AI CRAWLER ACCESS"))
        if result.cdn_check.any_blocked:
            lines.append("  ❌ AI crawlers blocked by CDN/WAF")
            for bot in result.cdn_check.bot_results:
                icon = "✅" if not bot["blocked"] and not bot["challenge_detected"] else "❌"
                lines.append(f"  {icon} {bot['bot']}: HTTP {bot['status']}")
        else:
            lines.append("  ✅ All AI crawlers can access the site")

    # JS Rendering
    if result.js_rendering and result.js_rendering.checked:
        lines.append("")
        lines.append(_section_header("10. JS RENDERING CHECK"))
        if result.js_rendering.js_dependent:
            lines.append(f"  ❌ {result.js_rendering.details}")
        else:
            lines.append(f"  ✅ {result.js_rendering.details}")

    # Prompt Injection Detection (#276)
    if result.prompt_injection and result.prompt_injection.checked:
        lines.append("")
        lines.append(_section_header("11. PROMPT INJECTION DETECTION"))
        pi = result.prompt_injection
        severity_icons = {"clean": "✅", "suspicious": "⚠️ ", "critical": "❌"}
        lines.append(
            f"  {severity_icons.get(pi.severity, '?')} Severity: {pi.severity.upper()} ({pi.patterns_found} pattern)"
        )
        if pi.hidden_text_found:
            lines.append(f"  ❌ Hidden text: {pi.hidden_text_count} element(s)")
        if pi.invisible_unicode_found:
            lines.append(f"  ⚠️  Invisible Unicode: {pi.invisible_unicode_count} char(s)")
        if pi.llm_instruction_found:
            lines.append(f"  ❌ LLM instructions: {pi.llm_instruction_count} found")
        if pi.html_comment_injection_found:
            lines.append(f"  ❌ HTML comment injection: {pi.html_comment_injection_count} found")
        if pi.monochrome_text_found:
            lines.append(f"  ⚠️  Monochrome text: {pi.monochrome_text_count} element(s)")
        if pi.microfont_found:
            lines.append(f"  ⚠️  Micro-font: {pi.microfont_count} element(s)")
        if pi.data_attr_injection_found:
            lines.append(f"  ⚠️  Data attribute injection: {pi.data_attr_injection_count} found")
        if pi.aria_hidden_injection_found:
            lines.append(f"  ❌ aria-hidden injection: {pi.aria_hidden_injection_count} found")

    # Trust Stack Score (#273)
    if result.trust_stack and result.trust_stack.checked:
        lines.append("")
        lines.append(_section_header("12. TRUST STACK SCORE"))
        ts = result.trust_stack
        lines.append(f"  Grade: {ts.grade} ({ts.composite_score}/25) — Trust level: {ts.trust_level}")
        for layer in [ts.technical, ts.identity, ts.social, ts.academic, ts.consistency]:
            bar_filled = layer.score
            bar_empty = 5 - bar_filled
            bar = "█" * bar_filled + "░" * bar_empty
            lines.append(f"  [{bar}] {layer.label}: {layer.score}/5")

    # Score
    lines.append("")
    lines.append(_section_header("📊 FINAL GEO SCORE"))
    bar_filled = int(result.score / 5)
    bar_empty = 20 - bar_filled
    bar = "█" * bar_filled + "░" * bar_empty
    lines.append(f"\n  [{bar}] {result.score}/100")

    # Fix #46: band labels
    band_labels = {
        "excellent": "🏆 EXCELLENT — Site is well optimized for AI search engines!",
        "good": "✅ GOOD — Core optimizations in place, fine-tune content and schema",
        "foundation": "⚠️  FOUNDATION — Core elements missing, implement priority fixes",
        "critical": "❌ CRITICAL — Site is not visible to AI search engines",
    }
    lines.append(f"\n  {band_labels.get(result.band, result.band)}")
    # Fix #442: generazione dinamica delle bande da SCORE_BANDS (non hardcoded)
    _band_order = ["critical", "foundation", "good", "excellent"]
    _band_parts = [f"{SCORE_BANDS[b][0]}–{SCORE_BANDS[b][1]} = {b}" for b in _band_order if b in SCORE_BANDS]
    lines.append(f"\n  Score bands: {' | '.join(_band_parts)}")

    # Recommendations
    lines.append("\n  📋 PRIORITY NEXT STEPS:")
    if not result.recommendations:
        lines.append("  🎉 Excellent! All main optimizations are implemented.")
    else:
        for i, action in enumerate(result.recommendations, 1):
            lines.append(f"  {i}. {action}")

    lines.append("")
    return "\n".join(lines)


def format_batch_audit_json(result: BatchAuditResult) -> str:
    """Formatta BatchAuditResult come JSON."""
    data = {
        "mode": "batch",
        "sitemap_url": result.sitemap_url,
        "timestamp": result.timestamp,
        "discovered_urls": result.discovered_urls,
        "audited_urls": result.audited_urls,
        "successful_urls": result.successful_urls,
        "failed_urls": result.failed_urls,
        "average_score": result.average_score,
        "average_band": result.average_band,
        "band_counts": result.band_counts,
        "average_score_breakdown": result.average_score_breakdown,
        "top_pages": [asdict(page) for page in result.top_pages],
        "worst_pages": [asdict(page) for page in result.worst_pages],
        "pages": [asdict(page) for page in result.pages],
    }
    return json.dumps(data, indent=2)


def format_batch_audit_text(result: BatchAuditResult) -> str:
    """Formatta BatchAuditResult come report testuale leggibile."""
    lines = []

    lines.append("")
    lines.append("🔍 " * 20)
    lines.append(f"  GEO BATCH AUDIT — {result.sitemap_url}")
    lines.append("  github.com/auriti-labs/geo-optimizer-skill")
    lines.append("🔍 " * 20)
    lines.append("")
    lines.append(
        "   "
        f"URLs discovered: {result.discovered_urls} | "
        f"Audited: {result.audited_urls} | "
        f"Success: {result.successful_urls} | "
        f"Failed: {result.failed_urls}"
    )
    lines.append(f"   Average score: {result.average_score:.2f}/100 ({result.average_band.upper()})")

    lines.append("")
    lines.append(_section_header("1. CATEGORY AVERAGES"))
    if result.average_score_breakdown:
        category_labels = {
            "robots": ("Robots.txt", _MAX_ROBOTS),
            "llms": ("llms.txt", _MAX_LLMS),
            "schema": ("Schema", _MAX_SCHEMA),
            "meta": ("Meta", _MAX_META),
            "content": ("Content", _MAX_CONTENT),
            "signals": ("Signals", _MAX_SIGNALS),
            "ai_discovery": ("AI Discovery", _MAX_AI_DISC),
            "brand_entity": ("Brand & Entity", _MAX_BRAND),
        }
        for category, score in result.average_score_breakdown.items():
            label, max_score = category_labels.get(category, (category.replace("_", " ").title(), 0))
            suffix = f"/{max_score}" if max_score else ""
            lines.append(f"  • {label}: {score:.2f}{suffix}")
    else:
        lines.append("  ⚠️  No successful page audits available")

    lines.append("")
    lines.append(_section_header("2. WORST PAGES"))
    if result.worst_pages:
        for index, page in enumerate(result.worst_pages, start=1):
            lines.append(f"  {index}. {page.url} — {page.score}/100 ({page.band})")
    else:
        lines.append("  ⚠️  No failing pages identified")

    lines.append("")
    lines.append(_section_header("3. TOP PAGES"))
    if result.top_pages:
        for index, page in enumerate(result.top_pages, start=1):
            lines.append(f"  {index}. {page.url} — {page.score}/100 ({page.band})")
    else:
        lines.append("  ⚠️  No successful pages audited")

    if result.failed_urls:
        lines.append("")
        lines.append(_section_header("4. FAILURES"))
        for page in result.pages:
            if page.error:
                lines.append(f"  • {page.url} — {page.error}")

    return "\n".join(lines)


def format_audit_diff_json(result: AuditDiffResult) -> str:
    """Formatta AuditDiffResult come JSON."""
    data = {
        "mode": "diff",
        "before_url": result.before_url,
        "after_url": result.after_url,
        "timestamp": result.timestamp,
        "before_score": result.before_score,
        "after_score": result.after_score,
        "score_delta": result.score_delta,
        "before_band": result.before_band,
        "after_band": result.after_band,
        "before_http_status": result.before_http_status,
        "after_http_status": result.after_http_status,
        "before_error": result.before_error,
        "after_error": result.after_error,
        "before_recommendations_count": result.before_recommendations_count,
        "after_recommendations_count": result.after_recommendations_count,
        "recommendations_delta": result.recommendations_delta,
        "category_deltas": [asdict(item) for item in result.category_deltas],
        "improved_categories": [asdict(item) for item in result.improved_categories],
        "regressed_categories": [asdict(item) for item in result.regressed_categories],
        "unchanged_categories": [asdict(item) for item in result.unchanged_categories],
    }
    return json.dumps(data, indent=2)


def format_audit_diff_text(result: AuditDiffResult) -> str:
    """Formatta AuditDiffResult come confronto testuale leggibile."""
    lines = []
    score_sign = "+" if result.score_delta > 0 else ""
    rec_sign = "+" if result.recommendations_delta > 0 else ""

    lines.append("")
    lines.append("🔍 " * 20)
    lines.append("  GEO DIFF — A/B COMPARISON")
    lines.append("  github.com/auriti-labs/geo-optimizer-skill")
    lines.append("🔍 " * 20)
    lines.append("")
    lines.append(f"   Before: {result.before_url}")
    lines.append(f"   After:  {result.after_url}")
    lines.append("")
    lines.append(
        "   "
        f"Score: {result.before_score}/100 ({result.before_band.upper()}) → "
        f"{result.after_score}/100 ({result.after_band.upper()}) "
        f"({score_sign}{result.score_delta})"
    )
    lines.append(
        "   "
        f"Recommendations: {result.before_recommendations_count} → "
        f"{result.after_recommendations_count} ({rec_sign}{result.recommendations_delta})"
    )

    lines.append("")
    lines.append(_section_header("1. CATEGORY DELTAS"))
    for item in result.category_deltas:
        sign = "+" if item.delta > 0 else ""
        suffix = f"/{item.max_score}" if item.max_score else ""
        lines.append(f"  • {item.label}: {item.before_score}{suffix} → {item.after_score}{suffix} ({sign}{item.delta})")

    lines.append("")
    lines.append(_section_header("2. IMPROVEMENTS"))
    if result.improved_categories:
        for item in result.improved_categories[:5]:
            lines.append(f"  • {item.label}: +{item.delta}")
    else:
        lines.append("  • No category improved")

    lines.append("")
    lines.append(_section_header("3. REGRESSIONS"))
    if result.regressed_categories:
        for item in result.regressed_categories[:5]:
            lines.append(f"  • {item.label}: {item.delta}")
    else:
        lines.append("  • No regressions detected")

    if result.before_error or result.after_error:
        lines.append("")
        lines.append(_section_header("4. ERRORS"))
        if result.before_error:
            lines.append(f"  • Before audit error: {result.before_error}")
        if result.after_error:
            lines.append(f"  • After audit error: {result.after_error}")

    return "\n".join(lines)


def format_history_json(result: HistoryResult) -> str:
    """Formatta HistoryResult come JSON."""
    return json.dumps(asdict(result), indent=2)


def format_history_text(result: HistoryResult) -> str:
    """Formatta la history GEO come testo leggibile."""
    lines = []
    lines.append("")
    lines.append("🔍 " * 20)
    lines.append("  GEO HISTORY — SCORE TREND")
    lines.append("  github.com/auriti-labs/geo-optimizer-skill")
    lines.append("🔍 " * 20)
    lines.append("")
    lines.append(f"   URL: {result.url}")
    lines.append(f"   Snapshots: {result.total_snapshots} | Retention: {result.retention_days} days")

    if result.latest_score is None:
        lines.append("")
        lines.append("  No saved snapshots found for this URL.")
        return "\n".join(lines)

    delta_text = "n/a" if result.score_delta is None else f"{result.score_delta:+d}"
    lines.append(
        "   "
        f"Latest: {result.latest_score}/100 ({(result.latest_band or 'critical').upper()}) | "
        f"Delta vs previous: {delta_text}"
    )
    lines.append(f"   Best: {result.best_score}/100 | Worst: {result.worst_score}/100")

    lines.append("")
    lines.append(_section_header("1. TREND"))
    for entry in result.entries:
        delta_text = "—" if entry.delta is None else f"{entry.delta:+d}"
        bar = "█" * max(1, min(25, int(round(entry.score / 4))))
        lines.append(f"  {entry.timestamp[:10]}  {entry.score:>3}/100  {entry.band.upper():<10} {delta_text:>4}  {bar}")

    return "\n".join(lines)


def format_tracking_text(audit_result: AuditResult, history_result: HistoryResult) -> str:
    """Formatta il risultato di `geo track` come testo."""
    lines = []
    lines.append("")
    lines.append("🔍 " * 20)
    lines.append("  GEO TRACK — MONITORING SNAPSHOT")
    lines.append("  github.com/auriti-labs/geo-optimizer-skill")
    lines.append("🔍 " * 20)
    lines.append("")
    lines.append(f"   URL: {audit_result.url}")
    lines.append(f"   Current score: {audit_result.score}/100 ({audit_result.band.upper()})")
    if history_result.score_delta is None:
        lines.append("   Baseline snapshot saved.")
    else:
        lines.append(f"   Delta vs previous snapshot: {history_result.score_delta:+d}")
    lines.append(f"   Snapshots stored: {history_result.total_snapshots}")

    if history_result.entries:
        lines.append("")
        lines.append(_section_header("1. RECENT SNAPSHOTS"))
        for entry in history_result.entries[:5]:
            delta_text = "—" if entry.delta is None else f"{entry.delta:+d}"
            lines.append(f"  • {entry.timestamp[:10]} — {entry.score}/100 ({entry.band}) [{delta_text}]")

    return "\n".join(lines)


def format_tracking_json(audit_result: AuditResult, history_result: HistoryResult) -> str:
    """Formatta il risultato di `geo track` come JSON."""
    data = {
        "audit": json.loads(format_audit_json(audit_result)),
        "history": asdict(history_result),
    }
    return json.dumps(data, indent=2)


def format_history_report_html(result: HistoryResult) -> str:
    """Genera un report HTML minimale con il trend storico GEO."""
    rows = []
    for entry in result.entries:
        width = max(4, min(100, entry.score))
        delta = "—" if entry.delta is None else f"{entry.delta:+d}"
        rows.append(
            "<tr>"
            f"<td>{escape(entry.timestamp[:10])}</td>"
            f"<td>{entry.score}/100</td>"
            f"<td>{escape(entry.band.upper())}</td>"
            f"<td>{escape(delta)}</td>"
            "<td><div class='track'><span class='fill' style='width:"
            f"{width}%'></span></div></td>"
            "</tr>"
        )

    latest = (
        "n/a"
        if result.latest_score is None
        else f"{result.latest_score}/100 ({(result.latest_band or 'critical').upper()})"
    )
    delta = "n/a" if result.score_delta is None else f"{result.score_delta:+d}"
    tbody = "".join(rows) if rows else '<tr><td colspan="5">No snapshots available.</td></tr>'

    return (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>GEO History Report — {escape(result.url)}</title>"
        "<style>"
        "body{font-family:system-ui,sans-serif;background:#f6f7fb;color:#101828;margin:0;padding:32px;}"
        ".wrap{max-width:960px;margin:0 auto;background:#fff;border:1px solid #d0d5dd;border-radius:20px;padding:32px;}"
        "h1{margin:0 0 8px;font-size:2rem;}p{color:#475467;margin:0 0 20px;}"
        ".meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin:24px 0;}"
        ".card{background:#f8fafc;border:1px solid #e4e7ec;border-radius:16px;padding:16px;}"
        ".label{font-size:.8rem;text-transform:uppercase;letter-spacing:.08em;color:#667085;}"
        ".value{font-size:1.5rem;font-weight:700;margin-top:6px;}"
        "table{width:100%;border-collapse:collapse;margin-top:16px;}th,td{padding:12px 8px;border-bottom:1px solid #eaecf0;text-align:left;}"
        ".track{width:100%;height:10px;background:#e4e7ec;border-radius:999px;overflow:hidden;}"
        ".fill{display:block;height:100%;background:linear-gradient(90deg,#06b6d4,#22c55e);}"
        "</style></head><body><div class='wrap'>"
        "<h1>GEO History Report</h1>"
        f"<p>{escape(result.url)}</p>"
        "<div class='meta'>"
        f"<div class='card'><div class='label'>Latest</div><div class='value'>{escape(latest)}</div></div>"
        f"<div class='card'><div class='label'>Delta</div><div class='value'>{escape(delta)}</div></div>"
        f"<div class='card'><div class='label'>Snapshots</div><div class='value'>{result.total_snapshots}</div></div>"
        f"<div class='card'><div class='label'>Retention</div><div class='value'>{result.retention_days}d</div></div>"
        "</div>"
        "<table><thead><tr><th>Date</th><th>Score</th><th>Band</th><th>Δ</th><th>Trend</th></tr></thead>"
        f"<tbody>{tbody}</tbody>"
        "</table></div></body></html>"
    )


def format_monitor_json(result: MonitorResult) -> str:
    """Formatta MonitorResult come JSON."""
    return json.dumps(asdict(result), indent=2)


def format_monitor_text(result: MonitorResult) -> str:
    """Formatta il monitor passivo della visibilita' AI come testo."""
    lines = []
    lines.append("")
    lines.append("🔍 " * 20)
    lines.append("  GEO MONITOR — PASSIVE AI VISIBILITY")
    lines.append("  github.com/auriti-labs/geo-optimizer-skill")
    lines.append("🔍 " * 20)
    lines.append("")
    lines.append(f"   Domain: {result.domain}")
    lines.append(f"   Homepage: {result.url}")
    lines.append(f"   Visibility score: {result.visibility_score}/100 ({result.band.upper()}) | Mode: {result.mode}")
    lines.append(
        f"   Latest GEO score: {result.latest_geo_score}/100 ({(result.latest_geo_band or 'critical').upper()})"
    )
    delta_text = "n/a" if result.score_delta is None else f"{result.score_delta:+d}"
    lines.append(f"   Local trend: {delta_text} | Snapshots stored: {result.total_snapshots}")

    lines.append("")
    lines.append(_section_header("1. PASSIVE SIGNALS"))
    for signal in result.signals:
        lines.append(f"  • {signal.label}: {signal.score}/{signal.max_score} [{signal.status.upper()}]")

    lines.append("")
    lines.append(_section_header("2. NEXT ACTIONS"))
    if result.recommendations:
        for item in result.recommendations[:5]:
            lines.append(f"  • {item}")
    else:
        lines.append("  • No immediate action required")

    lines.append("")
    lines.append("  Note: passive mode does not query LLM APIs or verify direct brand mentions in answers.")
    return "\n".join(lines)


def format_snapshot_archive_json(result) -> str:
    """Formatta snapshot singolo o archivio come JSON."""
    return json.dumps(asdict(result), indent=2)


def format_snapshot_saved_text(result: AnswerSnapshot) -> str:
    """Formatta il risultato di salvataggio di uno snapshot."""
    lines = []
    lines.append("")
    lines.append("🔍 " * 20)
    lines.append("  GEO SNAPSHOTS — SAVED ANSWER")
    lines.append("  github.com/auriti-labs/geo-optimizer-skill")
    lines.append("🔍 " * 20)
    lines.append("")
    lines.append(f"   Snapshot ID: {result.snapshot_id}")
    lines.append(f"   Query: {result.query}")
    lines.append(f"   Model: {result.model}" + (f" | Provider: {result.provider}" if result.provider else ""))
    lines.append(f"   Timestamp: {result.recorded_at}")
    lines.append(f"   Citations stored: {len(result.citations)}")
    if result.citations:
        lines.append("")
        lines.append(_section_header("1. CITATIONS"))
        for citation in result.citations[:10]:
            lines.append(f"  • #{citation.position} — {citation.url}")
    return "\n".join(lines)


def format_snapshot_archive_text(result: AnswerSnapshotArchive) -> str:
    """Formatta una query sull'archivio snapshot come testo."""
    lines = []
    lines.append("")
    lines.append("🔍 " * 20)
    lines.append("  GEO SNAPSHOTS — ANSWER ARCHIVE")
    lines.append("  github.com/auriti-labs/geo-optimizer-skill")
    lines.append("🔍 " * 20)
    lines.append("")
    lines.append(f"   Query: {result.query or 'all'}")
    lines.append(f"   Range: {result.date_from or 'beginning'} → {result.date_to or 'now'}")
    lines.append(f"   Snapshots: {result.total_snapshots}")

    if not result.entries:
        lines.append("")
        lines.append("  No saved answer snapshots found for these filters.")
        return "\n".join(lines)

    lines.append("")
    lines.append(_section_header("1. SNAPSHOTS"))
    for entry in result.entries:
        lines.append(
            f"  • #{entry.snapshot_id} — {entry.recorded_at[:19]} | {entry.model} | citations: {len(entry.citations)}"
        )
        lines.append(f"    Query: {entry.query}")
        preview = entry.answer_text.replace("\n", " ").strip()
        if len(preview) > 120:
            preview = preview[:117].rstrip() + "..."
        lines.append(f"    Answer: {preview}")

    return "\n".join(lines)


def _section_header(text: str) -> str:
    width = 60
    return f"{'=' * width}\n  {text}\n{'=' * width}"


# Functions _robots_score, _llms_score, _schema_score, _meta_score, _content_score
# are imported from scoring_helpers (fix #77 — removed duplication)
