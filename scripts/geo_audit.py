#!/usr/bin/env python3
"""
GEO Audit Script — Generative Engine Optimization
Checks the GEO configuration of a website.

Author: Juan Camilo Auriti (juancamilo.auriti@gmail.com)


Usage:
    python geo_audit.py --url https://example.com
    python geo_audit.py --url https://example.com --verbose
"""

import argparse
import json
import sys
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("❌ Missing dependencies. Install with: pip install requests beautifulsoup4")
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
    "Perplexity-User": "Perplexity (citation fetch)",
    "Google-Extended": "Google (Gemini training)",
    "Applebot-Extended": "Apple (AI training)",
    "cohere-ai": "Cohere (language models)",
    "DuckAssistBot": "DuckDuckGo AI",
    "Bytespider": "ByteDance/TikTok AI",
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
    """Fetch a URL, return (response, error_msg)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        return r, None
    except requests.exceptions.Timeout:
        return None, f"Timeout ({timeout}s)"
    except requests.exceptions.ConnectionError as e:
        return None, f"Connection failed: {e}"
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
    # Parse robots.txt — collect bots by status
    current_agents = []
    agent_rules = {}  # agent -> list of Disallow paths

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("user-agent:"):
            agent = line.split(":", 1)[1].strip()
            current_agents = [agent]
            if agent not in agent_rules:
                agent_rules[agent] = []
        elif line.lower().startswith("disallow:"):
            path = line.split(":", 1)[1].strip()
            for agent in current_agents:
                if agent in agent_rules:
                    agent_rules[agent].append(path)

    print()
    for bot, description in AI_BOTS.items():
        # Check case-insensitive
        found_agent = None
        for agent in agent_rules:
            if agent.lower() == bot.lower():
                found_agent = agent
                break

        if found_agent is None:
            results["bots_missing"].append(bot)
            if bot in CITATION_BOTS:
                fail(f"{bot} NOT configured — CRITICAL for AI citations! ({description})")
            else:
                warn(f"{bot} not configured ({description})")
        else:
            disallows = agent_rules[found_agent]
            if any(d in ["/", "/*"] for d in disallows):
                results["bots_blocked"].append(bot)
                if bot in CITATION_BOTS:
                    fail(f"{bot} BLOCKED — will not appear in AI citations!")
                else:
                    warn(f"{bot} blocked (training disabled) — OK if intentional")
            elif disallows == [] or all(d == "" for d in disallows):
                results["bots_allowed"].append(bot)
                ok(f"{bot} allowed ✓ ({description})")
            else:
                results["bots_allowed"].append(bot)
                ok(f"{bot} partially allowed: {disallows} ({description})")

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
                    elif t == "WebApplication":
                        results["has_webapp"] = True
                        ok(f"WebApplication schema ✓ (name: {schema.get('name', 'n/a')})")
                    elif t == "FAQPage":
                        results["has_faq"] = True
                        entities = schema.get("mainEntity", [])
                        ok(f"FAQPage schema ✓ ({len(entities)} questions)")
                    elif t in VALUABLE_SCHEMAS:
                        ok(f"{t} schema ✓")
                    else:
                        info(f"Schema type: {t}")

        except json.JSONDecodeError as e:
            warn(f"JSON-LD #{i+1} invalid: {e}")

    if not results["has_website"]:
        fail("WebSite schema missing — essential for AI entity understanding")
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
        ok(f"H1: {h1.text.strip()[:60]}")
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
    if schema["has_webapp"]: score += 8
    if schema["has_faq"]: score += 7

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
  python geo_audit.py --url https://example.com
  python geo_audit.py --url https://example.com --verbose
        """
    )
    parser.add_argument("--url", required=True, help="URL of the site to audit (e.g. https://example.com)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # Normalize URL
    base_url = args.url.rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url

    print("\n" + "🔍 " * 20)
    print(f"  GEO AUDIT — {base_url}")
    print(f"  github.com/auriti-web-design/geo-optimizer-skill")
    print("🔍 " * 20)

    # Fetch homepage
    print("\n⏳ Fetching homepage...")
    r, err = fetch_url(base_url)
    if err or not r:
        print(f"\n❌ ERROR: Unable to reach {base_url}: {err}")
        sys.exit(1)

    soup = BeautifulSoup(r.text, "html.parser")
    print(f"   Status: {r.status_code} | Size: {len(r.text):,} bytes")

    # Run audits
    robots_results = audit_robots_txt(base_url)
    llms_results = audit_llms_txt(base_url)
    schema_results = audit_schema(soup, base_url)
    meta_results = audit_meta_tags(soup, base_url)
    content_results = audit_content_quality(soup, base_url)

    # Final score
    score = compute_geo_score(robots_results, llms_results, schema_results, meta_results, content_results)

    print_header("📊 FINAL GEO SCORE")
    bar_filled = int(score / 5)
    bar_empty = 20 - bar_filled
    bar = "█" * bar_filled + "░" * bar_empty
    print(f"\n  [{bar}] {score}/100")

    if score >= 80:
        print(f"\n  🏆 EXCELLENT — Site is optimized for AI search engines!")
    elif score >= 60:
        print(f"\n  ✅ GOOD — Some optimizations still possible")
    elif score >= 40:
        print(f"\n  ⚠️  FAIR — Implement the missing optimizations")
    else:
        print(f"\n  ❌ CRITICAL — Site is not optimized for AI search")

    print("\n  📋 NEXT PRIORITY STEPS:")

    actions = []
    if not robots_results["citation_bots_ok"]:
        actions.append("1. Update robots.txt with all AI bots (see SKILL.md)")
    if not llms_results["found"]:
        actions.append("2. Create /llms.txt: ./geo scripts/generate_llms_txt.py --base-url " + base_url)
    if not schema_results["has_website"]:
        actions.append("3. Add WebSite JSON-LD schema")
    if not schema_results["has_faq"]:
        actions.append("4. Add FAQPage schema with frequently asked questions")
    if not meta_results["has_description"]:
        actions.append("5. Add optimized meta description")
    if not content_results["has_numbers"]:
        actions.append("6. Add concrete numerical statistics (+40% AI visibility)")
    if not content_results["has_links"]:
        actions.append("7. Cite authoritative sources with external links")

    if not actions:
        print("  🎉 Great! All main optimizations are implemented.")
    else:
        for action in actions:
            print(f"  {action}")

    print("\n  Ref: SKILL.md for detailed instructions")
    print("  Ref: references/princeton-geo-methods.md for advanced methods")
    print()

    return score


if __name__ == "__main__":
    main()
