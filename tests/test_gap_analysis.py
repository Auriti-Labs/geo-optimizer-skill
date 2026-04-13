"""Test per la gap analysis GEO."""

from __future__ import annotations

from geo_optimizer.core.gap_analysis import build_gap_analysis
from geo_optimizer.models.results import (
    AiDiscoveryResult,
    AuditResult,
    BrandEntityResult,
    ContentResult,
    LlmsTxtResult,
    MetaResult,
    RobotsResult,
    SchemaResult,
    SignalsResult,
)


def _make_result(
    url: str,
    score: int,
    band: str,
    *,
    robots=None,
    llms=None,
    schema=None,
    meta=None,
    content=None,
    signals=None,
    ai_discovery=None,
    brand_entity=None,
    score_breakdown=None,
) -> AuditResult:
    """Crea un AuditResult minimo ma personalizzabile per i test di gap analysis."""
    return AuditResult(
        url=url,
        score=score,
        band=band,
        robots=robots or RobotsResult(),
        llms=llms or LlmsTxtResult(),
        schema=schema or SchemaResult(),
        meta=meta or MetaResult(),
        content=content or ContentResult(),
        signals=signals or SignalsResult(),
        ai_discovery=ai_discovery or AiDiscoveryResult(),
        brand_entity=brand_entity or BrandEntityResult(),
        score_breakdown=score_breakdown or {},
    )


class TestGapAnalysis:
    """Test per il motore di interpretazione dei gap competitivi."""

    def test_build_gap_analysis_prioritizes_highest_impact_actions(self):
        """I gap vengono ordinati per impatto e riferiti al sito più debole."""
        weaker = _make_result(
            "https://weaker.example.com",
            52,
            "foundation",
            robots=RobotsResult(found=False, citation_bots_ok=False),
            llms=LlmsTxtResult(found=False, has_sections=False, has_links=False),
            schema=SchemaResult(has_faq=False, has_organization=False, has_website=False),
            meta=MetaResult(has_title=False, has_canonical=False, has_og_title=False, has_og_description=False),
            content=ContentResult(has_links=False, has_front_loading=False, has_heading_hierarchy=False),
            signals=SignalsResult(has_lang=False, has_rss=False),
            ai_discovery=AiDiscoveryResult(has_well_known_ai=False, has_summary=False, has_faq=False),
            brand_entity=BrandEntityResult(kg_pillar_count=0, has_about_link=False),
            score_breakdown={"robots": 0, "llms": 0, "schema": 0, "meta": 0},
        )
        stronger = _make_result(
            "https://stronger.example.com",
            84,
            "good",
            robots=RobotsResult(found=True, citation_bots_ok=True),
            llms=LlmsTxtResult(found=True, has_sections=True, has_links=True),
            schema=SchemaResult(has_faq=True, has_organization=True, has_website=True),
            meta=MetaResult(has_title=True, has_canonical=True, has_og_title=True, has_og_description=True),
            content=ContentResult(has_links=True, has_front_loading=True, has_heading_hierarchy=True),
            signals=SignalsResult(has_lang=True, has_rss=True),
            ai_discovery=AiDiscoveryResult(has_well_known_ai=True, has_summary=True, has_faq=True),
            brand_entity=BrandEntityResult(kg_pillar_count=3, has_about_link=True),
            score_breakdown={"robots": 18, "llms": 11, "schema": 8, "meta": 12},
        )

        result = build_gap_analysis(weaker, stronger)

        assert result.weaker_url == "https://weaker.example.com"
        assert result.stronger_url == "https://stronger.example.com"
        assert result.score_gap == 32
        assert result.action_plan[0].impact_points >= result.action_plan[-1].impact_points
        assert any(action.title == "Allow critical citation bots" for action in result.action_plan)
        assert any(action.command.startswith("geo fix --url https://weaker.example.com --only robots") for action in result.action_plan)

    def test_build_gap_analysis_exposes_weaker_strengths(self):
        """Le categorie in cui il sito debole è avanti vengono riportate come strengths."""
        weaker = _make_result(
            "https://weaker.example.com",
            60,
            "foundation",
            score_breakdown={"robots": 18, "meta": 4},
        )
        stronger = _make_result(
            "https://stronger.example.com",
            70,
            "good",
            score_breakdown={"robots": 10, "meta": 10},
        )

        result = build_gap_analysis(weaker, stronger)

        assert any(strength.category == "robots" for strength in result.strengths)
