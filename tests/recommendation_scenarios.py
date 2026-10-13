"""Deterministic input scenarios for the recommendation tests.

The module deliberately imports only result dataclasses and ``build_recommendations``
so the very same scenarios can run against a checkout that predates the
``recommendations_by_category`` field. The golden file
``tests/fixtures/recommendations_golden.json`` was produced that way: it holds the
flat ``recommendations`` list emitted by the pre-change implementation, and the
tests assert the current output is byte-identical to it.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

from geo_optimizer.core.audit import _build_audit_result, run_full_audit, run_full_audit_async
from geo_optimizer.models.config import CATEGORY_MAX, CATEGORY_MAX_V2
from geo_optimizer.models.results import (
    AiDiscoveryResult,
    AuditResult,
    BrandEntityResult,
    CdnAiCrawlerResult,
    ContentResult,
    GoogleAiReadinessResult,
    JsRenderingResult,
    LlmsTxtResult,
    MetaResult,
    MultimodalResult,
    NegativeSignalsResult,
    PromptInjectionResult,
    ReadinessCheck,
    RobotsResult,
    SchemaResult,
    SignalsResult,
    WebMcpResult,
)

BASE_URL = "https://example.com"


def failing_google_ai() -> GoogleAiReadinessResult:
    """Google AI readiness with one failing and one warning check (both scored)."""
    return GoogleAiReadinessResult(
        checked=True,
        checks=[
            ReadinessCheck(
                id="G-INDEX",
                status="fail",
                points=0,
                max_points=3,
                evidence="Page is not indexable",
                source_url="https://developers.google.com/search/docs",
            ),
            ReadinessCheck(
                id="G-SNIPPET",
                status="warn",
                points=1,
                max_points=2,
                evidence="Snippet controls are restrictive",
                source_url="https://developers.google.com/search/docs/snippet",
            ),
        ],
    )


def worst_case_inputs() -> dict[str, Any]:
    """Every audited area fails and every optional informational module fires.

    This is the widest input the recommendation builder can receive: it touches
    all scored categories plus every bucket that has no scored category
    (negative signals, prompt injection, UGC, WebMCP, multimodal).
    """
    return {
        "base_url": BASE_URL,
        "robots": RobotsResult(found=True, citation_bots_ok=False, crawl_delay=30.0),
        "llms": LlmsTxtResult(found=False),
        "schema": SchemaResult(
            json_parse_errors=2,
            has_product=True,
            ecommerce_signals={"price": False, "availability": True, "complete": False},
            schema_missing_fields={"Organization": ["logo", "url"]},
        ),
        "meta": MetaResult(
            x_robots_noindex=True,
            x_robots_tag="noindex",
            has_noai=True,
            noai_value="noai, noimageai",
        ),
        "content": ContentResult(word_count=10),
        "ai_discovery": AiDiscoveryResult(),
        "signals": SignalsResult(),
        "brand_entity": BrandEntityResult(names_found=["Acme", "ACME Inc"], kg_pillar_count=0),
        "webmcp": WebMcpResult(checked=True, readiness_level="none"),
        "negative_signals": NegativeSignalsResult(
            checked=True,
            cta_density_high=True,
            cta_count=12,
            is_thin_content=True,
            has_keyword_stuffing=True,
            stuffed_word="seo",
            stuffed_density=7.5,
            boilerplate_high=True,
            boilerplate_ratio=0.8,
            has_mixed_signals=True,
            mixed_signal_detail="promotional tone with informational schema",
            severity="high",
        ),
        "prompt_injection": PromptInjectionResult(
            checked=True,
            severity="high",
            llm_instruction_found=True,
            html_comment_injection_found=True,
            hidden_text_found=True,
            ugc_surface_found=True,
            ugc_surface_samples=["comments", "reviews"],
            ugc_injection_risk=True,
        ),
        "multimodal": MultimodalResult(
            checked=True,
            total_images=10,
            images_with_alt=2,
            alt_coverage=0.2,
            has_video=True,
            has_audio=True,
        ),
        "google_ai": failing_google_ai(),
    }


def ugc_advisory_inputs() -> dict[str, Any]:
    """Clean injection scan that still exposes a UGC surface (advisory, not critical)."""
    inputs = worst_case_inputs()
    inputs["prompt_injection"] = PromptInjectionResult(
        checked=True,
        severity="clean",
        ugc_surface_found=True,
        ugc_surface_samples=["comments"],
        ugc_injection_risk=False,
    )
    return inputs


def minimal_inputs() -> dict[str, Any]:
    """Only the mandatory arguments, every area failing (the shape of older callers)."""
    return {
        "base_url": BASE_URL,
        "robots": RobotsResult(),
        "llms": LlmsTxtResult(),
        "schema": SchemaResult(),
        "meta": MetaResult(),
        "content": ContentResult(),
    }


def mixed_inputs() -> dict[str, Any]:
    """A partly healthy site: robots update (not create), llms present but thin."""
    return {
        "base_url": BASE_URL,
        "robots": RobotsResult(found=True, citation_bots_ok=False),
        "llms": LlmsTxtResult(found=True, sections_count=0, links_count=1, validation_warnings=["llms.txt: no H1"]),
        "schema": SchemaResult(has_website=True),
        "meta": MetaResult(has_title=True, has_canonical=True),
        "content": ContentResult(has_h1=True, word_count=400, has_numbers=True),
        "ai_discovery": AiDiscoveryResult(has_well_known_ai=True),
        "signals": SignalsResult(has_lang=True),
        "brand_entity": BrandEntityResult(kg_pillar_count=2, has_about_link=True),
    }


# Score breakdowns that exercise the "recoverable points" reordering
BREAKDOWN_V1 = {
    "robots": 18,
    "llms": 0,
    "schema": 0,
    "meta": 12,
    "content": 12,
    "signals": 6,
    "ai_discovery": 0,
    "brand_entity": 10,
    "negative_penalty": -4,
}
BREAKDOWN_V2 = {
    "google_ai": 5,
    "robots": 3,
    "schema": 0,
    "content": 14,
    "brand_entity": 12,
    "meta": 11,
    "llms": 6,
    "signals": 0,
    "ai_discovery": 3,
    "negative_penalty": -6,
}


def scenarios() -> dict[str, dict[str, Any]]:
    """Name -> keyword arguments for ``build_recommendations``."""
    worst = worst_case_inputs()
    return {
        "minimal_static": minimal_inputs(),
        "mixed_static": mixed_inputs(),
        "worst_static": worst,
        "worst_v1_breakdown": {**worst_case_inputs(), "score_breakdown": BREAKDOWN_V1, "category_max": CATEGORY_MAX},
        "worst_v2_breakdown": {
            **worst_case_inputs(),
            "score_breakdown": BREAKDOWN_V2,
            "category_max": CATEGORY_MAX_V2,
        },
        "ugc_advisory_static": ugc_advisory_inputs(),
        "ugc_advisory_v2_breakdown": {
            **ugc_advisory_inputs(),
            "score_breakdown": BREAKDOWN_V2,
            "category_max": CATEGORY_MAX_V2,
        },
        "mixed_v2_breakdown": {**mixed_inputs(), "score_breakdown": BREAKDOWN_V2, "category_max": CATEGORY_MAX_V2},
    }


# ─── Full-audit scenarios (real build path, mocked network) ──────────────────

# Bare page: no <title>, no meta description, no canonical, no lang, no H1, no schema.
BARE_HTML = "<html><head></head><body><p>Hello.</p></body></html>"


def _bare_home_response(url: str = BASE_URL) -> Mock:
    return Mock(status_code=200, text=BARE_HTML, content=BARE_HTML.encode(), headers={}, url=url)


def run_all_failing_sync(score_version: int) -> AuditResult:
    """``run_full_audit`` against a bare homepage with every companion file missing."""
    home = _bare_home_response()

    def _fetch(url: str, *args: Any, **kwargs: Any):
        return (home, None) if url == BASE_URL else (None, "Not found")

    with (
        patch("geo_optimizer.core.audit.fetch_url", side_effect=_fetch),
        patch("geo_optimizer.core.audit.check_markdown_negotiation", return_value=False),
        patch("geo_optimizer.core.audit.audit_cdn_ai_crawler", return_value=CdnAiCrawlerResult()),
    ):
        return run_full_audit(BASE_URL, score_version=score_version)


def run_all_failing_async(score_version: int) -> AuditResult:
    """``run_full_audit_async`` against the same bare homepage."""
    responses = {BASE_URL: (_bare_home_response(), None)}
    with (
        patch("geo_optimizer.utils.http_async.fetch_urls_async", new=AsyncMock(return_value=responses)),
        patch("geo_optimizer.core.audit.check_markdown_negotiation_async", new=AsyncMock(return_value=False)),
        patch("geo_optimizer.core.audit.asyncio.to_thread", new=AsyncMock(return_value=CdnAiCrawlerResult())),
    ):
        return asyncio.run(run_full_audit_async(BASE_URL, score_version=score_version))


def build_result_with_cdn_and_js(score_version: int = 2) -> AuditResult:
    """``_build_audit_result`` with a CDN block and a JS-dependent page (both appended after the builder)."""
    return _build_audit_result(
        BASE_URL,
        RobotsResult(),
        LlmsTxtResult(),
        SchemaResult(),
        MetaResult(),
        ContentResult(),
        http_status=200,
        page_size=100,
        cdn_check=CdnAiCrawlerResult(
            checked=True,
            any_blocked=True,
            cdn_detected="cloudflare",
            bot_results=[{"bot": "GPTBot", "blocked": True, "challenge_detected": False}],
        ),
        js_rendering=JsRenderingResult(checked=True, js_dependent=True, raw_word_count=12),
        score_version=score_version,
    )


def full_audit_scenarios() -> dict[str, AuditResult]:
    """Name -> AuditResult produced by the real orchestration code."""
    return {
        "full_sync_all_failing_v2": run_all_failing_sync(2),
        "full_sync_all_failing_v1": run_all_failing_sync(1),
        "full_async_all_failing_v2": run_all_failing_async(2),
        "build_result_cdn_js_v2": build_result_with_cdn_and_js(2),
        "build_result_cdn_js_v1": build_result_with_cdn_and_js(1),
    }
