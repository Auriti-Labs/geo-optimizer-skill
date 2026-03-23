"""
GEO scoring calculation functions shared across all CLI formatters.

Centralizes the 5 scoring functions to eliminate duplication
across formatters.py, rich_formatter.py, html_formatter.py, github_formatter.py.
Fix #77.
"""

from geo_optimizer.models.config import CONTENT_MIN_WORDS, SCORING
from geo_optimizer.models.results import AuditResult


def robots_score(r: AuditResult) -> int:
    """robots.txt score aligned with compute_geo_score() in audit.py.

    Distinguishes citation bots explicitly allowed (dedicated rule) from those
    allowed only via wildcard User-agent: * — fixes divergence between scoring_helpers and audit.
    """
    if not r.robots.found:
        return 0
    s = SCORING["robots_found"]
    if r.robots.citation_bots_ok:
        if r.robots.citation_bots_explicit:
            s += SCORING["robots_citation_ok"]
        else:
            s += SCORING["robots_some_allowed"]
    elif r.robots.bots_allowed:
        s += SCORING["robots_some_allowed"]
    return s


def llms_score(r: AuditResult) -> int:
    """llms.txt score aligned with SCORING (config.py).

    Guard: without llms.txt found the score is zero (#105).
    """
    if not r.llms.found:
        return 0
    s = SCORING["llms_found"]
    s += SCORING["llms_h1"] if r.llms.has_h1 else 0
    s += SCORING["llms_sections"] if r.llms.has_sections else 0
    s += SCORING["llms_links"] if r.llms.has_links else 0
    return s


def schema_score(r: AuditResult) -> int:
    """JSON-LD schema score aligned with SCORING (config.py)."""
    s = SCORING["schema_website"] if r.schema.has_website else 0
    s += SCORING["schema_faq"] if r.schema.has_faq else 0
    s += SCORING["schema_webapp"] if r.schema.has_webapp else 0
    s += SCORING["schema_article"] if r.schema.has_article else 0
    s += SCORING["schema_organization"] if r.schema.has_organization else 0
    return s


def meta_score(r: AuditResult) -> int:
    """Meta tags score aligned with SCORING (config.py)."""
    s = SCORING["meta_title"] if r.meta.has_title else 0
    s += SCORING["meta_description"] if r.meta.has_description else 0
    s += SCORING["meta_canonical"] if r.meta.has_canonical else 0
    s += SCORING["meta_og"] if (r.meta.has_og_title and r.meta.has_og_description) else 0
    return s


def content_score(r: AuditResult) -> int:
    """Content quality score aligned with SCORING (config.py)."""
    s = SCORING["content_h1"] if r.content.has_h1 else 0
    s += SCORING["content_numbers"] if r.content.has_numbers else 0
    s += SCORING["content_links"] if r.content.has_links else 0
    s += SCORING["content_word_count"] if r.content.word_count >= CONTENT_MIN_WORDS else 0
    return s
