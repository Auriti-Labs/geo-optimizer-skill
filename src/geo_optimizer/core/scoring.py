"""
GEO scoring engine — calcola il punteggio 0-100 dai pesi SCORING.

Separato da audit.py per abilitare estensibilità, override dello scoring
e breakdown per categoria (v4.0).
"""

from __future__ import annotations

import logging

from geo_optimizer.models.config import (
    CONTENT_MIN_WORDS,
    LLMS_DEPTH_HIGH_WORDS,
    LLMS_DEPTH_WORDS,
    SCORE_BANDS,
    SCORING,
)

_logger = logging.getLogger(__name__)


def compute_geo_score(robots, llms, schema, meta, content, signals=None, ai_discovery=None) -> int:
    """Calcola il punteggio GEO 0-100 dai pesi SCORING (v4.0)."""
    breakdown = compute_score_breakdown(robots, llms, schema, meta, content, signals, ai_discovery)
    total = sum(breakdown.values())
    # Fix #316: segnala overflow per rilevare disallineamenti nei pesi SCORING
    if total > 100:
        _logger.warning("Score overflow: %d > 100 (verificare pesi SCORING)", total)
    return min(total, 100)


def compute_score_breakdown(robots, llms, schema, meta, content, signals=None, ai_discovery=None) -> dict[str, int]:
    """Ritorna il breakdown del punteggio per categoria."""
    return {
        "robots": _score_robots(robots),
        "llms": _score_llms(llms),
        "schema": _score_schema(schema),
        "meta": _score_meta(meta),
        "content": _score_content(content),
        "signals": _score_signals(signals) if signals is not None else 0,
        "ai_discovery": _score_ai_discovery(ai_discovery) if ai_discovery is not None else 0,
    }


def get_score_band(score: int) -> str:
    """Ritorna il nome della banda di punteggio da SCORE_BANDS."""
    for band_name, (low, high) in SCORE_BANDS.items():
        if low <= score <= high:
            return band_name
    return "critical"


def _score_robots(robots) -> int:
    """Calcola il punteggio robots.txt."""
    if not robots.found:
        return 0
    s = SCORING["robots_found"]
    if robots.citation_bots_ok:
        if robots.citation_bots_explicit:
            # Punteggio pieno: bot di citazione esplicitamente permessi
            s += SCORING["robots_citation_ok"]
        else:
            # Permesso solo via wildcard: punteggio parziale
            s += SCORING["robots_some_allowed"]
    elif robots.bots_allowed:
        s += SCORING["robots_some_allowed"]
    return s


def _score_llms(llms) -> int:
    """Calcola il punteggio llms.txt con qualità graduata."""
    if not llms.found:
        return 0
    s = SCORING["llms_found"]
    s += SCORING["llms_h1"] if llms.has_h1 else 0
    # #39: bonus blockquote (1 punto dal budget llms_found ridotto)
    s += SCORING.get("llms_blockquote", 1) if getattr(llms, "has_blockquote", False) else 0
    s += SCORING["llms_sections"] if llms.has_sections else 0
    s += SCORING["llms_links"] if llms.has_links else 0
    # Profondità contenuto: bonus per file più ricchi
    s += SCORING["llms_depth"] if llms.word_count >= LLMS_DEPTH_WORDS else 0
    s += SCORING["llms_depth_high"] if llms.word_count >= LLMS_DEPTH_HIGH_WORDS else 0
    s += SCORING["llms_full"] if llms.has_full else 0
    return s


def _score_schema(schema) -> int:
    """Calcola il punteggio schema JSON-LD.

    Schema richness (Growth Marshal Feb 2026): schema con solo @type + name + url
    è generico e non aiuta. Schema con 5+ attributi rilevanti → punti pieni.
    """
    s = SCORING["schema_any_valid"] if schema.any_schema_found else 0
    # Schema richness: premia schema con attributi ricchi, penalizza quelli generici
    s += min(schema.schema_richness_score, SCORING["schema_richness"])
    s += SCORING["schema_faq"] if schema.has_faq else 0
    s += SCORING["schema_article"] if schema.has_article else 0
    s += SCORING["schema_organization"] if schema.has_organization else 0
    s += SCORING["schema_website"] if schema.has_website else 0
    s += SCORING["schema_sameas"] if schema.has_sameas else 0
    return s


def _score_meta(meta) -> int:
    """Calcola il punteggio meta tag."""
    s = SCORING["meta_title"] if meta.has_title else 0
    s += SCORING["meta_description"] if meta.has_description else 0
    s += SCORING["meta_canonical"] if meta.has_canonical else 0
    s += SCORING["meta_og"] if (meta.has_og_title and meta.has_og_description) else 0
    return s


def _score_content(content) -> int:
    """Calcola il punteggio qualità contenuto."""
    s = SCORING["content_h1"] if content.has_h1 else 0
    s += SCORING["content_numbers"] if content.has_numbers else 0
    s += SCORING["content_links"] if content.has_links else 0
    s += SCORING["content_word_count"] if content.word_count >= CONTENT_MIN_WORDS else 0
    s += SCORING["content_heading_hierarchy"] if content.has_heading_hierarchy else 0
    s += SCORING["content_lists_or_tables"] if content.has_lists_or_tables else 0
    s += SCORING["content_front_loading"] if content.has_front_loading else 0
    return s


def _score_signals(signals) -> int:
    """Calcola il punteggio segnali tecnici (v4.0)."""
    if signals is None:
        return 0
    s = SCORING["signals_lang"] if signals.has_lang else 0
    s += SCORING["signals_rss"] if signals.has_rss else 0
    s += SCORING["signals_freshness"] if signals.has_freshness else 0
    return s


def _score_ai_discovery(ai_discovery) -> int:
    """Calcola il punteggio AI discovery (geo-checklist.dev standard)."""
    if ai_discovery is None:
        return 0
    s = SCORING["ai_discovery_well_known"] if ai_discovery.has_well_known_ai else 0
    s += SCORING["ai_discovery_summary"] if ai_discovery.has_summary and ai_discovery.summary_valid else 0
    s += SCORING["ai_discovery_faq"] if ai_discovery.has_faq else 0
    s += SCORING["ai_discovery_service"] if ai_discovery.has_service else 0
    return s
