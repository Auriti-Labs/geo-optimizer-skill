"""
GEO scoring engine — computes the 0-100 score from SCORING weights.

Separated from audit.py to enable extensibility, scoring override
and per-category breakdown (v4.0).
"""

from __future__ import annotations

import logging

from geo_optimizer.models.config import (
    CATEGORY_MAX_V2,
    CONTENT_MIN_WORDS,
    LLMS_DEPTH_HIGH_WORDS,
    LLMS_DEPTH_WORDS,
    NEGATIVE_PENALTY_HIGH,
    NEGATIVE_PENALTY_LOW,
    NEGATIVE_PENALTY_MED,
    ROBOTS_PARTIAL_BY_VERSION,
    ROBOTS_PARTIAL_SCORE,
    SCORE_BANDS,
    SCORING,
    SCORING_BY_VERSION,
    XROBOTS_NOINDEX_PENALTY,
)
from geo_optimizer.models.results import (
    AiDiscoveryResult,
    BrandEntityResult,
    ContentResult,
    GoogleAiReadinessResult,
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
    google_ai: GoogleAiReadinessResult | None = None,
    version: int = 1,
) -> int:
    """Calcola il punteggio GEO 0-100 per la versione di rubric richiesta."""
    breakdown = compute_score_breakdown(
        robots,
        llms,
        schema,
        meta,
        content,
        signals,
        ai_discovery,
        brand_entity,
        negative_signals,
        google_ai,
        version,
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
    google_ai: GoogleAiReadinessResult | None = None,
    version: int = 1,
) -> dict[str, int]:
    """Restituisce il dettaglio per categoria della versione di rubric richiesta."""
    weights = SCORING_BY_VERSION[version]
    breakdown = {
        "robots": _score_robots(robots, weights, ROBOTS_PARTIAL_BY_VERSION[version]),
        "llms": _score_llms(llms, weights),
        "schema": _score_schema(schema, weights),
        "meta": _score_meta(meta, weights, version=version),
        "content": _score_content(content, weights),
        "signals": _score_signals(signals, weights, version=version) if signals is not None else 0,
        "ai_discovery": _score_ai_discovery(ai_discovery, weights) if ai_discovery is not None else 0,
        "brand_entity": _score_brand_entity(brand_entity, weights) if brand_entity is not None else 0,
        "negative_penalty": _penalty_negative_signals(negative_signals),
    }
    if version >= 2:
        breakdown["google_ai"] = (
            min(google_ai.points, CATEGORY_MAX_V2["google_ai"]) if google_ai is not None and google_ai.checked else 0
        )
    return breakdown


def get_score_band(score: int) -> str:
    """Return the score band name from SCORE_BANDS."""
    for band_name, (low, high) in SCORE_BANDS.items():
        if low <= score <= high:
            return band_name
    return "critical"


def _score_robots(robots, w: dict = SCORING, partial: int = ROBOTS_PARTIAL_SCORE) -> int:
    """Compute the robots.txt score."""
    if not robots.found:
        return 0
    s: int = w.get("robots_found", 0)
    if robots.citation_bots_ok:
        if robots.citation_bots_explicit:
            # Full score: citation bots explicitly allowed
            s += w.get("robots_citation_ok", 0)
        else:
            # Allowed only via wildcard: partial score
            s += partial
    elif robots.bots_allowed:
        s += partial
    return s


def _score_llms(llms, w: dict = SCORING) -> int:
    """Compute the llms.txt score with graduated quality."""
    if not llms.found:
        return 0
    s: int = w.get("llms_found", 0)
    s += w.get("llms_h1", 0) if llms.has_h1 else 0
    # #39: blockquote bonus (1 point from reduced llms_found budget)
    s += w.get("llms_blockquote", 0) if getattr(llms, "has_blockquote", False) else 0
    s += w.get("llms_sections", 0) if llms.has_sections else 0
    s += w.get("llms_links", 0) if llms.has_links else 0
    # Content depth: bonus for richer files
    s += w.get("llms_depth", 0) if llms.word_count >= LLMS_DEPTH_WORDS else 0
    s += w.get("llms_depth_high", 0) if llms.word_count >= LLMS_DEPTH_HIGH_WORDS else 0
    s += w.get("llms_full", 0) if llms.has_full else 0
    return s


def _score_schema(schema, w: dict = SCORING) -> int:
    """Compute the JSON-LD schema score.

    Schema richness (Growth Marshal Feb 2026): a schema with only @type + name + url
    is generic and unhelpful. A schema with 5+ relevant attributes → full points.
    Schema completeness (gap #3): types present but missing required fields get partial credit.
    """
    s = w.get("schema_any_valid", 0) if schema.any_schema_found else 0
    # Schema richness: rewards rich attribute schemas, penalizes generic ones
    # Fix #394: intermediate step for richness (avg >= 4 → 2pt)
    # Fix M-5: floor guard on richness score
    s += max(0, min(schema.schema_richness_score, w.get("schema_richness", 0)))

    incomplete = getattr(schema, "incomplete_schema_types", [])

    # FAQPage: 3pt full, 1pt if incomplete (missing mainEntity)
    if schema.has_faq:
        schema_faq = w.get("schema_faq", 0)
        s += min(1, schema_faq) if "FAQPage" in incomplete else schema_faq

    # Article subtypes: 3pt full, 1pt if incomplete (missing headline or author)
    if schema.has_article:
        article_incomplete = any(
            t in incomplete for t in ("Article", "BlogPosting", "NewsArticle", "TechArticle", "ScholarlyArticle")
        )
        schema_article = w.get("schema_article", 0)
        s += min(1, schema_article) if article_incomplete else schema_article

    # Organization: 3pt full, 1pt if incomplete (missing name or url)
    if schema.has_organization:
        schema_organization = w.get("schema_organization", 0)
        s += min(1, schema_organization) if "Organization" in incomplete else schema_organization

    # WebSite: 2pt full, 1pt if incomplete (missing url or name)
    if schema.has_website:
        schema_website = w.get("schema_website", 0)
        s += min(1, schema_website) if "WebSite" in incomplete else schema_website

    s += w.get("schema_sameas", 0) if schema.has_sameas else 0
    s += w.get("schema_visible_match", 0) if getattr(schema, "visible_match", False) else 0
    return int(s)


def _score_meta(meta, w: dict = SCORING, *, version: int = 1) -> int:
    """Compute the meta tag score."""
    s = w.get("meta_title", 0) if meta.has_title else 0
    s += w.get("meta_description", 0) if meta.has_description else 0
    s += w.get("meta_canonical", 0) if meta.has_canonical else 0
    s += w.get("meta_og", 0) if (meta.has_og_title and meta.has_og_description) else 0
    # X-Robots-Tag: noindex via HTTP header overrides canonical — AI crawlers skip this page
    if version == 1 and getattr(meta, "x_robots_noindex", False):
        s = max(0, s - XROBOTS_NOINDEX_PENALTY)
    return s


def _score_content(content, w: dict = SCORING) -> int:
    """Compute the content quality score."""
    s = w.get("content_h1", 0) if content.has_h1 else 0
    s += w.get("content_numbers", 0) if content.has_numbers else 0
    s += w.get("content_links", 0) if content.has_links else 0
    s += w.get("content_word_count", 0) if content.word_count >= CONTENT_MIN_WORDS else 0
    s += w.get("content_heading_hierarchy", 0) if content.has_heading_hierarchy else 0
    s += w.get("content_lists_or_tables", 0) if content.has_lists_or_tables else 0
    s += w.get("content_front_loading", 0) if content.has_front_loading else 0
    s += w.get("content_images_alt", 0) if getattr(content, "images_alt_ok", False) else 0
    return s


def _score_signals(signals, w: dict = SCORING, *, version: int = 1) -> int:
    """Compute the technical signals score (v4.0)."""
    if signals is None:
        return 0
    s = w.get("signals_lang", 0) if signals.has_lang else 0
    s += w.get("signals_rss", 0) if signals.has_rss else 0
    fresh = signals.has_freshness and (version == 1 or getattr(signals, "freshness_valid", False))
    s += w.get("signals_freshness", 0) if fresh else 0
    return s


def _score_ai_discovery(ai_discovery, w: dict = SCORING) -> int:
    """Compute the AI discovery score (geo-checklist.dev standard)."""
    if ai_discovery is None:
        return 0
    s = w.get("ai_discovery_well_known", 0) if ai_discovery.has_well_known_ai else 0
    s += w.get("ai_discovery_summary", 0) if ai_discovery.has_summary and ai_discovery.summary_valid else 0
    s += w.get("ai_discovery_faq", 0) if ai_discovery.has_faq else 0
    s += w.get("ai_discovery_service", 0) if ai_discovery.has_service else 0
    s += w.get("ai_discovery_markdown", 0) if getattr(ai_discovery, "has_markdown", False) else 0
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


def _score_brand_entity(brand_entity, w: dict = SCORING) -> int:
    """Compute the Brand & Entity score (v4.3)."""
    if brand_entity is None:
        return 0
    s = 0
    # Entity Coherence (3 points total = 2pt name + 1pt description)
    coherence_name = w.get("brand_entity_coherence", 0) - _BRAND_COHERENCE_DESC
    if brand_entity.brand_name_consistent:
        s += coherence_name
    if brand_entity.schema_desc_matches_meta:
        s += _BRAND_COHERENCE_DESC
    # Knowledge Graph Readiness (3 points)
    pillars = brand_entity.kg_pillar_count
    if pillars >= 3:
        s += w.get("brand_kg_readiness", 0)
    elif pillars >= 2:
        s += w.get("brand_kg_readiness", 0) - 1
    elif pillars >= 1:
        s += w.get("brand_kg_readiness", 0) - 2
    # About/Contact (2 points)
    about_link = w.get("brand_about_contact", 0) - _BRAND_CONTACT_INFO
    if brand_entity.has_about_link:
        s += about_link
    if brand_entity.has_contact_info:
        s += _BRAND_CONTACT_INFO
    # Geographic Identity (1 point)
    if brand_entity.has_geo_schema or brand_entity.has_hreflang:
        s += w.get("brand_geo_identity", 0)
    # Topic Authority (1 point)
    if brand_entity.faq_depth >= 3 or brand_entity.has_recent_articles:
        s += w.get("brand_topic_authority", 0)
    return s
