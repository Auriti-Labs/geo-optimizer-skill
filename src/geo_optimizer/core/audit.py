"""
GEO Audit business logic.

Extracted from scripts/geo_audit.py. All functions return dataclasses
instead of printing — the CLI layer handles display and formatting.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from urllib.parse import urljoin, urlparse

from geo_optimizer.core.scoring import (  # noqa: F401 (re-esportato per retrocompatibilità)
    compute_geo_score,
    compute_score_breakdown,
    get_score_band,
)
from geo_optimizer.models.config import (  # noqa: F401 (VALUABLE_SCHEMAS re-exported)
    AI_BOTS,
    CITATION_BOTS,
    CONTENT_MIN_WORDS,
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
from geo_optimizer.utils.robots_parser import classify_bot, parse_robots_txt


def audit_robots_txt(base_url: str, bots: dict = None) -> RobotsResult:
    """Check robots.txt for AI bot access. Returns RobotsResult.

    Args:
        base_url: Base URL of the site.
        bots: Dictionary of bots to check. Default: AI_BOTS from config.
              Fix #120: allows passing extra bots from project_config.extra_bots.
    """
    robots_url = urljoin(base_url, "/robots.txt")
    r, err = fetch_url(robots_url)

    result = RobotsResult()

    if err or not r:
        return result

    # Only 200 responses are valid robots.txt (403, 500, etc. are not)
    if r.status_code != 200:
        return result

    result.found = True

    content = r.text

    # Parse robots.txt into structured rules
    agent_rules = parse_robots_txt(content)

    # Use provided bots or default AI_BOTS
    effective_bots = bots if bots is not None else AI_BOTS

    # Classify each AI bot
    for bot, description in effective_bots.items():
        bot_status = classify_bot(bot, description, agent_rules)

        if bot_status.status == "missing":
            result.bots_missing.append(bot)
        elif bot_status.status == "blocked":
            result.bots_blocked.append(bot)
        elif bot_status.status == "partial":
            # #106 — Partially blocked: treated as allowed for compatibility
            # but tracked separately in bots_partial
            result.bots_allowed.append(bot)
            result.bots_partial.append(bot)
        else:
            # "allowed" (fully permitted)
            result.bots_allowed.append(bot)

    # Check citation bots (allowed also includes partial)
    result.citation_bots_ok = all(b in result.bots_allowed for b in CITATION_BOTS)

    # #111 — Verify that citation bots are EXPLICITLY allowed (not only via wildcard)
    # Full score only with specific rules for citation bots
    citation_explicit = []
    for bot in CITATION_BOTS:
        bot_status = classify_bot(bot, "", agent_rules)
        if bot_status.status in ("allowed", "partial") and not bot_status.via_wildcard:
            citation_explicit.append(bot)
    result.citation_bots_explicit = len(citation_explicit) == len(CITATION_BOTS)

    return result


def _validate_llms_content(result: LlmsTxtResult, content: str) -> None:
    """Validate llms.txt content against spec v2 and populate result fields.

    Popola has_blockquote, has_optional_section, companion_files_hint
    e validation_warnings sul result passato.

    Args:
        result: LlmsTxtResult già inizializzato con i campi base.
        content: Contenuto testuale del file llms.txt (già senza BOM).
    """
    lines = content.splitlines()
    warnings: list[str] = []

    # Validazione blockquote (> description) — REQUIRED per spec
    blockquotes = [line for line in lines if line.startswith("> ")]
    if blockquotes:
        result.has_blockquote = True
    else:
        warnings.append("llms.txt should have a > blockquote description after H1")

    # Validazione H1 come prima riga non vuota
    non_empty_lines = [line for line in lines if line.strip()]
    if non_empty_lines and not non_empty_lines[0].startswith("# "):
        warnings.append("H1 should be the first line of llms.txt")

    # Validazione link markdown
    if not result.has_links:
        warnings.append("llms.txt should contain markdown links to site pages")

    # Validazione lunghezza minima
    if result.word_count < 100:
        warnings.append("llms.txt is too short, consider adding more content")

    # Sezione ## Optional — buona pratica
    h2_lines = [line for line in lines if line.startswith("## ")]
    for h2 in h2_lines:
        if "optional" in h2.lower():
            result.has_optional_section = True
            break

    # Companion files: link a file .md (es. something.html.md)
    links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
    for _text, url in links:
        if url.endswith(".md"):
            result.companion_files_hint = True
            break

    result.validation_warnings = warnings


def audit_llms_txt(base_url: str) -> LlmsTxtResult:
    """Check for presence and quality of llms.txt. Returns LlmsTxtResult."""
    llms_url = urljoin(base_url, "/llms.txt")
    r, err = fetch_url(llms_url)

    result = LlmsTxtResult()

    if err or not r:
        return result

    # Only 200 responses contain a valid llms.txt
    if r.status_code != 200:
        return result

    result.found = True
    # Strip UTF-8 BOM if present (e.g. files generated by Yoast SEO)
    content = r.text.lstrip("\ufeff")
    lines = content.splitlines()
    result.word_count = len(content.split())

    # Check H1 (required)
    h1_lines = [line for line in lines if line.startswith("# ")]
    if h1_lines:
        result.has_h1 = True

    # Check blockquote description
    blockquotes = [line for line in lines if line.startswith("> ")]
    if blockquotes:
        # Fix #317: sincronizza has_description (alias retrocompatibile) con has_blockquote
        result.has_blockquote = True
        result.has_description = True

    # Check H2 sections
    h2_lines = [line for line in lines if line.startswith("## ")]
    if h2_lines:
        result.has_sections = True
    # #247: conta sezioni H2 per Policy Intelligence
    result.sections_count = len(h2_lines)

    # Check markdown links
    links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
    if links:
        result.has_links = True
    # #247: conta link per Policy Intelligence
    result.links_count = len(links)

    # #39: validazione v2 — conformità spec completa
    _validate_llms_content(result, content)

    # Check /llms-full.txt (llmstxt.org spec — optional extended version)
    full_url = urljoin(base_url, "/llms-full.txt")
    r_full, err_full = fetch_url(full_url)
    if r_full and r_full.status_code == 200 and len(r_full.text.strip()) > 0:
        result.has_full = True

    return result


def audit_schema(soup, url: str) -> SchemaResult:
    """Check JSON-LD schema on homepage. Returns SchemaResult."""
    result = SchemaResult()

    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    if not scripts:
        return result

    for script in scripts:
        try:
            # script.string can be None if the tag has multiple child nodes
            raw = script.string
            if not raw:
                raw = script.get_text()
            if not raw or not raw.strip():
                continue
            # Size limit: prevent DoS from oversized JSON-LD (fix #182)
            if len(raw) > 512 * 1024:
                logging.debug("JSON-LD too large (%d bytes), skipping", len(raw))
                continue
            data = json.loads(raw)
            # Fix: supporto formato @graph (usato da Yoast SEO, RankMath, ecc.)
            if isinstance(data, dict) and "@graph" in data:
                schemas = data["@graph"] if isinstance(data["@graph"], list) else [data["@graph"]]
            elif isinstance(data, list):
                schemas = data
            else:
                schemas = [data]

            for schema in schemas:
                schema_type = schema.get("@type", "unknown")
                if isinstance(schema_type, list):
                    schema_types = schema_type
                else:
                    schema_types = [schema_type]

                # Add the raw schema (cap at 50 to prevent memory bloat — fix #191)
                if len(result.raw_schemas) < 50:
                    result.raw_schemas.append(schema)

                for t in schema_types:
                    result.found_types.append(t)

                    if t == "WebSite":
                        result.has_website = True
                    elif t == "WebApplication":
                        result.has_webapp = True
                    elif t == "FAQPage":
                        result.has_faq = True
                    elif t in ("Article", "BlogPosting", "NewsArticle"):
                        result.has_article = True
                    elif t == "Organization":
                        result.has_organization = True
                    elif t == "HowTo":
                        result.has_howto = True
                    elif t in ("Person",):
                        result.has_person = True
                    elif t == "Product":
                        result.has_product = True

                    # Qualsiasi tipo schema valido (non unknown) contribuisce
                    if t != "unknown":
                        result.any_schema_found = True

                # Controlla la proprietà sameAs
                same_as = schema.get("sameAs", [])
                if isinstance(same_as, str):
                    same_as = [same_as]
                if same_as:
                    result.has_sameas = True
                    result.sameas_urls.extend(same_as[:10])  # limita a 10

                # Controlla dateModified
                if schema.get("dateModified"):
                    result.has_date_modified = True

        except json.JSONDecodeError as exc:
            # Parsing failed: log at debug (not critical, third-party scripts) — fix #81
            logging.debug("Invalid JSON schema ignored: %s", exc)

    # Schema richness (Growth Marshal Feb 2026): conta attributi per ogni schema
    # Schema generico (@type + name + url = 3 attributi) performa PEGGIO di nessuno schema
    # Schema ricco (5+ attributi) → 61.7% citation rate vs 41.6% generico
    _GENERIC_KEYS = {"@context", "@type", "@id"}
    attr_counts = []
    for schema_obj in result.raw_schemas:
        # Conta solo attributi rilevanti (esclusi @context, @type, @id)
        relevant_attrs = [k for k in schema_obj if k not in _GENERIC_KEYS]
        attr_counts.append(len(relevant_attrs))

    if attr_counts:
        result.avg_attributes_per_schema = round(sum(attr_counts) / len(attr_counts), 1)
        # Score: 0 se media < 3 (generico), 1 se 3-4, 3 se 5+ (ricco)
        avg = result.avg_attributes_per_schema
        if avg >= 5:
            result.schema_richness_score = 3
        elif avg >= 3:
            result.schema_richness_score = 1
        else:
            result.schema_richness_score = 0

    # #232: E-commerce GEO Profile — analizza ricchezza Product schema
    if result.has_product:
        for schema_obj in result.raw_schemas:
            schema_type = schema_obj.get("@type", "")
            types = schema_type if isinstance(schema_type, list) else [schema_type]
            if "Product" in types:
                offers = schema_obj.get("offers") or schema_obj.get("offer", {})
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                result.ecommerce_signals = {
                    "has_price": bool(offers.get("price") or offers.get("lowPrice")),
                    "has_availability": bool(offers.get("availability")),
                    "has_brand": bool(schema_obj.get("brand")),
                    "has_image": bool(schema_obj.get("image")),
                    "has_reviews": bool(schema_obj.get("aggregateRating") or schema_obj.get("review")),
                }
                result.ecommerce_signals["complete"] = all(
                    result.ecommerce_signals[k] for k in result.ecommerce_signals if k != "complete"
                )
                break

    return result


def audit_meta_tags(soup, url: str) -> MetaResult:
    """Check SEO/GEO meta tags. Returns MetaResult."""
    result = MetaResult()

    # Title
    title_tag = soup.find("title")
    if title_tag and title_tag.text.strip():
        result.has_title = True
        result.title_text = title_tag.text.strip()
        result.title_length = len(result.title_text)

    # Meta description
    desc = soup.find("meta", attrs={"name": "description"})
    if desc and desc.get("content", "").strip():
        result.has_description = True
        result.description_text = desc["content"].strip()
        result.description_length = len(result.description_text)

    # Canonical
    canonical = soup.find("link", attrs={"rel": "canonical"})
    if canonical and canonical.get("href"):
        result.has_canonical = True
        result.canonical_url = canonical["href"]

    # Open Graph
    og_title = soup.find("meta", attrs={"property": "og:title"})
    og_desc = soup.find("meta", attrs={"property": "og:description"})
    og_image = soup.find("meta", attrs={"property": "og:image"})

    if og_title and og_title.get("content"):
        result.has_og_title = True

    if og_desc and og_desc.get("content"):
        result.has_og_description = True

    if og_image and og_image.get("content"):
        result.has_og_image = True

    return result


def audit_content_quality(soup, url: str, soup_clean=None) -> ContentResult:
    """Check content quality for GEO. Returns ContentResult.

    Args:
        soup: BeautifulSoup dell'HTML originale.
        url: URL della pagina.
        soup_clean: (opzionale) BeautifulSoup già pulito (senza script/style).
                    Se fornito, evita il re-parse dell'HTML (fix #285).
    """
    import copy

    result = ContentResult()

    # H1
    h1 = soup.find("h1")
    if h1:
        result.has_h1 = True
        result.h1_text = h1.text.strip()

    # Headings
    headings = soup.find_all(["h1", "h2", "h3", "h4"])
    result.heading_count = len(headings)

    # Fix #285: usa soup_clean pre-calcolato se disponibile, altrimenti crea copia
    # Usa copy.deepcopy() invece di BS(str(soup)) per evitare re-parse costoso
    if soup_clean is None:
        soup_clean = copy.deepcopy(soup)
        for tag in soup_clean(["script", "style"]):
            tag.decompose()

    # Fix #107: separator=" " prevents word concatenation from adjacent tags
    # Example: <span>Hello</span><span>World</span> → "Hello World" instead of "HelloWorld"
    body_text = soup_clean.get_text(separator=" ", strip=True)
    numbers = re.findall(r"\b\d+[%\u20ac$\u00a3]|\b\d+\.\d+|\b\d{3,}\b", body_text)
    result.numbers_count = len(numbers)
    if len(numbers) >= 3:
        result.has_numbers = True

    # Word count
    words = body_text.split()
    result.word_count = len(words)

    # External links (citazioni)
    parsed = urlparse(url)
    base_domain = parsed.netloc
    all_links = soup.find_all("a", href=True)
    external_links = [link for link in all_links if link["href"].startswith("http") and base_domain not in link["href"]]
    result.external_links_count = len(external_links)
    if external_links:
        result.has_links = True

    # Gerarchia heading: H2 E H3 presenti
    h2_tags = soup_clean.find_all("h2")
    h3_tags = soup_clean.find_all("h3")
    if h2_tags and h3_tags:
        result.has_heading_hierarchy = True

    # Liste o tabelle
    lists = soup_clean.find_all(["ul", "ol", "table"])
    if lists:
        result.has_lists_or_tables = True

    # Front-loading: primo 30% del testo ha contenuto sostanziale con dati concreti
    # Fix #306: la soglia era calcolata male (sempre >= 50 per pagine >= 50 parole)
    if words:
        soglia_30 = max(len(words) * 30 // 100, 1)
        first_30pct = words[:soglia_30]
        # Il primo 30% deve avere almeno 50 parole E contenere numeri/statistiche
        if len(first_30pct) >= 50:
            import re as _re_fl

            numeri_nel_30pct = sum(1 for w in first_30pct if _re_fl.search(r"\d", w))
            if numeri_nel_30pct >= 1:
                result.has_front_loading = True

    return result


def audit_ai_discovery(base_url: str) -> AiDiscoveryResult:
    """Check AI discovery endpoints (geo-checklist.dev standard).

    Checks for:
    - /.well-known/ai.txt (HTTP 200)
    - /ai/summary.json (HTTP 200 + JSON valido con name e description)
    - /ai/faq.json (HTTP 200 + JSON valido)
    - /ai/service.json (HTTP 200 + JSON valido)

    Args:
        base_url: URL base del sito (normalizzato).

    Returns:
        AiDiscoveryResult con i risultati dei check.
    """
    result = AiDiscoveryResult()

    # Check /.well-known/ai.txt
    ai_txt_url = urljoin(base_url, "/.well-known/ai.txt")
    r, err = fetch_url(ai_txt_url)
    if r and not err and r.status_code == 200 and len(r.text.strip()) > 0:
        result.has_well_known_ai = True
        result.endpoints_found += 1

    # Check /ai/summary.json
    summary_url = urljoin(base_url, "/ai/summary.json")
    r, err = fetch_url(summary_url)
    if r and not err and r.status_code == 200:
        try:
            data = json.loads(r.text)
            result.has_summary = True
            result.endpoints_found += 1
            # Valida campi richiesti: name e description
            if isinstance(data, dict) and data.get("name") and data.get("description"):
                result.summary_valid = True
        except (json.JSONDecodeError, ValueError):
            pass

    # Check /ai/faq.json
    faq_url = urljoin(base_url, "/ai/faq.json")
    r, err = fetch_url(faq_url)
    if r and not err and r.status_code == 200:
        try:
            data = json.loads(r.text)
            result.has_faq = True
            result.endpoints_found += 1
            # Conta FAQ: supporta lista di oggetti o dict con chiave "faqs"
            if isinstance(data, list):
                result.faq_count = len(data)
            elif isinstance(data, dict) and isinstance(data.get("faqs"), list):
                result.faq_count = len(data["faqs"])
        except (json.JSONDecodeError, ValueError):
            pass

    # Check /ai/service.json
    service_url = urljoin(base_url, "/ai/service.json")
    r, err = fetch_url(service_url)
    if r and not err and r.status_code == 200:
        try:
            json.loads(r.text)
            result.has_service = True
            result.endpoints_found += 1
        except (json.JSONDecodeError, ValueError):
            pass

    return result


def _audit_ai_discovery_from_responses(r_ai_txt, r_summary, r_faq, r_service) -> AiDiscoveryResult:
    """Analyze AI discovery from pre-fetched HTTP responses (async path).

    Args:
        r_ai_txt: HTTP response for /.well-known/ai.txt (or None).
        r_summary: HTTP response for /ai/summary.json (or None).
        r_faq: HTTP response for /ai/faq.json (or None).
        r_service: HTTP response for /ai/service.json (or None).

    Returns:
        AiDiscoveryResult con i risultati dei check.
    """
    result = AiDiscoveryResult()

    # /.well-known/ai.txt
    if r_ai_txt and r_ai_txt.status_code == 200 and len(r_ai_txt.text.strip()) > 0:
        result.has_well_known_ai = True
        result.endpoints_found += 1

    # /ai/summary.json
    if r_summary and r_summary.status_code == 200:
        try:
            data = json.loads(r_summary.text)
            result.has_summary = True
            result.endpoints_found += 1
            if isinstance(data, dict) and data.get("name") and data.get("description"):
                result.summary_valid = True
        except (json.JSONDecodeError, ValueError):
            pass

    # /ai/faq.json
    if r_faq and r_faq.status_code == 200:
        try:
            data = json.loads(r_faq.text)
            result.has_faq = True
            result.endpoints_found += 1
            if isinstance(data, list):
                result.faq_count = len(data)
            elif isinstance(data, dict) and isinstance(data.get("faqs"), list):
                result.faq_count = len(data["faqs"])
        except (json.JSONDecodeError, ValueError):
            pass

    # /ai/service.json
    if r_service and r_service.status_code == 200:
        try:
            json.loads(r_service.text)
            result.has_service = True
            result.endpoints_found += 1
        except (json.JSONDecodeError, ValueError):
            pass

    return result


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
    """Build a prioritized list of recommendations.

    Args:
        base_url: URL base del sito.
        robots: RobotsResult.
        llms: LlmsTxtResult.
        schema: SchemaResult.
        meta: MetaResult.
        content: ContentResult.
        ai_discovery: AiDiscoveryResult (opzionale).
        signals: SignalsResult (opzionale, per raccomandazioni machine-readable #263).
        brand_entity: BrandEntityResult (opzionale, v4.3).
        webmcp: WebMcpResult (opzionale, #233).
        negative_signals: NegativeSignalsResult (opzionale, v4.3).
    """
    recommendations = []

    if not robots.citation_bots_ok:
        recommendations.append("Update robots.txt to include all AI bots (GPTBot, ClaudeBot, PerplexityBot)")
    if not llms.found:
        recommendations.append(
            f"Create /llms.txt for AI indexing: geo llms --base-url {base_url}. "
            "Note: llms.txt is an organizational signal, not a proven ranking factor. "
            "It helps structure content for AI systems."
        )
    elif llms.found:
        # #247: llms.txt Policy Intelligence — raccomandazioni sulla qualità del contenuto
        if llms.sections_count == 0:
            recommendations.append(
                "Add H2 sections to llms.txt to organize content by topic (e.g. ## Features, ## Documentation, ## API)"
            )
        if llms.links_count < 3:
            recommendations.append(
                f"llms.txt has only {llms.links_count} links. "
                "Add more markdown links to key pages for better AI indexing coverage."
            )
        # #39: aggiungi validation warnings alle raccomandazioni
        if hasattr(llms, "validation_warnings"):
            for warning in llms.validation_warnings:
                recommendations.append(warning)
    if not schema.has_website:
        recommendations.append("Add WebSite JSON-LD schema to homepage")
    if not schema.has_faq:
        recommendations.append("Add FAQPage schema with site FAQs")
    if not meta.has_description:
        recommendations.append("Add optimized meta description (150-160 characters)")
    if not content.has_numbers:
        recommendations.append("Add numerical data and concrete statistics (+40% AI visibility)")
    if not content.has_links:
        recommendations.append("Cite authoritative sources with external links (increase AI credibility)")

    # #263: Raccomandazioni Machine-Readable Presence (RSS + sitemap)
    if signals is not None and not signals.has_rss:
        recommendations.append(
            "Add RSS/Atom feed and link it in <head> with "
            '<link rel="alternate" type="application/rss+xml"> for AI discovery'
        )

    # Raccomandazioni AI discovery (geo-checklist.dev)
    if ai_discovery is not None:
        if not ai_discovery.has_well_known_ai:
            recommendations.append("Create /.well-known/ai.txt to define AI crawler permissions")
        if not ai_discovery.has_summary or not ai_discovery.summary_valid:
            recommendations.append("Create /ai/summary.json with site name and description for AI engines")
        if not ai_discovery.has_faq:
            recommendations.append("Create /ai/faq.json with structured FAQ for AI search visibility")
        if not ai_discovery.has_service:
            recommendations.append("Create /ai/service.json to describe service capabilities for AI")

    # #232: Raccomandazione e-commerce se Product schema è incompleto
    if schema.has_product and hasattr(schema, "ecommerce_signals"):
        signals_dict = schema.ecommerce_signals
        missing_fields = [k for k, v in signals_dict.items() if not v and k != "complete"]
        if missing_fields:
            recommendations.append(
                f"Complete Product schema: missing {', '.join(missing_fields)}. "
                "Rich Product schema improves AI shopping visibility."
            )

    # Brand & Entity raccomandazioni (v4.3)
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

    # WebMCP raccomandazioni (#233)
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

    # Negative Signals raccomandazioni (v4.3)
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
    soup_clean=None,  # Fix #285: soup pre-pulito (senza script/style) per evitare re-parse
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
) -> AuditResult:
    """Costruisce AuditResult dai sub-audit (fix #97: logica comune sync/async).

    Calcola score, band e raccomandazioni, poi esegue i plugin registrati
    in CheckRegistry (fix #104). I risultati dei plugin non influenzano il punteggio base.

    Args:
        base_url: URL del sito normalizzato.
        robots: Risultato audit robots.txt.
        llms: Risultato audit llms.txt.
        schema: Risultato audit schema JSON-LD.
        meta: Risultato audit meta tag.
        content: Risultato audit contenuto.
        http_status: HTTP status code della homepage.
        page_size: Dimensione della homepage in byte.
        soup: BeautifulSoup della homepage (opzionale, passato ai plugin).
        extra_checks: Dizionario con risultati pre-calcolati (non usato internamente).
        signals: Segnali tecnici v4.0 (lang, RSS, freshness).

    Returns:
        AuditResult completo con score, band, raccomandazioni e plugin.
    """
    from geo_optimizer.core.registry import CheckRegistry

    # Usa SignalsResult vuoto se non fornito
    effective_signals = signals if signals is not None else SignalsResult()

    # Usa AiDiscoveryResult vuoto se non fornito
    from geo_optimizer.models.results import AiDiscoveryResult

    effective_ai_discovery = ai_discovery if ai_discovery is not None else AiDiscoveryResult()

    # v4.3: usa BrandEntityResult vuoto se non fornito
    effective_brand_entity = brand_entity if brand_entity is not None else BrandEntityResult()

    # v4.3: usa WebMcpResult vuoto se non fornito (#233)
    effective_webmcp = webmcp if webmcp is not None else WebMcpResult()

    # v4.3: usa NegativeSignalsResult vuoto se non fornito
    effective_negative_signals = negative_signals if negative_signals is not None else NegativeSignalsResult()

    # v4.4: usa PromptInjectionResult vuoto se non fornito (#276)
    from geo_optimizer.models.results import PromptInjectionResult

    effective_prompt_injection = prompt_injection if prompt_injection is not None else PromptInjectionResult()

    # v4.5: usa TrustStackResult vuoto se non fornito (#273)
    from geo_optimizer.models.results import TrustStackResult

    effective_trust_stack = trust_stack if trust_stack is not None else TrustStackResult()

    # Calcola score, breakdown e band (v4.0: include signals, ai_discovery)
    score = compute_geo_score(
        robots, llms, schema, meta, content, effective_signals, effective_ai_discovery, effective_brand_entity
    )
    breakdown = compute_score_breakdown(
        robots, llms, schema, meta, content, effective_signals, effective_ai_discovery, effective_brand_entity
    )
    band = get_score_band(score)

    # Raccomandazioni
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

    # Fix #104: esegui plugin registrati in CheckRegistry
    # I risultati non influenzano il punteggio base
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

    # Citability Score: analisi contenuto con 42 metodi (fix #31)
    # Fix #285: passa soup_clean pre-calcolato per evitare re-parse in citability
    from geo_optimizer.core.citability import audit_citability

    citability = audit_citability(soup, base_url, soup_clean=soup_clean) if soup else CitabilityResult()

    # v4.2: CDN + JS checks (#225, #226)
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
    )


def run_full_audit(url: str, use_cache: bool = False, project_config=None) -> AuditResult:
    """Run complete audit and return AuditResult with all sub-results, score, band, and recommendations.

    Args:
        url: URL of the site to analyze.
        use_cache: If True, use disk cache for HTTP requests.
        project_config: Optional ProjectConfig — if it has extra_bots, merges them with AI_BOTS (fix #120).
    """
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
        return result

    # Fix #337: se la homepage ritorna errore HTTP, segnala e non analizzare la pagina di errore
    if r.status_code not in (200, 203):
        result = AuditResult(
            url=base_url,
            http_status=r.status_code,
            error=f"HTTP {r.status_code}",
        )
        result.recommendations = [
            f"Site returned HTTP {r.status_code}. Check for Cloudflare/WAF blocks or server errors."
        ]
        return result

    import copy

    soup = BeautifulSoup(r.text, "html.parser")

    # Fix #285: calcola soup_clean una volta sola e passalo ai sub-audit
    # Evita 3-4 re-parse dello stesso HTML (risparmio 50-200ms per pagina)
    soup_clean = copy.deepcopy(soup)
    for tag in soup_clean(["script", "style"]):
        tag.decompose()

    # Esegui tutti i sub-audit
    # Fix #120: passa effective_bots che include eventuali extra_bots da project_config
    robots = audit_robots_txt(base_url, bots=effective_bots)
    llms = audit_llms_txt(base_url)
    schema = audit_schema(soup, base_url)
    meta = audit_meta_tags(soup, base_url)
    content = audit_content_quality(soup, base_url, soup_clean=soup_clean)

    # v4.1: audit AI discovery endpoints
    ai_disc = audit_ai_discovery(base_url)

    # v4.2: CDN AI Crawler check (#225) + JS Rendering check (#226)
    cdn_result = audit_cdn_ai_crawler(base_url)
    js_result = audit_js_rendering(soup, r.text)

    # Fix #281: calcolo segnali tecnici (lang, RSS, freshness)
    signals = audit_signals(soup, schema)

    # v4.3: Brand & Entity signals (zero richieste HTTP, solo dati già disponibili)
    brand_entity_result = audit_brand_entity(soup, schema, meta, content)

    # v4.3: WebMCP Readiness check (#233) — zero fetch HTTP
    webmcp_result = audit_webmcp_readiness(soup, r.text, schema)

    # v4.3: Negative Signals detection — zero fetch HTTP
    negative_signals_result = audit_negative_signals(soup, r.text, content, meta, schema)

    # v4.4: Prompt Injection Pattern Detection (#276) — zero fetch HTTP
    from geo_optimizer.core.injection_detector import audit_prompt_injection

    prompt_injection_result = audit_prompt_injection(soup, r.text)

    # v4.5: Trust Stack Score (#273) — aggregazione 5-layer, zero fetch HTTP
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

    # Fix #97 + #104: usa _build_audit_result per logica comune e integrazione plugin
    return _build_audit_result(
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


async def run_full_audit_async(url: str, project_config=None) -> AuditResult:
    """Async variant of the full audit with parallel fetch (httpx).

    Runs homepage, robots.txt and llms.txt in parallel for a
    2-3x speedup compared to the synchronous version.

    Args:
        url: URL of the site to analyze.
        project_config: Optional ProjectConfig — if it has extra_bots, merges them with AI_BOTS.

    Requires: pip install geo-optimizer-skill[async]
    """
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
        return result

    # Fix #337: se la homepage ritorna errore HTTP, segnala e non analizzare la pagina di errore
    if r_home.status_code not in (200, 203):
        result = AuditResult(
            url=base_url,
            http_status=r_home.status_code,
            error=f"HTTP {r_home.status_code}",
        )
        result.recommendations = [
            f"Site returned HTTP {r_home.status_code}. Check for Cloudflare/WAF blocks or server errors."
        ]
        return result

    import copy

    soup = BeautifulSoup(r_home.text, "html.parser")

    # Fix #285: calcola soup_clean una volta sola per il path async
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

    # v4.1: AI discovery da risposte pre-scaricate
    ai_disc = _audit_ai_discovery_from_responses(r_ai_txt, r_ai_summary, r_ai_faq, r_ai_service)

    # v4.2: CDN AI Crawler check (#225) + JS Rendering check (#226)
    # Fix: wrappa chiamate sincrone con asyncio.to_thread per non bloccare l'event loop
    cdn_result = await asyncio.to_thread(audit_cdn_ai_crawler, base_url)
    js_result = audit_js_rendering(soup, r_home.text)

    # Fix #281: calcolo segnali tecnici (lang, RSS, freshness)
    signals = audit_signals(soup, schema)

    # v4.3: Brand & Entity signals (zero richieste HTTP, solo dati già disponibili)
    brand_entity_result = audit_brand_entity(soup, schema, meta, content)

    # v4.3: WebMCP Readiness check (#233) — zero fetch HTTP
    webmcp_result = audit_webmcp_readiness(soup, r_home.text, schema)

    # v4.3: Negative Signals detection — zero fetch HTTP
    negative_signals_result = audit_negative_signals(soup, r_home.text, content, meta, schema)

    # v4.4: Prompt Injection Pattern Detection (#276) — zero fetch HTTP
    from geo_optimizer.core.injection_detector import audit_prompt_injection

    prompt_injection_result = audit_prompt_injection(soup, r_home.text)

    # v4.5: Trust Stack Score (#273) — aggregazione 5-layer, zero fetch HTTP
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

    # Fix #97 + #104: usa _build_audit_result per logica comune e integrazione plugin
    return _build_audit_result(
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


def _audit_robots_from_response(r, bots: dict = None) -> RobotsResult:
    """Analyze robots.txt from an already-downloaded HTTP response.

    Args:
        r: HTTP response (or None if fetch failed).
        bots: Dictionary of bots to check. Default: AI_BOTS from config.
              Allows passing extra bots from project_config.extra_bots.
    """
    result = RobotsResult()

    if not r or r.status_code != 200:
        return result

    effective_bots = bots if bots is not None else AI_BOTS

    result.found = True
    content = r.text
    agent_rules = parse_robots_txt(content)

    for bot, description in effective_bots.items():
        bot_status = classify_bot(bot, description, agent_rules)

        if bot_status.status == "missing":
            result.bots_missing.append(bot)
        elif bot_status.status == "blocked":
            result.bots_blocked.append(bot)
        elif bot_status.status == "partial":
            result.bots_allowed.append(bot)
            result.bots_partial.append(bot)
        else:
            result.bots_allowed.append(bot)

    result.citation_bots_ok = all(b in result.bots_allowed for b in CITATION_BOTS)

    # #111 — Distinguish explicit permission from wildcard fallback
    citation_explicit = []
    for bot in CITATION_BOTS:
        bot_status = classify_bot(bot, "", agent_rules)
        if bot_status.status in ("allowed", "partial") and not bot_status.via_wildcard:
            citation_explicit.append(bot)
    result.citation_bots_explicit = len(citation_explicit) == len(CITATION_BOTS)

    return result


def _audit_llms_from_response(r, r_full=None) -> LlmsTxtResult:
    """Analyze llms.txt from an already-downloaded HTTP response.

    Args:
        r: HTTP response for /llms.txt (or None).
        r_full: HTTP response for /llms-full.txt (or None). Fix #184.
    """
    result = LlmsTxtResult()

    if not r or r.status_code != 200:
        return result

    result.found = True
    content = r.text.lstrip("\ufeff")
    lines = content.splitlines()
    result.word_count = len(content.split())

    h1_lines = [line for line in lines if line.startswith("# ")]
    if h1_lines:
        result.has_h1 = True

    blockquotes = [line for line in lines if line.startswith("> ")]
    if blockquotes:
        # Fix #317: sincronizza has_description (alias retrocompatibile) con has_blockquote
        result.has_blockquote = True
        result.has_description = True

    h2_lines = [line for line in lines if line.startswith("## ")]
    if h2_lines:
        result.has_sections = True
    # #247: conta sezioni H2 per Policy Intelligence
    result.sections_count = len(h2_lines)

    links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
    if links:
        result.has_links = True
    # #247: conta link per Policy Intelligence
    result.links_count = len(links)

    # #39: validazione v2 — conformità spec completa
    _validate_llms_content(result, content)

    # Check /llms-full.txt — fix #184: now works in the async path too
    if r_full and r_full.status_code == 200 and len(r_full.text.strip()) > 0:
        result.has_full = True

    return result


# ─── CDN AI Crawler Check (#225) ─────────────────────────────────────────────


def audit_cdn_ai_crawler(base_url: str) -> CdnAiCrawlerResult:
    """Check if CDN/WAF blocks AI crawler user-agents (#225).

    Simulates requests with AI bot User-Agents (GPTBot, ClaudeBot, PerplexityBot)
    and compares response status/size to a normal browser request.

    Based on OtterlyAI Citation Report 2026: 73% of sites have technical
    barriers blocking AI crawlers. CDN restrictions are barrier #2.

    Args:
        base_url: Base URL of the site (normalized).

    Returns:
        CdnAiCrawlerResult with per-bot comparison data.
    """
    from geo_optimizer.models.results import CdnAiCrawlerResult

    result = CdnAiCrawlerResult()

    # AI bots to test (most impactful for citations)
    test_bots = {
        "GPTBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GPTBot/1.2; +https://openai.com/gptbot)",
        "ClaudeBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +https://claudebot.ai)",
        "PerplexityBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
    }

    browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    # Challenge page indicators (Cloudflare, AWS WAF, etc.)
    challenge_indicators = [
        "cf-browser-verification",
        "challenge-platform",
        "just a moment",
        "checking your browser",
        "ray id",
        "access denied",
        "bot detection",
        "captcha",
        "blocked",
        "forbidden",
    ]

    # CDN detection headers
    cdn_header_map = {
        "cf-ray": "cloudflare",
        "cf-cache-status": "cloudflare",
        "x-amz-cf-id": "aws-cloudfront",
        "x-amz-request-id": "aws",
        "x-akamai-transformed": "akamai",
        "x-cdn": "",  # generic CDN
        "x-served-by": "",  # Fastly/Varnish
        "x-vercel-id": "vercel",
        "server": "",  # check value
    }

    from geo_optimizer.utils.http import create_session_with_retry
    from geo_optimizer.utils.validators import resolve_and_validate_url

    # Fix #283: validazione SSRF prima delle richieste CDN
    # Fix #305: DNS pinning con sessione pinnata (elimina TOCTOU)
    is_safe, reason, pinned_ips = resolve_and_validate_url(base_url)
    if not is_safe:
        result.error = f"URL non sicura: {reason}"
        return result

    # Sessione con DNS pinning — tutte le richieste usano gli IP già validati
    session = create_session_with_retry(total_retries=1, pinned_ips=pinned_ips)

    try:
        # Step 1: Browser request (baseline)
        try:
            browser_r = session.get(
                base_url,
                headers={"User-Agent": browser_ua},
                timeout=10,
                allow_redirects=False,
            )
            result.browser_status = browser_r.status_code
            # Fix #348: size check per evitare OOM su risposte enormi
            if len(browser_r.content) > 5 * 1024 * 1024:  # 5 MB
                result.error = "Response too large for CDN check"
                return result
            result.browser_content_length = len(browser_r.text)

            # Detect CDN from headers
            resp_headers = {k.lower(): v for k, v in browser_r.headers.items()}
            for header_key, cdn_name in cdn_header_map.items():
                if header_key in resp_headers:
                    result.cdn_headers[header_key] = resp_headers[header_key]
                    if cdn_name and not result.cdn_detected:
                        result.cdn_detected = cdn_name
            # Check server header for CDN names
            server_val = resp_headers.get("server", "").lower()
            if "cloudflare" in server_val:
                result.cdn_detected = "cloudflare"
            elif "akamaighost" in server_val or "akamai" in server_val:
                result.cdn_detected = "akamai"

        except Exception:
            # Non raggiungibile nemmeno come browser — skip check
            return result

        # Step 2: AI bot requests
        for bot_name, bot_ua in test_bots.items():
            bot_entry = {
                "bot": bot_name,
                "status": 0,
                "content_length": 0,
                "blocked": False,
                "challenge_detected": False,
            }
            try:
                bot_r = session.get(
                    base_url,
                    headers={"User-Agent": bot_ua},
                    timeout=10,
                    allow_redirects=False,
                )
                bot_entry["status"] = bot_r.status_code
                bot_entry["content_length"] = len(bot_r.text)

                # Check 1: HTTP error status
                if bot_r.status_code in (403, 429, 451, 503):
                    bot_entry["blocked"] = True

                # Check 2: Challenge/captcha page detection
                body_lower = bot_r.text[:5000].lower()
                if any(indicator in body_lower for indicator in challenge_indicators):
                    bot_entry["challenge_detected"] = True

                # Check 3: Content-length mismatch (>70% difference → probable block)
                if (
                    result.browser_content_length > 0
                    and bot_entry["content_length"] > 0
                    and result.browser_status == 200
                    and bot_r.status_code == 200
                ):
                    ratio = bot_entry["content_length"] / result.browser_content_length
                    if ratio < 0.3:
                        # Bot receives <30% of the content → likely a block page
                        bot_entry["blocked"] = True

            except Exception:
                bot_entry["blocked"] = True

            result.bot_results.append(bot_entry)

        result.checked = True
        result.any_blocked = any(b["blocked"] or b["challenge_detected"] for b in result.bot_results)

    except Exception:
        pass

    return result


# ─── JS Rendering Check (#226) ───────────────────────────────────────────────


def audit_js_rendering(soup, raw_html: str) -> JsRenderingResult:
    """Check if page content is accessible without JavaScript (#226).

    Analyzes raw HTML (as fetched by requests, without JS execution) for
    content indicators. AI crawlers typically don't execute JavaScript,
    so content that requires JS rendering is invisible to them.

    Based on OtterlyAI Citation Report 2026: JS rendering is barrier #3.

    Args:
        soup: BeautifulSoup of the page (parsed from raw HTML).
        raw_html: Raw HTML string of the page.

    Returns:
        JsRenderingResult with content analysis.
    """
    from geo_optimizer.models.results import JsRenderingResult

    result = JsRenderingResult()

    if not soup or not raw_html:
        return result

    result.checked = True

    # Extract body text (excluding script/style tags)
    body = soup.find("body")
    if not body:
        result.js_dependent = True
        result.details = "No <body> tag found in raw HTML"
        return result

    # Fix #24: usa deepcopy per non mutare il soup originale
    # (audit_citability ha bisogno dei <script type="application/ld+json"> intatti)
    import copy

    body_clean = copy.deepcopy(body)
    for tag in body_clean.find_all(["script", "style", "noscript"]):
        tag.decompose()

    body_text = body_clean.get_text(separator=" ", strip=True)
    result.raw_word_count = len(body_text.split())

    # Count headings in raw HTML (dal body pulito, fix #24)
    headings = body_clean.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    result.raw_heading_count = len(headings)

    # Check for empty SPA root containers
    spa_indicators = [
        ("div", {"id": "root"}),
        ("div", {"id": "app"}),
        ("div", {"id": "__next"}),
        ("div", {"id": "__nuxt"}),
        ("div", {"id": "gatsby-focus-wrapper"}),
    ]
    for tag_name, attrs in spa_indicators:
        el = body_clean.find(tag_name, attrs)
        if el:
            # Check if the element is essentially empty (< 50 chars of text)
            inner_text = el.get_text(strip=True)
            if len(inner_text) < 50:
                result.has_empty_root = True
                break

    # Check for <noscript> content
    # Fix #27: usa soup originale (non mutato grazie a fix #24)
    noscript_tags = soup.find_all("noscript")
    for ns in noscript_tags:
        ns_text = ns.get_text(strip=True)
        if len(ns_text) > 20:
            result.has_noscript_content = True
            break

    # Detect JS frameworks from raw HTML
    html_lower = raw_html[:10000].lower()
    if "/__next/" in html_lower or "_next/static" in html_lower or "__next" in html_lower:
        result.framework_detected = "next.js"
    elif "__nuxt" in html_lower or "_nuxt/" in html_lower:
        result.framework_detected = "nuxt"
    elif "react" in html_lower and ('id="root"' in html_lower or "createroot" in html_lower):
        result.framework_detected = "react"
    elif "ng-version" in html_lower or "ng-app" in html_lower:
        result.framework_detected = "angular"
    elif "data-v-" in html_lower or 'id="app"' in html_lower:
        result.framework_detected = "vue"
    elif "gatsby" in html_lower:
        result.framework_detected = "gatsby"
    elif "astro" in html_lower or "_astro/" in html_lower:
        result.framework_detected = "astro"

    # Determine if content is JS-dependent
    # Thresholds: < 100 words in body AND 0 headings → likely SPA
    if result.raw_word_count < 100 and result.raw_heading_count == 0:
        result.js_dependent = True
        result.details = (
            f"Only {result.raw_word_count} words and 0 headings in raw HTML. "
            "Content likely requires JavaScript to render. "
            "AI crawlers won't see it. Consider SSR/SSG or pre-rendering."
        )
    elif result.has_empty_root and result.raw_word_count < 200:
        result.js_dependent = True
        result.details = (
            f"Empty SPA root container detected with only {result.raw_word_count} words. "
            f"Framework: {result.framework_detected or 'unknown'}. "
            "Implement server-side rendering for AI crawler accessibility."
        )
    elif result.raw_word_count < 50:
        result.js_dependent = True
        result.details = (
            f"Critically low content: {result.raw_word_count} words in raw HTML. "
            "Page appears to be a JavaScript-only application."
        )
    else:
        result.details = (
            f"{result.raw_word_count} words and {result.raw_heading_count} headings "
            "found in raw HTML. Content is accessible without JavaScript."
        )

    return result


# ─── Fix #281: Calcolo SignalsResult ─────────────────────────────────────────


def audit_signals(soup, schema_result) -> SignalsResult:
    """Calcola i segnali tecnici: lang, RSS, freshness.

    Args:
        soup: BeautifulSoup del documento HTML.
        schema_result: SchemaResult con gli schema JSON-LD trovati.

    Returns:
        SignalsResult con has_lang, has_rss, has_freshness popolati.
    """
    signals = SignalsResult()

    # 1. Controllo lang attribute su <html>
    html_tag = soup.find("html")
    if html_tag:
        lang_val = html_tag.get("lang", "").strip()
        if lang_val:
            signals.has_lang = True
            signals.lang_value = lang_val

    # 2. Controllo RSS/Atom feed
    rss_link = soup.find("link", attrs={"type": lambda t: t and ("rss" in t.lower() or "atom" in t.lower())})
    if rss_link:
        signals.has_rss = True
        signals.rss_url = rss_link.get("href", "")

    # 3. Controllo freshness (dateModified nello schema o meta tag)
    # Cerca dateModified negli schema JSON-LD
    if schema_result and schema_result.raw_schemas:
        for s in schema_result.raw_schemas:
            date_mod = s.get("dateModified", "") or s.get("datePublished", "")
            if date_mod:
                signals.has_freshness = True
                signals.freshness_date = str(date_mod)
                break

    # Fallback: meta tag article:modified_time
    if not signals.has_freshness:
        meta_mod = soup.find("meta", attrs={"property": "article:modified_time"})
        if meta_mod and meta_mod.get("content", "").strip():
            signals.has_freshness = True
            signals.freshness_date = meta_mod["content"].strip()

    return signals


# ─── Brand & Entity Signals (v4.3) ───────────────────────────────────────────


def audit_brand_entity(soup, schema_result, meta_result, content_result) -> BrandEntityResult:
    """Analizza segnali di brand identity ed entity per la percezione AI (v4.3).

    Lavora solo su dati già fetchati, zero richieste HTTP.

    Args:
        soup: BeautifulSoup della homepage.
        schema_result: SchemaResult già calcolato.
        meta_result: MetaResult già calcolato.
        content_result: ContentResult già calcolato.

    Returns:
        BrandEntityResult con i segnali brand/entity popolati.
    """
    from collections import Counter

    from geo_optimizer.models.config import KG_PILLAR_DOMAINS

    result = BrandEntityResult()
    if soup is None:
        return result

    # ── 1. Entity Coherence ──────────────────────────────────────
    # Raccoglie nomi brand da varie fonti
    names = []

    # H1
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        h1_text = h1.get_text(strip=True)
        # Prende la prima parte prima di separatori comuni
        for sep in (" — ", " - ", " | ", " · "):
            if sep in h1_text:
                h1_text = h1_text.split(sep)[0].strip()
                break
        if h1_text:
            names.append(h1_text)

    # Title tag
    if meta_result.title_text:
        title_name = meta_result.title_text
        for sep in (" — ", " - ", " | ", " · "):
            if sep in title_name:
                title_name = title_name.split(sep)[0].strip()
                break
        if title_name:
            names.append(title_name)

    # og:title
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content", ""):
        og_name = og_title["content"]
        for sep in (" — ", " - ", " | ", " · "):
            if sep in og_name:
                og_name = og_name.split(sep)[0].strip()
                break
        if og_name:
            names.append(og_name)

    # Schema Organization name
    for raw_schema in schema_result.raw_schemas:
        schemas_to_check = []
        if "@graph" in raw_schema:
            schemas_to_check.extend(raw_schema["@graph"])
        else:
            schemas_to_check.append(raw_schema)
        for s in schemas_to_check:
            s_type = s.get("@type", "")
            if isinstance(s_type, list):
                s_type = s_type[0] if s_type else ""
            if s_type == "Organization" and s.get("name"):
                names.append(s["name"])

    result.names_found = names[:10]

    # Consistenza: almeno 2 nomi, e i più comuni sono uguali (case-insensitive)
    if len(names) >= 2:
        lower_names = [n.lower().strip() for n in names]
        freq = Counter(lower_names)
        most_common_name, most_common_count = freq.most_common(1)[0]
        if most_common_count >= 2:
            result.brand_name_consistent = True

    # Schema description vs meta description
    if meta_result.description_text:
        meta_desc_lower = meta_result.description_text.lower()[:100]
        for raw_schema in schema_result.raw_schemas:
            schemas_to_check = []
            if "@graph" in raw_schema:
                schemas_to_check.extend(raw_schema["@graph"])
            else:
                schemas_to_check.append(raw_schema)
            for s in schemas_to_check:
                schema_desc = s.get("description", "")
                if schema_desc and isinstance(schema_desc, str):
                    schema_desc_lower = schema_desc.lower()[:100]
                    # Overlap significativo: almeno 30 char in comune
                    if meta_desc_lower[:30] in schema_desc_lower or schema_desc_lower[:30] in meta_desc_lower:
                        result.schema_desc_matches_meta = True
                        break

    # ── 2. Knowledge Graph Readiness ─────────────────────────────
    for url in schema_result.sameas_urls:
        url_lower = url.lower()
        for domain in KG_PILLAR_DOMAINS:
            if domain in url_lower:
                result.kg_pillar_urls.append(url)
                if "wikipedia.org" in url_lower:
                    result.has_wikipedia = True
                elif "wikidata.org" in url_lower:
                    result.has_wikidata = True
                elif "linkedin.com" in url_lower:
                    result.has_linkedin = True
                elif "crunchbase.com" in url_lower:
                    result.has_crunchbase = True
                break
    result.kg_pillar_count = sum(
        [
            result.has_wikipedia,
            result.has_wikidata,
            result.has_linkedin,
            result.has_crunchbase,
        ]
    )

    # ── 3. About/Contact Signals ─────────────────────────────────
    # Cerca link /about nella pagina
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].lower()
        if "/about" in href or "/chi-siamo" in href or "/team" in href:
            result.has_about_link = True
            break

    # Cerca Organization con address/telephone/email o Person con jobTitle
    for raw_schema in schema_result.raw_schemas:
        schemas_to_check = []
        if "@graph" in raw_schema:
            schemas_to_check.extend(raw_schema["@graph"])
        else:
            schemas_to_check.append(raw_schema)
        for s in schemas_to_check:
            s_type = s.get("@type", "")
            if isinstance(s_type, list):
                s_type = s_type[0] if s_type else ""
            if s_type == "Organization" and (
                s.get("address") or s.get("telephone") or s.get("email") or s.get("contactPoint")
            ):
                result.has_contact_info = True
            elif s_type == "Person" and (s.get("jobTitle") or s.get("hasCredential") or s.get("alumniOf")):
                result.has_contact_info = True

    # ── 4. Geographic Identity ───────────────────────────────────
    # hreflang tags
    hreflang_tags = soup.find_all("link", attrs={"rel": "alternate", "hreflang": True})
    result.hreflang_count = len(hreflang_tags)
    result.has_hreflang = result.hreflang_count > 0

    # Schema geo (address, areaServed, LocalBusiness)
    for raw_schema in schema_result.raw_schemas:
        schemas_to_check = []
        if "@graph" in raw_schema:
            schemas_to_check.extend(raw_schema["@graph"])
        else:
            schemas_to_check.append(raw_schema)
        for s in schemas_to_check:
            s_type = s.get("@type", "")
            if isinstance(s_type, list):
                s_type = s_type[0] if s_type else ""
            if s_type == "LocalBusiness" or s.get("areaServed") or (s_type == "Organization" and s.get("address")):
                result.has_geo_schema = True
                break

    # ── 5. Topic Authority ───────────────────────────────────────
    # FAQ depth dal FAQPage schema
    for raw_schema in schema_result.raw_schemas:
        schemas_to_check = []
        if "@graph" in raw_schema:
            schemas_to_check.extend(raw_schema["@graph"])
        else:
            schemas_to_check.append(raw_schema)
        for s in schemas_to_check:
            s_type = s.get("@type", "")
            if isinstance(s_type, list):
                s_type = s_type[0] if s_type else ""
            if s_type == "FAQPage":
                main_entity = s.get("mainEntity", [])
                if isinstance(main_entity, list):
                    result.faq_depth += len(main_entity)

    # Article/BlogPosting con dateModified
    result.has_recent_articles = schema_result.has_date_modified and (
        schema_result.has_article or any(t in ("BlogPosting", "NewsArticle") for t in schema_result.found_types)
    )

    return result


# ─── WebMCP Readiness Check (#233) ───────────────────────────────────────────


def _extract_actions(schema_obj, action_types: set) -> None:
    """Estrae potentialAction da un oggetto schema JSON-LD (ricorsivo).

    Args:
        schema_obj: Oggetto schema (dict, list o valore primitivo).
        action_types: Set in cui aggiungere i tipi azione trovati.
    """
    if isinstance(schema_obj, dict):
        # Supporta @graph (Yoast SEO, RankMath)
        if "@graph" in schema_obj:
            for item in schema_obj["@graph"]:
                _extract_actions(item, action_types)
            return

        potential = schema_obj.get("potentialAction")
        if potential:
            if isinstance(potential, dict):
                action_type = potential.get("@type", "")
                if action_type:
                    action_types.add(action_type)
            elif isinstance(potential, list):
                for action in potential:
                    if isinstance(action, dict):
                        action_type = action.get("@type", "")
                        if action_type:
                            action_types.add(action_type)
    elif isinstance(schema_obj, list):
        for item in schema_obj:
            _extract_actions(item, action_types)


def audit_webmcp_readiness(soup, raw_html: str, schema_result) -> WebMcpResult:
    """Verifica WebMCP readiness e agent-readiness signals (#233).

    Analizza:
    1. WebMCP API: registerTool(), attributi toolname/tooldescription
    2. Schema potentialAction: SearchAction, BuyAction, OrderAction
    3. Form accessibili: form con label + aria-label/placeholder
    4. OpenAPI: link a /api-docs, /swagger, openapi.json

    Zero fetch HTTP — lavora solo su dati già disponibili.

    Args:
        soup: BeautifulSoup della pagina.
        raw_html: HTML grezzo della pagina.
        schema_result: SchemaResult con gli schema JSON-LD trovati.

    Returns:
        WebMcpResult con i segnali di readiness rilevati.
    """
    result = WebMcpResult()
    if soup is None or not raw_html:
        return result

    result.checked = True

    # ── 1. WebMCP Detection ──────────────────────────────────────
    # API imperativa: navigator.modelContext.registerTool()
    if "modelContext" in raw_html and "registerTool" in raw_html:
        result.has_register_tool = True

    # API dichiarativa: attributi toolname/tooldescription nei tag HTML
    tool_elements = soup.find_all(attrs={"toolname": True})
    if tool_elements:
        result.has_tool_attributes = True
        result.tool_count = len(tool_elements)

    # ── 2. Schema potentialAction ────────────────────────────────
    action_types: set = set()
    for raw_schema in schema_result.raw_schemas:
        _extract_actions(raw_schema, action_types)

    if action_types:
        result.has_potential_action = True
        result.potential_actions = sorted(action_types)

    # ── 3. Form accessibili (agent-usable) ───────────────────────
    forms = soup.find_all("form")
    labeled_count = 0
    for form in forms:
        # Un form è "agent-usable" se ha:
        # - almeno 1 input con label associata O aria-label O placeholder descrittivo
        # - un action o method definito
        inputs = form.find_all(["input", "select", "textarea"])
        has_labels = False
        for inp in inputs:
            inp_type = (inp.get("type") or "text").lower()
            if inp_type in ("hidden", "submit", "button"):
                continue
            # Label associata via for/id
            inp_id = inp.get("id")
            if inp_id and form.find("label", attrs={"for": inp_id}):
                has_labels = True
                break
            # aria-label o placeholder
            if inp.get("aria-label") or inp.get("placeholder"):
                has_labels = True
                break
        if has_labels and len(inputs) > 0:
            labeled_count += 1

    if labeled_count > 0:
        result.has_labeled_forms = True
        result.labeled_forms_count = labeled_count

    # ── 4. OpenAPI/Swagger detection ─────────────────────────────
    openapi_patterns = ["/api-docs", "/swagger", "openapi.json", "openapi.yaml", "swagger.json"]
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].lower()
        if any(pattern in href for pattern in openapi_patterns):
            result.has_openapi = True
            break
    # Anche nei link tag
    if not result.has_openapi:
        for link in soup.find_all("link", href=True):
            href = link["href"].lower()
            if any(pattern in href for pattern in openapi_patterns):
                result.has_openapi = True
                break

    # ── Readiness level ──────────────────────────────────────────
    webmcp_signals = sum([result.has_register_tool, result.has_tool_attributes])
    agent_signals = sum([result.has_potential_action, result.has_labeled_forms, result.has_openapi])

    if webmcp_signals > 0 and agent_signals >= 2:
        result.readiness_level = "advanced"
        result.agent_ready = True
    elif webmcp_signals > 0 or agent_signals >= 2:
        result.readiness_level = "ready"
        result.agent_ready = True
    elif agent_signals >= 1:
        result.readiness_level = "basic"
    else:
        result.readiness_level = "none"

    return result


def audit_negative_signals(soup, raw_html, content_result, meta_result, schema_result) -> NegativeSignalsResult:
    """Rileva segnali negativi che riducono la citabilità AI.

    Basato su UC Berkeley EMNLP 2024 e analisi LLM-perspective.
    Zero fetch HTTP — lavora solo su dati già disponibili.

    Args:
        soup: BeautifulSoup della pagina.
        raw_html: HTML grezzo (non usato direttamente, disponibile per future estensioni).
        content_result: ContentResult già calcolato.
        meta_result: MetaResult già calcolato.
        schema_result: SchemaResult già calcolato.

    Returns:
        NegativeSignalsResult con i segnali negativi rilevati.
    """
    from collections import Counter

    result = NegativeSignalsResult()
    if soup is None:
        return result

    result.checked = True

    # ── 1. CTA density (auto-promozionale) ───────────────────────
    # Pattern CTA aggressivi
    cta_patterns = re.compile(
        r"\b(buy now|sign up|subscribe|get started|free trial|order now|"
        r"act now|limited time|don.t miss|hurry|compra ora|iscriviti|"
        r"prova gratis|acquista|registrati|offerta limitata)\b",
        re.IGNORECASE,
    )
    text = soup.get_text(separator=" ", strip=True)
    cta_matches = cta_patterns.findall(text)
    result.cta_count = len(cta_matches)
    # > 5 CTA in una pagina = eccessivo
    word_count = content_result.word_count if content_result.word_count > 0 else max(len(text.split()), 1)
    if result.cta_count > 5 or (word_count > 0 and result.cta_count / word_count > 0.01):
        result.cta_density_high = True

    # ── 2. Popup/interstitial nel DOM ────────────────────────────
    popup_classes = ["modal", "popup", "overlay", "interstitial", "lightbox", "cookie-banner"]
    for cls in popup_classes:
        elements = soup.find_all(attrs={"class": lambda c, _cls=cls: c and _cls in str(c).lower()})
        if elements:
            result.popup_indicators.append(cls)
    # Anche data attributes
    for attr in ["data-modal", "data-popup", "data-overlay"]:
        if soup.find(attrs={attr: True}):
            result.popup_indicators.append(attr)
    result.has_popup_signals = len(result.popup_indicators) > 0

    # ── 3. Thin content ──────────────────────────────────────────
    # < 300 parole E ha un H1 che promette contenuto sostanziale
    if content_result.word_count < 300:
        h1 = content_result.h1_text.lower() if content_result.h1_text else ""
        # H1 che promette contenuto complesso
        complex_patterns = [
            "guide",
            "guida",
            "tutorial",
            "how to",
            "come",
            "complete",
            "completa",
            "definitive",
            "definitiva",
            "everything",
            "tutto",
        ]
        if any(p in h1 for p in complex_patterns) or content_result.heading_count >= 3:
            result.is_thin_content = True

    # ── 4. Broken/empty links ────────────────────────────────────
    broken_count = 0
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if href in ("", "#", "javascript:void(0)", "javascript:;", "javascript:void(0);"):
            broken_count += 1
    result.broken_links_count = broken_count
    result.has_broken_links = broken_count > 3

    # ── 5. Keyword stuffing ──────────────────────────────────────
    # Calcola frequenza parole (escluse stop words e parole corte)
    stop_words = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "it",
        "this",
        "that",
        "not",
        "no",
        "as",
        "by",
        "from",
        "il",
        "la",
        "le",
        "lo",
        "gli",
        "un",
        "una",
        "di",
        "da",
        "del",
        "che",
        "per",
        "con",
        "su",
        "al",
        "dei",
        "nel",
        "è",
        "sono",
        "ha",
        "hanno",
        "più",
        "anche",
        "come",
        "se",
        "non",
        "i",
    }
    words = re.findall(r"\b[a-zA-ZÀ-ÿ]{4,}\b", text.lower())
    if len(words) > 50:
        freq = Counter(w for w in words if w not in stop_words)
        total = len(words)
        for word, count in freq.most_common(3):
            density = count / total
            # > 3% density per una singola parola = stuffing
            if density > 0.03 and count >= 5:
                result.has_keyword_stuffing = True
                result.stuffed_word = word
                result.stuffed_density = round(density * 100, 1)
                break

    # ── 6. Assenza autore ────────────────────────────────────────
    # Cerca Person schema
    for raw_schema in schema_result.raw_schemas:
        schemas_to_check = []
        if isinstance(raw_schema, dict) and "@graph" in raw_schema:
            schemas_to_check.extend(raw_schema["@graph"])
        elif isinstance(raw_schema, dict):
            schemas_to_check.append(raw_schema)
        for s in schemas_to_check:
            s_type = s.get("@type", "")
            if isinstance(s_type, list):
                s_type = s_type[0] if s_type else ""
            if s_type == "Person":
                result.has_author_signal = True
                break
            # author nested
            if s.get("author"):
                result.has_author_signal = True
                break
        if result.has_author_signal:
            break

    # Anche rel=author o class=author nel HTML
    if not result.has_author_signal and (
        soup.find("a", rel="author") or soup.find(attrs={"class": lambda c: c and "author" in str(c).lower()})
    ):
        result.has_author_signal = True

    # ── 7. Boilerplate ratio ─────────────────────────────────────
    # Contenuto in <main>, <article>, role="main" vs totale
    main_content = soup.find("main") or soup.find("article") or soup.find(attrs={"role": "main"})
    total_text_len = len(text)
    if main_content and total_text_len > 0:
        main_text_len = len(main_content.get_text(separator=" ", strip=True))
        result.boilerplate_ratio = round(1.0 - (main_text_len / total_text_len), 2)
    elif total_text_len > 0:
        # No <main>/<article> — stima nav+footer
        nav_footer_len = 0
        for tag in soup.find_all(["nav", "footer", "header"]):
            nav_footer_len += len(tag.get_text(separator=" ", strip=True))
        if nav_footer_len > 0:
            result.boilerplate_ratio = round(nav_footer_len / total_text_len, 2)
    result.boilerplate_high = result.boilerplate_ratio > 0.6

    # ── 8. Mixed signals ─────────────────────────────────────────
    # H1 promette molto, contenuto poco
    h1 = content_result.h1_text.lower() if content_result.h1_text else ""
    big_promise_words = [
        "complete",
        "completa",
        "ultimate",
        "definitiva",
        "comprehensive",
        "everything",
        "tutto",
        "in-depth",
        "approfondita",
    ]
    if any(w in h1 for w in big_promise_words) and content_result.word_count < 1000:
        result.has_mixed_signals = True
        result.mixed_signal_detail = f"H1 promises depth but only {content_result.word_count} words"

    # ── Summary ──────────────────────────────────────────────────
    negatives = [
        result.cta_density_high,
        result.has_popup_signals,
        result.is_thin_content,
        result.has_broken_links,
        result.has_keyword_stuffing,
        not result.has_author_signal,  # assenza autore = negativo
        result.boilerplate_high,
        result.has_mixed_signals,
    ]
    result.signals_found = sum(negatives)

    if result.signals_found >= 4:
        result.severity = "high"
    elif result.signals_found >= 2:
        result.severity = "medium"
    elif result.signals_found >= 1:
        result.severity = "low"
    else:
        result.severity = "clean"

    return result
