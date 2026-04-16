"""
Site-wide semantic coherence orchestrator (#253).

Fetches pages from a sitemap, extracts terminology, and runs
cross-page coherence analysis.
"""

from __future__ import annotations

import asyncio

from bs4 import BeautifulSoup

from geo_optimizer.core.coherence_analyzer import analyze_coherence
from geo_optimizer.core.llms_generator import fetch_sitemap
from geo_optimizer.core.term_extractor import extract_page_terms
from geo_optimizer.models.results import PageTermExtract, SemanticCoherenceResult
from geo_optimizer.utils.http import fetch_url

_DEFAULT_MAX_PAGES = 20


def run_site_coherence(
    sitemap_url: str,
    *,
    max_pages: int = _DEFAULT_MAX_PAGES,
) -> SemanticCoherenceResult:
    """Run cross-page semantic coherence analysis from a sitemap.

    Args:
        sitemap_url: URL of the sitemap XML.
        max_pages: Maximum number of pages to analyze.

    Returns:
        SemanticCoherenceResult with issues and coherence score.
    """
    entries = fetch_sitemap(sitemap_url)
    if not entries:
        return SemanticCoherenceResult(checked=True)

    urls = _dedupe_urls(entries, max_pages)
    extracts = _fetch_and_extract(urls)
    return analyze_coherence(extracts)


async def run_site_coherence_async(
    sitemap_url: str,
    *,
    max_pages: int = _DEFAULT_MAX_PAGES,
) -> SemanticCoherenceResult:
    """Async variant with parallel page fetching."""
    entries = await asyncio.to_thread(fetch_sitemap, sitemap_url)
    if not entries:
        return SemanticCoherenceResult(checked=True)

    urls = _dedupe_urls(entries, max_pages)

    try:
        from geo_optimizer.utils.http_async import fetch_urls_async

        responses = await fetch_urls_async(urls)
        extracts: list[PageTermExtract] = []
        for url in urls:
            resp, err = responses.get(url, (None, None))
            if resp and not err:
                soup = BeautifulSoup(resp.text, "html.parser")
                extracts.append(extract_page_terms(soup, url=url))
    except ImportError:
        extracts = await asyncio.to_thread(_fetch_and_extract, urls)

    return analyze_coherence(extracts)


def _dedupe_urls(entries, max_pages: int) -> list[str]:
    """Deduplicate and limit sitemap URLs."""
    seen: set[str] = set()
    urls: list[str] = []
    for entry in entries:
        if entry.url not in seen:
            seen.add(entry.url)
            urls.append(entry.url)
            if len(urls) >= max_pages:
                break
    return urls


def _fetch_and_extract(urls: list[str]) -> list[PageTermExtract]:
    """Fetch pages synchronously and extract terms."""
    extracts: list[PageTermExtract] = []
    for url in urls:
        resp, err = fetch_url(url)
        if resp and not err:
            soup = BeautifulSoup(resp.text, "html.parser")
            extracts.append(extract_page_terms(soup, url=url))
    return extracts
