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
    NEGATIVE_PENALTY_HIGH,
    NEGATIVE_PENALTY_LOW,
    NEGATIVE_PENALTY_MED,
    ROBOTS_PARTIAL_SCORE,
    SCORE_BANDS,
    SCORING,
    XROBOTS_NOINDEX_PENALTY,
)
from geo_optimizer.models.results import (
    AiDiscoveryResult,
    BrandEntityResult,
    ContentResult,
    LlmsTxtResult,
    MetaResult,
    NegativeSignalsResult,
    RobotsResult,
    SchemaResult,
    SignalsResult,
)

_logger = logging.getLogger(__name__)


def compute_geo_score(
    robots: RobotsResult,
    llms: LlmsTxtResult,
    schema: SchemaResult,
    meta: MetaResult,
    content: ContentResult,
    signals: SignalsResult | None = None,
    ai_discovery: AiDiscoveryResult | None = None,
    brand_entity: BrandEntityResult | None = None,
    negative_signals: NegativeSignalsResult | None = None,
) -> int:
    """Compute the GEO score 0-100 from SCORING weights (v4.0)."""
    breakdown = compute_score_breakdown(
        robots, llms, schema, meta, content, signals, ai_discovery, brand_entity, negative_signals
    )
    total = sum(breakdown.values())
    # Fix #316: report overflow to detect misalignments in SCORING weights
    if total > 100:
        _logger.warning("Score overflow: %d > 100 (check SCORING weights)", total)
    # Fix M-5: floor guard — score can never go negative
    return max(0, min(total, 100))


def compute_score_breakdown(
    robots: RobotsResult,
    llms: LlmsTxtResult,
    schema: SchemaResult,
    meta: MetaResult,
    content: ContentResult,
    signals: SignalsResult | None = None,
    ai_discovery: AiDiscoveryResult | None = None,
    brand_entity: BrandEntityResult | None = None,
    negative_signals: NegativeSignalsResult | None = None,
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
        "negative_penalty": _penalty_negative_signals(negative_signals),
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
    Schema completeness (gap #3): types present but missing required fields get partial credit.
    """
    s = SCORING["schema_any_valid"] if schema.any_schema_found else 0
    # Schema richness: rewards rich attribute schemas, penalizes generic ones
    # Fix #394: intermediate step for richness (avg >= 4 → 2pt)
    # Fix M-5: floor guard on richness score
    s += max(0, min(schema.schema_richness_score, SCORING["schema_richness"]))

    incomplete = getattr(schema, "incomplete_schema_types", [])

    # FAQPage: 3pt full, 1pt if incomplete (missing mainEntity)
    if schema.has_faq:
        s += 1 if "FAQPage" in incomplete else SCORING["schema_faq"]

    # Article subtypes: 3pt full, 1pt if incomplete (missing headline or author)
    if schema.has_article:
        article_incomplete = any(
            t in incomplete for t in ("Article", "BlogPosting", "NewsArticle", "TechArticle", "ScholarlyArticle")
        )
        s += 1 if article_incomplete else SCORING["schema_article"]

    # Organization: 3pt full, 1pt if incomplete (missing name or url)
    if schema.has_organization:
        s += 1 if "Organization" in incomplete else SCORING["schema_organization"]

    # WebSite: 2pt full, 1pt if incomplete (missing url or name)
    if schema.has_website:
        s += 1 if "WebSite" in incomplete else SCORING["schema_website"]

    s += SCORING["schema_sameas"] if schema.has_sameas else 0
    return int(s)


def _score_meta(meta) -> int:
    """Compute the meta tag score."""
    s = SCORING["meta_title"] if meta.has_title else 0
    s += SCORING["meta_description"] if meta.has_description else 0
    s += SCORING["meta_canonical"] if meta.has_canonical else 0
    s += SCORING["meta_og"] if (meta.has_og_title and meta.has_og_description) else 0
    # X-Robots-Tag: noindex via HTTP header overrides canonical — AI crawlers skip this page
    if getattr(meta, "x_robots_noindex", False):
        s = max(0, s - XROBOTS_NOINDEX_PENALTY)
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


def _penalty_negative_signals(negative_signals) -> int:
    """Return a negative score adjustment based on detected negative signals (gap #1)."""
    if negative_signals is None or not getattr(negative_signals, "checked", False):
        return 0
    severity = getattr(negative_signals, "severity", "clean")
    if severity == "high":
        return -NEGATIVE_PENALTY_HIGH
    if severity == "medium":
        return -NEGATIVE_PENALTY_MED
    if severity == "low":
        return -NEGATIVE_PENALTY_LOW
    return 0


#  brand_entity_coherence and brand_about_contact are each a single SCORING
#  budget split across two sub-signals below. They aren't separate SCORING
#  keys because formatters._MAX_BRAND (and similar) sum SCORING by
#  "brand_"-prefix — a new sub-key would double-count into that total. The
#  assertions make a future edit to the parent SCORING value fail loudly
#  here instead of silently letting CATEGORY_MAX drift out of sync with what
#  this function can actually award (fix #410 introduced the hardcoded
#  literals; this only ties them back to their source of truth).
_BRAND_COHERENCE_NAME = 2
_BRAND_COHERENCE_DESC = 1
assert SCORING["brand_entity_coherence"] == _BRAND_COHERENCE_NAME + _BRAND_COHERENCE_DESC

_BRAND_ABOUT_LINK = 1
_BRAND_CONTACT_INFO = 1
assert SCORING["brand_about_contact"] == _BRAND_ABOUT_LINK + _BRAND_CONTACT_INFO


def _score_brand_entity(brand_entity) -> int:
    """Compute the Brand & Entity score (v4.3)."""
    if brand_entity is None:
        return 0
    s = 0
    # Entity Coherence (3 points total = 2pt name + 1pt description)
    if brand_entity.brand_name_consistent:
        s += _BRAND_COHERENCE_NAME
    if brand_entity.schema_desc_matches_meta:
        s += _BRAND_COHERENCE_DESC
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
        s += _BRAND_ABOUT_LINK
    if brand_entity.has_contact_info:
        s += _BRAND_CONTACT_INFO
    # Geographic Identity (1 point)
    if brand_entity.has_geo_schema or brand_entity.has_hreflang:
        s += SCORING["brand_geo_identity"]
    # Topic Authority (1 point)
    if brand_entity.faq_depth >= 3 or brand_entity.has_recent_articles:
        s += SCORING["brand_topic_authority"]
    return s
