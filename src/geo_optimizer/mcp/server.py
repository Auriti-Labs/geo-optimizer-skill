"""
MCP Server for GEO Optimizer.

Exposes core functionality as MCP tools usable from
Claude Code, Cursor, Windsurf and any MCP client.

Available tools:
    geo_audit            — Full GEO audit (score 0-100)
    geo_fix              — Generate automatic fixes (robots, llms, schema, meta)
    geo_llms_generate    — Generate llms.txt content from sitemap
    geo_schema_validate  — Validate JSON-LD schema

Available resources:
    geo://ai-bots        — List of tracked AI bots
    geo://score-bands    — GEO score bands

Start:
    geo-mcp              # Entry point from pyproject.toml
    python -m geo_optimizer.mcp.server  # Direct
"""

from __future__ import annotations

import json
from dataclasses import asdict
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP

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
        return json.dumps({"error": str(e), "url": url})


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
        valid = {"robots", "llms", "schema", "meta"}
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
        return json.dumps({"error": str(e), "url": url})


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
    """Analyze content citability using the 9 Princeton GEO methods.

    Evaluates page content according to the 9 methods from the
    Princeton KDD 2024 paper (Quotation +41%, Statistics +33%, Fluency +29%,
    Cite Sources +27%, Technical Terms +18%, Authoritative +16%,
    Easy-to-Understand +14%, Unique Words +7%, Keyword Stuffing -9%).

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
        return json.dumps({"error": str(e), "url": url})


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
        return json.dumps({"valid": False, "error": str(e)})


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


# ─── Entry point ──────────────────────────────────────────────────────────────


def main() -> None:
    """Entry point for the MCP server (stdio transport)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
