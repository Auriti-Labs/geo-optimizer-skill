"""
GEO Audit — Multi-Platform Citation Profile (#228).

Heuristic scoring for ChatGPT, Perplexity, and Google AI readiness
based on data already available in the audit (zero additional HTTP).

Platform preferences based on Superlines 2026 and OtterlyAI research:
- ChatGPT: community presence, Wikipedia-style structure, news coverage
- Perplexity: source diversity, citation density, freshness
- Google AI: domain authority signals, schema markup, traditional SEO
"""

from __future__ import annotations

from geo_optimizer.models.results import (
    AiDiscoveryResult,
    CitabilityResult,
    ContentResult,
    LlmsTxtResult,
    MetaResult,
    PlatformCitationResult,
    PlatformScore,
    RobotsResult,
    SchemaResult,
    SignalsResult,
)


def audit_platform_citation(
    robots: RobotsResult,
    llms: LlmsTxtResult,
    schema: SchemaResult,
    meta: MetaResult,
    content: ContentResult,
    citability: CitabilityResult,
    signals: SignalsResult | None = None,
    ai_discovery: AiDiscoveryResult | None = None,
) -> PlatformCitationResult:
    """Compute per-platform citation readiness scores.

    Uses only data already computed by the audit — zero additional HTTP.
    """
    return PlatformCitationResult(
        checked=True,
        platforms=[
            _score_chatgpt(robots, llms, content, citability, schema),
            _score_perplexity(robots, llms, content, citability, signals),
            _score_google_ai(robots, schema, meta, content, citability, ai_discovery),
        ],
    )


def _score_chatgpt(robots, llms, content, citability, schema) -> PlatformScore:
    """ChatGPT favors: community signals, structured answers, Wikipedia-style."""
    score = 0
    strengths: list[str] = []
    recs: list[str] = []

    # GPTBot access
    if any(b == "GPTBot" for b in robots.bots_allowed):
        score += 15
        strengths.append("GPTBot allowed in robots.txt")
    else:
        recs.append("Allow GPTBot in robots.txt")

    # llms.txt
    if llms.found:
        score += 15
        strengths.append("llms.txt present")
    else:
        recs.append("Add /llms.txt for LLM-friendly site summary")

    # FAQ schema (ChatGPT loves Q&A format)
    if schema.has_faq:
        score += 15
        strengths.append("FAQ schema present")
    else:
        recs.append("Add FAQPage schema for Q&A-style answers")

    # Content structure
    if content.has_h1 and content.word_count >= 300:
        score += 10
        strengths.append("Well-structured content")

    # Citability
    if citability.total_score >= 60:
        score += 15
        strengths.append(f"Citability score {citability.total_score}/100")
    elif citability.total_score >= 40:
        score += 8

    # Organization schema (entity clarity)
    if schema.has_organization:
        score += 10
        strengths.append("Organization schema present")
    else:
        recs.append("Add Organization schema for entity clarity")

    # HowTo schema
    if schema.has_howto:
        score += 10
        strengths.append("HowTo schema present")

    # Article schema
    if schema.has_article:
        score += 10
        strengths.append("Article schema present")

    return PlatformScore(platform="chatgpt", score=min(score, 100), strengths=strengths, recommendations=recs)


def _score_perplexity(robots, llms, content, citability, signals) -> PlatformScore:
    """Perplexity favors: source diversity, citation density, freshness."""
    score = 0
    strengths: list[str] = []
    recs: list[str] = []

    # PerplexityBot access
    if any(b == "PerplexityBot" for b in robots.bots_allowed):
        score += 15
        strengths.append("PerplexityBot allowed")
    else:
        recs.append("Allow PerplexityBot in robots.txt")

    # llms.txt with links (source diversity)
    if llms.found and llms.has_links:
        score += 15
        strengths.append("llms.txt with links")
    elif llms.found:
        score += 8
        recs.append("Add links in llms.txt for source diversity")
    else:
        recs.append("Add /llms.txt with links to key resources")

    # Citation density (Perplexity values inline citations)
    if citability.total_score >= 70:
        score += 20
        strengths.append(f"High citability ({citability.total_score}/100)")
    elif citability.total_score >= 50:
        score += 12

    # Freshness
    if signals and signals.has_freshness:
        score += 15
        strengths.append("Content freshness signals present")
    else:
        recs.append("Add dateModified schema or freshness indicators")

    # Content depth
    if content.word_count >= 500:
        score += 10
        strengths.append("Substantial content depth")
    elif content.word_count >= 300:
        score += 5

    # External links (source diversity)
    if content.has_links and content.external_links_count >= 3:
        score += 10
        strengths.append("External links for source diversity")
    else:
        recs.append("Add external links to authoritative sources")

    # RSS feed
    if signals and signals.has_rss:
        score += 10
        strengths.append("RSS feed available")

    return PlatformScore(platform="perplexity", score=min(score, 100), strengths=strengths, recommendations=recs)


def _score_google_ai(robots, schema, meta, content, citability, ai_discovery) -> PlatformScore:
    """Google AI Overviews favors: schema, domain authority, traditional SEO."""
    score = 0
    strengths: list[str] = []
    recs: list[str] = []

    # Google-Extended access
    if any(b == "Google-Extended" for b in robots.bots_allowed):
        score += 10
        strengths.append("Google-Extended allowed")
    else:
        recs.append("Allow Google-Extended in robots.txt")

    # Schema richness (Google loves structured data)
    if schema.schema_richness_score >= 5:
        score += 20
        strengths.append(f"Rich schema ({schema.schema_richness_score} types)")
    elif schema.any_schema_found:
        score += 10
        recs.append("Add more schema types for richer structured data")
    else:
        recs.append("Add JSON-LD schema markup")

    # Meta tags (traditional SEO)
    if meta.has_title and meta.has_description and meta.has_canonical:
        score += 15
        strengths.append("Complete meta tags")
    else:
        recs.append("Complete title, description, and canonical meta tags")

    # Open Graph
    if meta.has_og_title and meta.has_og_description:
        score += 10
        strengths.append("Open Graph tags present")

    # Citability
    if citability.total_score >= 60:
        score += 15
        strengths.append(f"Citability score {citability.total_score}/100")
    elif citability.total_score >= 40:
        score += 8

    # Content quality
    if content.has_h1 and content.word_count >= 300:
        score += 10
        strengths.append("Quality content structure")

    # AI discovery endpoints
    if ai_discovery and ai_discovery.has_well_known_ai:
        score += 10
        strengths.append("AI discovery endpoints present")
    else:
        recs.append("Add /.well-known/ai.txt for AI discovery")

    # sameAs links (domain authority proxy)
    if schema.has_sameas:
        score += 10
        strengths.append("sameAs links for authority signals")
    else:
        recs.append("Add sameAs links to social profiles and Wikipedia")

    return PlatformScore(platform="google_ai", score=min(score, 100), strengths=strengths, recommendations=recs)
