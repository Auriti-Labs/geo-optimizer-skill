"""Tests for Multi-Platform Citation Profile (#228)."""

from __future__ import annotations

from geo_optimizer.core.audit_platform import audit_platform_citation
from geo_optimizer.models.results import (
    CitabilityResult,
    ContentResult,
    LlmsTxtResult,
    MetaResult,
    RobotsResult,
    SchemaResult,
    SignalsResult,
)


def _defaults(**overrides):
    """Build default audit sub-results with overrides."""
    return {
        "robots": overrides.get("robots", RobotsResult()),
        "llms": overrides.get("llms", LlmsTxtResult()),
        "schema": overrides.get("schema", SchemaResult()),
        "meta": overrides.get("meta", MetaResult()),
        "content": overrides.get("content", ContentResult()),
        "citability": overrides.get("citability", CitabilityResult()),
        "signals": overrides.get("signals", SignalsResult()),
    }


class TestPlatformCitation:
    def test_returns_three_platforms(self):
        result = audit_platform_citation(**_defaults())
        assert result.checked is True
        assert len(result.platforms) == 3
        names = [p.platform for p in result.platforms]
        assert "chatgpt" in names
        assert "perplexity" in names
        assert "google_ai" in names

    def test_all_scores_0_to_100(self):
        result = audit_platform_citation(**_defaults())
        for p in result.platforms:
            assert 0 <= p.score <= 100

    def test_gptbot_allowed_boosts_chatgpt(self):
        robots_with = RobotsResult(bots_allowed=["GPTBot"])
        robots_without = RobotsResult(bots_allowed=[])
        r_with = audit_platform_citation(**_defaults(robots=robots_with))
        r_without = audit_platform_citation(**_defaults(robots=robots_without))
        chatgpt_with = next(p for p in r_with.platforms if p.platform == "chatgpt")
        chatgpt_without = next(p for p in r_without.platforms if p.platform == "chatgpt")
        assert chatgpt_with.score > chatgpt_without.score

    def test_llms_txt_boosts_perplexity(self):
        llms_with = LlmsTxtResult(found=True, has_links=True)
        llms_without = LlmsTxtResult(found=False)
        r_with = audit_platform_citation(**_defaults(llms=llms_with))
        r_without = audit_platform_citation(**_defaults(llms=llms_without))
        perp_with = next(p for p in r_with.platforms if p.platform == "perplexity")
        perp_without = next(p for p in r_without.platforms if p.platform == "perplexity")
        assert perp_with.score > perp_without.score

    def test_schema_boosts_google_ai(self):
        schema_rich = SchemaResult(any_schema_found=True, schema_richness_score=6, has_website=True)
        schema_empty = SchemaResult()
        r_with = audit_platform_citation(**_defaults(schema=schema_rich))
        r_without = audit_platform_citation(**_defaults(schema=schema_empty))
        google_with = next(p for p in r_with.platforms if p.platform == "google_ai")
        google_without = next(p for p in r_without.platforms if p.platform == "google_ai")
        assert google_with.score > google_without.score

    def test_high_citability_boosts_all(self):
        high = CitabilityResult(total_score=80)
        low = CitabilityResult(total_score=10)
        r_high = audit_platform_citation(**_defaults(citability=high))
        r_low = audit_platform_citation(**_defaults(citability=low))
        for platform in ["chatgpt", "perplexity", "google_ai"]:
            s_high = next(p for p in r_high.platforms if p.platform == platform).score
            s_low = next(p for p in r_low.platforms if p.platform == platform).score
            assert s_high >= s_low

    def test_recommendations_present_for_empty_site(self):
        result = audit_platform_citation(**_defaults())
        for p in result.platforms:
            assert len(p.recommendations) > 0

    def test_strengths_present_for_optimized_site(self):
        result = audit_platform_citation(
            robots=RobotsResult(bots_allowed=["GPTBot", "PerplexityBot", "Google-Extended"]),
            llms=LlmsTxtResult(found=True, has_links=True, has_h1=True),
            schema=SchemaResult(any_schema_found=True, schema_richness_score=6, has_faq=True, has_organization=True, has_sameas=True),
            meta=MetaResult(has_title=True, has_description=True, has_canonical=True, has_og_title=True, has_og_description=True),
            content=ContentResult(has_h1=True, word_count=600, has_links=True, external_links_count=5),
            citability=CitabilityResult(total_score=75),
            signals=SignalsResult(has_freshness=True, has_rss=True),
        )
        for p in result.platforms:
            assert len(p.strengths) > 0
            assert p.score >= 50
