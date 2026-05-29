"""Tests for Multi-Platform Citation Profile (#228)."""

from __future__ import annotations

from geo_optimizer.core.audit_platform import audit_platform_citation
from geo_optimizer.models.results import (
    AiDiscoveryResult,
    CitabilityResult,
    ContentResult,
    JsRenderingResult,
    LlmsTxtResult,
    MetaResult,
    MethodScore,
    RobotsResult,
    SchemaResult,
    SignalsResult,
)


def _google_ai(result):
    """Extract the google_ai PlatformScore from a result."""
    return next(p for p in result.platforms if p.platform == "google_ai")


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

    def test_backward_compat_without_js_rendering_kwarg(self):
        # Calling without js_rendering must not raise (default None).
        result = audit_platform_citation(**_defaults())
        assert _google_ai(result) is not None


class TestGoogleAiRealign:
    """Google AI lens aligned to Google's AI optimization guide (#realign)."""

    def test_well_known_ai_does_not_affect_google_ai_score(self):
        # Google does NOT use .well-known/ai.txt — toggling it must not move the score.
        with_ai = audit_platform_citation(
            **_defaults(), ai_discovery=AiDiscoveryResult(has_well_known_ai=True)
        )
        without_ai = audit_platform_citation(
            **_defaults(), ai_discovery=AiDiscoveryResult(has_well_known_ai=False)
        )
        assert _google_ai(with_ai).score == _google_ai(without_ai).score

    def test_no_ai_txt_recommendation_for_google_ai(self):
        result = audit_platform_citation(
            **_defaults(), ai_discovery=AiDiscoveryResult(has_well_known_ai=False)
        )
        recs = " ".join(_google_ai(result).recommendations).lower()
        assert "ai.txt" not in recs
        assert ".well-known" not in recs

    def test_freshness_boosts_google_ai_by_4(self):
        fresh = audit_platform_citation(**_defaults(signals=SignalsResult(has_freshness=True)))
        stale = audit_platform_citation(**_defaults(signals=SignalsResult(has_freshness=False)))
        assert _google_ai(fresh).score - _google_ai(stale).score == 4

    def test_ssr_safe_content_boosts_google_ai_by_3(self):
        ssr = audit_platform_citation(
            **_defaults(), js_rendering=JsRenderingResult(checked=True, js_dependent=False)
        )
        js_only = audit_platform_citation(
            **_defaults(), js_rendering=JsRenderingResult(checked=True, js_dependent=True)
        )
        assert _google_ai(ssr).score - _google_ai(js_only).score == 3

    def test_js_dependent_content_gets_ssr_recommendation(self):
        result = audit_platform_citation(
            **_defaults(), js_rendering=JsRenderingResult(checked=True, js_dependent=True)
        )
        recs = " ".join(_google_ai(result).recommendations).lower()
        assert "server-side" in recs or "server side" in recs

    def test_image_alt_quality_boosts_google_ai_by_3(self):
        good = CitabilityResult(
            total_score=10,
            methods=[MethodScore(name="image_alt_quality", label="Image alt", detected=True, score=5, max_score=5)],
        )
        bad = CitabilityResult(
            total_score=10,
            methods=[MethodScore(name="image_alt_quality", label="Image alt", detected=False, score=0, max_score=5)],
        )
        r_good = audit_platform_citation(**_defaults(citability=good))
        r_bad = audit_platform_citation(**_defaults(citability=bad))
        assert _google_ai(r_good).score - _google_ai(r_bad).score == 3

    def test_missing_image_alt_recommendation(self):
        bad = CitabilityResult(
            total_score=10,
            methods=[MethodScore(name="image_alt_quality", label="Image alt", detected=False, score=0, max_score=5)],
        )
        result = audit_platform_citation(**_defaults(citability=bad))
        recs = " ".join(_google_ai(result).recommendations).lower()
        assert "alt text" in recs

    def test_google_ai_score_capped_at_100(self):
        result = audit_platform_citation(
            robots=RobotsResult(bots_allowed=["Google-Extended"]),
            llms=LlmsTxtResult(),
            schema=SchemaResult(any_schema_found=True, schema_richness_score=6, has_sameas=True),
            meta=MetaResult(
                has_title=True, has_description=True, has_canonical=True, has_og_title=True, has_og_description=True
            ),
            content=ContentResult(has_h1=True, word_count=600),
            citability=CitabilityResult(
                total_score=90,
                methods=[MethodScore(name="image_alt_quality", label="Image alt", detected=True, score=5, max_score=5)],
            ),
            signals=SignalsResult(has_freshness=True),
            js_rendering=JsRenderingResult(checked=True, js_dependent=False),
        )
        assert _google_ai(result).score <= 100

    def test_chatgpt_perplexity_unchanged_by_realign(self):
        # llms.txt remains valid outside Google — other lenses still reward it.
        llms_with = LlmsTxtResult(found=True, has_links=True)
        result = audit_platform_citation(**_defaults(llms=llms_with))
        chatgpt = next(p for p in result.platforms if p.platform == "chatgpt")
        perp = next(p for p in result.platforms if p.platform == "perplexity")
        assert any("llms.txt" in s.lower() for s in chatgpt.strengths)
        assert any("llms.txt" in s.lower() for s in perp.strengths)

    def test_strengths_present_for_optimized_site(self):
        result = audit_platform_citation(
            robots=RobotsResult(bots_allowed=["GPTBot", "PerplexityBot", "Google-Extended"]),
            llms=LlmsTxtResult(found=True, has_links=True, has_h1=True),
            schema=SchemaResult(
                any_schema_found=True, schema_richness_score=6, has_faq=True, has_organization=True, has_sameas=True
            ),
            meta=MetaResult(
                has_title=True, has_description=True, has_canonical=True, has_og_title=True, has_og_description=True
            ),
            content=ContentResult(has_h1=True, word_count=600, has_links=True, external_links_count=5),
            citability=CitabilityResult(total_score=75),
            signals=SignalsResult(has_freshness=True, has_rss=True),
        )
        for p in result.platforms:
            assert len(p.strengths) > 0
            assert p.score >= 50
