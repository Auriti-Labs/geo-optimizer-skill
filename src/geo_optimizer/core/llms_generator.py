"""
llms.txt generator — core logic for building llms.txt from XML sitemaps.

Extracted from scripts/generate_llms_txt.py.  All functions return data;
nothing is printed to stdout.  Status updates go through an optional
``on_status`` callback or standard ``logging``.
"""

import logging
import re
from collections import defaultdict
from typing import Callable, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from geo_optimizer.models.config import (
    CATEGORY_PATTERNS,
    HEADERS,
    OPTIONAL_CATEGORIES,
    SECTION_PRIORITY_ORDER,
    SKIP_PATTERNS,
)
from geo_optimizer.models.results import SitemapUrl
from geo_optimizer.utils.http import create_session_with_retry
from geo_optimizer.utils.validators import url_belongs_to_domain, validate_public_url

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sitemap fetching
# ---------------------------------------------------------------------------

_MAX_SITEMAP_DEPTH = 3  # Limite profondità ricorsione sitemap index


def fetch_sitemap(
    sitemap_url: str,
    on_status: Optional[Callable[[str], None]] = None,
    _depth: int = 0,
) -> List[SitemapUrl]:
    """Download and parse an XML sitemap, including sitemap index files.

    Uses automatic retry with exponential backoff for transient failures.
    Recursion is limited to ``_MAX_SITEMAP_DEPTH`` levels to prevent
    sitemap bomb attacks.

    Args:
        sitemap_url: URL of the XML sitemap to fetch.
        on_status: Optional callback for progress messages.
        _depth: Internal recursion depth counter (non usare direttamente).

    Returns:
        List of :class:`SitemapUrl` entries discovered in the sitemap.
    """
    urls: List[SitemapUrl] = []

    # Protezione anti-bomb: limita profondità ricorsione
    if _depth >= _MAX_SITEMAP_DEPTH:
        logger.warning("Profondità massima sitemap raggiunta (%d), skip: %s", _depth, sitemap_url)
        if on_status:
            on_status(f"Max sitemap depth reached ({_depth}), skipping: {sitemap_url}")
        return urls

    if on_status:
        on_status(f"Fetching sitemap: {sitemap_url}")
    logger.info("Fetching sitemap: %s", sitemap_url)

    try:
        session = create_session_with_retry()
        r = session.get(sitemap_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        logger.error("Sitemap error (after retries): %s", e)
        if on_status:
            on_status(f"Sitemap error (after retries): {e}")
        return urls

    soup = BeautifulSoup(r.content, "xml")

    # Sitemap index (contains other sitemaps)
    sitemap_tags = soup.find_all("sitemap")
    if sitemap_tags:
        logger.info("Sitemap index found: %d sitemaps", len(sitemap_tags))
        if on_status:
            on_status(f"Sitemap index found: {len(sitemap_tags)} sitemaps")
        for sitemap in sitemap_tags[:10]:  # Limit to 10 sub-sitemaps
            loc = sitemap.find("loc")
            if loc:
                sub_url = urljoin(sitemap_url, loc.text.strip())
                sub_urls = fetch_sitemap(sub_url, on_status=on_status, _depth=_depth + 1)
                urls.extend(sub_urls)
        return urls

    # Regular sitemap
    url_tags = soup.find_all("url")
    logger.info("URLs found: %d", len(url_tags))
    if on_status:
        on_status(f"URLs found: {len(url_tags)}")

    for url_tag in url_tags:
        loc = url_tag.find("loc")
        if not loc:
            continue

        entry = SitemapUrl(
            url=urljoin(sitemap_url, loc.text.strip()),
        )

        lastmod = url_tag.find("lastmod")
        if lastmod:
            entry.lastmod = lastmod.text.strip()

        priority = url_tag.find("priority")
        if priority:
            try:
                entry.priority = float(priority.text.strip())
            except ValueError:
                pass

        urls.append(entry)

    return urls


# ---------------------------------------------------------------------------
# URL filtering & classification
# ---------------------------------------------------------------------------

def should_skip(url: str) -> bool:
    """Check whether *url* should be skipped based on :data:`SKIP_PATTERNS`."""
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False


def categorize_url(url: str, base_domain: str) -> str:
    """Assign a category to *url* based on :data:`CATEGORY_PATTERNS`.

    Args:
        url: Full URL to categorise.
        base_domain: The site's domain (used only for context, not matching).

    Returns:
        Category name string, e.g. ``"Blog & Articles"`` or ``"Main Pages"``.
    """
    path = urlparse(url).path.lower()

    for pattern, category in CATEGORY_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            return category

    # Root / homepage
    if path in ["/", ""]:
        return "_homepage"

    # Top-level pages without a matching category
    parts = [p for p in path.split("/") if p]
    if len(parts) == 1:
        return "Main Pages"

    return "Other"


# ---------------------------------------------------------------------------
# Title helpers
# ---------------------------------------------------------------------------

def fetch_page_title(url: str) -> Optional[str]:
    """Attempt to fetch the ``<title>`` (or ``<h1>``) of a page.

    Uses a short timeout and limited retry to avoid blocking on slow pages.

    Returns:
        The page title string, or ``None`` on failure.
    """
    try:
        session = create_session_with_retry(total_retries=2, backoff_factor=0.5)
        r = session.get(url, headers=HEADERS, timeout=5)
        # Non usare titoli da pagine di errore (404, 500, ecc.)
        if r.status_code != 200:
            return None
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
    """Generate a human-readable label from a URL.

    Args:
        url: Full URL.
        base_domain: The site's domain (unused but kept for API parity).

    Returns:
        A title-cased label derived from the URL path.
    """
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


# ---------------------------------------------------------------------------
# llms.txt generation
# ---------------------------------------------------------------------------

def generate_llms_txt(
    base_url: str,
    urls: List[SitemapUrl],
    site_name: str = None,
    description: str = None,
    fetch_titles: bool = False,
    max_urls_per_section: int = 20,
) -> str:
    """Generate the content of an ``llms.txt`` file.

    Args:
        base_url: The site's base URL (e.g. ``https://example.com``).
        urls: Sitemap entries to include.
        site_name: Human-readable site name (auto-derived if ``None``).
        description: One-line description used in the blockquote header.
        fetch_titles: When ``True``, fetch ``<title>`` from each page
            to use as the link label.  This is slow for large sitemaps.
        max_urls_per_section: Cap on links per section (default 20).

    Returns:
        The full ``llms.txt`` content as a string.
    """
    parsed = urlparse(base_url)
    domain = parsed.netloc

    if not site_name:
        site_name = domain.replace("www.", "").split(".")[0].title()

    if not description:
        description = f"Website {site_name} available at {base_url}"

    # Filter and categorize URLs
    categorized = defaultdict(list)
    seen: set = set()

    for url_data in sorted(urls, key=lambda x: -x.priority):
        url = url_data.url

        # Normalize URL
        if not url.startswith("http"):
            url = urljoin(base_url, url)

        # Filtro dominio sicuro (previene bypass con substring match)
        if not url_belongs_to_domain(url, domain):
            continue

        # Skip unwanted URLs
        if should_skip(url):
            continue

        # Deduplication
        if url in seen:
            continue
        seen.add(url)

        category = categorize_url(url, domain)

        # Generate label (fetch from page if requested)
        label = url_data.title
        if not label and fetch_titles:
            fetched = fetch_page_title(url)
            if fetched:
                label = fetched
        if not label:
            label = url_to_label(url, domain)

        categorized[category].append({
            "url": url,
            "label": label,
            "priority": url_data.priority,
        })

    # Build llms.txt
    lines: List[str] = []

    # Required header
    lines.append(f"# {site_name}")
    lines.append("")
    lines.append(f"> {description}")
    lines.append("")

    lines.append("")

    # Homepage first (if present)
    if "_homepage" in categorized:
        for item in categorized["_homepage"][:1]:
            lines.append(f"The main homepage is available at: [{site_name}]({item['url']})")
        lines.append("")

    # Main sections
    important_categories = [
        c for c in SECTION_PRIORITY_ORDER
        if c in categorized and c != "_homepage"
    ]
    remaining = [
        c for c in categorized
        if c not in SECTION_PRIORITY_ORDER and c != "_homepage"
    ]

    all_categories = important_categories + sorted(remaining)

    # Separate "Optional" (secondary) sections
    main_categories: List[str] = []
    optional_categories: List[str] = []

    for cat in all_categories:
        if cat in OPTIONAL_CATEGORIES:
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


# ---------------------------------------------------------------------------
# Sitemap discovery
# ---------------------------------------------------------------------------

def discover_sitemap(
    base_url: str,
    on_status: Optional[Callable[[str], None]] = None,
) -> Optional[str]:
    """Discover the site's sitemap URL from ``robots.txt`` or common paths.

    Args:
        base_url: The site's base URL.
        on_status: Optional callback for progress messages.

    Returns:
        The sitemap URL if found, otherwise ``None``.
    """
    common_paths = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap-index.xml",
        "/sitemaps/sitemap.xml",
        "/wp-sitemap.xml",
        "/sitemap-0.xml",
    ]

    session = create_session_with_retry(total_retries=2, backoff_factor=0.5)

    # Controlla robots.txt per la direttiva Sitemap:
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc
    robots_url = urljoin(base_url, "/robots.txt")
    try:
        r = session.get(robots_url, headers=HEADERS, timeout=5)
        for line in r.text.splitlines():
            if line.lower().startswith("sitemap:"):
                sitemap_url = line.split(":", 1)[1].strip()
                # Validazione anti-SSRF: l'URL sitemap deve appartenere
                # allo stesso dominio e puntare a un host pubblico
                if not url_belongs_to_domain(sitemap_url, base_domain):
                    logger.warning("Sitemap URL esterno ignorato: %s", sitemap_url)
                    continue
                safe, reason = validate_public_url(sitemap_url)
                if not safe:
                    logger.warning("Sitemap URL non sicuro ignorato: %s (%s)", sitemap_url, reason)
                    continue
                logger.info("Sitemap found in robots.txt: %s", sitemap_url)
                if on_status:
                    on_status(f"Sitemap found in robots.txt: {sitemap_url}")
                return sitemap_url
    except Exception:
        pass

    # Try common paths
    for path in common_paths:
        url = urljoin(base_url, path)
        try:
            r = session.head(url, headers=HEADERS, timeout=5)
            if r.status_code == 200:
                logger.info("Sitemap found: %s", url)
                if on_status:
                    on_status(f"Sitemap found: {url}")
                return url
        except Exception:
            continue

    logger.warning("No sitemap found automatically for %s", base_url)
    if on_status:
        on_status("No sitemap found automatically")
    return None
