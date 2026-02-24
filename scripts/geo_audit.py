#!/usr/bin/env python3
"""
GEO Audit Script — Generative Engine Optimization
Checks the GEO configuration of a website.

Author: Juan Camilo Auriti (juancamilo.auriti@gmail.com)


Usage:
    ./geo scripts/geo_audit.py --url https://example.com
    ./geo scripts/geo_audit.py --url https://example.com --verbose
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

# Dependencies are imported lazily inside main() so --help always works.
requests = None
BeautifulSoup = None


def _ensure_deps():
    global requests, BeautifulSoup
    if requests is not None:
        return
    try:
        import requests as _requests
        from bs4 import BeautifulSoup as _BS
        requests = _requests
        BeautifulSoup = _BS
    except ImportError:
        print("❌ Missing dependencies. Run: pip install requests beautifulsoup4")
        print("   Or use the ./geo wrapper which activates the bundled venv automatically.")
        sys.exit(1)

# ─── AI bots that should be listed in robots.txt ──────────────────────────────
AI_BOTS = {
    "GPTBot": "OpenAI (ChatGPT training)",
    "OAI-SearchBot": "OpenAI (ChatGPT search citations)",
    "ChatGPT-User": "OpenAI (ChatGPT on-demand fetch)",
    "anthropic-ai": "Anthropic (Claude training)",
    "ClaudeBot": "Anthropic (Claude citations)",
    "claude-web": "Anthropic (Claude web crawl)",
    "PerplexityBot": "Perplexity AI (index builder)",
    "Perplexity-User": "Perplexity (citation fetch on-demand)",
    "Google-Extended": "Google (Gemini training)",
    "Applebot-Extended": "Apple (AI training)",
    "cohere-ai": "Cohere (language models)",
    "DuckAssistBot": "DuckDuckGo AI",
    "Bytespider": "ByteDance/TikTok AI",
    "meta-externalagent": "Meta AI (Facebook/Instagram AI)",
}

# Critical citation bots (search-oriented, not just training)
CITATION_BOTS = {"OAI-SearchBot", "ClaudeBot", "PerplexityBot"}

# ─── Schema types to look for ─────────────────────────────────────────────────
VALUABLE_SCHEMAS = [
    "WebSite", "WebApplication", "FAQPage", "Article", "BlogPosting",
    "HowTo", "Recipe", "Product", "Organization", "Person", "BreadcrumbList"
]

HEADERS = {
    "User-Agent": "GEO-Audit/1.0 (https://github.com/auriti-web-design/geo-optimizer-skill)"
}

# Global verbose flag (set in main())
VERBOSE = False


def print_header(text: str):
    width = 60
    print("\n" + "=" * width)
    print(f"  {text}")
    print("=" * width)


def ok(msg: str):
    print(f"  ✅ {msg}")


def fail(msg: str):
    print(f"  ❌ {msg}")


def warn(msg: str):
    print(f"  ⚠️  {msg}")


def info(msg: str):
    print(f"  ℹ️  {msg}")


def fetch_url(url: str, timeout: int = 10):
    """
    Fetch a URL with automatic retry on transient failures.
    
    Retry strategy:
    - 3 attempts with exponential backoff (1s, 2s, 4s)
    - Retries on: connection errors, timeouts, 5xx server errors, 429 rate limit
    
    Returns:
        tuple: (response, error_msg) where response is None on failure
    """
    from http_utils import create_session_with_retry
    
    try:
        session = create_session_with_retry(
            total_retries=3,
            backoff_factor=1.0,
            status_forcelist=[408, 429, 500, 502, 503, 504]
        )
        r = session.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        return r, None
    except requests.exceptions.Timeout:
        return None, f"Timeout ({timeout}s) after 3 retries"
    except requests.exceptions.ConnectionError as e:
        return None, f"Connection failed after 3 retries: {e}"
    except Exception as e:
        return None, str(e)


def audit_robots_txt(base_url: str) -> dict:
    """Check robots.txt for AI bot access."""
    print_header("1. ROBOTS.TXT — AI Bot Access")
    robots_url = urljoin(base_url, "/robots.txt")
    r, err = fetch_url(robots_url)

    results = {
        "found": False,
        "bots_allowed": [],
        "bots_missing": [],
        "bots_blocked": [],
        "citation_bots_ok": False,
    }

    if err or not r:
        fail(f"robots.txt not reachable: {err}")
        return results

    if r.status_code == 404:
        fail("robots.txt not found (404)")
        return results

    if r.status_code != 200:
        warn(f"robots.txt status: {r.status_code}")

    results["found"] = True
    ok(f"robots.txt found ({r.status_code})")

    content = r.text

    if VERBOSE:
        print(f"     → Size: {len(content)} bytes")
        print(f"     → Preview: {content[:200]}...")
        print()

    # Parse robots.txt — collect rules per agent (supports Allow, Disallow, stacking)
    agent_rules = {}  # agent -> {"allow": [...], "disallow": [...]}
    current_agents = []
    last_was_agent = False  # track consecutive User-agent lines for stacking

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        lower = line.lower()
        if lower.startswith("user-agent:"):
            agent = line.split(":", 1)[1].strip()
            agent = agent.split("#")[0].strip()  # strip inline comments
            # RFC 9309: consecutive User-agent lines share the same rules
            if not last_was_agent:
                current_agents = []
            if agent not in agent_rules:
                agent_rules[agent] = {"allow": [], "disallow": []}
            current_agents.append(agent)
            last_was_agent = True
        elif lower.startswith("disallow:"):
            path = line.split(":", 1)[1].strip()
            path = path.split("#")[0].strip()
            for agent in current_agents:
                agent_rules[agent]["disallow"].append(path)
            last_was_agent = False
        elif lower.startswith("allow:"):
            path = line.split(":", 1)[1].strip()
            path = path.split("#")[0].strip()
            for agent in current_agents:
                agent_rules[agent]["allow"].append(path)
            last_was_agent = False
        else:
            last_was_agent = False

    print()
    for bot, description in AI_BOTS.items():
        # Find matching agent (case-insensitive), fallback to wildcard *
        found_agent = None
        for agent in agent_rules:
            if agent.lower() == bot.lower():
                found_agent = agent
                break

        # Fallback to wildcard User-agent: *
        if found_agent is None and "*" in agent_rules:
            found_agent = "*"

        if found_agent is None:
            results["bots_missing"].append(bot)
            if bot in CITATION_BOTS:
                fail(f"{bot} NOT configured — CRITICAL for AI citations! ({description})")
            else:
                warn(f"{bot} not configured ({description})")
        else:
            rules = agent_rules[found_agent]
            disallows = rules["disallow"]
            allows = rules["allow"]

            # Check if fully blocked (Disallow: / or Disallow: /*)
            is_blocked = any(d in ["/", "/*"] for d in disallows)
            # Check if Allow overrides the block (Allow: / explicitly re-allows)
            has_allow_root = any(a in ["/", "/*"] for a in allows)

            if is_blocked and not has_allow_root:
                results["bots_blocked"].append(bot)
                if bot in CITATION_BOTS:
                    fail(f"{bot} BLOCKED — will not appear in AI citations!")
                else:
                    warn(f"{bot} blocked (training disabled) — OK if intentional")
            elif not disallows or all(d == "" for d in disallows):
                results["bots_allowed"].append(bot)
                ok(f"{bot} allowed ✓ ({description})")
            else:
                results["bots_allowed"].append(bot)
                ok(f"{bot} partially allowed: disallow={disallows} ({description})")

    # Summary citation bots
    citation_ok = all(b in results["bots_allowed"] for b in CITATION_BOTS)
    results["citation_bots_ok"] = citation_ok
    print()
    if citation_ok:
        ok("All critical CITATION bots are correctly configured")
    else:
        missing_cit = [b for b in CITATION_BOTS if b not in results["bots_allowed"]]
        fail(f"Missing/blocked CITATION bots: {', '.join(missing_cit)}")

    return results


def audit_llms_txt(base_url: str) -> dict:
    """Check for presence and quality of llms.txt."""
    print_header("2. LLMS.TXT — AI Index File")
    llms_url = urljoin(base_url, "/llms.txt")
    r, err = fetch_url(llms_url)

    results = {
        "found": False,
        "has_h1": False,
        "has_description": False,
        "has_sections": False,
        "has_links": False,
        "word_count": 0,
    }

    if err or not r:
        fail(f"llms.txt not reachable: {err}")
        info("Generate with: ./geo scripts/generate_llms_txt.py --base-url " + base_url)
        return results

    if r.status_code == 404:
        fail("llms.txt not found — essential for AI indexing!")
        info("Generate with: ./geo scripts/generate_llms_txt.py --base-url " + base_url)
        return results

    results["found"] = True
    content = r.text
    lines = content.splitlines()
    results["word_count"] = len(content.split())

    ok(f"llms.txt found ({r.status_code}, {len(content)} bytes, ~{results['word_count']} words)")
    
    if VERBOSE:
        print(f"     → Total lines: {len(lines)}")
        print(f"     → Preview: {content[:300]}...")
        print()

    # Check H1 (required)
    h1_lines = [l for l in lines if l.startswith("# ")]
    if h1_lines:
        results["has_h1"] = True
        ok(f"H1 present: {h1_lines[0]}")
    else:
        fail("H1 missing — the spec requires a mandatory H1 title")

    # Check blockquote description
    blockquotes = [l for l in lines if l.startswith("> ")]
    if blockquotes:
        results["has_description"] = True
        ok("Blockquote description present")
    else:
        warn("Blockquote description missing (recommended)")

    # Check H2 sections
    h2_lines = [l for l in lines if l.startswith("## ")]
    if h2_lines:
        results["has_sections"] = True
        ok(f"H2 sections present: {len(h2_lines)} ({', '.join(l[3:] for l in h2_lines[:3])}...)")
    else:
        warn("No H2 sections — add sections to organize links")

    # Check markdown links
    import re
    links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
    if links:
        results["has_links"] = True
        ok(f"Links found: {len(links)} links to site pages")
    else:
        warn("No links found — add links to main pages")

    return results


def audit_schema(soup: BeautifulSoup, url: str) -> dict:
    """Check JSON-LD schema on the homepage."""
    print_header("3. SCHEMA JSON-LD — Structured Data")

    results = {
        "found_types": [],
        "has_website": False,
        "has_webapp": False,
        "has_faq": False,
        "raw_schemas": [],
    }

    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    if not scripts:
        fail("No JSON-LD schema found on homepage")
        info("Add WebSite + WebApplication + FAQPage schemas")
        return results

    ok(f"Found {len(scripts)} JSON-LD blocks")
    
    if VERBOSE:
        print(f"     → Parsing {len(scripts)} schema blocks...")
        print()

    for i, script in enumerate(scripts):
        try:
            data = json.loads(script.string)
            schemas = data if isinstance(data, list) else [data]

            for schema in schemas:
                schema_type = schema.get("@type", "unknown")
                if isinstance(schema_type, list):
                    schema_types = schema_type
                else:
                    schema_types = [schema_type]

                for t in schema_types:
                    results["found_types"].append(t)
                    results["raw_schemas"].append(schema)

                    if t == "WebSite":
                        results["has_website"] = True
                        ok(f"WebSite schema ✓ (url: {schema.get('url', 'n/a')})")
                        if VERBOSE:
                            print(f"        → name: {schema.get('name', 'n/a')}")
                            print(f"        → description: {schema.get('description', 'n/a')[:80]}...")
                    elif t == "WebApplication":
                        results["has_webapp"] = True
                        ok(f"WebApplication schema ✓ (name: {schema.get('name', 'n/a')})")
                        if VERBOSE:
                            print(f"        → applicationCategory: {schema.get('applicationCategory', 'n/a')}")
                    elif t == "FAQPage":
                        results["has_faq"] = True
                        entities = schema.get("mainEntity", [])
                        ok(f"FAQPage schema ✓ ({len(entities)} questions)")
                        if VERBOSE and entities:
                            print(f"        → First question: {entities[0].get('name', 'n/a')[:80]}...")
                    elif t in VALUABLE_SCHEMAS:
                        ok(f"{t} schema ✓")
                    else:
                        info(f"Schema type: {t}")

        except json.JSONDecodeError as e:
            warn(f"JSON-LD #{i+1} invalid: {e}")

    if not results["has_website"]:
        fail("WebSite schema missing — essential for AI entity understanding")
    elif results["found_types"].count("WebSite") > 1:
        warn(f"Multiple WebSite schemas found ({results['found_types'].count('WebSite')}) — keep only one per page")
    if not results["has_faq"]:
        warn("FAQPage schema missing — very useful for AI citations on questions")

    return results


def audit_meta_tags(soup: BeautifulSoup, url: str) -> dict:
    """Check SEO/GEO meta tags."""
    print_header("4. META TAGS — SEO & Open Graph")

    results = {
        "has_title": False,
        "has_description": False,
        "has_canonical": False,
        "has_og_title": False,
        "has_og_description": False,
        "has_og_image": False,
    }

    # Title
    title_tag = soup.find("title")
    if title_tag and title_tag.text.strip():
        results["has_title"] = True
        title_text = title_tag.text.strip()
        if len(title_text) > 60:
            warn(f"Title present but long ({len(title_text)} chars): {title_text[:60]}...")
        else:
            ok(f"Title: {title_text}")
    else:
        fail("Title missing")

    # Meta description
    desc = soup.find("meta", attrs={"name": "description"})
    if desc and desc.get("content", "").strip():
        results["has_description"] = True
        content = desc["content"].strip()
        if len(content) < 120:
            warn(f"Meta description short ({len(content)} chars): {content}")
        elif len(content) > 160:
            warn(f"Meta description long ({len(content)} chars) — may be truncated")
        else:
            ok(f"Meta description ({len(content)} chars) ✓")
    else:
        fail("Meta description missing — important for AI snippets")

    # Canonical
    canonical = soup.find("link", attrs={"rel": "canonical"})
    if canonical and canonical.get("href"):
        results["has_canonical"] = True
        ok(f"Canonical: {canonical['href']}")
    else:
        warn("Canonical URL missing")

    # Open Graph
    og_title = soup.find("meta", attrs={"property": "og:title"})
    og_desc = soup.find("meta", attrs={"property": "og:description"})
    og_image = soup.find("meta", attrs={"property": "og:image"})

    if og_title and og_title.get("content"):
        results["has_og_title"] = True
        ok("og:title ✓")
    else:
        warn("og:title missing")

    if og_desc and og_desc.get("content"):
        results["has_og_description"] = True
        ok("og:description ✓")
    else:
        warn("og:description missing")

    if og_image and og_image.get("content"):
        results["has_og_image"] = True
        ok("og:image ✓")
    else:
        warn("og:image missing")

    return results


def audit_content_quality(soup: BeautifulSoup, url: str) -> dict:
    """Check content quality for GEO."""
    print_header("5. CONTENT QUALITY — GEO Best Practices")

    results = {
        "has_h1": False,
        "heading_count": 0,
        "has_numbers": False,
        "has_links": False,
        "word_count": 0,
    }

    # H1
    h1 = soup.find("h1")
    if h1:
        results["has_h1"] = True
        h1_text = h1.text.strip()[:60]
        ok(f"H1: {h1_text}")
        if VERBOSE:
            print(f"     → Full H1: {h1.text.strip()}")
            print()
    else:
        warn("H1 missing on homepage")

    # Headings
    headings = soup.find_all(["h1", "h2", "h3", "h4"])
    results["heading_count"] = len(headings)
    if len(headings) >= 3:
        ok(f"Good heading structure: {len(headings)} headings (H1–H4)")
    elif len(headings) > 0:
        warn(f"Few headings: {len(headings)} — add more H2/H3 structure")

    # Check for numbers/statistics
    import re
    body_text = soup.get_text()
    numbers = re.findall(r'\b\d+[%€$£]|\b\d+\.\d+|\b\d{3,}\b', body_text)
    if len(numbers) >= 3:
        results["has_numbers"] = True
        ok(f"Numerical data present: {len(numbers)} numbers/statistics found ✓")
    else:
        warn("Few numerical data points — add concrete statistics for +40% AI visibility")

    # Word count
    words = body_text.split()
    results["word_count"] = len(words)
    if len(words) >= 300:
        ok(f"Sufficient content: ~{len(words)} words")
    else:
        warn(f"Thin content: ~{len(words)} words — add more descriptive content")

    # External links (citations)
    parsed = urlparse(url)
    base_domain = parsed.netloc
    all_links = soup.find_all("a", href=True)
    external_links = [l for l in all_links if l["href"].startswith("http") and base_domain not in l["href"]]
    if external_links:
        results["has_links"] = True
        ok(f"External links (citations): {len(external_links)} links to external sources ✓")
    else:
        warn("No external source links — cite authoritative sources for +40% AI visibility")

    return results


def compute_geo_score(robots: dict, llms: dict, schema: dict, meta: dict, content: dict) -> int:
    """Calculate a GEO score from 0 to 100."""
    score = 0

    # robots.txt (20 points)
    if robots["found"]:
        score += 5
    if robots["citation_bots_ok"]:
        score += 15
    elif robots["bots_allowed"]:
        score += 8

    # llms.txt (20 points)
    if llms["found"]:
        score += 10
        if llms["has_h1"]: score += 3
        if llms["has_sections"]: score += 4
        if llms["has_links"]: score += 3

    # Schema (25 points)
    if schema["has_website"]: score += 10
    if schema["has_faq"]: score += 10
    if schema["has_webapp"]: score += 5

    # Meta tags (20 points)
    if meta["has_title"]: score += 5
    if meta["has_description"]: score += 8
    if meta["has_canonical"]: score += 3
    if meta["has_og_title"] and meta["has_og_description"]: score += 4

    # Content (15 points)
    if content["has_h1"]: score += 4
    if content["has_numbers"]: score += 6
    if content["has_links"]: score += 5

    return min(score, 100)


def main():
    parser = argparse.ArgumentParser(
        description="GEO Audit — Check AI search optimization of a website",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./geo scripts/geo_audit.py --url https://example.com
  ./geo scripts/geo_audit.py --url https://example.com --verbose
  ./geo scripts/geo_audit.py --url https://example.com --format json
  ./geo scripts/geo_audit.py --url https://example.com --format json --output report.json
        """
    )
    parser.add_argument("--url", required=True, help="URL of the site to audit (e.g. https://example.com)")
    parser.add_argument("--verbose", action="store_true", help="Show detailed check output with raw data for debugging")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format: text (default) or json")
    parser.add_argument("--output", help="Output file path (optional, writes to stdout if not specified)")
    args = parser.parse_args()

    _ensure_deps()
    
    # Set global verbose flag
    global VERBOSE
    VERBOSE = args.verbose

    # Normalize URL
    base_url = args.url.rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url

    # Suppress verbose output in JSON mode
    json_mode = args.format == "json"
    if json_mode:
        VERBOSE = False  # JSON mode overrides verbose
    
    if not json_mode:
        print("\n" + "🔍 " * 20)
        print(f"  GEO AUDIT — {base_url}")
        print(f"  github.com/auriti-web-design/geo-optimizer-skill")
        print("🔍 " * 20)

    # Fetch homepage
    if not json_mode:
        print("\n⏳ Fetching homepage...")
    r, err = fetch_url(base_url)
    if err or not r:
        if json_mode:
            error_data = {"error": f"Unable to reach {base_url}: {err}", "url": base_url}
            print(json.dumps(error_data, indent=2))
        else:
            print(f"\n❌ ERROR: Unable to reach {base_url}: {err}")
        sys.exit(1)

    soup = BeautifulSoup(r.text, "html.parser")
    if not json_mode:
        print(f"   Status: {r.status_code} | Size: {len(r.text):,} bytes")
        if VERBOSE:
            print(f"   Response time: {r.elapsed.total_seconds():.2f}s")
            print(f"   Content-Type: {r.headers.get('Content-Type', 'n/a')}")

    # Run audits (suppressing print output in JSON mode)
    import io
    import contextlib

    if json_mode:
        devnull = io.StringIO()
        ctx = contextlib.redirect_stdout(devnull)
    else:
        ctx = contextlib.nullcontext()

    with ctx:
        robots_results = audit_robots_txt(base_url)
        llms_results = audit_llms_txt(base_url)
        schema_results = audit_schema(soup, base_url)
        meta_results = audit_meta_tags(soup, base_url)
        content_results = audit_content_quality(soup, base_url)

    # Final score
    score = compute_geo_score(robots_results, llms_results, schema_results, meta_results, content_results)

    # Determine score band
    if score >= 91:
        band = "excellent"
    elif score >= 71:
        band = "good"
    elif score >= 41:
        band = "foundation"
    else:
        band = "critical"

    # Build recommendations
    recommendations = []
    if not robots_results["citation_bots_ok"]:
        recommendations.append("Update robots.txt with all AI bots (see SKILL.md)")
    if not llms_results["found"]:
        recommendations.append(f"Create /llms.txt: ./geo scripts/generate_llms_txt.py --base-url {base_url}")
    if not schema_results["has_website"]:
        recommendations.append("Add WebSite JSON-LD schema")
    if not schema_results["has_faq"]:
        recommendations.append("Add FAQPage schema with frequently asked questions")
    if not meta_results["has_description"]:
        recommendations.append("Add optimized meta description")
    if not content_results["has_numbers"]:
        recommendations.append("Add concrete numerical statistics (+40% AI visibility)")
    if not content_results["has_links"]:
        recommendations.append("Cite authoritative sources with external links")

    # JSON output
    if args.format == "json":
        output_data = {
            "url": base_url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "score": score,
            "band": band,
            "checks": {
                "robots_txt": {
                    "score": 20 if robots_results["citation_bots_ok"] else (13 if robots_results["bots_allowed"] else (5 if robots_results["found"] else 0)),
                    "max": 20,
                    "passed": robots_results["citation_bots_ok"],
                    "details": {
                        "found": robots_results["found"],
                        "citation_bots_ok": robots_results["citation_bots_ok"],
                        "bots_allowed": robots_results["bots_allowed"],
                        "bots_blocked": robots_results["bots_blocked"],
                        "bots_missing": robots_results["bots_missing"]
                    }
                },
                "llms_txt": {
                    "score": (10 if llms_results["found"] else 0) + 
                             (3 if llms_results["has_h1"] else 0) +
                             (4 if llms_results["has_sections"] else 0) +
                             (3 if llms_results["has_links"] else 0),
                    "max": 20,
                    "passed": llms_results["found"] and llms_results["has_h1"],
                    "details": {
                        "found": llms_results["found"],
                        "has_h1": llms_results["has_h1"],
                        "has_description": llms_results["has_description"],
                        "has_sections": llms_results["has_sections"],
                        "has_links": llms_results["has_links"],
                        "word_count": llms_results["word_count"]
                    }
                },
                "schema_jsonld": {
                    "score": (10 if schema_results["has_website"] else 0) +
                             (10 if schema_results["has_faq"] else 0) +
                             (5 if schema_results["has_webapp"] else 0),
                    "max": 25,
                    "passed": schema_results["has_website"],
                    "details": {
                        "has_website": schema_results["has_website"],
                        "has_webapp": schema_results["has_webapp"],
                        "has_faq": schema_results["has_faq"],
                        "found_types": schema_results["found_types"]
                    }
                },
                "meta_tags": {
                    "score": (5 if meta_results["has_title"] else 0) +
                             (8 if meta_results["has_description"] else 0) +
                             (3 if meta_results["has_canonical"] else 0) +
                             (4 if (meta_results["has_og_title"] and meta_results["has_og_description"]) else 0),
                    "max": 20,
                    "passed": meta_results["has_title"] and meta_results["has_description"],
                    "details": {
                        "has_title": meta_results["has_title"],
                        "has_description": meta_results["has_description"],
                        "has_canonical": meta_results["has_canonical"],
                        "has_og_title": meta_results["has_og_title"],
                        "has_og_description": meta_results["has_og_description"],
                        "has_og_image": meta_results["has_og_image"]
                    }
                },
                "content": {
                    "score": (4 if content_results["has_h1"] else 0) +
                             (6 if content_results["has_numbers"] else 0) +
                             (5 if content_results["has_links"] else 0),
                    "max": 15,
                    "passed": content_results["has_h1"],
                    "details": {
                        "has_h1": content_results["has_h1"],
                        "heading_count": content_results["heading_count"],
                        "has_numbers": content_results["has_numbers"],
                        "has_links": content_results["has_links"],
                        "word_count": content_results["word_count"]
                    }
                }
            },
            "recommendations": recommendations
        }
        
        json_output = json.dumps(output_data, indent=2)
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_output)
            print(f"✅ JSON report written to: {args.output}")
        else:
            print(json_output)
    
    # Text output (default)
    else:
        print_header("📊 FINAL GEO SCORE")
        bar_filled = int(score / 5)
        bar_empty = 20 - bar_filled
        bar = "█" * bar_filled + "░" * bar_empty
        print(f"\n  [{bar}] {score}/100")

        if score >= 91:
            print(f"\n  🏆 EXCELLENT — Site is well optimized for AI search engines!")
        elif score >= 71:
            print(f"\n  ✅ GOOD — Core optimizations in place, fine-tune content and schema")
        elif score >= 41:
            print(f"\n  ⚠️  FOUNDATION — Core elements missing, implement priority fixes below")
        else:
            print(f"\n  ❌ CRITICAL — Site is not visible to AI search engines")

        print(f"\n  Score bands: 0–40 = critical | 41–70 = foundation | 71–90 = good | 91–100 = excellent")

        print("\n  📋 NEXT PRIORITY STEPS:")

        if not recommendations:
            print("  🎉 Great! All main optimizations are implemented.")
        else:
            for i, action in enumerate(recommendations, 1):
                print(f"  {i}. {action}")

        print("\n  Ref: SKILL.md for detailed instructions")
        print("  Ref: references/princeton-geo-methods.md for advanced methods")
        print()

    return score


if __name__ == "__main__":
    main()
