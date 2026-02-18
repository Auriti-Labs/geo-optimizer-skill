#!/usr/bin/env python3
"""
Generate llms.txt — Generates llms.txt from an XML sitemap
Generative Engine Optimization (GEO) Skill

Author: Juan Camilo Auriti (juancamilo.auriti@gmail.com)
Skill: geo-optimizer (OpenClaw)

Usage:
    python generate_llms_txt.py --base-url https://example.com
    python generate_llms_txt.py --base-url https://example.com --output ./public/llms.txt
    python generate_llms_txt.py --base-url https://example.com --sitemap https://example.com/sitemap-0.xml
    python generate_llms_txt.py --base-url https://example.com --site-name "MySite" --description "Description"
"""

import argparse
import sys
import re
from urllib.parse import urljoin, urlparse
from datetime import datetime
from collections import defaultdict

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("❌ Missing dependencies. Install with: pip install requests beautifulsoup4")
    sys.exit(1)

HEADERS = {
    "User-Agent": "GEO-Optimizer/1.0 (https://github.com/auriti-web-design/geo-optimizer-skill)"
}

# Category mapping — URL pattern → section name
CATEGORY_PATTERNS = [
    (r"/blog/", "Blog & Articles"),
    (r"/article", "Articles"),
    (r"/post/", "Posts"),
    (r"/finance/", "Finance Tools"),
    (r"/health/", "Health & Wellness"),
    (r"/math/", "Math"),
    (r"/calcul", "Calculators"),
    (r"/tool", "Tools"),
    (r"/app/", "Applications"),
    (r"/docs?/", "Documentation"),
    (r"/guide/", "Guides"),
    (r"/tutorial", "Tutorials"),
    (r"/product", "Products"),
    (r"/service", "Services"),
    (r"/about", "About"),
    (r"/contact", "Contact"),
    (r"/privacy", "Privacy & Legal"),
    (r"/terms", "Terms"),
]

SKIP_PATTERNS = [
    r"/wp-", r"/admin", r"/login", r"/logout", r"/register",
    r"/cart", r"/checkout", r"/account", r"/user/",
    r"\.(xml|json|rss|atom|pdf|jpg|png|css|js)$",
    r"/tag/", r"/category/\w+/page/", r"/page/\d+",
]


def fetch_sitemap(sitemap_url: str) -> list:
    """Download and parse an XML sitemap, including sitemap index files."""
    urls = []
    print(f"⏳ Fetching sitemap: {sitemap_url}")

    try:
        r = requests.get(sitemap_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"❌ Sitemap error: {e}")
        return urls

    soup = BeautifulSoup(r.content, "xml")

    # Sitemap index (contains other sitemaps)
    sitemap_tags = soup.find_all("sitemap")
    if sitemap_tags:
        print(f"   Sitemap index found: {len(sitemap_tags)} sitemaps")
        for sitemap in sitemap_tags[:10]:  # Limit to 10 sub-sitemaps
            loc = sitemap.find("loc")
            if loc:
                sub_urls = fetch_sitemap(loc.text.strip())
                urls.extend(sub_urls)
        return urls

    # Regular sitemap
    url_tags = soup.find_all("url")
    print(f"   URLs found: {len(url_tags)}")

    for url_tag in url_tags:
        loc = url_tag.find("loc")
        if not loc:
            continue

        url_data = {
            "url": loc.text.strip(),
            "lastmod": None,
            "priority": 0.5,
            "title": None,
        }

        lastmod = url_tag.find("lastmod")
        if lastmod:
            url_data["lastmod"] = lastmod.text.strip()

        priority = url_tag.find("priority")
        if priority:
            try:
                url_data["priority"] = float(priority.text.strip())
            except ValueError:
                pass

        urls.append(url_data)

    return urls


def should_skip(url: str) -> bool:
    """Check whether the URL should be skipped."""
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False


def categorize_url(url: str, base_domain: str) -> str:
    """Assign a category to the URL."""
    path = urlparse(url).path.lower()

    for pattern, category in CATEGORY_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            return category

    # Root/homepage
    if path in ["/", ""]:
        return "_homepage"

    # Top-level pages without a matching category
    parts = [p for p in path.split("/") if p]
    if len(parts) == 1:
        return "Main Pages"

    return "Other"


def fetch_page_title(url: str) -> str:
    """Attempt to fetch the page title (with short timeout)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.find("title")
        if title:
            return title.text.strip()
        h1 = soup.find("h1")
        if h1:
            return h1.text.strip()
    except Exception:
        pass
    return None


def url_to_label(url: str, base_domain: str) -> str:
    """Generate a human-readable label from a URL."""
    path = urlparse(url).path
    # Remove leading and trailing slashes
    path = path.strip("/")
    if not path:
        return "Homepage"
    # Take the last segment and clean it
    parts = path.split("/")
    last = parts[-1]
    # Convert slug to title
    label = last.replace("-", " ").replace("_", " ").title()
    # If it's only digits, use the full path
    if label.isdigit():
        label = "/".join(parts[-2:]).replace("-", " ").replace("_", " ").title()
    return label or path


def generate_llms_txt(
    base_url: str,
    urls: list,
    site_name: str = None,
    description: str = None,
    fetch_titles: bool = False,
    max_urls_per_section: int = 20,
) -> str:
    """Generate the content of llms.txt."""
    parsed = urlparse(base_url)
    domain = parsed.netloc

    if not site_name:
        site_name = domain.replace("www.", "").split(".")[0].title()

    if not description:
        description = f"Website {site_name} available at {base_url}"

    # Filter and categorize URLs
    categorized = defaultdict(list)
    seen = set()

    for url_data in sorted(urls, key=lambda x: -x.get("priority", 0.5)):
        url = url_data["url"]

        # Normalize URL
        if not url.startswith("http"):
            url = urljoin(base_url, url)

        # Skip URLs outside the domain
        if domain not in urlparse(url).netloc:
            continue

        # Skip unwanted URLs
        if should_skip(url):
            continue

        # Deduplication
        if url in seen:
            continue
        seen.add(url)

        category = categorize_url(url, domain)

        # Generate label
        label = url_data.get("title") or url_to_label(url, domain)

        categorized[category].append({
            "url": url,
            "label": label,
            "priority": url_data.get("priority", 0.5),
        })

    # Build llms.txt
    lines = []

    # Required header
    lines.append(f"# {site_name}")
    lines.append("")
    lines.append(f"> {description}")
    lines.append("")

    # Additional info
    lines.append(f"Auto-generated by GEO Optimizer on {datetime.now().strftime('%Y-%m-%d')}.")
    lines.append(f"Base URL: {base_url}")
    lines.append("")

    # Homepage first (if present)
    if "_homepage" in categorized:
        for item in categorized["_homepage"][:1]:
            lines.append(f"The main homepage is available at: [{site_name}]({item['url']})")
        lines.append("")

    # Category order by importance
    priority_order = [
        "Tools", "Calculators", "Finance Tools", "Health & Wellness",
        "Math", "Applications", "Main Pages",
        "Documentation", "Guides", "Tutorials",
        "Blog & Articles", "Articles", "Posts",
        "Products", "Services",
        "About", "Contact",
        "Other",
        "Privacy & Legal", "Terms",
    ]

    # Main sections
    important_categories = [c for c in priority_order if c in categorized and c != "_homepage"]
    remaining = [c for c in categorized if c not in priority_order and c != "_homepage"]

    all_categories = important_categories + sorted(remaining)

    # Separate "Optional" (secondary) sections
    main_categories = []
    optional_categories = []

    for cat in all_categories:
        items = categorized[cat]
        # Secondary categories go to Optional
        if cat in ["Privacy & Legal", "Terms", "Contact", "Other"]:
            optional_categories.append(cat)
        else:
            main_categories.append(cat)

    # Main sections
    for category in main_categories:
        items = categorized[category][:max_urls_per_section]
        if not items:
            continue

        lines.append(f"## {category}")
        lines.append("")
        for item in items:
            lines.append(f"- [{item['label']}]({item['url']})")
        lines.append("")

    # Optional section (can be skipped by LLMs with short context)
    if optional_categories:
        lines.append("## Optional")
        lines.append("")
        for category in optional_categories:
            items = categorized[category][:5]
            for item in items:
                lines.append(f"- [{item['label']}]({item['url']}): {category}")
        lines.append("")

    return "\n".join(lines)


def discover_sitemap(base_url: str) -> str:
    """Discover the site's sitemap."""
    common_paths = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap-index.xml",
        "/sitemaps/sitemap.xml",
        "/wp-sitemap.xml",
        "/sitemap-0.xml",
    ]

    # First check robots.txt for Sitemap: directive
    robots_url = urljoin(base_url, "/robots.txt")
    try:
        r = requests.get(robots_url, headers=HEADERS, timeout=5)
        for line in r.text.splitlines():
            if line.lower().startswith("sitemap:"):
                sitemap_url = line.split(":", 1)[1].strip()
                print(f"   Sitemap found in robots.txt: {sitemap_url}")
                return sitemap_url
    except Exception:
        pass

    # Try common paths
    for path in common_paths:
        url = urljoin(base_url, path)
        try:
            r = requests.head(url, headers=HEADERS, timeout=5)
            if r.status_code == 200:
                print(f"   Sitemap found: {url}")
                return url
        except Exception:
            continue

    print("   ⚠️  No sitemap found automatically")
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Generate llms.txt from XML sitemap for GEO optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_llms_txt.py --base-url https://example.com
  python generate_llms_txt.py --base-url https://example.com --output ./public/llms.txt
  python generate_llms_txt.py --base-url https://example.com --site-name "MySite" \\
      --description "Free online calculators for finance and math"
  python generate_llms_txt.py --base-url https://example.com \\
      --sitemap https://example.com/sitemap-index.xml --fetch-titles
        """
    )
    parser.add_argument("--base-url", required=True, help="Base URL of the site (e.g. https://example.com)")
    parser.add_argument("--output", default=None, help="Output file (default: stdout)")
    parser.add_argument("--sitemap", default=None, help="Sitemap URL (auto-detected if not specified)")
    parser.add_argument("--site-name", default=None, help="Site name")
    parser.add_argument("--description", default=None, help="Site description (blockquote)")
    parser.add_argument("--fetch-titles", action="store_true", help="Fetch titles from pages (slow)")
    parser.add_argument("--max-per-section", type=int, default=20, help="Max URLs per section (default: 20)")

    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url

    print(f"\n🌐 GEO llms.txt Generator")
    print(f"   Site: {base_url}")

    # Auto-detect sitemap
    sitemap_url = args.sitemap
    if not sitemap_url:
        print("\n🔍 Searching for sitemap...")
        sitemap_url = discover_sitemap(base_url)

    if not sitemap_url:
        print("❌ No sitemap found. Specify --sitemap manually.")
        # Create a minimal llms.txt
        minimal_content = f"# {args.site_name or base_url.split('//')[1].split('.')[0].title()}\n\n"
        minimal_content += f"> {args.description or 'Website available at ' + base_url}\n\n"
        minimal_content += "## Main Pages\n\n"
        minimal_content += f"- [Homepage]({base_url})\n"
        if args.output:
            with open(args.output, "w") as f:
                f.write(minimal_content)
            print(f"✅ Minimal llms.txt written to: {args.output}")
        else:
            print("\n--- llms.txt ---")
            print(minimal_content)
        return

    # Fetch URLs from sitemap
    print("\n📥 Fetching URLs from sitemap...")
    urls = fetch_sitemap(sitemap_url)

    if not urls:
        print("❌ No URLs found in sitemap")
        sys.exit(1)

    print(f"   Total URLs: {len(urls)}")

    # Generate llms.txt
    print("\n📝 Generating llms.txt...")
    content = generate_llms_txt(
        base_url=base_url,
        urls=urls,
        site_name=args.site_name,
        description=args.description,
        fetch_titles=args.fetch_titles,
        max_urls_per_section=args.max_per_section,
    )

    # Output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\n✅ llms.txt written to: {args.output}")
        print(f"   Size: {len(content)} bytes")
        print(f"   Lines: {len(content.splitlines())}")
        print(f"\n   Upload the file to: {base_url}/llms.txt")
    else:
        print("\n" + "─" * 50)
        print(content)
        print("─" * 50)
        print(f"\n✅ Save with: --output /path/to/public/llms.txt")


if __name__ == "__main__":
    main()
