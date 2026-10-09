"""Test di regressione per la rubric GEO versionata."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock, patch

from geo_optimizer.core.audit import build_recommendations, run_full_audit, run_full_audit_async
from geo_optimizer.core.scoring import compute_geo_score, compute_score_breakdown
from geo_optimizer.models.config import CATEGORY_MAX, CATEGORY_MAX_V2, SCORING, SCORING_V2
from geo_optimizer.models.results import (
    AiDiscoveryResult,
    BrandEntityResult,
    CdnAiCrawlerResult,
    ContentResult,
    GoogleAiReadinessResult,
    LlmsTxtResult,
    MetaResult,
    ReadinessCheck,
    RobotsResult,
    SchemaResult,
    SignalsResult,
)


def test_v2_totals_and_v1_untouched():
    assert sum(CATEGORY_MAX_V2.values()) == 100
    assert sum(CATEGORY_MAX.values()) == 100 and CATEGORY_MAX["llms"] == 18 and SCORING["meta_canonical"] == 3
    assert SCORING_V2["meta_canonical"] == 0
    assert CATEGORY_MAX_V2 == {
        "google_ai": 20,
        "robots": 14,
        "schema": 14,
        "content": 14,
        "brand_entity": 12,
        "meta": 11,
        "llms": 6,
        "signals": 6,
        "ai_discovery": 3,
    }


def _perfect():
    return {
        "robots": RobotsResult(
            found=True,
            citation_bots_ok=True,
            citation_bots_explicit=True,
            bots_allowed=["Googlebot"],
        ),
        "llms": LlmsTxtResult(
            found=True,
            has_h1=True,
            has_blockquote=True,
            has_sections=True,
            has_links=True,
            word_count=6000,
            has_full=True,
        ),
        "schema": SchemaResult(
            any_schema_found=True,
            schema_richness_score=3,
            has_faq=True,
            has_article=True,
            has_organization=True,
            has_website=True,
            visible_match=True,
        ),
        "meta": MetaResult(
            has_title=True,
            has_description=True,
            has_canonical=True,
            has_og_title=True,
            has_og_description=True,
        ),
        "content": ContentResult(
            has_h1=True,
            has_numbers=True,
            has_links=True,
            word_count=2000,
            has_heading_hierarchy=True,
            has_lists_or_tables=True,
            has_front_loading=True,
            images_alt_ok=True,
        ),
        "signals": SignalsResult(
            has_lang=True,
            has_rss=True,
            has_freshness=True,
            freshness_valid=True,
        ),
        "ai_discovery": AiDiscoveryResult(
            has_well_known_ai=True,
            has_summary=True,
            summary_valid=True,
            has_markdown=True,
        ),
        "brand_entity": BrandEntityResult(
            brand_name_consistent=True,
            schema_desc_matches_meta=True,
            kg_pillar_count=3,
            has_about_link=True,
            has_contact_info=True,
            has_hreflang=True,
            faq_depth=3,
        ),
        "google_ai": GoogleAiReadinessResult(checked=True, points=20, max_points=20),
    }


def test_perfect_site_scores_100_in_both_versions():
    perfect = _perfect()
    assert compute_geo_score(**perfect, version=2) == 100
    v1 = {key: value for key, value in perfect.items() if key != "google_ai"}
    # v1 non conosce i campi nuovi: con ai_discovery faq/service mancanti v1 perde 2 punti, atteso
    assert compute_geo_score(**v1) == 100 - SCORING["ai_discovery_faq"] - SCORING["ai_discovery_service"]


def test_v2_breakdown_never_exceeds_category_max():
    breakdown = compute_score_breakdown(**_perfect(), version=2)
    assert all(breakdown[key] <= CATEGORY_MAX_V2[key] for key in CATEGORY_MAX_V2)


def test_v2_canonical_moves_out_of_meta_and_llms_shrinks():
    breakdown = compute_score_breakdown(**_perfect(), version=2)
    assert breakdown["meta"] == 11 and breakdown["llms"] == 6 and breakdown["google_ai"] == 20


@patch("geo_optimizer.core.audit.fetch_url", return_value=(None, "Connection failed"))
def test_unreachable_site_has_empty_google_ai(_):
    result = run_full_audit("https://unreachable.test")
    assert result.error
    assert result.score == 0
    assert result.google_ai.checked is False
    assert result.score_version == 2


def _successful_response(url: str = "https://example.com") -> Mock:
    html = """<html lang="en"><head><title>Example</title>
    <meta name="description" content="Example description">
    <link rel="canonical" href="https://example.com"></head>
    <body><h1>Example</h1><p>Useful content with <a href="/about">a link</a>.</p></body></html>"""
    return Mock(status_code=200, text=html, content=html.encode(), headers={}, url=url)


def test_default_v2_success_path_sync_and_async():
    response = _successful_response()
    async_responses = {
        "https://example.com": (response, None),
    }
    with (
        patch("geo_optimizer.core.audit.fetch_url", return_value=(response, None)),
        patch("geo_optimizer.core.audit.check_markdown_negotiation", return_value=False),
        patch("geo_optimizer.core.audit.audit_cdn_ai_crawler", return_value=CdnAiCrawlerResult()),
    ):
        sync_result = run_full_audit("https://example.com")

    with (
        patch("geo_optimizer.utils.http_async.fetch_urls_async", new=AsyncMock(return_value=async_responses)),
        patch("geo_optimizer.core.audit.check_markdown_negotiation_async", new=AsyncMock(return_value=False)),
        patch(
            "geo_optimizer.core.audit.asyncio.to_thread",
            new=AsyncMock(return_value=CdnAiCrawlerResult()),
        ),
    ):
        async_result = asyncio.run(run_full_audit_async("https://example.com"))

    for result in (sync_result, async_result):
        assert result.google_ai.checked is True
        assert result.score_version == 2
        assert result.score_max == CATEGORY_MAX_V2
        assert "google_ai" in result.score_breakdown


def test_failing_google_ai_check_id_is_in_recommendations():
    google_ai = GoogleAiReadinessResult(
        checked=True,
        checks=[
            ReadinessCheck(
                id="G-INDEX",
                status="fail",
                points=0,
                max_points=3,
                evidence="Page is not indexable",
                source_url="https://developers.google.com/search/docs",
            )
        ],
    )
    recommendations = build_recommendations(
        "https://example.com",
        RobotsResult(found=True, citation_bots_ok=True),
        LlmsTxtResult(found=True),
        SchemaResult(),
        MetaResult(
            has_title=True, has_description=True, has_canonical=True, has_og_title=True, has_og_description=True
        ),
        ContentResult(),
        google_ai=google_ai,
        category_max=CATEGORY_MAX_V2,
    )

    assert any("[G-INDEX]" in recommendation for recommendation in recommendations)


def test_recommendation_recoverable_points_use_v2_category_max():
    recommendations = build_recommendations(
        "https://example.com",
        RobotsResult(),
        LlmsTxtResult(),
        SchemaResult(),
        MetaResult(),
        ContentResult(),
        score_breakdown={"robots": 9, "llms": 0, "meta": 0},
        category_max=CATEGORY_MAX_V2,
    )

    title_index = next(i for i, item in enumerate(recommendations) if "<title>" in item)
    llms_index = next(i for i, item in enumerate(recommendations) if "Create /llms.txt" in item)
    robots_index = next(i for i, item in enumerate(recommendations) if "Create robots.txt" in item)
    assert title_index < llms_index < robots_index
    assert CATEGORY_MAX_V2["llms"] == 6


def test_v1_success_has_v1_score_max_and_no_google_ai_breakdown():
    response = _successful_response()
    with (
        patch("geo_optimizer.core.audit.fetch_url", return_value=(response, None)),
        patch("geo_optimizer.core.audit.check_markdown_negotiation", return_value=False),
        patch("geo_optimizer.core.audit.audit_cdn_ai_crawler", return_value=CdnAiCrawlerResult()),
    ):
        result = run_full_audit("https://example.com", score_version=1)

    assert result.score_version == 1
    assert result.score_max == CATEGORY_MAX
    assert "google_ai" not in result.score_breakdown


def test_http_error_is_not_written_to_cache():
    response = _successful_response()
    response.status_code = 403
    with (
        patch("geo_optimizer.utils.cache.FileCache") as cache_cls,
        patch("geo_optimizer.core.audit.fetch_url", return_value=(response, None)),
    ):
        cache_cls.return_value.get.return_value = None
        result = run_full_audit("https://blocked.example", use_cache=True)

    assert result.http_status == 403
    cache_cls.return_value.put.assert_not_called()


def test_google_ai_points_are_capped_at_category_max():
    perfect = _perfect()
    perfect["google_ai"].points = 999
    breakdown = compute_score_breakdown(**perfect, version=2)
    assert breakdown["google_ai"] == CATEGORY_MAX_V2["google_ai"]


def test_json_output_exposes_score_max_of_the_result_version():
    """Il JSON espone i massimi della rubrica del risultato (contratto documentato in json-contract.md)."""
    import json

    from geo_optimizer.cli.formatters import format_audit_json
    from geo_optimizer.models.config import CATEGORY_MAX_BY_VERSION
    from geo_optimizer.models.results import AuditResult

    for version in (1, 2):
        result = AuditResult(
            url="https://example.com", score_version=version, score_max=dict(CATEGORY_MAX_BY_VERSION[version])
        )
        assert json.loads(format_audit_json(result))["score_max"] == CATEGORY_MAX_BY_VERSION[version]
    # Risultato legacy senza score_max: fallback ai massimi v1
    assert (
        json.loads(format_audit_json(AuditResult(url="https://example.com")))["score_max"] == CATEGORY_MAX_BY_VERSION[1]
    )
