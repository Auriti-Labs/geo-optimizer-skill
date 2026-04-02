"""
GEO scoring engine — computes the 0-100 score from SCORING weights.

Separated from audit.py to enable extensibility, scoring override
and per-category breakdown (v4.0).
"""

from __future__ import annotations

import logging

from geo_optimizer.models.config import (
    CONTENT_MIN_WORDS,
    LLMS_DEPTH_HIGH_WORDS,
    LLMS_DEPTH_WORDS,
    ROBOTS_PARTIAL_SCORE,
    SCORE_BANDS,
    SCORING,
)

_logger = logging.getLogger(__name__)


def compute_geo_score(robots, llms, schema, meta, content, signals=None, ai_discovery=None, brand_entity=None) -> int:
    """Compute the GEO score 0-100 from SCORING weights (v4.0)."""
    breakdown = compute_score_breakdown(robots, llms, schema, meta, content, signals, ai_discovery, brand_entity)
    total = sum(breakdown.values())
    # Fix #316: report overflow to detect misalignments in SCORING weights
    if total > 100:
        _logger.warning("Score overflow: %d > 100 (check SCORING weights)", total)
    return min(total, 100)


def compute_score_breakdown(
    robots, llms, schema, meta, content, signals=None, ai_discovery=None, brand_entity=None
) -> dict[str, int]:
    """Return the score breakdown by category."""
    return {
        "robots": _score_robots(robots),
        "llms": _score_llms(llms),
        "schema": _score_schema(schema),
        "meta": _score_meta(meta),
        "content": _score_content(content),
        "signals": _score_signals(signals) if signals is not None else 0,
        "ai_discovery": _score_ai_discovery(ai_discovery) if ai_discovery is not None else 0,
        "brand_entity": _score_brand_entity(brand_entity) if brand_entity is not None else 0,
    }


def get_score_band(score: int) -> str:
    """Return the score band name from SCORE_BANDS."""
    for band_name, (low, high) in SCORE_BANDS.items():
        if low <= score <= high:
            return band_name
    return "critical"


def _score_robots(robots) -> int:
    """Compute the robots.txt score."""
    if not robots.found:
        return 0
    s = SCORING["robots_found"]
    if robots.citation_bots_ok:
        if robots.citation_bots_explicit:
            # Full score: citation bots explicitly allowed
            s += SCORING["robots_citation_ok"]
        else:
            # Allowed only via wildcard: partial score
            s += ROBOTS_PARTIAL_SCORE
    elif robots.bots_allowed:
        s += ROBOTS_PARTIAL_SCORE
    return s


def _score_llms(llms) -> int:
    """Compute the llms.txt score with graduated quality."""
    if not llms.found:
        return 0
    s = SCORING["llms_found"]
    s += SCORING["llms_h1"] if llms.has_h1 else 0
    # #39: blockquote bonus (1 point from reduced llms_found budget)
    s += SCORING.get("llms_blockquote", 1) if getattr(llms, "has_blockquote", False) else 0
    s += SCORING["llms_sections"] if llms.has_sections else 0
    s += SCORING["llms_links"] if llms.has_links else 0
    # Content depth: bonus for richer files
    s += SCORING["llms_depth"] if llms.word_count >= LLMS_DEPTH_WORDS else 0
    s += SCORING["llms_depth_high"] if llms.word_count >= LLMS_DEPTH_HIGH_WORDS else 0
    s += SCORING["llms_full"] if llms.has_full else 0
    return s


def _score_schema(schema) -> int:
    """Compute the JSON-LD schema score.

    Schema richness (Growth Marshal Feb 2026): a schema with only @type + name + url
    is generic and unhelpful. A schema with 5+ relevant attributes → full points.
    """
    s = SCORING["schema_any_valid"] if schema.any_schema_found else 0
    # Schema richness: rewards rich attribute schemas, penalizes generic ones
    # Fix #394: intermediate step for richness (avg >= 4 → 2pt)
    s += min(schema.schema_richness_score, SCORING["schema_richness"])
    s += SCORING["schema_faq"] if schema.has_faq else 0
    s += SCORING["schema_article"] if schema.has_article else 0
    s += SCORING["schema_organization"] if schema.has_organization else 0
    s += SCORING["schema_website"] if schema.has_website else 0
    s += SCORING["schema_sameas"] if schema.has_sameas else 0
    return s


def _score_meta(meta) -> int:
    """Compute the meta tag score."""
    s = SCORING["meta_title"] if meta.has_title else 0
    s += SCORING["meta_description"] if meta.has_description else 0
    s += SCORING["meta_canonical"] if meta.has_canonical else 0
    s += SCORING["meta_og"] if (meta.has_og_title and meta.has_og_description) else 0
    return s


def _score_content(content) -> int:
    """Compute the content quality score."""
    s = SCORING["content_h1"] if content.has_h1 else 0
    s += SCORING["content_numbers"] if content.has_numbers else 0
    s += SCORING["content_links"] if content.has_links else 0
    s += SCORING["content_word_count"] if content.word_count >= CONTENT_MIN_WORDS else 0
    s += SCORING["content_heading_hierarchy"] if content.has_heading_hierarchy else 0
    s += SCORING["content_lists_or_tables"] if content.has_lists_or_tables else 0
    s += SCORING["content_front_loading"] if content.has_front_loading else 0
    return s


def _score_signals(signals) -> int:
    """Compute the technical signals score (v4.0)."""
    if signals is None:
        return 0
    s = SCORING["signals_lang"] if signals.has_lang else 0
    s += SCORING["signals_rss"] if signals.has_rss else 0
    s += SCORING["signals_freshness"] if signals.has_freshness else 0
    return s


def _score_ai_discovery(ai_discovery) -> int:
    """Compute the AI discovery score (geo-checklist.dev standard)."""
    if ai_discovery is None:
        return 0
    s = SCORING["ai_discovery_well_known"] if ai_discovery.has_well_known_ai else 0
    s += SCORING["ai_discovery_summary"] if ai_discovery.has_summary and ai_discovery.summary_valid else 0
    s += SCORING["ai_discovery_faq"] if ai_discovery.has_faq else 0
    s += SCORING["ai_discovery_service"] if ai_discovery.has_service else 0
    return s


def _score_brand_entity(brand_entity) -> int:
    """Compute the Brand & Entity score (v4.3)."""
    if brand_entity is None:
        return 0
    s = 0
    # Entity Coherence (3 points total = 2pt name + 1pt description)
    # Fix #410: use explicit values instead of SCORING[key] - 1
    if brand_entity.brand_name_consistent:
        s += 2
    if brand_entity.schema_desc_matches_meta:
        s += 1
    # Knowledge Graph Readiness (3 points)
    pillars = brand_entity.kg_pillar_count
    if pillars >= 3:
        s += SCORING["brand_kg_readiness"]  # 3pt
    elif pillars >= 2:
        s += 2
    elif pillars >= 1:
        s += 1
    # About/Contact (2 points)
    if brand_entity.has_about_link:
        s += 1
    if brand_entity.has_contact_info:
        s += 1
    # Geographic Identity (1 point)
    if brand_entity.has_geo_schema or brand_entity.has_hreflang:
        s += SCORING["brand_geo_identity"]
    # Topic Authority (1 point)
    if brand_entity.faq_depth >= 3 or brand_entity.has_recent_articles:
        s += SCORING["brand_topic_authority"]
    return s
