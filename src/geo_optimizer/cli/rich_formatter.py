"""
Rich formatter — default output of ``geo audit`` in a terminal (design v3).

Compact dashboard: score, eight aligned category rows, extra checks and top
fixes, readable without scrolling. ``--verbose`` appends the per-category cards.
:func:`is_rich_available` stays for environments that strip rich.
"""

from __future__ import annotations

import io
import os
import shutil

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
from geo_optimizer.models.config import CATEGORY_MAX as _CATEGORY_MAX
from geo_optimizer.models.results import AuditResult

try:
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# ── Public helpers ────────────────────────────────────────────────────────────


def is_rich_available() -> bool:
    """Check whether the rich library is available."""
    return RICH_AVAILABLE


# ── Modern color palette ──────────────────────────────────────────────────────

# WCAG AA accessible colors on dark background
_COLORS = {
    "excellent": "#22c55e",  # verde brillante
    "good": "#06b6d4",  # ciano
    "foundation": "#f59e0b",  # ambra
    "critical": "#ef4444",  # rosso
    "accent": "#8b5cf6",  # viola
    "muted": "#64748b",  # grigio ardesia
    "surface": "#1e293b",  # card background
    "dim": "#475569",  # secondary text
    "brand_1": "#3b82f6",  # blu brand
    "brand_2": "#06b6d4",  # ciano brand
    "brand_3": "#8b5cf6",  # viola brand
}

# Score bands with descriptions and icons
_BAND_CONFIG = {
    "excellent": {"icon": "🏆", "label": "EXCELLENT", "desc": "AI-ready — fully optimized"},
    "good": {"icon": "✅", "label": "GOOD", "desc": "Solid foundation — minor improvements needed"},
    "foundation": {"icon": "⚡", "label": "FOUNDATION", "desc": "Key elements missing"},
    "critical": {"icon": "🚨", "label": "CRITICAL", "desc": "Not visible to AI engines"},
}


def _band_color(band: str) -> str:
    """Return the color for the given band."""
    return _COLORS.get(band, _COLORS["critical"])


def _score_color(score: int, max_score: int = 100) -> str:
    """Rich color based on score percentage."""
    pct = score / max_score if max_score > 0 else 0
    if pct >= 0.85:
        return _COLORS["excellent"]
    if pct >= 0.60:
        return _COLORS["good"]
    if pct >= 0.30:
        return _COLORS["foundation"]
    return _COLORS["critical"]


# ── Micro progress bar ────────────────────────────────────────────────────────


def _micro_bar(score: int, max_score: int, width: int = 20) -> Text:
    """Barra di progresso compatta con gradiente."""
    pct = score / max_score if max_score > 0 else 0
    filled = int(pct * width)
    empty = width - filled
    color = _score_color(score, max_score)

    bar = Text()
    bar.append("▓" * filled, style=f"{color}")
    bar.append("░" * empty, style=f"{_COLORS['dim']}")
    bar.append(f" {int(pct * 100)}%", style=f"bold {color}")
    return bar


# ── Builder card for each check ───────────────────────────────────────────────


def _check_status_text(passed: bool) -> Text:
    """Badge status compatto."""
    if passed:
        return Text(" PASS ", style=f"bold white on {_COLORS['excellent']}")
    return Text(" FAIL ", style=f"bold white on {_COLORS['critical']}")


def _build_robots_card(result: AuditResult, score: int, max_score: int) -> Panel:
    """Detailed card for Robots.txt."""
    content_parts = []

    bar = _micro_bar(score, max_score)
    content_parts.append(bar)
    content_parts.append(Text())

    if not result.robots.found:
        content_parts.append(Text("  File not found", style=f"italic {_COLORS['dim']}"))
    else:
        # Bot info with detail
        info = Text()
        info.append(f"  ✓ {len(result.robots.bots_allowed)}", style=f"bold {_COLORS['excellent']}")
        info.append(" allowed", style=_COLORS["dim"])
        if result.robots.bots_blocked:
            info.append(f"   ✗ {len(result.robots.bots_blocked)}", style=f"bold {_COLORS['critical']}")
            info.append(" blocked", style=_COLORS["dim"])
        if result.robots.bots_partial:
            info.append(f"   ◐ {len(result.robots.bots_partial)}", style=f"bold {_COLORS['foundation']}")
            info.append(" partial", style=_COLORS["dim"])
        content_parts.append(info)

        # Citation bots
        citation = Text()
        if result.robots.citation_bots_ok:
            citation.append("  ✓ Citation bots", style=_COLORS["excellent"])
            if result.robots.citation_bots_explicit:
                citation.append(" (explicit)", style=_COLORS["dim"])
        else:
            citation.append("  ✗ Citation bots missing", style=_COLORS["critical"])
        content_parts.append(citation)

    color = _score_color(score, max_score)
    t = Table(show_header=False, box=None, expand=True, padding=0)
    t.add_column(ratio=1)
    for part in content_parts:
        t.add_row(part)

    return Panel(
        t,
        title="[bold]🤖 Robots.txt[/]",
        title_align="left",
        subtitle=f"[bold {color}]{score}[/][dim]/{max_score}[/]",
        subtitle_align="right",
        border_style=color,
        box=box.ROUNDED,
        padding=(1, 2),
    )


def _build_llms_card(result: AuditResult, score: int, max_score: int) -> Panel:
    """Detailed card for llms.txt."""
    content_parts = []

    bar = _micro_bar(score, max_score)
    content_parts.append(bar)
    content_parts.append(Text())

    if not result.llms.found:
        content_parts.append(Text("  File not found", style=f"italic {_COLORS['dim']}"))
    else:
        # Structure details
        features = []
        if result.llms.has_h1:
            features.append(("H1", True))
        else:
            features.append(("H1", False))
        if result.llms.has_sections:
            features.append(("Sections", True))
        else:
            features.append(("Sections", False))
        if result.llms.has_links:
            features.append(("Links", True))
        else:
            features.append(("Links", False))
        if result.llms.has_full:
            features.append(("llms-full.txt", True))
        else:
            features.append(("llms-full.txt", False))

        feat_text = Text("  ")
        for label, present in features:
            if present:
                feat_text.append(f"✓ {label}", style=_COLORS["excellent"])
            else:
                feat_text.append(f"✗ {label}", style=_COLORS["dim"])
            feat_text.append("  ", style="default")
        content_parts.append(feat_text)

        # Word count
        wc = Text()
        wc.append(f"  ~{result.llms.word_count:,} words", style=_COLORS["dim"])
        if result.llms.sections_count:
            wc.append(f"  •  {result.llms.sections_count} sections", style=_COLORS["dim"])
        content_parts.append(wc)

    color = _score_color(score, max_score)
    t = Table(show_header=False, box=None, expand=True, padding=0)
    t.add_column(ratio=1)
    for part in content_parts:
        t.add_row(part)

    return Panel(
        t,
        title="[bold]📄 llms.txt[/]",
        title_align="left",
        subtitle=f"[bold {color}]{score}[/][dim]/{max_score}[/]",
        subtitle_align="right",
        border_style=color,
        box=box.ROUNDED,
        padding=(1, 2),
    )


def _build_schema_card(result: AuditResult, score: int, max_score: int) -> Panel:
    """Detailed card for Schema JSON-LD."""
    content_parts = []

    bar = _micro_bar(score, max_score)
    content_parts.append(bar)
    content_parts.append(Text())

    if not result.schema.found_types:
        content_parts.append(Text("  No schema found", style=f"italic {_COLORS['dim']}"))
    else:
        # Schemas found as inline tags
        types_text = Text("  ")
        for i, schema_type in enumerate(result.schema.found_types[:6]):
            if i > 0:
                types_text.append("  ", style="default")
            types_text.append(f" {schema_type} ", style=f"bold {_COLORS['accent']} on #2e1065")
        content_parts.append(types_text)

        # Feature check
        schema_features = []
        if result.schema.has_faq:
            schema_features.append("FAQPage")
        if result.schema.has_article:
            schema_features.append("Article")
        if result.schema.has_organization:
            schema_features.append("Organization")
        if result.schema.has_website:
            schema_features.append("WebSite")
        if result.schema.has_sameas:
            schema_features.append("sameAs")

        if schema_features:
            feat = Text()
            feat.append("  ✓ ", style=_COLORS["excellent"])
            feat.append(" • ".join(schema_features), style=_COLORS["dim"])
            content_parts.append(feat)

        # Richness
        if result.schema.schema_richness_score > 0:
            rich_text = Text()
            rich_text.append(f"  Richness: {result.schema.schema_richness_score}/3", style=_COLORS["dim"])
            rich_text.append(f"  (avg {result.schema.avg_attributes_per_schema:.0f} attr)", style=_COLORS["dim"])
            content_parts.append(rich_text)

    color = _score_color(score, max_score)
    t = Table(show_header=False, box=None, expand=True, padding=0)
    t.add_column(ratio=1)
    for part in content_parts:
        t.add_row(part)

    return Panel(
        t,
        title="[bold]🔗 Schema JSON-LD[/]",
        title_align="left",
        subtitle=f"[bold {color}]{score}[/][dim]/{max_score}[/]",
        subtitle_align="right",
        border_style=color,
        box=box.ROUNDED,
        padding=(1, 2),
    )


def _build_meta_card(result: AuditResult, score: int, max_score: int) -> Panel:
    """Detailed card for Meta Tags."""
    content_parts = []

    bar = _micro_bar(score, max_score)
    content_parts.append(bar)
    content_parts.append(Text())

    # 2x2 meta tag grid
    checks = [
        ("Title", result.meta.has_title),
        ("Description", result.meta.has_description),
        ("Canonical", result.meta.has_canonical),
        ("Open Graph", result.meta.has_og_title),
    ]
    row1 = Text("  ")
    for label, present in checks[:2]:
        icon = "✓" if present else "✗"
        color_tag = _COLORS["excellent"] if present else _COLORS["critical"]
        row1.append(f"{icon} {label}", style=color_tag)
        row1.append("     ", style="default")
    content_parts.append(row1)

    row2 = Text("  ")
    for label, present in checks[2:]:
        icon = "✓" if present else "✗"
        color_tag = _COLORS["excellent"] if present else _COLORS["critical"]
        row2.append(f"{icon} {label}", style=color_tag)
        row2.append("  ", style="default")
    content_parts.append(row2)

    # Title preview (if present)
    if result.meta.title_text:
        title_preview = result.meta.title_text[:50]
        if len(result.meta.title_text) > 50:
            title_preview += "…"
        preview = Text()
        preview.append(f'  "{title_preview}"', style=f"italic {_COLORS['dim']}")
        content_parts.append(preview)

    color = _score_color(score, max_score)
    t = Table(show_header=False, box=None, expand=True, padding=0)
    t.add_column(ratio=1)
    for part in content_parts:
        t.add_row(part)

    return Panel(
        t,
        title="[bold]🏷️  Meta Tags[/]",
        title_align="left",
        subtitle=f"[bold {color}]{score}[/][dim]/{max_score}[/]",
        subtitle_align="right",
        border_style=color,
        box=box.ROUNDED,
        padding=(1, 2),
    )


def _build_content_card(result: AuditResult, score: int, max_score: int) -> Panel:
    """Detailed card for Content Quality."""
    content_parts = []

    bar = _micro_bar(score, max_score)
    content_parts.append(bar)
    content_parts.append(Text())

    # Main metrics
    metrics = Text("  ")
    metrics.append(f"{result.content.word_count:,}", style=f"bold {_COLORS['brand_2']}")
    metrics.append(" words", style=_COLORS["dim"])
    metrics.append("  •  ", style=_COLORS["dim"])
    metrics.append(f"{result.content.heading_count}", style=f"bold {_COLORS['brand_2']}")
    metrics.append(" headings", style=_COLORS["dim"])
    if result.content.numbers_count:
        metrics.append("  •  ", style=_COLORS["dim"])
        metrics.append(f"{result.content.numbers_count}", style=f"bold {_COLORS['brand_2']}")
        metrics.append(" stats", style=_COLORS["dim"])
    content_parts.append(metrics)

    # Compact feature checks
    features = [
        ("H1", result.content.has_h1),
        ("Hierarchy", result.content.has_heading_hierarchy),
        ("Lists", result.content.has_lists_or_tables),
        ("Front-load", result.content.has_front_loading),
        ("Ext. links", result.content.has_links),
    ]
    feat_text = Text("  ")
    for label, present in features:
        if present:
            feat_text.append(f"✓ {label}", style=_COLORS["excellent"])
        else:
            feat_text.append(f"✗ {label}", style=_COLORS["dim"])
        feat_text.append("  ", style="default")
    content_parts.append(feat_text)

    color = _score_color(score, max_score)
    t = Table(show_header=False, box=None, expand=True, padding=0)
    t.add_column(ratio=1)
    for part in content_parts:
        t.add_row(part)

    return Panel(
        t,
        title="[bold]📝 Content Quality[/]",
        title_align="left",
        subtitle=f"[bold {color}]{score}[/][dim]/{max_score}[/]",
        subtitle_align="right",
        border_style=color,
        box=box.ROUNDED,
        padding=(1, 2),
    )


def _build_signals_card(result: AuditResult, score: int, max_score: int) -> Panel:
    """Card compatta per Signals + AI Discovery combinati."""
    if not result.signals:
        return Panel(Text("No signals data"), title="Signals", border_style="dim")
    content_parts = []

    bar = _micro_bar(score, max_score)
    content_parts.append(bar)
    content_parts.append(Text())

    # Signals
    signals_items = [
        ("Lang attr", result.signals.has_lang),
        ("RSS feed", result.signals.has_rss),
        ("Freshness", result.signals.has_freshness),
    ]
    sig_text = Text("  ")
    for label, present in signals_items:
        if present:
            sig_text.append(f"✓ {label}", style=_COLORS["excellent"])
        else:
            sig_text.append(f"✗ {label}", style=_COLORS["dim"])
        sig_text.append("  ", style="default")
    content_parts.append(sig_text)

    # Lang value if present
    if result.signals.has_lang and result.signals.lang_value:
        lang_text = Text()
        lang_text.append(f'  lang="{result.signals.lang_value}"', style=f"italic {_COLORS['dim']}")
        content_parts.append(lang_text)

    color = _score_color(score, max_score)
    t = Table(show_header=False, box=None, expand=True, padding=0)
    t.add_column(ratio=1)
    for part in content_parts:
        t.add_row(part)

    return Panel(
        t,
        title="[bold]📡 Signals[/]",
        title_align="left",
        subtitle=f"[bold {color}]{score}[/][dim]/{max_score}[/]",
        subtitle_align="right",
        border_style=color,
        box=box.ROUNDED,
        padding=(1, 2),
    )


def _build_ai_discovery_card(result: AuditResult) -> Panel | None:
    """Card per AI Discovery endpoints."""
    ai = result.ai_discovery
    if not ai.endpoints_found and not ai.has_well_known_ai:
        # Only show if there is data or score > 0
        pass

    content_parts = []

    # AI Discovery score
    from geo_optimizer.core.scoring import _score_ai_discovery

    score = _score_ai_discovery(ai)
    max_score = 6

    bar = _micro_bar(score, max_score)
    content_parts.append(bar)
    content_parts.append(Text())

    endpoints = [
        ("/.well-known/ai.txt", ai.has_well_known_ai),
        ("/ai/summary.json", ai.has_summary),
        ("/ai/faq.json", ai.has_faq),
        ("/ai/service.json", ai.has_service),
    ]
    for path, present in endpoints:
        line = Text("  ")
        if present:
            line.append("✓ ", style=_COLORS["excellent"])
            line.append(path, style=f"bold {_COLORS['dim']}")
        else:
            line.append("✗ ", style=_COLORS["critical"])
            line.append(path, style=_COLORS["dim"])
        content_parts.append(line)

    color = _score_color(score, max_score)
    t = Table(show_header=False, box=None, expand=True, padding=0)
    t.add_column(ratio=1)
    for part in content_parts:
        t.add_row(part)

    return Panel(
        t,
        title="[bold]🔍 AI Discovery[/]",
        title_align="left",
        subtitle=f"[bold {color}]{score}[/][dim]/{max_score}[/]",
        subtitle_align="right",
        border_style=color,
        box=box.ROUNDED,
        padding=(1, 2),
    )


def _build_brand_entity_card(result: AuditResult, score: int, max_score: int) -> Panel:
    """Detailed card for Brand & Entity Signals."""
    content_parts = []

    bar = _micro_bar(score, max_score)
    content_parts.append(bar)
    content_parts.append(Text())

    be = result.brand_entity

    # Brand name consistency
    coherence = Text("  ")
    if be.brand_name_consistent:
        coherence.append("✓ Brand name consistent", style=_COLORS["excellent"])
    else:
        coherence.append("✗ Brand name inconsistent", style=_COLORS["critical"])
    if be.names_found:
        coherence.append(f"  ({', '.join(be.names_found[:3])})", style=_COLORS["dim"])
    content_parts.append(coherence)

    # Knowledge Graph pillars
    kg = Text("  ")
    if be.kg_pillar_count > 0:
        kg.append(f"✓ {be.kg_pillar_count}/4 KG pillars", style=_COLORS["excellent"])
        pillars = []
        if be.has_wikipedia:
            pillars.append("Wikipedia")
        if be.has_wikidata:
            pillars.append("Wikidata")
        if be.has_linkedin:
            pillars.append("LinkedIn")
        if be.has_crunchbase:
            pillars.append("Crunchbase")
        kg.append(f"  ({', '.join(pillars)})", style=_COLORS["dim"])
    else:
        kg.append("✗ No Knowledge Graph links", style=_COLORS["dim"])
    content_parts.append(kg)

    # About, Contact, Geo
    signals_text = Text("  ")
    items = [
        ("About page", be.has_about_link),
        ("Contact info", be.has_contact_info),
        ("Geo schema", be.has_geo_schema or be.has_hreflang),
    ]
    for label, present in items:
        if present:
            signals_text.append(f"✓ {label}", style=_COLORS["excellent"])
        else:
            signals_text.append(f"✗ {label}", style=_COLORS["dim"])
        signals_text.append("  ", style="default")
    content_parts.append(signals_text)

    # Topic authority: FAQ + recent articles
    if be.faq_depth > 0 or be.has_recent_articles:
        topic = Text("  ")
        if be.faq_depth > 0:
            topic.append(f"{be.faq_depth} FAQ", style=f"bold {_COLORS['brand_2']}")
        if be.has_recent_articles:
            if be.faq_depth > 0:
                topic.append("  •  ", style=_COLORS["dim"])
            topic.append("Articles with dateModified", style=_COLORS["dim"])
        content_parts.append(topic)

    color = _score_color(score, max_score)
    t = Table(show_header=False, box=None, expand=True, padding=0)
    t.add_column(ratio=1)
    for part in content_parts:
        t.add_row(part)

    return Panel(
        t,
        title="[bold]🏢 Brand & Entity[/]",
        title_align="left",
        subtitle=f"[bold {color}]{score}[/][dim]/{max_score}[/]",
        subtitle_align="right",
        border_style=color,
        box=box.ROUNDED,
        padding=(1, 2),
    )


def _build_cdn_card(result: AuditResult) -> Panel | None:
    """Card per CDN AI Crawler Access."""
    cdn = result.cdn_check
    if not cdn.checked:
        return None

    content_parts = []

    if cdn.cdn_detected:
        header = Text()
        header.append("  CDN: ", style=_COLORS["dim"])
        header.append(cdn.cdn_detected.upper(), style=f"bold {_COLORS['brand_1']}")
        content_parts.append(header)

    # Bot results come tabella compatta
    for bot in cdn.bot_results:
        line = Text("  ")
        if not bot["blocked"] and not bot["challenge_detected"]:
            line.append("✓ ", style=_COLORS["excellent"])
        else:
            line.append("✗ ", style=_COLORS["critical"])
        line.append(f"{bot['bot']}", style="bold")
        line.append(f"  HTTP {bot['status']}", style=_COLORS["dim"])
        if bot["challenge_detected"]:
            line.append("  (challenge)", style=_COLORS["foundation"])
        elif bot["blocked"]:
            line.append("  (blocked)", style=_COLORS["critical"])
        content_parts.append(line)

    color = _COLORS["excellent"] if not cdn.any_blocked else _COLORS["critical"]
    status = "PASS" if not cdn.any_blocked else "BLOCKED"

    t = Table(show_header=False, box=None, expand=True, padding=0)
    t.add_column(ratio=1)
    for part in content_parts:
        t.add_row(part)

    return Panel(
        t,
        title="[bold]🛡️  CDN Crawler Access[/]",
        title_align="left",
        subtitle=f"[bold {color}]{status}[/]",
        subtitle_align="right",
        border_style=color,
        box=box.ROUNDED,
        padding=(1, 2),
    )


def _build_js_card(result: AuditResult) -> Panel | None:
    """Card per JS Rendering Check."""
    js = result.js_rendering
    if not js.checked:
        return None

    content_parts = []

    metrics = Text()
    metrics.append(f"  {js.raw_word_count:,}", style=f"bold {_COLORS['brand_2']}")
    metrics.append(" words in raw HTML", style=_COLORS["dim"])
    metrics.append(f"  •  {js.raw_heading_count}", style=f"bold {_COLORS['brand_2']}")
    metrics.append(" headings", style=_COLORS["dim"])
    content_parts.append(metrics)

    if js.framework_detected:
        fw = Text()
        fw.append("  Framework: ", style=_COLORS["dim"])
        fw.append(js.framework_detected, style=f"bold {_COLORS['accent']}")
        content_parts.append(fw)

    if js.has_empty_root:
        content_parts.append(Text("  ⚠ Empty SPA container detected", style=_COLORS["foundation"]))
    if js.has_noscript_content:
        content_parts.append(Text("  ℹ Fallback <noscript> present", style=_COLORS["dim"]))

    color = _COLORS["excellent"] if not js.js_dependent else _COLORS["critical"]
    status = "PASS" if not js.js_dependent else "JS-DEPENDENT"

    t = Table(show_header=False, box=None, expand=True, padding=0)
    t.add_column(ratio=1)
    for part in content_parts:
        t.add_row(part)

    return Panel(
        t,
        title="[bold]⚙️  JS Rendering[/]",
        title_align="left",
        subtitle=f"[bold {color}]{status}[/]",
        subtitle_align="right",
        border_style=color,
        box=box.ROUNDED,
        padding=(1, 2),
    )


def _build_webmcp_card(result: AuditResult) -> Panel | None:
    """Card per WebMCP Readiness Check (#233)."""
    wm = result.webmcp
    if not wm.checked:
        return None

    content_parts = []

    # Badge readiness level
    level_colors = {
        "advanced": _COLORS["excellent"],
        "ready": _COLORS["good"],
        "basic": _COLORS["foundation"],
        "none": _COLORS["dim"],
    }
    level_icons = {
        "advanced": "🚀",
        "ready": "✅",
        "basic": "⚡",
        "none": "—",
    }
    level_color = level_colors.get(wm.readiness_level, _COLORS["dim"])
    level_icon = level_icons.get(wm.readiness_level, "—")

    header = Text()
    header.append(f"  {level_icon} ", style="default")
    header.append(wm.readiness_level.upper(), style=f"bold {level_color}")
    content_parts.append(header)
    content_parts.append(Text())

    # Native WebMCP signals
    webmcp_items = [
        ("registerTool() API", wm.has_register_tool),
        ("toolname attributes", wm.has_tool_attributes),
        ("Declared in ai/summary.json", wm.has_webmcp_declaration),
    ]
    for label, present in webmcp_items:
        line = Text("  ")
        if present:
            line.append(f"✓ {label}", style=_COLORS["excellent"])
            if label == "toolname attributes" and wm.tool_count:
                line.append(f" ({wm.tool_count})", style=_COLORS["dim"])
            elif label == "Declared in ai/summary.json" and wm.declared_tool_count:
                line.append(f" ({wm.declared_tool_count})", style=_COLORS["dim"])
        else:
            line.append(f"✗ {label}", style=_COLORS["dim"])
        content_parts.append(line)

    # Agent-readiness signals
    agent_items = [
        ("potentialAction", wm.has_potential_action),
        ("Labeled forms", wm.has_labeled_forms),
        ("OpenAPI spec", wm.has_openapi),
    ]
    for label, present in agent_items:
        line = Text("  ")
        if present:
            line.append(f"✓ {label}", style=_COLORS["excellent"])
            if label == "potentialAction" and wm.potential_actions:
                line.append(f" ({', '.join(wm.potential_actions[:3])})", style=_COLORS["dim"])
            elif label == "Labeled forms" and wm.labeled_forms_count:
                line.append(f" ({wm.labeled_forms_count})", style=_COLORS["dim"])
        else:
            line.append(f"✗ {label}", style=_COLORS["dim"])
        content_parts.append(line)

    color = level_color
    t = Table(show_header=False, box=None, expand=True, padding=0)
    t.add_column(ratio=1)
    for part in content_parts:
        t.add_row(part)

    return Panel(
        t,
        title="[bold]🤖 WebMCP Readiness[/]",
        title_align="left",
        subtitle=f"[bold {color}]{wm.readiness_level.upper()}[/]",
        subtitle_align="right",
        border_style=color,
        box=box.ROUNDED,
        padding=(1, 2),
    )


def _build_negative_signals_card(result: AuditResult) -> Panel | None:
    """Card per Negative Signals Detection (v4.3)."""
    ns = result.negative_signals
    if not ns.checked:
        return None

    content_parts = []

    # Badge severity
    sev_colors = {
        "clean": _COLORS["excellent"],
        "low": _COLORS["foundation"],
        "medium": _COLORS["foundation"],
        "high": _COLORS["critical"],
    }
    sev_icons = {"clean": "✅", "low": "⚡", "medium": "⚠️", "high": "🚨"}
    sev_color = sev_colors.get(ns.severity, _COLORS["dim"])

    header = Text()
    header.append(f"  {sev_icons.get(ns.severity, '—')} ", style="default")
    header.append(
        f"{ns.signals_found} negative signal{'s' if ns.signals_found != 1 else ''}",
        style=f"bold {sev_color}",
    )
    content_parts.append(header)
    content_parts.append(Text())

    # Details for each signal
    checks = [
        ("CTA overload", ns.cta_density_high, f"{ns.cta_count} CTAs" if ns.cta_count else ""),
        (
            "Popup/modal",
            ns.has_popup_signals,
            ", ".join(ns.popup_indicators[:3]) if ns.popup_indicators else "",
        ),
        ("Thin content", ns.is_thin_content, ""),
        (
            "Broken links",
            ns.has_broken_links,
            f"{ns.broken_links_count} empty hrefs" if ns.broken_links_count else "",
        ),
        (
            "Keyword stuffing",
            ns.has_keyword_stuffing,
            f"'{ns.stuffed_word}' {ns.stuffed_density}%" if ns.stuffed_word else "",
        ),
        ("Author signal", ns.has_author_signal, ""),  # inverted: True = good
        (
            "Boilerplate",
            ns.boilerplate_high,
            f"{int(ns.boilerplate_ratio * 100)}%" if ns.boilerplate_ratio else "",
        ),
        ("Mixed signals", ns.has_mixed_signals, ns.mixed_signal_detail),
    ]

    for label, is_negative, detail in checks:
        line = Text("  ")
        if label == "Author signal":
            # Inverted: has_author = good
            if is_negative:
                line.append(f"✓ {label}", style=_COLORS["excellent"])
            else:
                line.append(f"✗ No {label.lower()}", style=_COLORS["critical"])
        else:
            if is_negative:
                line.append(f"✗ {label}", style=_COLORS["critical"])
                if detail:
                    line.append(f"  ({detail})", style=_COLORS["dim"])
            else:
                line.append(f"✓ {label}", style=_COLORS["excellent"])
        content_parts.append(line)

    t = Table(show_header=False, box=None, expand=True, padding=0)
    t.add_column(ratio=1)
    for part in content_parts:
        t.add_row(part)

    return Panel(
        t,
        title="[bold]⚠️  Negative Signals[/]",
        title_align="left",
        subtitle=f"[bold {sev_color}]{ns.severity.upper()}[/]",
        subtitle_align="right",
        border_style=sev_color,
        box=box.ROUNDED,
        padding=(1, 2),
    )


# ── Main formatter ────────────────────────────────────────────────────────────


def _bar(score: int, max_score: int, width: int) -> Text:
    """Barra piena/vuota colorata in base alla percentuale."""
    filled = round(score / max_score * width) if max_score > 0 else 0
    bar = Text("█" * filled, style=_score_color(score, max_score))
    bar.append("░" * (width - filled), style=_COLORS["dim"])
    return bar


def _missing(pairs: list[tuple[str, bool]]) -> str:
    """'missing a, b' per i check falliti, stringa vuota se tutto ok."""
    names = [name for name, ok in pairs if not ok]
    return f"missing {', '.join(names)}" if names else ""


def _category_rows(result: AuditResult) -> list[tuple[str, int, int, str]]:
    """(label, score, max, dettaglio breve) per le 8 categorie del punteggio."""
    from geo_optimizer.core.scoring import _score_ai_discovery

    r, ll, sc, m, c = result.robots, result.llms, result.schema, result.meta, result.content
    sig, ai, be = result.signals, result.ai_discovery, result.brand_entity

    robots = "robots.txt not found"
    if r.found:
        robots = f"{len(r.bots_allowed)} AI bots allowed"
        if r.bots_blocked:
            robots += f" · {len(r.bots_blocked)} blocked"
    llms = "llms.txt not found"
    if ll.blocked_by_cdn:
        llms = "blocked by CDN/WAF"
    elif ll.found:
        llms = f"~{ll.word_count:,} words · {ll.sections_count} sections"
    schema = f"{len(sc.found_types)} types" if sc.any_schema_found else "no JSON-LD found"
    meta = _missing(
        [
            ("title", m.has_title),
            ("description", m.has_description),
            ("canonical", m.has_canonical),
            ("og:image", m.has_og_image),
        ]
    )
    signals = _missing([("lang", sig.has_lang), ("RSS", sig.has_rss), ("freshness", sig.has_freshness)])

    return [
        ("Robots.txt", _robots_score(result), _CATEGORY_MAX["robots"], robots),
        ("llms.txt", _llms_score(result), _CATEGORY_MAX["llms"], llms),
        ("Schema JSON-LD", _schema_score(result), _CATEGORY_MAX["schema"], schema),
        ("Meta tags", _meta_score(result), _CATEGORY_MAX["meta"], meta),
        (
            "Content",
            _content_score(result),
            _CATEGORY_MAX["content"],
            f"{c.word_count:,} words · {c.heading_count} headings",
        ),
        ("Signals", _signals_score(result), _CATEGORY_MAX["signals"], signals),
        (
            "AI discovery",
            _score_ai_discovery(ai) if ai else 0,
            _CATEGORY_MAX["ai_discovery"],
            f"{ai.endpoints_found}/4 endpoints" if ai else "",
        ),
        (
            "Brand & entity",
            _brand_entity_score(result),
            _CATEGORY_MAX["brand_entity"],
            f"{be.kg_pillar_count}/4 Knowledge Graph pillars",
        ),
    ]


def _extra_checks(result: AuditResult) -> Text | None:
    """Una riga con i check informativi eseguiti (CDN, JS, injection, trust, decay)."""
    ok, bad, warn = _COLORS["excellent"], _COLORS["critical"], _COLORS["foundation"]
    items: list[tuple[str, str, str]] = []
    if result.cdn_check.checked:
        blocked = result.cdn_check.any_blocked
        items.append(("CDN", "blocked" if blocked else "✓", bad if blocked else ok))
    if result.js_rendering.checked:
        js = result.js_rendering.js_dependent
        items.append(("JS", "required" if js else "✓", bad if js else ok))
    if result.prompt_injection.checked:
        sev = result.prompt_injection.severity
        items.append(("Injection", "✓" if sev == "clean" else sev, ok if sev == "clean" else bad))
    if result.trust_stack.checked:
        grade = result.trust_stack.grade
        items.append(("Trust", grade, ok if grade in ("A", "B") else warn))
    if result.content_decay.checked:
        risk = result.content_decay.decay_risk
        items.append(("Decay", risk.upper(), ok if risk == "low" else warn))
    if not items:
        return None
    line = Text()
    for i, (name, value, color) in enumerate(items):
        if i:
            line.append("   ")
        line.append(f"{name} ", style=_COLORS["muted"])
        line.append(value, style=f"bold {color}")
    return line


def _detail_cards(result: AuditResult, rows: list[tuple[str, int, int, str]]) -> list[Panel]:
    """Le card per categoria esistenti, mostrate solo con --verbose."""
    s = [score for _, score, _, _ in rows]
    cards = [
        _build_robots_card(result, s[0], _CATEGORY_MAX["robots"]),
        _build_llms_card(result, s[1], _CATEGORY_MAX["llms"]),
        _build_schema_card(result, s[2], _CATEGORY_MAX["schema"]),
        _build_meta_card(result, s[3], _CATEGORY_MAX["meta"]),
        _build_content_card(result, s[4], _CATEGORY_MAX["content"]),
        _build_signals_card(result, s[5], _CATEGORY_MAX["signals"]),
        _build_ai_discovery_card(result),
        _build_brand_entity_card(result, s[7], _CATEGORY_MAX["brand_entity"]),
        _build_cdn_card(result),
        _build_js_card(result),
        _build_webmcp_card(result),
        _build_negative_signals_card(result),
    ]
    return [card for card in cards if card is not None]


def format_audit_rich(result: AuditResult, verbose: bool = False, width: int | None = None) -> str:
    """Formatta AuditResult come dashboard compatta (stringa ANSI).

    Layout: header · punteggio + banda · 8 righe categoria · check extra ·
    top 5 fix · footer. ``verbose`` aggiunge le card dettagliate.
    """
    from geo_optimizer import __version__

    if width is None:
        width = min(shutil.get_terminal_size(fallback=(100, 24)).columns, 100)
    buf = io.StringIO()
    console = Console(
        file=buf, width=width, force_terminal=True, no_color=bool(os.getenv("NO_COLOR"))
    )  # no-color.org: set e non vuota
    # testo secondario in "muted": "dim" (#475569) è sotto AA su sfondo scuro
    dim, brand, warn = _COLORS["muted"], _COLORS["brand_1"], _COLORS["foundation"]

    # Header: prodotto · URL a sinistra, metadati HTTP a destra
    meta = f"HTTP {result.http_status} · {result.page_size / 1024:,.0f} KB"
    if result.audit_duration_ms is not None:
        meta += f" · {result.audit_duration_ms / 1000:.1f}s"
    header = Table.grid(expand=True)
    header.add_column()
    header.add_column(justify="right")
    left = Text(" GEO Optimizer ", style=f"bold {brand}")
    left.append(f"{__version__} · ", style=dim)
    left.append(result.url, style="bold")
    header.add_row(left, Text(meta, style=dim))
    console.print()
    console.print(header)
    console.print()

    if result.error:
        console.print(Text(f" ✗ Audit failed: {result.error}", style=f"bold {_COLORS['critical']}"))
        console.print(Text("   The site could not be analyzed: the scores below are empty, not a real 0.", style=dim))
        console.print()

    # Punteggio e banda
    band_color = _band_color(result.band)
    band_cfg = _BAND_CONFIG.get(result.band, _BAND_CONFIG["critical"])
    score_line = Text("   ")
    score_line.append(str(result.score), style=f"bold {band_color}")
    score_line.append(" /100   ", style=dim)
    score_line.append(band_cfg["label"], style=f"bold {band_color}")
    score_line.append(f"  {band_cfg['desc']}", style=dim)
    console.print(score_line)
    console.print(Text("   ").append_text(_bar(result.score, 100, min(40, width - 6))))
    console.print()

    # Le 8 categorie, allineate in colonne
    rows = _category_rows(result)
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold", min_width=16, no_wrap=True)
    grid.add_column(no_wrap=True)
    grid.add_column(justify="right", no_wrap=True)
    grid.add_column(style=dim, overflow="ellipsis", no_wrap=True)
    bar_width = 16 if width >= 80 else 8
    for label, score, max_score, detail in rows:
        score_txt = Text(str(score), style=f"bold {_score_color(score, max_score)}")
        score_txt.append(f"/{max_score}", style=dim)
        grid.add_row(f" {label}", _bar(score, max_score, bar_width), score_txt, detail)
    console.print(grid)

    extra = _extra_checks(result)
    if extra:
        console.print()
        console.print(Text(" Extra checks     ", style="bold").append_text(extra))

    # Top fix nell'ordine prodotto dal core, senza punti stimati
    recs = result.recommendations
    if recs:
        console.print()
        console.print(Text(" Top fixes", style=f"bold {warn}"))
        fixes = Table.grid(padding=(0, 2))
        fixes.add_column(justify="right", style=f"bold {warn}", no_wrap=True)
        fixes.add_column(overflow="fold")
        for i, rec in enumerate(recs if verbose else recs[:5], 1):
            fixes.add_row(f"  {i}", rec)
        console.print(fixes)
        if not verbose and len(recs) > 5:
            console.print(Text(f"      +{len(recs) - 5} more with --verbose", style=dim))

    if verbose:
        console.print()
        for card in _detail_cards(result, rows):
            console.print(card)

    # Footer: comandi successivi + funnel verso la piattaforma
    console.print()
    hints = Text(" ")
    if not verbose:
        hints.append("geo audit --verbose", style=f"bold {brand}")
        hints.append(" for every check · ", style=dim)
    hints.append("geo fix", style=f"bold {brand}")
    hints.append(" to generate the missing files", style=dim)
    console.print(hints)
    funnel = Text(" Free plan: 1 monitored domain + weekly drift email → ", style=dim)
    funnel.append("geoready.dev", style=f"{brand} underline")
    console.print(funnel)
    if result.band in ("excellent", "good"):
        badge = Text(f" {result.score}/100 is embed-worthy — add a live badge to your README → ", style=dim)
        badge.append("geoready.dev/badge", style=f"{brand} underline")
        console.print(badge)
    console.print()
    return buf.getvalue()
