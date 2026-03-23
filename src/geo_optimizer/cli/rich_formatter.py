"""
Rich formatter for premium CLI output.

Requires ``rich`` as optional dependency:
    pip install geo-optimizer-skill[rich]

Provides branded panels, color-coded score gauge, per-check card panels
with progress bars, Tree view for schema types, and animated spinner.
Graceful fallback via :func:`is_rich_available`.
"""

from __future__ import annotations

import io
import os

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
from geo_optimizer.models.results import AuditResult

try:
    from rich import box
    from rich.align import Align
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.tree import Tree

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# ── Public helpers ─────────────────────────────────────────────────────────────


def is_rich_available() -> bool:
    """Check whether the rich library is available."""
    return RICH_AVAILABLE


def _status_icon(passed: bool) -> str:
    """Return check/cross icon."""
    return "✅" if passed else "❌"


# ── Color and bar helpers ──────────────────────────────────────────────────────


def _score_color(score: int, max_score: int = 100) -> str:
    """Return Rich color name based on score percentage."""
    pct = score / max_score if max_score > 0 else 0
    if pct >= 0.85:
        return "green"
    if pct >= 0.6:
        return "cyan"
    if pct >= 0.3:
        return "yellow"
    return "red"


def _render_bar(score: int, max_score: int, width: int = 60) -> Text:
    """Render a colored progress bar as Rich Text."""
    pct = score / max_score if max_score > 0 else 0
    filled = int(pct * width)
    empty = width - filled
    color = _score_color(score, max_score)

    bar = Text()
    bar.append("━" * filled, style=f"bold {color}")
    bar.append("━" * empty, style="bright_black")
    bar.append(f"  {int(pct * 100)}%", style=f"dim {color}")
    return bar


def _stack(*renderables) -> Table:
    """Stack renderables vertically using an invisible Table layout."""
    t = Table(show_header=False, box=None, expand=True, padding=0)
    t.add_column(ratio=1)
    for r in renderables:
        t.add_row(r)
    return t


# ── Check content builders ─────────────────────────────────────────────────────


def _build_robots_content(result: AuditResult, bar: Text):
    """Build inner content for Robots.txt check panel."""
    if not result.robots.found:
        detail = Text("Not found", style="dim italic")
    else:
        parts = [f"{len(result.robots.bots_allowed)} bots allowed"]
        if result.robots.bots_blocked:
            parts.append(f"{len(result.robots.bots_blocked)} blocked")
        if result.robots.bots_partial:
            parts.append(f"{len(result.robots.bots_partial)} partial")
        detail = Text("  •  ".join(parts))
    return _stack(detail, Text(""), bar)


def _build_llms_content(result: AuditResult, bar: Text):
    """Build inner content for llms.txt check panel."""
    if not result.llms.found:
        detail = Text("Not found", style="dim italic")
    else:
        parts = [f"~{result.llms.word_count} words"]
        if result.llms.has_h1:
            parts.append("H1")
        if result.llms.has_sections:
            parts.append("sections")
        if result.llms.has_full:
            parts.append("llms-full.txt")
        detail = Text("  •  ".join(parts))
    return _stack(detail, Text(""), bar)


def _build_schema_content(result: AuditResult, bar: Text):
    """Build inner content for Schema JSON-LD check panel with Tree view."""
    if not result.schema.found_types:
        detail = Text("No schema", style="dim italic")
        return _stack(detail, Text(""), bar)

    tree = Tree("📋 Types", guide_style="dim cyan")
    for schema_type in result.schema.found_types[:5]:
        tree.add(f"[bold]{schema_type}[/]")
    return _stack(tree, Text(""), bar)


def _build_meta_content(result: AuditResult, bar: Text):
    """Build inner content for Meta Tags check panel with inline checkmarks."""
    meta_checks = [
        ("title", result.meta.has_title),
        ("description", result.meta.has_description),
        ("canonical", result.meta.has_canonical),
        ("OG", result.meta.has_og_title),
    ]
    parts = []
    for label, present in meta_checks:
        if present:
            parts.append(f"[green]✓[/] {label}")
        else:
            parts.append(f"[red]✗[/] [dim]{label}[/]")
    detail = Text.from_markup("   ".join(parts))
    return _stack(detail, Text(""), bar)


def _build_content_content(result: AuditResult, bar: Text):
    """Build inner content for Content Quality check panel."""
    parts = []
    if result.content.has_h1:
        parts.append("H1")
    parts.append(f"~{result.content.word_count} words")
    if result.content.has_numbers:
        parts.append(f"{result.content.numbers_count} stat")
    if result.content.has_links:
        parts.append(f"{result.content.external_links_count} link ext")
    detail = Text("  •  ".join(parts))
    return _stack(detail, Text(""), bar)


# ── Main formatter ─────────────────────────────────────────────────────────────


def format_audit_rich(result: AuditResult) -> str:
    """Format AuditResult with premium Rich card-based output.

    Each check is rendered as a colored Panel (card) with:
    - Title: icon + check name (top-left border)
    - Subtitle: score (bottom-right border)
    - Content: details + progress bar
    - Border color: matches score status

    Returns a string with ANSI codes for colored terminal output.
    """
    from geo_optimizer import __version__

    _no_color = "NO_COLOR" in os.environ
    buf = io.StringIO()
    console = Console(file=buf, width=80, force_terminal=True, no_color=_no_color)

    # ── Header panel ──────────────────────────────────────────────
    header = Text()
    header.append("\n  🔍  ", style="bold")
    header.append("G E O   O P T I M I Z E R", style="bold bright_white")
    header.append("\n\n  Target    ", style="dim")
    header.append(result.url, style="bold cyan underline")
    header.append("\n  Response  ", style="dim")
    header.append(str(result.http_status), style="bold")
    header.append(f"  •  {result.page_size:,} bytes", style="dim")
    header.append("\n")

    console.print()
    console.print(
        Panel(
            header,
            box=box.ROUNDED,
            border_style="bright_blue",
            subtitle=f"[dim]v{__version__}[/dim]",
            subtitle_align="right",
        )
    )

    # ── Main score gauge ──────────────────────────────────────────
    main_color = _score_color(result.score)

    console.print()
    score_display = Text()
    score_display.append(f"{result.score}", style=f"bold {main_color}")
    score_display.append(" / 100", style="dim")
    console.print(Align.center(score_display))

    # Score bar (centered)
    main_filled = int(result.score * 50 / 100)
    main_empty = 50 - main_filled
    main_bar = Text()
    main_bar.append("━" * main_filled, style=f"bold {main_color}")
    main_bar.append("━" * main_empty, style="bright_black")
    console.print(Align.center(main_bar))

    # Band label
    band_labels = {
        "excellent": "EXCELLENT — Site is well optimized for AI engines",
        "good": "GOOD — Core optimizations in place",
        "foundation": "FOUNDATION — Core elements missing",
        "critical": "CRITICAL — Not visible to AI engines",
    }
    band_icons = {"excellent": "🏆", "good": "✅", "foundation": "⚠️ ", "critical": "❌"}
    band_icon = band_icons.get(result.band, "")
    band_label = band_labels.get(result.band, result.band.upper())
    console.print(Align.center(Text(f"{band_icon}  {band_label}", style=main_color)))
    console.print()

    # ── Check cards ───────────────────────────────────────────────
    checks = [
        ("Robots.txt", _robots_score(result), 20, result.robots.citation_bots_ok, _build_robots_content),
        ("llms.txt", _llms_score(result), 20, result.llms.found and result.llms.has_h1, _build_llms_content),
        ("Schema JSON-LD", _schema_score(result), 25, result.schema.has_website, _build_schema_content),
        ("Meta Tags", _meta_score(result), 20, result.meta.has_title and result.meta.has_description, _build_meta_content),
        ("Content Quality", _content_score(result), 15, result.content.has_h1, _build_content_content),
    ]

    for name, score, max_score, passed, builder in checks:
        icon = _status_icon(passed)
        color = _score_color(score, max_score)
        bar = _render_bar(score, max_score)
        content = builder(result, bar)

        console.print(
            Panel(
                content,
                title=f"{icon} [bold]{name}[/]",
                title_align="left",
                subtitle=f"[bold {color}]{score} / {max_score}[/]",
                subtitle_align="right",
                border_style=color,
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )

    # ── Recommendations card ──────────────────────────────────────
    if result.recommendations:
        rec_lines = []
        for i, rec in enumerate(result.recommendations, 1):
            rec_lines.append(f"  [yellow bold]{i}.[/]  {rec}")
        rec_text = "\n".join(rec_lines)

        console.print()
        console.print(
            Panel(
                rec_text,
                title="💡 [bold]Recommendations[/]",
                title_align="left",
                border_style="yellow",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )

    console.print()
    return buf.getvalue()
