"""
Rich formatter for premium CLI output.

Requires ``rich`` as optional dependency:
    pip install geo-optimizer-skill[rich]

Provides branded panels, color-coded score gauge, per-check progress bars,
and animated spinner. Graceful fallback via :func:`is_rich_available`.
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
    from rich.align import Align
    from rich.console import Console
    from rich.panel import Panel
    from rich.rule import Rule
    from rich.table import Table
    from rich.text import Text

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


def _render_bar(score: int, max_score: int, width: int = 48) -> Text:
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


# ── Detail builders ────────────────────────────────────────────────────────────


def _robots_details(result: AuditResult) -> str:
    if not result.robots.found:
        return "Not found"
    parts = [f"{len(result.robots.bots_allowed)} bots allowed"]
    if result.robots.bots_blocked:
        parts.append(f"{len(result.robots.bots_blocked)} blocked")
    return "  •  ".join(parts)


def _llms_details(result: AuditResult) -> str:
    if not result.llms.found:
        return "Not found"
    parts = [f"~{result.llms.word_count} words"]
    if result.llms.has_h1:
        parts.append("H1")
    if result.llms.has_sections:
        parts.append("sections")
    if result.llms.has_full:
        parts.append("llms-full.txt")
    return "  •  ".join(parts)


def _schema_details(result: AuditResult) -> str:
    if not result.schema.found_types:
        return "No schema"
    return ", ".join(result.schema.found_types[:4])


def _meta_details(result: AuditResult) -> str:
    parts = []
    if result.meta.has_title:
        parts.append("title")
    if result.meta.has_description:
        parts.append("description")
    if result.meta.has_canonical:
        parts.append("canonical")
    if result.meta.has_og_title:
        parts.append("OG")
    return ", ".join(parts) if parts else "No meta tags"


def _content_details(result: AuditResult) -> str:
    parts = []
    if result.content.has_h1:
        parts.append("H1")
    parts.append(f"~{result.content.word_count} words")
    if result.content.has_numbers:
        parts.append(f"{result.content.numbers_count} stat")
    if result.content.has_links:
        parts.append(f"{result.content.external_links_count} link ext")
    return ", ".join(parts)


# ── Main formatter ─────────────────────────────────────────────────────────────


def format_audit_rich(result: AuditResult) -> str:
    """Format AuditResult with premium Rich output.

    Returns a string with ANSI escape codes for colored terminal output.
    Does not print directly — the caller (audit_cmd) handles output.
    """
    from geo_optimizer import __version__

    _no_color = "NO_COLOR" in os.environ
    buf = io.StringIO()
    console = Console(file=buf, width=80, force_terminal=True, no_color=_no_color)

    # ── Header panel ──────────────────────────────────────────────
    header = Text()
    header.append("\n  🔍  ", style="bold")
    header.append("G E O   O P T I M I Z E R", style="bold bright_white")
    header.append("\n\n  Target   ", style="dim")
    header.append(result.url, style="bold cyan underline")
    header.append("\n  Status   ", style="dim")
    header.append(str(result.http_status), style="bold")
    header.append(f"  •  {result.page_size:,} bytes", style="dim")
    header.append("\n")

    console.print()
    console.print(
        Panel(
            header,
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

    # Score bar
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
    icon = band_icons.get(result.band, "")
    label = band_labels.get(result.band, result.band.upper())
    console.print(Align.center(Text(f"{icon}  {label}", style=main_color)))
    console.print()

    # ── Check results ─────────────────────────────────────────────
    console.print(Rule("Check Results", style="bright_blue"))
    console.print()

    checks = [
        (
            "Robots.txt",
            _robots_score(result),
            20,
            result.robots.citation_bots_ok,
            _robots_details(result),
        ),
        (
            "llms.txt",
            _llms_score(result),
            20,
            result.llms.found and result.llms.has_h1,
            _llms_details(result),
        ),
        (
            "Schema JSON-LD",
            _schema_score(result),
            25,
            result.schema.has_website,
            _schema_details(result),
        ),
        (
            "Meta Tags",
            _meta_score(result),
            20,
            result.meta.has_title and result.meta.has_description,
            _meta_details(result),
        ),
        (
            "Content Quality",
            _content_score(result),
            15,
            result.content.has_h1,
            _content_details(result),
        ),
    ]

    for name, score, max_score, passed, details in checks:
        icon_str = _status_icon(passed)
        color = _score_color(score, max_score)

        # Check header: icon + name + right-aligned score
        ht = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        ht.add_column(width=3)
        ht.add_column(ratio=1)
        ht.add_column(justify="right", width=8)
        ht.add_row(
            f" {icon_str}",
            Text(name, style="bold"),
            Text(f"{score} / {max_score}", style=f"bold {color}"),
        )
        console.print(ht)

        # Details
        console.print(f"      [dim]{details}[/dim]")

        # Mini progress bar
        bar = _render_bar(score, max_score)
        bar_line = Text("      ")
        bar_line.append_text(bar)
        console.print(bar_line)
        console.print()

    # ── Recommendations ───────────────────────────────────────────
    if result.recommendations:
        console.print(Rule("Recommendations", style="yellow"))
        console.print()
        for i, rec in enumerate(result.recommendations, 1):
            console.print(f"  [yellow bold]{i}.[/]  {rec}")
        console.print()

    return buf.getvalue()
