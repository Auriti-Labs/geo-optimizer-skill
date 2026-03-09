"""
Output formatters per la CLI.

Gestisce output testo e JSON dei risultati di audit.
Fix #127: _() importata per utilizzo futuro (localizzazione completa in v3.2.0).
"""

import json
from dataclasses import asdict

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

# Fix #127: disponibile per wrapping stringhe UI in v3.2.0
from geo_optimizer.i18n import _  # noqa: F401
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
    lines.append("  github.com/auriti-labs/geo-optimizer-skill")
    lines.append("🔍 " * 20)
    lines.append("")
    lines.append(f"   Status: {result.http_status} | Size: {result.page_size:,} bytes")

    # Robots
    lines.append("")
    lines.append(_section_header("1. ROBOTS.TXT — Accesso Bot AI"))
    if not result.robots.found:
        lines.append("  ❌ robots.txt non trovato")
    else:
        lines.append("  ✅ robots.txt trovato")
        for bot in result.robots.bots_allowed:
            lines.append(f"  ✅ {bot} autorizzato ✓")
        for bot in result.robots.bots_blocked:
            lines.append(f"  ⚠️  {bot} bloccato")
        for bot in result.robots.bots_missing:
            lines.append(f"  ⚠️  {bot} non configurato")
        if result.robots.citation_bots_ok:
            lines.append("  ✅ Tutti i bot CITATION critici sono correttamente configurati")

    # llms.txt
    lines.append("")
    lines.append(_section_header("2. LLMS.TXT — File Indice per AI"))
    if not result.llms.found:
        lines.append("  ❌ llms.txt non trovato — essenziale per l'indicizzazione AI!")
    else:
        lines.append(f"  ✅ llms.txt trovato (~{result.llms.word_count} parole)")
        if result.llms.has_h1:
            lines.append("  ✅ H1 presente")
        else:
            lines.append("  ❌ H1 mancante")
        if result.llms.has_sections:
            lines.append("  ✅ Sezioni H2 presenti")
        if result.llms.has_links:
            lines.append("  ✅ Link trovati")

    # Schema
    lines.append("")
    lines.append(_section_header("3. SCHEMA JSON-LD — Dati Strutturati"))
    if not result.schema.found_types:
        lines.append("  ❌ Nessuno schema JSON-LD trovato nella homepage")
    else:
        for t in result.schema.found_types:
            lines.append(f"  ✅ Schema {t} ✓")
        if not result.schema.has_website:
            lines.append("  ❌ Schema WebSite mancante")
        if not result.schema.has_faq:
            lines.append("  ⚠️  Schema FAQPage mancante")

    # Meta
    lines.append("")
    lines.append(_section_header("4. META TAG — SEO & Open Graph"))
    if result.meta.has_title:
        lines.append(f"  ✅ Title: {result.meta.title_text}")
    else:
        lines.append("  ❌ Title mancante")
    if result.meta.has_description:
        lines.append(f"  ✅ Meta description ({result.meta.description_length} caratteri) ✓")
    else:
        lines.append("  ❌ Meta description mancante")
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
    lines.append(_section_header("5. QUALITÀ DEI CONTENUTI — Best Practice GEO"))
    if result.content.has_h1:
        lines.append(f"  ✅ H1: {result.content.h1_text}")
    else:
        lines.append("  ⚠️  H1 mancante nella homepage")
    lines.append(f"  {'✅' if result.content.heading_count >= 3 else '⚠️ '} {result.content.heading_count} intestazioni")
    if result.content.has_numbers:
        lines.append(f"  ✅ {result.content.numbers_count} numeri/statistiche trovati ✓")
    else:
        lines.append("  ⚠️  Pochi dati numerici")
    lines.append(f"  {'✅' if result.content.word_count >= 300 else '⚠️ '} ~{result.content.word_count} parole")
    if result.content.has_links:
        lines.append(f"  ✅ {result.content.external_links_count} link esterni ✓")
    else:
        lines.append("  ⚠️  Nessun link a fonti esterne")

    # Score
    lines.append("")
    lines.append(_section_header("📊 SCORE GEO FINALE"))
    bar_filled = int(result.score / 5)
    bar_empty = 20 - bar_filled
    bar = "█" * bar_filled + "░" * bar_empty
    lines.append(f"\n  [{bar}] {result.score}/100")

    # Fix #46: band label in italiano
    band_labels = {
        "excellent": "🏆 ECCELLENTE — Il sito è ottimizzato al meglio per i motori AI!",
        "good": "✅ BUONO — Ottimizzazioni core in place, perfeziona contenuto e schema",
        "foundation": "⚠️  BASE — Elementi core mancanti, implementa le priorità seguenti",
        "critical": "❌ CRITICO — Il sito non è visibile ai motori di ricerca AI",
    }
    lines.append(f"\n  {band_labels.get(result.band, result.band)}")
    lines.append("\n  Fasce score: 0–40 = critico | 41–70 = base | 71–90 = buono | 91–100 = eccellente")

    # Recommendations
    lines.append("\n  📋 PROSSIMI PASSI PRIORITARI:")
    if not result.recommendations:
        lines.append("  🎉 Ottimo! Tutte le ottimizzazioni principali sono implementate.")
    else:
        for i, action in enumerate(result.recommendations, 1):
            lines.append(f"  {i}. {action}")

    lines.append("")
    return "\n".join(lines)


def _section_header(text: str) -> str:
    width = 60
    return f"{'=' * width}\n  {text}\n{'=' * width}"


# Le funzioni _robots_score, _llms_score, _schema_score, _meta_score, _content_score
# sono importate da scoring_helpers (fix #77 — eliminata duplicazione)
