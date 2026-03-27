"""
MCP Server for GEO Optimizer.

Exposes core functionality as MCP tools usable from
Claude Code, Cursor, Windsurf and any MCP client.

Available tools:
    geo_audit            — Full GEO audit (score 0-100)
    geo_fix              — Generate automatic fixes (robots, llms, schema, meta)
    geo_llms_generate    — Generate llms.txt content from sitemap
    geo_citability       — Citability score (11 Princeton + AutoGEO methods)
    geo_schema_validate  — Validate JSON-LD schema
    geo_compare          — Compare GEO scores across multiple sites
    geo_ai_discovery     — Check AI discovery endpoints (.well-known/ai.txt, etc.)
    geo_check_bots       — Check which AI bots can access via robots.txt

Available resources:
    geo://ai-bots            — List of tracked AI bots
    geo://score-bands        — GEO score bands
    geo://methods            — 42 citability methods with impact data (dynamic)
    geo://changelog          — Latest changes
    geo://ai-discovery-spec  — AI discovery endpoint specification

Start:
    geo-mcp              # Entry point from pyproject.toml
    python -m geo_optimizer.mcp.server  # Direct
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("geo-optimizer")


# ─── Serialization helper ────────────────────────────────────────────────────


def _to_json(data: object) -> str:
    """Serialize dataclass or dict to readable JSON."""
    if hasattr(data, "__dataclass_fields__"):
        data = asdict(data)
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def _normalize_url(url: str) -> str:
    """Normalize URL by adding scheme if missing."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


# ─── Tool 1: geo_audit ───────────────────────────────────────────────────────


@mcp.tool()
def geo_audit(url: str) -> str:
    """Run a complete GEO audit on a website.

    Analyzes 5 areas: robots.txt (AI bot access), llms.txt (AI index),
    JSON-LD schema, SEO meta tags and content quality.
    Returns score 0-100 with details and recommendations.

    Args:
        url: URL of the site to audit (e.g. https://example.com)
    """
    from geo_optimizer.utils.validators import validate_public_url

    url = _normalize_url(url)

    # Anti-SSRF validation
    safe, reason = validate_public_url(url)
    if not safe:
        return json.dumps({"error": f"Unsafe URL: {reason}"})

    try:
        from geo_optimizer.core.audit import run_full_audit

        result = run_full_audit(url)
        return _to_json(result)
    except Exception as e:
        # Fix #314: non esporre str(e) al client — logga internamente
        logger.error("Errore geo_audit per %s: %s", url, e)
        return json.dumps({"error": "Errore interno durante l'operazione", "url": url})


# ─── Tool 2: geo_fix ─────────────────────────────────────────────────────────


@mcp.tool()
def geo_fix(url: str, only: str = "") -> str:
    """Generate automatic GEO fixes for a website.

    Analyzes the site and generates corrective artifacts:
    - robots.txt with missing AI bots
    - Complete llms.txt via sitemap
    - Missing JSON-LD schemas (WebSite, Organization)
    - Missing HTML meta tags

    Args:
        url: URL of the site to optimize (e.g. https://example.com)
        only: Filter categories (comma-separated): robots,llms,schema,meta.
              Empty = all categories.
    """
    from geo_optimizer.utils.validators import validate_public_url

    url = _normalize_url(url)

    safe, reason = validate_public_url(url)
    if not safe:
        return json.dumps({"error": f"Unsafe URL: {reason}"})

    # Parse category filter with validation (fix #186)
    only_set = None
    if only:
        only_set = {c.strip().lower() for c in only.split(",")}
        valid = {"robots", "llms", "schema", "meta", "ai_discovery"}
        invalid = only_set - valid
        if invalid:
            return json.dumps(
                {"error": f"Invalid categories: {', '.join(sorted(invalid))}. Valid: {', '.join(sorted(valid))}"}
            )

    try:
        from geo_optimizer.core.fixer import run_all_fixes

        plan = run_all_fixes(url=url, only=only_set)
        return _to_json(plan)
    except Exception as e:
        # Fix #314: non esporre str(e) al client — logga internamente
        logger.error("Errore geo_fix per %s: %s", url, e)
        return json.dumps({"error": "Errore interno durante l'operazione", "url": url})


# ─── Tool 3: geo_llms_generate ───────────────────────────────────────────────


@mcp.tool()
def geo_llms_generate(url: str) -> str:
    """Generate llms.txt content for a website.

    llms.txt is the AI index file at the site root (spec llmstxt.org).
    Discovers sitemap, categorizes URLs and generates the complete file
    with H1 header, description, H2 sections and markdown links.

    Args:
        url: Base URL of the site (e.g. https://example.com)
    """
    from geo_optimizer.utils.validators import validate_public_url

    url = _normalize_url(url)

    safe, reason = validate_public_url(url)
    if not safe:
        return f"Error: Unsafe URL — {reason}"

    try:
        from geo_optimizer.core.llms_generator import (
            discover_sitemap,
            fetch_sitemap,
            generate_llms_txt,
        )

        parsed = urlparse(url)
        site_name = parsed.netloc.replace("www.", "")

        # Discover and download sitemap
        sitemap_url = discover_sitemap(url)
        urls = []
        if sitemap_url:
            urls = fetch_sitemap(sitemap_url)

        # Generate llms.txt
        content = generate_llms_txt(
            base_url=url,
            urls=urls,
            site_name=site_name,
            description=f"Information about {site_name} for AI search engines",
        )
        return content
    except Exception as e:
        return f"Error: {e}"


# ─── Tool 4: geo_citability ───────────────────────────────────────────────────


@mcp.tool()
def geo_citability(url: str) -> str:
    """Analyze content citability using 42 methods (Princeton GEO + AutoGEO + content analysis).

    Evaluates page content with 42 methods from Princeton KDD 2024,
    AutoGEO ICLR 2026, SE Ranking 2025, and Growth Marshal 2026.

    Returns score 0-100 with per-method detail and suggestions.

    Args:
        url: URL of the page to analyze (e.g. https://example.com)
    """
    from geo_optimizer.utils.validators import validate_public_url

    url = _normalize_url(url)

    safe, reason = validate_public_url(url)
    if not safe:
        return json.dumps({"error": f"Unsafe URL: {reason}"})

    try:
        from bs4 import BeautifulSoup

        from geo_optimizer.core.citability import audit_citability
        from geo_optimizer.utils.http import fetch_url

        r, err = fetch_url(url)
        if err or not r:
            return json.dumps({"error": f"Cannot reach {url}: {err}"})

        soup = BeautifulSoup(r.text, "html.parser")
        result = audit_citability(soup, url)
        return _to_json(result)
    except Exception as e:
        # Fix #314: non esporre str(e) al client — logga internamente
        logger.error("Errore geo_citability per %s: %s", url, e)
        return json.dumps({"error": "Errore interno durante l'operazione", "url": url})


# ─── Tool 5: geo_schema_validate ─────────────────────────────────────────────


@mcp.tool()
def geo_schema_validate(json_string: str, schema_type: str = "") -> str:
    """Validate a JSON-LD schema against schema.org requirements.

    Checks that the JSON-LD contains all required fields
    for the specified schema type (e.g. WebSite, FAQPage, Article).

    Args:
        json_string: JSON-LD string to validate
        schema_type: Schema type (e.g. "website", "faqpage"). If empty, auto-detected.
    """
    # Size limit: prevent DoS from huge JSON-LD (fix #182)
    if len(json_string) > 512 * 1024:
        return json.dumps({"valid": False, "error": "JSON-LD too large (max 512 KB)"})

    try:
        from geo_optimizer.core.schema_validator import validate_jsonld_string

        schema_t = schema_type.strip().lower() if schema_type else None
        is_valid, error_msg = validate_jsonld_string(json_string, schema_t)

        return json.dumps(
            {
                "valid": is_valid,
                "error": error_msg,
                "schema_type": schema_type or "auto-detected",
            }
        )
    except Exception as e:
        # Fix #314: non esporre str(e) al client — logga internamente
        logger.error("Errore geo_schema_validate: %s", e)
        return json.dumps({"valid": False, "error": "Errore interno durante la validazione"})


# ─── Tool 6: geo_compare ──────────────────────────────────────────────────────


@mcp.tool()
def geo_compare(urls: str) -> str:
    """Compare GEO scores across multiple websites (max 5).

    Returns a ranked comparison with score, band and per-category breakdown.

    Args:
        urls: Comma-separated URLs (e.g. "site1.com, site2.com")
    """
    from geo_optimizer.utils.validators import validate_public_url

    url_list = [u.strip() for u in urls.split(",") if u.strip()]
    if not url_list:
        return json.dumps({"error": "Nessuna URL fornita"})
    if len(url_list) > 5:
        return json.dumps({"error": "Massimo 5 URL per confronto"})

    results = []
    for u in url_list:
        u = _normalize_url(u)
        safe, reason = validate_public_url(u)
        if not safe:
            results.append({"url": u, "error": f"URL non sicura: {reason}"})
            continue
        try:
            from geo_optimizer.core.audit import run_full_audit

            result = run_full_audit(u)
            results.append(
                {
                    "url": u,
                    "score": result.score,
                    "band": result.band,
                    "breakdown": result.score_breakdown,
                    "recommendations_count": len(result.recommendations),
                }
            )
        except Exception as e:
            # Fix #314: non esporre str(e) al client — logga internamente
            logger.error("Errore geo_compare per %s: %s", u, e)
            results.append({"url": u, "error": "Errore interno durante l'operazione"})

    # Ordina per score decrescente
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return json.dumps({"comparison": results, "total_sites": len(results)}, indent=2)


# ─── Tool 7: geo_ai_discovery ────────────────────────────────────────────────


@mcp.tool()
def geo_ai_discovery(url: str) -> str:
    """Check AI discovery endpoints on a website.

    Verifies: /.well-known/ai.txt, /ai/summary.json, /ai/faq.json, /ai/service.json
    Based on the emerging geo-checklist.dev standard.

    Args:
        url: URL to check (e.g. https://example.com)
    """
    from geo_optimizer.utils.validators import validate_public_url

    url = _normalize_url(url)
    safe, reason = validate_public_url(url)
    if not safe:
        return json.dumps({"error": f"URL non sicura: {reason}"})

    try:
        from geo_optimizer.core.audit import audit_ai_discovery

        result = audit_ai_discovery(url)
        return _to_json(result)
    except Exception as e:
        # Fix #314: non esporre str(e) al client — logga internamente
        logger.error("Errore geo_ai_discovery per %s: %s", url, e)
        return json.dumps({"error": "Errore interno durante l'operazione", "url": url})


# ─── Tool 8: geo_check_bots ──────────────────────────────────────────────────


@mcp.tool()
def geo_check_bots(url: str) -> str:
    """Check which AI bots can access a website via robots.txt.

    Returns per-bot status (allowed/blocked/missing) with tier classification
    (training/search/user) and citation bot verification.

    Args:
        url: URL to check (e.g. https://example.com)
    """
    from geo_optimizer.utils.validators import validate_public_url

    url = _normalize_url(url)
    safe, reason = validate_public_url(url)
    if not safe:
        return json.dumps({"error": f"URL non sicura: {reason}"})

    try:
        from geo_optimizer.core.audit import audit_robots_txt
        from geo_optimizer.models.config import AI_BOTS, BOT_TIERS

        result = audit_robots_txt(url)

        # Costruisci dettaglio per-bot con tier
        bot_details = {}
        for bot, desc in AI_BOTS.items():
            tier = "unknown"
            for t, bots in BOT_TIERS.items():
                if bot in bots:
                    tier = t
                    break
            if bot in result.bots_allowed:
                status = "allowed"
            elif bot in result.bots_blocked:
                status = "blocked"
            else:
                status = "missing"
            bot_details[bot] = {"description": desc, "status": status, "tier": tier}

        return json.dumps(
            {
                "url": url,
                "robots_found": result.found,
                "citation_bots_ok": result.citation_bots_ok,
                "bots": bot_details,
                "summary": {
                    "allowed": len(result.bots_allowed),
                    "blocked": len(result.bots_blocked),
                    "missing": len(result.bots_missing),
                },
            },
            indent=2,
        )
    except Exception as e:
        # Fix #314: non esporre str(e) al client — logga internamente
        logger.error("Errore geo_check_bots per %s: %s", url, e)
        return json.dumps({"error": "Errore interno durante l'operazione", "url": url})


# ─── Resource: AI Bots ────────────────────────────────────────────────────────


@mcp.resource("geo://ai-bots")
def get_ai_bots() -> str:
    """List of 16 AI bots tracked by GEO Optimizer with 3-tier classification."""
    from geo_optimizer.models.config import AI_BOTS, BOT_TIERS, CITATION_BOTS

    return json.dumps(
        {
            "ai_bots": AI_BOTS,
            "tiers": {k: sorted(v) for k, v in BOT_TIERS.items()},
            "citation_bots": sorted(CITATION_BOTS),
            "total": len(AI_BOTS),
        },
        indent=2,
    )


# ─── Resource: Score Bands ────────────────────────────────────────────────────


@mcp.resource("geo://score-bands")
def get_score_bands() -> str:
    """GEO score bands (critical 0-40, foundation 41-70, good 71-90, excellent 91-100)."""
    from geo_optimizer.models.config import SCORE_BANDS

    return json.dumps(SCORE_BANDS, indent=2)


# Fix #282: rimossa prima registrazione duplicata di geo://methods

# ─── Resource: Citability Methods ─────────────────────────────────────────────


@mcp.resource("geo://methods")
def get_citability_methods() -> str:
    """All 42 citability methods with measured impact (fix #1: generati dinamicamente dal motore)."""
    from bs4 import BeautifulSoup

    from geo_optimizer.core.citability import audit_citability

    # Genera i metodi da un soup vuoto per ottenere nomi, label, max_score e impact reali
    empty_soup = BeautifulSoup("<html><body></body></html>", "html.parser")
    result = audit_citability(empty_soup, "http://example.com")

    methods = [
        {
            "name": m.name,
            "label": m.label,
            "impact": m.impact,
            "max_score": m.max_score,
        }
        for m in result.methods
    ]
    total_max = sum(m.max_score for m in result.methods)
    return json.dumps(
        {
            "methods": methods,
            "total_methods": len(methods),
            "total_max_score": total_max,
            "note": "Score capped at 100",
            "source": "Princeton KDD 2024 + AutoGEO ICLR 2026 + SE Ranking 2025 + Growth Marshal 2026",
        },
        indent=2,
    )


# ─── Resource: Changelog ─────────────────────────────────────────────────────


@mcp.resource("geo://changelog")
def get_changelog() -> str:
    """Latest changes from CHANGELOG.md (first 50 lines)."""
    from pathlib import Path

    changelog_path = Path(__file__).parent.parent.parent.parent / "CHANGELOG.md"
    if not changelog_path.exists():
        return "CHANGELOG.md not found"
    lines = changelog_path.read_text(encoding="utf-8").splitlines()[:50]
    return "\n".join(lines)


# ─── Resource: AI Discovery Spec ─────────────────────────────────────────────


@mcp.resource("geo://ai-discovery-spec")
def get_ai_discovery_spec() -> str:
    """Specification of AI discovery endpoints (geo-checklist.dev standard)."""
    spec = {
        "standard": "geo-checklist.dev (emerging)",
        "endpoints": [
            {
                "path": "/.well-known/ai.txt",
                "description": "AI crawler permissions (similar to robots.txt but AI-specific)",
                "content_type": "text/plain",
                "required_fields": None,
            },
            {
                "path": "/ai/summary.json",
                "description": "Site summary for AI systems",
                "content_type": "application/json",
                "required_fields": ["name", "description"],
                "schema": {
                    "name": "string",
                    "description": "string (max 800 chars)",
                    "url": "string",
                    "lastModified": "ISO 8601 date",
                },
            },
            {
                "path": "/ai/faq.json",
                "description": "Structured FAQ for AI systems",
                "content_type": "application/json",
                "required_fields": ["questions"],
                "schema": {"questions": [{"question": "string", "answer": "string"}]},
            },
            {
                "path": "/ai/service.json",
                "description": "Service capabilities for AI systems",
                "content_type": "application/json",
                "required_fields": ["name", "capabilities"],
                "schema": {"name": "string", "description": "string", "capabilities": ["string"]},
            },
        ],
    }
    return json.dumps(spec, indent=2)


# ─── Entry point ──────────────────────────────────────────────────────────────


def main() -> None:
    """Entry point for the MCP server (stdio transport)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
