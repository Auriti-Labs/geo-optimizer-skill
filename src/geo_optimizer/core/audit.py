"""
GEO Audit business logic.

Extracted from scripts/geo_audit.py. All functions return dataclasses
instead of printing — the CLI layer handles display and formatting.
"""

from __future__ import annotations

import asyncio
import logging
import time
from urllib.parse import urljoin

# ─── Re-exports from split modules (backward compatibility, #402) ────────────
from geo_optimizer.core.audit_ai_discovery import (
    _audit_ai_discovery_from_responses,
    audit_ai_discovery,  # noqa: F401
)
from geo_optimizer.core.audit_brand import audit_brand_entity  # noqa: F401
from geo_optimizer.core.audit_cdn import audit_cdn_ai_crawler  # noqa: F401
from geo_optimizer.core.audit_content import audit_content_quality  # noqa: F401
from geo_optimizer.core.audit_js import audit_js_rendering  # noqa: F401
from geo_optimizer.core.audit_llms import (
    _audit_llms_from_response,
    _validate_llms_content,  # noqa: F401
    audit_llms_txt,  # noqa: F401
)
from geo_optimizer.core.audit_meta import audit_meta_tags  # noqa: F401
from geo_optimizer.core.audit_negative import audit_negative_signals  # noqa: F401
from geo_optimizer.core.audit_robots import (
    _audit_robots_from_response,
    audit_robots_txt,  # noqa: F401
)
from geo_optimizer.core.audit_schema import audit_schema  # noqa: F401
from geo_optimizer.core.audit_signals import audit_signals  # noqa: F401
from geo_optimizer.core.audit_webmcp import _extract_actions, audit_webmcp_readiness  # noqa: F401
from geo_optimizer.core.scoring import (  # noqa: F401 (re-exported for backward compatibility)
    compute_geo_score,
    compute_score_breakdown,
    get_score_band,
)
from geo_optimizer.models.config import (  # noqa: F401 (VALUABLE_SCHEMAS re-exported)
    ABOUT_LINK_PATTERNS,
    AI_BOTS,
    AUDIT_TIMEOUT_SECONDS,
    CITATION_BOTS,
    CONTENT_MIN_WORDS,
    KEYWORD_STUFFING_THRESHOLD,
    SCORE_BANDS,
    SCORING,
    VALUABLE_SCHEMAS,
)
from geo_optimizer.models.results import (
    AiDiscoveryResult,
    AuditResult,
    BrandEntityResult,
    CachedResponse,
    CdnAiCrawlerResult,
    CitabilityResult,
    ContentResult,
    JsRenderingResult,
    LlmsTxtResult,
    MetaResult,
    NegativeSignalsResult,
    RobotsResult,
    SchemaResult,
    SignalsResult,
    WebMcpResult,
)
from geo_optimizer.utils.http import fetch_url


def build_recommendations(
    base_url,
    robots,
    llms,
    schema,
    meta,
    content,
    ai_discovery=None,
    signals=None,
    brand_entity=None,
    webmcp=None,
    negative_signals=None,
    prompt_injection=None,
) -> list:
    """Build a prioritized list of recommendations based on audit results."""
    recommendations = []

    # Fix #453: split robots recommendation — create vs update
    if not robots.found:
        recommendations.append("Create robots.txt with Allow rules for AI bots (GPTBot, ClaudeBot, PerplexityBot)")
    elif not robots.citation_bots_ok:
        recommendations.append("Update robots.txt to include all AI bots (GPTBot, ClaudeBot, PerplexityBot)")
    if not llms.found:
        recommendations.append(
            f"Create /llms.txt for AI indexing: geo llms --base-url {base_url}. "
            "Note: llms.txt is an organizational signal, not a proven ranking factor. "
            "It helps structure content for AI systems."
        )
    elif llms.found:
        # #247: llms.txt Policy Intelligence — recommendations on content quality
        if llms.sections_count == 0:
            recommendations.append(
                "Add H2 sections to llms.txt to organize content by topic (e.g. ## Features, ## Documentation, ## API)"
            )
        if llms.links_count < 3:
            recommendations.append(
                f"llms.txt has only {llms.links_count} links. "
                "Add more markdown links to key pages for better AI indexing coverage."
            )
        # #39: add validation warnings to recommendations
        if hasattr(llms, "validation_warnings"):
            for warning in llms.validation_warnings:
                recommendations.append(warning)
    # Fix #399: report JSON-LD parse errors
    if schema.json_parse_errors > 0:
        recommendations.append(
            f"Found {schema.json_parse_errors} JSON-LD script(s) with parse errors — validate at schema.org/validator"
        )
    if not schema.has_website:
        recommendations.append("Add WebSite JSON-LD schema to homepage")
    if not schema.has_faq:
        recommendations.append("Add FAQPage schema with site FAQs")
    # Fix #453: missing recommendations for key SCORING signals
    if not schema.has_organization:
        recommendations.append("Add Organization JSON-LD schema with name, url, and logo")
    if not meta.has_title:
        recommendations.append("Add a <title> tag — the strongest on-page signal for AI search (5 pts)")
    if not meta.has_description:
        recommendations.append("Add optimized meta description (150-160 characters)")
    if not meta.has_canonical:
        recommendations.append('Add <link rel="canonical"> to prevent duplicate content issues in AI indexing')
    if not meta.has_og_title or not meta.has_og_description:
        recommendations.append("Add Open Graph tags (og:title, og:description, og:image) for AI and social previews")
    if not content.has_h1:
        recommendations.append("Add a single H1 heading that clearly states the page topic")
    if content.word_count < 300:
        recommendations.append("Expand content to 300+ words — AI engines need substance to cite")
    if not content.has_numbers:
        recommendations.append("Add numerical data and concrete statistics (+40% AI visibility)")
    if not content.has_links:
        recommendations.append("Cite authoritative sources with external links (increase AI credibility)")
    if hasattr(content, "has_heading_hierarchy") and not content.has_heading_hierarchy:
        recommendations.append("Add H2/H3 subheadings to structure content for AI extraction")
    if hasattr(content, "has_front_loading") and not content.has_front_loading:
        recommendations.append("Front-load key information in the first 30% of content for AI snippet selection")

    # Fix #453: lang attribute recommendation (3 pts)
    if signals is not None and not signals.has_lang:
        recommendations.append('Add lang attribute to <html> tag (e.g., lang="en") for AI language detection')

    # #263: Machine-Readable Presence recommendations (RSS + sitemap)
    if signals is not None and not signals.has_rss:
        recommendations.append(
            "Add RSS/Atom feed and link it in <head> with "
            '<link rel="alternate" type="application/rss+xml"> for AI discovery'
        )

    # AI discovery recommendations (geo-checklist.dev)
    if ai_discovery is not None:
        if not ai_discovery.has_well_known_ai:
            recommendations.append("Create /.well-known/ai.txt to define AI crawler permissions")
        if not ai_discovery.has_summary or not ai_discovery.summary_valid:
            recommendations.append("Create /ai/summary.json with site name and description for AI engines")
        if not ai_discovery.has_faq:
            recommendations.append("Create /ai/faq.json with structured FAQ for AI search visibility")
        if not ai_discovery.has_service:
            recommendations.append("Create /ai/service.json to describe service capabilities for AI")

    # #232: E-commerce recommendation when Product schema is incomplete
    if schema.has_product and hasattr(schema, "ecommerce_signals"):
        signals_dict = schema.ecommerce_signals
        missing_fields = [k for k, v in signals_dict.items() if not v and k != "complete"]
        if missing_fields:
            recommendations.append(
                f"Complete Product schema: missing {', '.join(missing_fields)}. "
                "Rich Product schema improves AI shopping visibility."
            )

    # Brand & Entity recommendations (v4.3)
    if brand_entity is not None:
        if not brand_entity.brand_name_consistent and len(brand_entity.names_found) >= 2:
            recommendations.append("Use consistent brand name across title, og:title, H1, and schema Organization")
        if brand_entity.kg_pillar_count == 0:
            recommendations.append(
                "Add sameAs links in Organization schema to Wikipedia, Wikidata, LinkedIn, or Crunchbase "
                "for Knowledge Graph disambiguation"
            )
        elif brand_entity.kg_pillar_count < 3:
            recommendations.append(
                f"Add more sameAs links to Knowledge Graph pillars "
                f"(currently {brand_entity.kg_pillar_count}/4: Wikipedia, Wikidata, LinkedIn, Crunchbase)"
            )
        if not brand_entity.has_about_link:
            recommendations.append("Add a visible /about or /chi-siamo link to build trust signals for AI")
        if not brand_entity.has_contact_info:
            recommendations.append(
                "Add address, telephone or contactPoint to Organization schema for entity validation"
            )

    # WebMCP recommendations (#233)
    if webmcp is not None and webmcp.checked:
        if webmcp.readiness_level == "none":
            recommendations.append("Add potentialAction (SearchAction) to WebSite schema for AI agent discoverability")
        if not webmcp.has_labeled_forms and not webmcp.has_tool_attributes:
            recommendations.append(
                "Add descriptive labels to forms (label, aria-label) to make them usable by AI agents"
            )
        if not webmcp.has_register_tool and not webmcp.has_tool_attributes:
            recommendations.append(
                "Consider adding WebMCP toolname/tooldescription attributes to interactive elements "
                "for Chrome AI agent support"
            )

    # Negative Signals recommendations (v4.3)
    if negative_signals is not None and negative_signals.checked:
        if negative_signals.cta_density_high:
            recommendations.append(
                f"Reduce promotional CTAs ({negative_signals.cta_count} found) "
                "— AI engines deprioritize overly promotional content"
            )
        if negative_signals.is_thin_content:
            recommendations.append(
                "Content is thin for the topic promised by H1 — expand to 500+ words for AI citation eligibility"
            )
        if negative_signals.has_keyword_stuffing:
            recommendations.append(
                f"Keyword stuffing detected: '{negative_signals.stuffed_word}' "
                f"at {negative_signals.stuffed_density}% density — diversify vocabulary"
            )
        if negative_signals.boilerplate_high:
            recommendations.append(
                f"High boilerplate ratio ({int(negative_signals.boilerplate_ratio * 100)}%) "
                "— use <main> tag to help AI extract core content"
            )
        if negative_signals.has_mixed_signals:
            recommendations.append(f"Mixed signals: {negative_signals.mixed_signal_detail}")

    # v4.4: Prompt Injection raccomandazioni (#276)
    if prompt_injection is not None and prompt_injection.checked and prompt_injection.severity != "clean":
        if prompt_injection.llm_instruction_found:
            recommendations.append(
                "⚠️ CRITICAL: LLM prompt instructions detected in page content — "
                "this is a manipulation pattern that AI engines actively penalize"
            )
        if prompt_injection.html_comment_injection_found:
            recommendations.append(
                "⚠️ Prompt injection in HTML comments detected — AI crawlers read comments, remove them"
            )
        if prompt_injection.hidden_text_found:
            recommendations.append(
                "Hidden text detected (display:none/visibility:hidden with content) — "
                "AI crawlers can read it and may penalize this cloaking pattern"
            )

    return recommendations


def _build_audit_result(
    base_url: str,
    robots: RobotsResult,
    llms: LlmsTxtResult,
    schema: SchemaResult,
    meta: MetaResult,
    content: ContentResult,
    http_status: int,
    page_size: int,
    soup=None,
    soup_clean=None,  # Fix #285: pre-cleaned soup (without script/style) to avoid re-parsing
    extra_checks: dict = None,
    signals: SignalsResult = None,  # v4.0: segnali tecnici
    ai_discovery=None,  # Standard AI discovery endpoints (.well-known/ai.txt, ecc.)
    cdn_check=None,  # v4.2: CDN AI Crawler check (#225)
    js_rendering=None,  # v4.2: JS Rendering check (#226)
    brand_entity=None,  # v4.3: Brand & Entity signals
    webmcp=None,  # v4.3: WebMCP Readiness check (#233)
    negative_signals=None,  # v4.3: Negative Signals detection
    prompt_injection=None,  # v4.4: Prompt Injection Detection (#276)
    trust_stack=None,  # v4.5: Trust Stack Score (#273)
    rag_chunk=None,  # v4.7: RAG Chunk Readiness (#353)
) -> AuditResult:
    """Build AuditResult from sub-audits (fix #97: shared sync/async logic).

    Computes score, band and recommendations, then runs plugins registered
    in CheckRegistry (fix #104). Plugin results do not affect the base score.

    Args:
        base_url: Normalized site URL.
        robots: robots.txt audit result.
        llms: llms.txt audit result.
        schema: JSON-LD schema audit result.
        meta: Meta tag audit result.
        content: Content audit result.
        http_status: HTTP status code of the homepage.
        page_size: Homepage size in bytes.
        soup: BeautifulSoup of the homepage (optional, passed to plugins).
        extra_checks: Dict with pre-computed results (not used internally).
        signals: Technical signals v4.0 (lang, RSS, freshness).

    Returns:
        Complete AuditResult with score, band, recommendations and plugins.
    """
    from geo_optimizer.core.registry import CheckRegistry

    # Use empty SignalsResult if not provided
    effective_signals = signals if signals is not None else SignalsResult()

    # Use empty AiDiscoveryResult if not provided

    effective_ai_discovery = ai_discovery if ai_discovery is not None else AiDiscoveryResult()

    # v4.3: use empty BrandEntityResult if not provided
    effective_brand_entity = brand_entity if brand_entity is not None else BrandEntityResult()

    # v4.3: use empty WebMcpResult if not provided (#233)
    effective_webmcp = webmcp if webmcp is not None else WebMcpResult()

    # v4.3: use empty NegativeSignalsResult if not provided
    effective_negative_signals = negative_signals if negative_signals is not None else NegativeSignalsResult()

    # v4.4: use empty PromptInjectionResult if not provided (#276)
    from geo_optimizer.models.results import PromptInjectionResult

    effective_prompt_injection = prompt_injection if prompt_injection is not None else PromptInjectionResult()

    # v4.5: use empty TrustStackResult if not provided (#273)
    from geo_optimizer.models.results import TrustStackResult

    effective_trust_stack = trust_stack if trust_stack is not None else TrustStackResult()

    # v4.7: RAG Chunk Readiness (#353) — compute if not pre-computed
    if rag_chunk is not None:
        effective_rag_chunk = rag_chunk
    elif soup is not None:
        from geo_optimizer.core.audit_rag import audit_rag_readiness

        effective_rag_chunk = audit_rag_readiness(soup, soup_clean)
    else:
        from geo_optimizer.models.results import RagChunkResult

        effective_rag_chunk = RagChunkResult()

    # Compute score, breakdown, and band (v4.0: includes signals, ai_discovery)
    score = compute_geo_score(
        robots, llms, schema, meta, content, effective_signals, effective_ai_discovery, effective_brand_entity
    )
    breakdown = compute_score_breakdown(
        robots, llms, schema, meta, content, effective_signals, effective_ai_discovery, effective_brand_entity
    )
    band = get_score_band(score)

    # Recommendations
    recommendations = build_recommendations(
        base_url,
        robots,
        llms,
        schema,
        meta,
        content,
        effective_ai_discovery,
        effective_signals,
        effective_brand_entity,
        effective_webmcp,
        effective_negative_signals,
        effective_prompt_injection,
    )

    # Fix #460: load entry_point plugins if not already loaded (API + MCP callers)
    CheckRegistry.load_entry_points()

    # Fix #104: run plugins registered in CheckRegistry
    # Their results do not affect the base score
    plugin_results = {}
    if CheckRegistry.all():
        check_results = CheckRegistry.run_all(base_url, soup=soup)
        plugin_results = {
            r.name: {
                "score": r.score,
                "max_score": r.max_score,
                "passed": r.passed,
                "message": r.message,
                "details": r.details,
            }
            for r in check_results
        }

    # Citability Score: content analysis with 47 methods (fix #31)
    # Fix #285: pass pre-computed soup_clean to avoid re-parsing in citability
    from geo_optimizer.core.citability import audit_citability

    citability = audit_citability(soup, base_url, soup_clean=soup_clean) if soup else CitabilityResult()

    # v4.2: CDN + JS rendering checks (#225, #226)
    effective_cdn = cdn_check if cdn_check is not None else CdnAiCrawlerResult()
    effective_js = js_rendering if js_rendering is not None else JsRenderingResult()

    # Add CDN/JS warnings to recommendations
    if effective_cdn.checked and effective_cdn.any_blocked:
        blocked_bots = [b["bot"] for b in effective_cdn.bot_results if b["blocked"] or b["challenge_detected"]]
        cdn_name = effective_cdn.cdn_detected or "CDN/WAF"
        recommendations.append(
            f"⚠️ {cdn_name.upper()} blocks AI crawlers: {', '.join(blocked_bots)}. "
            "Configure your CDN to allow AI bot User-Agents (GPTBot, ClaudeBot, PerplexityBot)."
        )

    if effective_js.checked and effective_js.js_dependent:
        recommendations.append(
            f"⚠️ Content requires JavaScript to render ({effective_js.raw_word_count} words in raw HTML). "
            "AI crawlers don't execute JS. Implement SSR, SSG, or pre-rendering."
        )

    return AuditResult(
        url=base_url,
        score=score,
        band=band,
        robots=robots,
        llms=llms,
        schema=schema,
        meta=meta,
        content=content,
        citability=citability,
        recommendations=recommendations,
        http_status=http_status,
        page_size=page_size,
        extra_checks=plugin_results,
        signals=effective_signals,
        ai_discovery=effective_ai_discovery,
        score_breakdown=breakdown,
        cdn_check=effective_cdn,
        js_rendering=effective_js,
        brand_entity=effective_brand_entity,
        webmcp=effective_webmcp,
        negative_signals=effective_negative_signals,
        prompt_injection=effective_prompt_injection,
        trust_stack=effective_trust_stack,
        rag_chunk=effective_rag_chunk,
    )


def run_full_audit(url: str, use_cache: bool = False, project_config=None) -> AuditResult:
    """Run complete audit and return AuditResult with all sub-results, score, band, and recommendations.

    Args:
        url: URL of the site to analyze.
        use_cache: If True, use disk cache for HTTP requests.
        project_config: Optional ProjectConfig — if it has extra_bots, merges them with AI_BOTS (fix #120).
    """
    _t0 = time.perf_counter()
    from bs4 import BeautifulSoup

    # Fix #120: if config has extra_bots, merge with AI_BOTS for this audit
    effective_bots = dict(AI_BOTS)
    if project_config is not None and project_config.extra_bots:
        effective_bots.update(project_config.extra_bots)

    # Normalize URL
    base_url = url.rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url

    # Fetch homepage (with optional cache)
    if use_cache:
        from geo_optimizer.utils.cache import FileCache

        cache = FileCache()
        cached = cache.get(base_url)
        if cached:
            # Build response-like object from cache (fix #83: use dataclass)
            status_code, text, headers = cached
            r = CachedResponse(
                status_code=status_code,
                text=text,
                content=text.encode("utf-8"),
                headers=headers,
            )
            err = None
        else:
            r, err = fetch_url(base_url)
            if r and not err:
                cache.put(base_url, r.status_code, r.text, dict(r.headers))
    else:
        r, err = fetch_url(base_url)
    if err or not r:
        result = AuditResult(
            url=base_url,
            error=str(err) if err else "Connection failed",
        )
        result.recommendations = [f"Unable to reach {base_url}: {err}"]
        result.audit_duration_ms = int((time.perf_counter() - _t0) * 1000)
        return result

    # Fix #337: if homepage returns HTTP error, report it and skip analysis of the error page
    if r.status_code not in (200, 203):
        result = AuditResult(
            url=base_url,
            http_status=r.status_code,
            error=f"HTTP {r.status_code}",
        )
        result.recommendations = [
            f"Site returned HTTP {r.status_code}. Check for Cloudflare/WAF blocks or server errors."
        ]
        result.audit_duration_ms = int((time.perf_counter() - _t0) * 1000)
        return result

    import copy

    soup = BeautifulSoup(r.text, "html.parser")

    # Fix #285: compute soup_clean once and pass it to all sub-audits
    # Avoids 3-4 re-parses of the same HTML (saves 50-200ms per page)
    soup_clean = copy.deepcopy(soup)
    for tag in soup_clean(["script", "style"]):
        tag.decompose()

    # Fetch robots.txt, llms.txt, llms-full.txt and AI discovery with local fetch_url
    # (identical pattern to the async version — allows mocking with patch on audit.fetch_url)
    robots_url_full = urljoin(base_url, "/robots.txt")
    llms_url_full = urljoin(base_url, "/llms.txt")
    llms_full_url = urljoin(base_url, "/llms-full.txt")
    ai_txt_url = urljoin(base_url, "/.well-known/ai.txt")
    ai_summary_url = urljoin(base_url, "/ai/summary.json")
    ai_faq_url = urljoin(base_url, "/ai/faq.json")
    ai_service_url = urljoin(base_url, "/ai/service.json")

    r_robots, _ = fetch_url(robots_url_full)
    r_llms, _ = fetch_url(llms_url_full)
    r_llms_full, _ = fetch_url(llms_full_url)
    r_ai_txt, _ = fetch_url(ai_txt_url)
    r_ai_summary, _ = fetch_url(ai_summary_url)
    r_ai_faq, _ = fetch_url(ai_faq_url)
    r_ai_service, _ = fetch_url(ai_service_url)

    # Run all sub-audits using the pre-downloaded responses
    # Fix #120: pass effective_bots which includes any extra_bots from project_config
    robots = _audit_robots_from_response(r_robots, bots=effective_bots)
    llms = _audit_llms_from_response(r_llms, r_full=r_llms_full)
    schema = audit_schema(soup, base_url)
    meta = audit_meta_tags(soup, base_url)
    content = audit_content_quality(soup, base_url, soup_clean=soup_clean)

    # v4.1: AI discovery endpoints audit (usa risposte pre-scaricate)
    ai_disc = _audit_ai_discovery_from_responses(r_ai_txt, r_ai_summary, r_ai_faq, r_ai_service)

    # v4.2: CDN AI Crawler check (#225) + JS Rendering check (#226)
    cdn_result = audit_cdn_ai_crawler(base_url)
    js_result = audit_js_rendering(soup, r.text)

    # Fix #281: compute technical signals (lang, RSS, freshness)
    signals = audit_signals(soup, schema)

    # v4.3: Brand & Entity signals (zero HTTP requests, uses pre-fetched data only)
    brand_entity_result = audit_brand_entity(soup, schema, meta, content)

    # v4.3: WebMCP Readiness check (#233) — zero HTTP fetch
    webmcp_result = audit_webmcp_readiness(soup, r.text, schema)

    # v4.3: Negative Signals detection — zero HTTP fetch
    negative_signals_result = audit_negative_signals(soup, r.text, content, meta, schema)

    # v4.4: Prompt Injection Pattern Detection (#276) — zero HTTP fetch
    from geo_optimizer.core.injection_detector import audit_prompt_injection

    prompt_injection_result = audit_prompt_injection(soup, r.text)

    # v4.5: Trust Stack Score (#273) — 5-layer aggregation, zero HTTP fetch
    from geo_optimizer.core.trust_stack import audit_trust_stack

    try:
        resp_headers = dict(r.headers)
    except (TypeError, AttributeError):
        resp_headers = {}
    trust_stack_result = audit_trust_stack(
        soup=soup,
        base_url=base_url,
        response_headers=resp_headers,
        brand_entity=brand_entity_result,
        schema=schema,
        meta=meta,
        content=content,
        negative_signals=negative_signals_result,
    )

    # Fix #97 + #104: use _build_audit_result for shared logic and plugin integration
    result = _build_audit_result(
        base_url=base_url,
        robots=robots,
        llms=llms,
        schema=schema,
        meta=meta,
        content=content,
        http_status=r.status_code,
        page_size=len(r.text),
        soup=soup,
        soup_clean=soup_clean,
        ai_discovery=ai_disc,
        cdn_check=cdn_result,
        js_rendering=js_result,
        signals=signals,
        brand_entity=brand_entity_result,
        webmcp=webmcp_result,
        negative_signals=negative_signals_result,
        prompt_injection=prompt_injection_result,
        trust_stack=trust_stack_result,
    )
    result.audit_duration_ms = int((time.perf_counter() - _t0) * 1000)
    if result.audit_duration_ms > AUDIT_TIMEOUT_SECONDS * 1000:
        logging.getLogger(__name__).warning(
            "Audit exceeded %ds budget: %dms for %s", AUDIT_TIMEOUT_SECONDS, result.audit_duration_ms, base_url
        )
    return result


async def run_full_audit_async(url: str, project_config=None) -> AuditResult:
    """Async variant of the full audit with parallel fetch (httpx).

    Runs homepage, robots.txt and llms.txt in parallel for a
    2-3x speedup compared to the synchronous version.

    Args:
        url: URL of the site to analyze.
        project_config: Optional ProjectConfig — if it has extra_bots, merges them with AI_BOTS.

    Requires: pip install geo-optimizer-skill[async]
    """
    _t0 = time.perf_counter()
    from bs4 import BeautifulSoup

    from geo_optimizer.utils.http_async import fetch_urls_async

    # Merge extra_bots from config, same as in the synchronous version
    effective_bots = dict(AI_BOTS)
    if project_config is not None and project_config.extra_bots:
        effective_bots.update(project_config.extra_bots)

    # Normalize URL
    base_url = url.rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url

    # Parallel fetch: homepage + robots.txt + llms.txt + llms-full.txt + AI discovery
    robots_url = urljoin(base_url, "/robots.txt")
    llms_url = urljoin(base_url, "/llms.txt")
    llms_full_url = urljoin(base_url, "/llms-full.txt")
    # v4.1: AI discovery endpoints (geo-checklist.dev)
    ai_txt_url = urljoin(base_url, "/.well-known/ai.txt")
    ai_summary_url = urljoin(base_url, "/ai/summary.json")
    ai_faq_url = urljoin(base_url, "/ai/faq.json")
    ai_service_url = urljoin(base_url, "/ai/service.json")

    responses = await fetch_urls_async(
        [
            base_url,
            robots_url,
            llms_url,
            llms_full_url,
            ai_txt_url,
            ai_summary_url,
            ai_faq_url,
            ai_service_url,
        ]
    )

    # Extract responses
    r_home, err_home = responses.get(base_url, (None, "URL not requested"))
    r_robots, _ = responses.get(robots_url, (None, None))
    r_llms, _ = responses.get(llms_url, (None, None))
    r_llms_full, _ = responses.get(llms_full_url, (None, None))
    # AI discovery responses
    r_ai_txt, _ = responses.get(ai_txt_url, (None, None))
    r_ai_summary, _ = responses.get(ai_summary_url, (None, None))
    r_ai_faq, _ = responses.get(ai_faq_url, (None, None))
    r_ai_service, _ = responses.get(ai_service_url, (None, None))

    if err_home or not r_home:
        result = AuditResult(
            url=base_url,
            error=str(err_home) if err_home else "Connection failed",
        )
        result.recommendations = [f"Unable to reach {base_url}: {err_home}"]
        result.audit_duration_ms = int((time.perf_counter() - _t0) * 1000)
        return result

    # Fix #337: if homepage returns HTTP error, report it and skip analysis of the error page
    if r_home.status_code not in (200, 203):
        result = AuditResult(
            url=base_url,
            http_status=r_home.status_code,
            error=f"HTTP {r_home.status_code}",
        )
        result.recommendations = [
            f"Site returned HTTP {r_home.status_code}. Check for Cloudflare/WAF blocks or server errors."
        ]
        result.audit_duration_ms = int((time.perf_counter() - _t0) * 1000)
        return result

    import copy

    soup = BeautifulSoup(r_home.text, "html.parser")

    # Fix #285: compute soup_clean once for the async path
    soup_clean = copy.deepcopy(soup)
    for tag in soup_clean(["script", "style"]):
        tag.decompose()

    # Sub-audit robots.txt (uses pre-fetched response with extra_bots)
    robots = _audit_robots_from_response(r_robots, bots=effective_bots)

    # Sub-audit llms.txt (uses pre-fetched response)
    llms = _audit_llms_from_response(r_llms, r_full=r_llms_full)

    # Sub-audits that work on the DOM (no additional fetch required)
    schema = audit_schema(soup, base_url)
    meta = audit_meta_tags(soup, base_url)
    content = audit_content_quality(soup, base_url, soup_clean=soup_clean)

    # v4.1: AI discovery from pre-fetched responses
    ai_disc = _audit_ai_discovery_from_responses(r_ai_txt, r_ai_summary, r_ai_faq, r_ai_service)

    # v4.2: CDN AI Crawler check (#225) + JS Rendering check (#226)
    # Fix: wrap synchronous calls with asyncio.to_thread to avoid blocking the event loop
    cdn_result = await asyncio.to_thread(audit_cdn_ai_crawler, base_url)
    js_result = audit_js_rendering(soup, r_home.text)

    # Fix #281: compute technical signals (lang, RSS, freshness)
    signals = audit_signals(soup, schema)

    # v4.3: Brand & Entity signals (zero HTTP requests, uses pre-fetched data only)
    brand_entity_result = audit_brand_entity(soup, schema, meta, content)

    # v4.3: WebMCP Readiness check (#233) — zero HTTP fetch
    webmcp_result = audit_webmcp_readiness(soup, r_home.text, schema)

    # v4.3: Negative Signals detection — zero HTTP fetch
    negative_signals_result = audit_negative_signals(soup, r_home.text, content, meta, schema)

    # v4.4: Prompt Injection Pattern Detection (#276) — zero HTTP fetch
    from geo_optimizer.core.injection_detector import audit_prompt_injection

    prompt_injection_result = audit_prompt_injection(soup, r_home.text)

    # v4.5: Trust Stack Score (#273) — 5-layer aggregation, zero HTTP fetch
    from geo_optimizer.core.trust_stack import audit_trust_stack

    try:
        resp_headers_async = dict(r_home.headers)
    except (TypeError, AttributeError):
        resp_headers_async = {}
    trust_stack_result = audit_trust_stack(
        soup=soup,
        base_url=base_url,
        response_headers=resp_headers_async,
        brand_entity=brand_entity_result,
        schema=schema,
        meta=meta,
        content=content,
        negative_signals=negative_signals_result,
    )

    # Fix #97 + #104: use _build_audit_result for shared logic and plugin integration
    result = _build_audit_result(
        base_url=base_url,
        robots=robots,
        llms=llms,
        schema=schema,
        meta=meta,
        content=content,
        http_status=r_home.status_code,
        page_size=len(r_home.text),
        soup=soup,
        soup_clean=soup_clean,
        ai_discovery=ai_disc,
        cdn_check=cdn_result,
        js_rendering=js_result,
        signals=signals,
        brand_entity=brand_entity_result,
        webmcp=webmcp_result,
        negative_signals=negative_signals_result,
        prompt_injection=prompt_injection_result,
        trust_stack=trust_stack_result,
    )
    result.audit_duration_ms = int((time.perf_counter() - _t0) * 1000)
    if result.audit_duration_ms > AUDIT_TIMEOUT_SECONDS * 1000:
        logging.getLogger(__name__).warning(
            "Audit exceeded %ds budget: %dms for %s", AUDIT_TIMEOUT_SECONDS, result.audit_duration_ms, base_url
        )
    return result
