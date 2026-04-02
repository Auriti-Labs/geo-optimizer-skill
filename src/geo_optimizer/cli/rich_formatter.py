"""
Rich formatter for premium CLI output — design v2.

Requires ``rich`` as an optional dependency:
    pip install geo-optimizer-skill[rich]

Design: immersive dashboard with gradient, large gauge, stacked bar
for category breakdown, detailed cards with micro-bar, and motivational footer.
Automatic fallback via :func:`is_rich_available`.
"""

from __future__ import annotations

import io
import os
from urllib.parse import urlparse

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
from geo_optimizer.models.results import AuditResult

try:
    from rich import box
    from rich.align import Align
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

# Icons per category (more expressive than simple check/cross)
_CATEGORY_ICONS = {
    "robots": "🤖",
    "llms": "📄",
    "schema": "🔗",
    "meta": "🏷️",
    "content": "📝",
    "signals": "📡",
    "ai_discovery": "🔍",
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


def _pct_color(pct: float) -> str:
    """Color for a percentage value (0.0 - 1.0)."""
    if pct >= 0.85:
        return _COLORS["excellent"]
    if pct >= 0.60:
        return _COLORS["good"]
    if pct >= 0.30:
        return _COLORS["foundation"]
    return _COLORS["critical"]


# ── Large ASCII Art for the score ────────────────────────────────────────────

# 5-row tall digits — thin and modern style
_DIGITS = {
    "0": ["╭━╮", "┃ ┃", "┃ ┃", "┃ ┃", "╰━╯"],
    "1": [" ╻ ", "╺┃ ", " ┃ ", " ┃ ", "╺┻╸"],
    "2": ["╭━╮", "╰━┃", "╭━╯", "┃  ", "╰━━"],
    "3": ["╭━╮", "╰━┃", " ━┃", "╭━┃", "╰━╯"],
    "4": ["╻ ╻", "┃ ┃", "╰━┃", "  ┃", "  ╹"],
    "5": ["╭━━", "┃  ", "╰━╮", "╭━┃", "╰━╯"],
    "6": ["╭━╮", "┃  ", "┣━╮", "┃ ┃", "╰━╯"],
    "7": ["━━╮", "  ┃", " ╻╯", " ┃ ", " ╹ "],
    "8": ["╭━╮", "┃ ┃", "┣━┫", "┃ ┃", "╰━╯"],
    "9": ["╭━╮", "┃ ┃", "╰━┃", "  ┃", "╰━╯"],
}


def _render_big_number(number: int, color: str) -> list[Text]:
    """Render a large number in ASCII art (5 rows)."""
    digits = str(number)
    lines = []
    for row in range(5):
        line = Text()
        for i, d in enumerate(digits):
            if i > 0:
                line.append(" ", style="default")
            line.append(_DIGITS[d][row], style=f"bold {color}")
        lines.append(line)
    return lines


# ── Horizontal stacked bar (category breakdown) ───────────────────────────────


def _render_stacked_bar(categories: list[tuple[str, int, int]], width: int = 68) -> Text:
    """Colored stacked bar showing the contribution of each category.

    Each segment is proportional to the score obtained relative to the total.
    """
    total_score = sum(score for _, score, _ in categories)
    bar = Text()

    # Colors per segment
    segment_colors = [
        _COLORS["brand_1"],  # robots - blue
        _COLORS["brand_2"],  # llms - cyan
        _COLORS["accent"],  # schema - purple
        _COLORS["excellent"],  # meta - green
        _COLORS["foundation"],  # content - amber
        _COLORS["good"],  # signals - light cyan
        _COLORS["brand_3"],  # ai_discovery - viola chiaro
    ]

    # Calculate the width of each segment
    if total_score == 0:
        bar.append("━" * width, style=f"dim {_COLORS['dim']}")
        return bar

    segments = []
    remaining_width = width
    for i, (_, score, _) in enumerate(categories):
        if i == len(categories) - 1:
            seg_width = remaining_width
        else:
            seg_width = max(1, round(score / total_score * width)) if score > 0 else 0
            remaining_width -= seg_width
        segments.append((seg_width, segment_colors[i % len(segment_colors)]))

    for seg_width, color in segments:
        if seg_width > 0:
            bar.append("━" * seg_width, style=f"bold {color}")

    # Fill the remainder up to 100 points
    filled_width = sum(sw for sw, _ in segments)
    empty_width = width - filled_width
    if empty_width > 0:
        bar.append("╌" * empty_width, style=f"{_COLORS['dim']}")

    return bar


def _render_legend(categories: list[tuple[str, int, int]]) -> Text:
    """Legenda compatta per la barra stacked."""
    segment_colors = [
        _COLORS["brand_1"],
        _COLORS["brand_2"],
        _COLORS["accent"],
        _COLORS["excellent"],
        _COLORS["foundation"],
        _COLORS["good"],
        _COLORS["brand_3"],
    ]

    legend = Text()
    for i, (name, score, max_score) in enumerate(categories):
        if i > 0:
            legend.append("  ", style="default")
        color = segment_colors[i % len(segment_colors)]
        legend.append("━━", style=f"bold {color}")
        legend.append(f" {name} ", style="dim")
        legend.append(f"{score}", style=f"bold {color}")
        legend.append(f"/{max_score}", style="dim")
    return legend


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


# ── Header branding ──────────────────────────────────────────────────────────

# Minimal but impactful logo
_LOGO_LINES = [
    ("  ╔══╗  ╔══╗  ╔══╗  ", _COLORS["brand_1"]),
    ("  ║ ═╣  ║╔═╝  ║  ║  ", _COLORS["brand_2"]),
    ("  ║ ╔╣  ║╚═╗  ║  ║  ", _COLORS["accent"]),
    ("  ╚══╝  ╚══╝  ╚══╝  ", _COLORS["brand_1"]),
]


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
        content_parts.append(Text("  File non trovato", style=f"italic {_COLORS['dim']}"))
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
        content_parts.append(Text("  File non trovato", style=f"italic {_COLORS['dim']}"))
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
        wc.append(f"  ~{result.llms.word_count:,} parole", style=_COLORS["dim"])
        if result.llms.sections_count:
            wc.append(f"  •  {result.llms.sections_count} sezioni", style=_COLORS["dim"])
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
        content_parts.append(Text("  Nessuno schema trovato", style=f"italic {_COLORS['dim']}"))
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
    metrics.append(" parole", style=_COLORS["dim"])
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
        coherence.append("✓ Brand name coerente", style=_COLORS["excellent"])
    else:
        coherence.append("✗ Brand name incoerente", style=_COLORS["critical"])
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
    metrics.append(" parole in HTML", style=_COLORS["dim"])
    metrics.append(f"  •  {js.raw_heading_count}", style=f"bold {_COLORS['brand_2']}")
    metrics.append(" headings", style=_COLORS["dim"])
    content_parts.append(metrics)

    if js.framework_detected:
        fw = Text()
        fw.append("  Framework: ", style=_COLORS["dim"])
        fw.append(js.framework_detected, style=f"bold {_COLORS['accent']}")
        content_parts.append(fw)

    if js.has_empty_root:
        content_parts.append(Text("  ⚠ Container SPA vuoto rilevato", style=_COLORS["foundation"]))
    if js.has_noscript_content:
        content_parts.append(Text("  ℹ Fallback <noscript> presente", style=_COLORS["dim"]))

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
    ]
    for label, present in webmcp_items:
        line = Text("  ")
        if present:
            line.append(f"✓ {label}", style=_COLORS["excellent"])
            if label == "toolname attributes" and wm.tool_count:
                line.append(f" ({wm.tool_count})", style=_COLORS["dim"])
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


def format_audit_rich(result: AuditResult) -> str:
    """Format AuditResult as an immersive dashboard.

    Layout:
    1. Header branding with gradient logo
    2. Info panel with URL and HTTP status
    3. Large score gauge with ASCII art number
    4. Stacked category breakdown bar
    5. Detailed check cards (7 categories)
    6. Optional cards (CDN, JS Rendering)
    7. Prioritized recommendations
    8. Motivational footer

    Returns string with ANSI codes for colored terminal output.
    """
    from geo_optimizer import __version__

    _no_color = "NO_COLOR" in os.environ
    buf = io.StringIO()
    console = Console(file=buf, width=80, force_terminal=True, no_color=_no_color)

    # ── 1. Header branding ───────────────────────────────────────
    console.print()
    for line_text, color in _LOGO_LINES:
        console.print(Align.center(Text(line_text, style=f"bold {color}")))
    console.print(Align.center(Text("O P T I M I Z E R", style=f"bold {_COLORS['dim']}")))
    console.print()

    # ── 2. Info panel ────────────────────────────────────────────
    urlparse(result.url).hostname or result.url
    info = Text()
    info.append("  🌐  ", style="default")
    info.append(result.url, style=f"bold {_COLORS['brand_2']} underline")
    info.append("\n  ⚡  ", style="default")
    info.append(f"HTTP {result.http_status}", style="bold")
    info.append(f"  •  {result.page_size:,} bytes", style=_COLORS["dim"])

    console.print(
        Panel(
            info,
            box=box.ROUNDED,
            border_style=_COLORS["brand_1"],
            subtitle=f"[{_COLORS['dim']}]v{__version__}[/]",
            subtitle_align="right",
            padding=(0, 1),
        )
    )

    # ── 3. Score gauge gigante ───────────────────────────────────
    main_color = _band_color(result.band)
    band_cfg = _BAND_CONFIG.get(result.band, _BAND_CONFIG["critical"])

    console.print()

    # Large ASCII art number
    big_lines = _render_big_number(result.score, main_color)
    for line in big_lines:
        # Add " / 100" next to the center row
        console.print(Align.center(line))

    # Score subtitle
    score_sub = Text()
    score_sub.append("/ 100", style=f"bold {_COLORS['dim']}")
    console.print(Align.center(score_sub))
    console.print()

    # Main score bar (gradient)
    main_width = 60
    main_filled = int(result.score * main_width / 100)
    main_empty = main_width - main_filled
    main_bar = Text()
    main_bar.append("█" * main_filled, style=f"bold {main_color}")
    main_bar.append("░" * main_empty, style=_COLORS["dim"])
    console.print(Align.center(main_bar))

    # Band label with icon and description
    band_text = Text()
    band_text.append(f"{band_cfg['icon']}  ", style="default")
    band_text.append(band_cfg["label"], style=f"bold {main_color}")
    band_text.append(f"  —  {band_cfg['desc']}", style=_COLORS["dim"])
    console.print(Align.center(band_text))
    console.print()

    # ── 4. Breakdown stacked bar ─────────────────────────────────
    r_score = _robots_score(result)
    l_score = _llms_score(result)
    s_score = _schema_score(result)
    m_score = _meta_score(result)
    c_score = _content_score(result)
    sig_score = _signals_score(result)
    be_score = _brand_entity_score(result)
    from geo_optimizer.core.scoring import _score_ai_discovery

    ai_score = _score_ai_discovery(result.ai_discovery) if result.ai_discovery else 0

    categories = [
        ("Robots", r_score, 18),
        ("llms.txt", l_score, 18),
        ("Schema", s_score, 16),
        ("Meta", m_score, 14),
        ("Content", c_score, 12),
        ("Signals", sig_score, 6),
        ("AI Disc.", ai_score, 6),
        ("Brand", be_score, 10),
    ]

    stacked = _render_stacked_bar(categories, width=68)
    legend = _render_legend(categories)

    breakdown_content = Table(show_header=False, box=None, expand=True, padding=0)
    breakdown_content.add_column(ratio=1)
    breakdown_content.add_row(Align.center(stacked))
    breakdown_content.add_row(Text())
    breakdown_content.add_row(Align.center(legend))

    console.print(
        Panel(
            breakdown_content,
            title="[bold]📊 Score Breakdown[/]",
            title_align="left",
            border_style=_COLORS["brand_1"],
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    # ── 5. Detailed check cards ──────────────────────────────────
    console.print()
    console.print(_build_robots_card(result, r_score, 18))
    console.print(_build_llms_card(result, l_score, 18))
    console.print(_build_schema_card(result, s_score, 16))
    console.print(_build_meta_card(result, m_score, 14))
    console.print(_build_content_card(result, c_score, 12))
    console.print(_build_signals_card(result, sig_score, 6))
    console.print(_build_ai_discovery_card(result))
    console.print(_build_brand_entity_card(result, be_score, 10))

    # ── 6. Optional cards ────────────────────────────────────────
    cdn_card = _build_cdn_card(result)
    if cdn_card:
        console.print(cdn_card)

    js_card = _build_js_card(result)
    if js_card:
        console.print(js_card)

    webmcp_card = _build_webmcp_card(result)
    if webmcp_card:
        console.print(webmcp_card)

    neg_card = _build_negative_signals_card(result)
    if neg_card:
        console.print(neg_card)

    # ── 7. Recommendations ─────────────────────────────────────────
    if result.recommendations:
        rec_parts = []
        for i, rec in enumerate(result.recommendations, 1):
            rec_line = Text()
            rec_line.append(f"  {i}. ", style=f"bold {_COLORS['foundation']}")
            rec_line.append(rec, style="default")
            rec_parts.append(rec_line)

        rec_table = Table(show_header=False, box=None, expand=True, padding=0)
        rec_table.add_column(ratio=1)
        for part in rec_parts:
            rec_table.add_row(part)

        console.print()
        console.print(
            Panel(
                rec_table,
                title="[bold]💡 Recommendations[/]",
                title_align="left",
                border_style=_COLORS["foundation"],
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )

    # ── 8. Footer ────────────────────────────────────────────────
    console.print()
    footer = Text()
    footer.append("  GEO Optimizer", style=f"bold {_COLORS['brand_1']}")
    footer.append(f"  v{__version__}", style=_COLORS["dim"])
    footer.append("  •  ", style=_COLORS["dim"])
    footer.append("github.com/Auriti-Labs/geo-optimizer-skill", style=f"{_COLORS['dim']} underline")
    console.print(Align.center(footer))

    # Motivational message based on band
    console.print()
    motiv_messages = {
        "excellent": "Your site is ready for AI engines. Keep it up! 🚀",
        "good": "Great work! A few tweaks to reach excellence.",
        "foundation": "The foundations are there. Follow the recommendations to scale.",
        "critical": "Start from the recommendations — every point counts.",
    }
    motiv = motiv_messages.get(result.band, "")
    if motiv:
        console.print(Align.center(Text(motiv, style=f"italic {_COLORS['dim']}")))

    console.print()
    return buf.getvalue()
