"""
Formatter Rich per output CLI avanzato.

Richiede ``rich`` come dipendenza opzionale:
    pip install geo-optimizer-skill[rich]

Fornisce tabelle colorate, barra score visuale e spinner durante le
operazioni HTTP. Fallback graceful: se rich non è installato,
:func:`is_rich_available` ritorna False e il CLI usa il testo piatto.
"""

from geo_optimizer.models.config import SCORING
from geo_optimizer.models.results import AuditResult

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def is_rich_available() -> bool:
    """Verifica se la libreria rich è disponibile."""
    return RICH_AVAILABLE


def format_audit_rich(result: AuditResult) -> str:
    """Formatta AuditResult con tabelle e colori Rich.

    Ritorna la stringa renderizzata (non stampa direttamente).
    """
    console = Console(record=True, width=80)

    # Header
    band_colors = {
        "excellent": "green",
        "good": "cyan",
        "foundation": "yellow",
        "critical": "red",
    }
    color = band_colors.get(result.band, "white")

    console.print()
    console.print(
        Panel(
            f"[bold]GEO AUDIT[/bold] — {result.url}\nStatus: {result.http_status} | Size: {result.page_size:,} bytes",
            title="[bold blue]GEO Optimizer[/bold blue]",
            border_style="blue",
        )
    )

    # Tabella check
    table = Table(title="Check Results", show_header=True, header_style="bold")
    table.add_column("Check", style="bold", width=22)
    table.add_column("Score", justify="center", width=10)
    table.add_column("Status", justify="center", width=8)
    table.add_column("Details", width=35)

    # Robots.txt
    robots_score = _robots_score(result)
    robots_details = []
    if result.robots.found:
        robots_details.append(f"{len(result.robots.bots_allowed)} bot consentiti")
        if result.robots.bots_blocked:
            robots_details.append(f"{len(result.robots.bots_blocked)} bloccati")
    else:
        robots_details.append("Non trovato")
    table.add_row(
        "Robots.txt",
        f"{robots_score}/20",
        _status_icon(result.robots.citation_bots_ok),
        ", ".join(robots_details),
    )

    # llms.txt
    llms_score = _llms_score(result)
    llms_details = []
    if result.llms.found:
        llms_details.append(f"~{result.llms.word_count} parole")
        if result.llms.has_h1:
            llms_details.append("H1")
        if result.llms.has_sections:
            llms_details.append("sezioni")
    else:
        llms_details.append("Non trovato")
    table.add_row(
        "llms.txt",
        f"{llms_score}/20",
        _status_icon(result.llms.found and result.llms.has_h1),
        ", ".join(llms_details),
    )

    # Schema JSON-LD
    schema_score = _schema_score(result)
    schema_details = result.schema.found_types if result.schema.found_types else ["Nessuno schema"]
    table.add_row(
        "Schema JSON-LD",
        f"{schema_score}/25",
        _status_icon(result.schema.has_website),
        ", ".join(schema_details[:3]),
    )

    # Meta Tags
    meta_score = _meta_score(result)
    meta_details = []
    if result.meta.has_title:
        meta_details.append("title")
    if result.meta.has_description:
        meta_details.append("description")
    if result.meta.has_canonical:
        meta_details.append("canonical")
    if result.meta.has_og_title:
        meta_details.append("OG")
    table.add_row(
        "Meta Tags",
        f"{meta_score}/20",
        _status_icon(result.meta.has_title and result.meta.has_description),
        ", ".join(meta_details) if meta_details else "Nessun meta tag",
    )

    # Content Quality
    content_score = _content_score(result)
    content_details = []
    if result.content.has_h1:
        content_details.append("H1")
    content_details.append(f"~{result.content.word_count} parole")
    if result.content.has_numbers:
        content_details.append(f"{result.content.numbers_count} stat")
    if result.content.has_links:
        content_details.append(f"{result.content.external_links_count} link ext")
    table.add_row(
        "Content Quality",
        f"{content_score}/15",
        _status_icon(result.content.has_h1),
        ", ".join(content_details),
    )

    console.print(table)
    console.print()

    # Barra score con colore
    bar_filled = int(result.score / 5)
    bar_empty = 20 - bar_filled
    bar = "█" * bar_filled + "░" * bar_empty
    score_text = Text(f"  [{bar}] {result.score}/100", style=f"bold {color}")
    console.print(score_text)

    band_labels = {
        "excellent": "EXCELLENT — Site is well optimized for AI search engines!",
        "good": "GOOD — Core optimizations in place, fine-tune content and schema",
        "foundation": "FOUNDATION — Core elements missing, implement priority fixes",
        "critical": "CRITICAL — Site is not visible to AI search engines",
    }
    band_icon = {"excellent": "🏆", "good": "✅", "foundation": "⚠️", "critical": "❌"}
    icon = band_icon.get(result.band, "")
    label = band_labels.get(result.band, result.band)
    console.print(f"  {icon} {label}", style=color)
    console.print()

    # Raccomandazioni
    if result.recommendations:
        console.print("[bold]Recommendations:[/bold]")
        for i, rec in enumerate(result.recommendations, 1):
            console.print(f"  {i}. {rec}")
        console.print()

    return console.export_text()


def _status_icon(passed: bool) -> str:
    return "✅" if passed else "❌"


def _robots_score(r: AuditResult) -> int:
    if r.robots.citation_bots_ok:
        return SCORING["robots_found"] + SCORING["robots_citation_ok"]
    if r.robots.bots_allowed:
        return SCORING["robots_found"] + SCORING["robots_some_allowed"]
    if r.robots.found:
        return SCORING["robots_found"]
    return 0


def _llms_score(r: AuditResult) -> int:
    s = SCORING["llms_found"] if r.llms.found else 0
    s += SCORING["llms_h1"] if r.llms.has_h1 else 0
    s += SCORING["llms_sections"] if r.llms.has_sections else 0
    s += SCORING["llms_links"] if r.llms.has_links else 0
    return s


def _schema_score(r: AuditResult) -> int:
    s = SCORING["schema_website"] if r.schema.has_website else 0
    s += SCORING["schema_faq"] if r.schema.has_faq else 0
    s += SCORING["schema_webapp"] if r.schema.has_webapp else 0
    return s


def _meta_score(r: AuditResult) -> int:
    s = SCORING["meta_title"] if r.meta.has_title else 0
    s += SCORING["meta_description"] if r.meta.has_description else 0
    s += SCORING["meta_canonical"] if r.meta.has_canonical else 0
    s += SCORING["meta_og"] if (r.meta.has_og_title and r.meta.has_og_description) else 0
    return s


def _content_score(r: AuditResult) -> int:
    s = SCORING["content_h1"] if r.content.has_h1 else 0
    s += SCORING["content_numbers"] if r.content.has_numbers else 0
    s += SCORING["content_links"] if r.content.has_links else 0
    return s
