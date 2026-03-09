"""
llms.txt generator — core logic for building llms.txt from XML sitemaps.

Extracted from scripts/generate_llms_txt.py.  All functions return data;
nothing is printed to stdout.  Status updates go through an optional
``on_status`` callback or standard ``logging``.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Callable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from geo_optimizer.models.config import (
    CATEGORY_PATTERNS,
    HEADERS,
    MAX_SUB_SITEMAPS,
    MAX_TOTAL_URLS,
    OPTIONAL_CATEGORIES,
    SECTION_PRIORITY_ORDER,
    SKIP_PATTERNS,
)
from geo_optimizer.models.results import SitemapUrl
from geo_optimizer.utils.http import create_session_with_retry
from geo_optimizer.utils.validators import url_belongs_to_domain, validate_public_url

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex precompilate a livello modulo (fix #123)
# Evita ricompilazione ad ogni chiamata in loop
# ---------------------------------------------------------------------------

# Pattern per verificare URL da skippare (SKIP_PATTERNS compilati)
_SKIP_PATTERNS_RE = [re.compile(p, re.IGNORECASE) for p in SKIP_PATTERNS]

# Pattern per categorizzare URL (CATEGORY_PATTERNS compilati)
_CATEGORY_PATTERNS_RE = [(re.compile(p, re.IGNORECASE), cat) for p, cat in CATEGORY_PATTERNS]

# Pattern per estrarre link markdown da llms.txt
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


# ---------------------------------------------------------------------------
# Sitemap fetching
# ---------------------------------------------------------------------------

_MAX_SITEMAP_DEPTH = 3  # Limite profondità ricorsione sitemap index


def fetch_sitemap(
    sitemap_url: str,
    on_status: Callable[[str], None] | None = None,
    _depth: int = 0,
    _total_count: list[int] | None = None,
    session=None,
) -> list[SitemapUrl]:
    """Scarica e parsa un sitemap XML, inclusi sitemap index.

    Usa retry automatico con backoff esponenziale per errori transitori.
    La ricorsione è limitata a ``_MAX_SITEMAP_DEPTH`` livelli (anti-bomb).
    Il totale URL è limitato a ``MAX_TOTAL_URLS`` (fix #124 — sitemap bomb).

    Args:
        sitemap_url: URL del sitemap XML.
        on_status: Callback opzionale per messaggi di progresso.
        _depth: Contatore profondità ricorsione (non usare direttamente).
        _total_count: Lista mutable [n] per tracking URL totali tra chiamate recursive.
        session: Session HTTP da riusare (fix #122). Se None, ne crea una nuova.

    Returns:
        Lista di :class:`SitemapUrl` trovati nel sitemap.
    """
    urls: list[SitemapUrl] = []

    # Fix #124: inizializza il contatore condiviso tra chiamate recursive
    if _total_count is None:
        _total_count = [0]

    # Fix #124: stop immediato se limite URL già raggiunto
    if _total_count[0] >= MAX_TOTAL_URLS:
        logger.warning("Limite URL raggiunto (%d), skip sitemap: %s", MAX_TOTAL_URLS, sitemap_url)
        if on_status:
            on_status(f"URL limit reached ({MAX_TOTAL_URLS}), skipping: {sitemap_url}")
        return urls

    # Protezione anti-bomb: limita profondità ricorsione
    if _depth >= _MAX_SITEMAP_DEPTH:
        logger.warning("Profondità massima sitemap raggiunta (%d), skip: %s", _depth, sitemap_url)
        if on_status:
            on_status(f"Max sitemap depth reached ({_depth}), skipping: {sitemap_url}")
        return urls

    if on_status:
        on_status(f"Fetching sitemap: {sitemap_url}")
    logger.info("Fetching sitemap: %s", sitemap_url)

    # Fix #122: usa la session passata o creane una nuova solo al primo livello
    if session is None:
        session = create_session_with_retry()

    try:
        r = session.get(sitemap_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except requests.exceptions.Timeout:
        logger.warning("Sitemap timeout: %s", sitemap_url)
        if on_status:
            on_status(f"Sitemap timeout: {sitemap_url}")
        return urls
    except requests.exceptions.HTTPError as e:
        logger.warning("Sitemap HTTP error: %s — %s", sitemap_url, e)
        if on_status:
            on_status(f"Sitemap HTTP error: {e}")
        return urls
    except requests.exceptions.RequestException as e:
        logger.warning("Sitemap request error (after retries): %s", e)
        if on_status:
            on_status(f"Sitemap error (after retries): {e}")
        return urls
    except Exception as e:
        # Catch finale per errori imprevisti (es. mock nei test) — fix #78
        logger.warning("Sitemap errore imprevisto: %s", e)
        if on_status:
            on_status(f"Sitemap error: {e}")
        return urls

    soup = BeautifulSoup(r.content, "xml")

    # Sitemap index (contiene altri sitemap)
    sitemap_tags = soup.find_all("sitemap")
    if sitemap_tags:
        logger.info("Sitemap index found: %d sitemaps", len(sitemap_tags))
        if on_status:
            on_status(f"Sitemap index found: {len(sitemap_tags)} sitemaps")
        for sitemap in sitemap_tags[:MAX_SUB_SITEMAPS]:  # Limit sub-sitemaps (fix #90)
            # Fix #124: stop se limite raggiunto durante iterazione sub-sitemap
            if _total_count[0] >= MAX_TOTAL_URLS:
                logger.warning("Limite URL raggiunto (%d), stop sub-sitemaps", MAX_TOTAL_URLS)
                break
            loc = sitemap.find("loc")
            if loc:
                sub_url = urljoin(sitemap_url, loc.text.strip())
                # Validazione anti-SSRF: verifica che sub-URL sia pubblico
                safe, reason = validate_public_url(sub_url)
                if not safe:
                    logger.warning("Sub-sitemap URL non sicuro ignorato: %s (%s)", sub_url, reason)
                    if on_status:
                        on_status(f"Sub-sitemap skipped (unsafe): {sub_url}")
                    continue
                # Fix #122: riusa la session; fix #124: passa il contatore
                sub_urls = fetch_sitemap(
                    sub_url,
                    on_status=on_status,
                    _depth=_depth + 1,
                    _total_count=_total_count,
                    session=session,
                )
                urls.extend(sub_urls)
        return urls

    # Sitemap normale
    url_tags = soup.find_all("url")
    logger.info("URLs found: %d", len(url_tags))
    if on_status:
        on_status(f"URLs found: {len(url_tags)}")

    for url_tag in url_tags:
        # Fix #124: stop se limite raggiunto durante iterazione URL
        if _total_count[0] >= MAX_TOTAL_URLS:
            logger.warning("Limite URL raggiunto (%d), stop parsing sitemap: %s", MAX_TOTAL_URLS, sitemap_url)
            if on_status:
                on_status(f"URL limit reached ({MAX_TOTAL_URLS}), stopping")
            break

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
        _total_count[0] += 1

    return urls


# ---------------------------------------------------------------------------
# URL filtering & classification
# ---------------------------------------------------------------------------


def should_skip(url: str) -> bool:
    """Verifica se l'URL deve essere escluso in base a :data:`_SKIP_PATTERNS_RE`.

    Usa regex precompilate a livello modulo (fix #123) per evitare
    ricompilazione ad ogni chiamata in loop.
    """
    for pattern_re in _SKIP_PATTERNS_RE:
        if pattern_re.search(url):
            return True
    return False


def categorize_url(url: str, base_domain: str) -> str:
    """Assegna una categoria all'URL in base a :data:`_CATEGORY_PATTERNS_RE`.

    Usa regex precompilate a livello modulo (fix #123).

    Args:
        url: URL completo da categorizzare.
        base_domain: Dominio base del sito (non usato nel matching).

    Returns:
        Nome della categoria, es. ``"Blog & Articles"`` o ``"Main Pages"``.
    """
    path = urlparse(url).path.lower()

    for pattern_re, category in _CATEGORY_PATTERNS_RE:
        if pattern_re.search(path):
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


def fetch_page_title(url: str) -> str | None:
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
    final = label or path
    # Tronca label troppo lunghe (fix #85)
    if len(final) > 80:
        final = final[:77] + "..."
    return final


# ---------------------------------------------------------------------------
# llms.txt generation
# ---------------------------------------------------------------------------


def generate_llms_txt(
    base_url: str,
    urls: list[SitemapUrl],
    site_name: str | None = None,
    description: str | None = None,
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

        categorized[category].append(
            {
                "url": url,
                "label": label,
                "priority": url_data.priority,
            }
        )

    # Build llms.txt
    lines: list[str] = []

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
    important_categories = [c for c in SECTION_PRIORITY_ORDER if c in categorized and c != "_homepage"]
    remaining = [c for c in categorized if c not in SECTION_PRIORITY_ORDER and c != "_homepage"]

    all_categories = important_categories + sorted(remaining)

    # Separate "Optional" (secondary) sections
    main_categories: list[str] = []
    optional_categories: list[str] = []

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
    on_status: Callable[[str], None] | None = None,
) -> str | None:
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

    # Controlla robots.txt per TUTTE le direttive Sitemap: (#116)
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
                # Restituisce il primo URL valido trovato in robots.txt
                # (gli altri vengono scoperti ricorsivamente da fetch_sitemap)
                return sitemap_url
    except Exception:
        pass

    # Prova i percorsi comuni: HEAD prima, fallback GET se 405/timeout (#115)
    for path in common_paths:
        url = urljoin(base_url, path)
        try:
            r = session.head(url, headers=HEADERS, timeout=5)
            if r.status_code == 200:
                logger.info("Sitemap found: %s", url)
                if on_status:
                    on_status(f"Sitemap found: {url}")
                return url
            if r.status_code == 405:
                # Server non supporta HEAD — fallback a GET (#115)
                logger.debug("HEAD 405 per %s, fallback a GET", url)
                r_get = session.get(url, headers=HEADERS, timeout=5)
                if r_get.status_code == 200:
                    logger.info("Sitemap found (via GET): %s", url)
                    if on_status:
                        on_status(f"Sitemap found: {url}")
                    return url
        except Exception:
            # Timeout o errore di rete: prova GET come fallback (#115)
            try:
                r_get = session.get(url, headers=HEADERS, timeout=5)
                if r_get.status_code == 200:
                    logger.info("Sitemap found (via GET fallback): %s", url)
                    if on_status:
                        on_status(f"Sitemap found: {url}")
                    return url
            except Exception:
                continue

    logger.warning("No sitemap found automatically for %s", base_url)
    if on_status:
        on_status("No sitemap found automatically")
    return None
