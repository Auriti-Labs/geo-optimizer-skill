"""
Site-level topical authority analysis (`geo authority`).

AI engines build an internal model of who is authoritative on what by
mapping entities, relationships, and multi-page topic coverage — a brand
with five interlinked pages covering a topic from different angles is more
visible than a brand with one strong page. This module groups sitemap pages
into topic clusters (shared key terms), then measures cluster depth,
internal interlinking (hub-and-spoke), and pillar-page presence.

Reuses the coherence pipeline: sitemap fetch + per-page term extraction.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from geo_optimizer.core.llms_generator import fetch_sitemap
from geo_optimizer.core.term_extractor import extract_page_terms
from geo_optimizer.models.results import PageTermExtract, TopicAuthorityResult, TopicCluster
from geo_optimizer.utils.http import fetch_url

_DEFAULT_MAX_PAGES = 20
_MAX_CLUSTERS = 10
_MIN_CLUSTER_PAGES = 2

# Terms appearing on more than this share of pages are navigation/footer
# boilerplate (menu labels live on every page), not topical clusters.
# Only applied when enough pages were analyzed for the ratio to mean something.
_BOILERPLATE_DF = 0.8
_BOILERPLATE_MIN_PAGES = 5

# Authority score weights (total 100) — rationale in the module docstring:
# depth of the strongest cluster matters most ("5 pages beat 1 strong page"),
# then whether the cluster is wired together, then pillar pages, then breadth.
_W_COVERAGE = 40  # strongest cluster size vs _COVERAGE_TARGET pages
_W_INTERLINK = 30  # mean interlink ratio across clusters
_W_PILLARS = 20  # share of clusters with a pillar page
_W_BREADTH = 10  # number of distinct clusters vs _BREADTH_TARGET
_COVERAGE_TARGET = 5
_BREADTH_TARGET = 3


def _normalize_host(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host.removeprefix("www.")


def _normalize_page_url(url: str) -> str:
    """Normalize for page-identity comparison: drop fragment, trailing slash."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    return f"{_normalize_host(url)}{path}"


def _extract_internal_links(soup: BeautifulSoup, page_url: str) -> set[str]:
    """Collect normalized same-host link targets from a page."""
    host = _normalize_host(page_url)
    links: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(page_url, href)
        if _normalize_host(absolute) == host:
            links.add(_normalize_page_url(absolute))
    return links


def _build_clusters(
    extracts: list[PageTermExtract],
    page_links: dict[str, set[str]],
    *,
    brand: str = "",
) -> list[TopicCluster]:
    """Group pages by shared key terms and measure interlinking per cluster."""
    # Space/punctuation-insensitive brand match: "GeoReady" must also catch
    # the extracted term "Geo Ready".
    brand_norm = re.sub(r"\W+", "", brand.lower())

    # term (lowercased) → display form + set of page URLs
    term_display: dict[str, str] = {}
    term_pages: dict[str, list[str]] = {}
    for extract in extracts:
        seen_on_page: set[str] = set()
        for term in extract.key_terms:
            key = term.lower()
            # The brand name appears everywhere by definition — it is identity,
            # not a topic, and would form one giant meaningless cluster.
            if brand_norm and brand_norm in re.sub(r"\W+", "", key):
                continue
            if key in seen_on_page:
                continue
            seen_on_page.add(key)
            term_display.setdefault(key, term)
            term_pages.setdefault(key, []).append(extract.url)

    apply_df_filter = len(extracts) >= _BOILERPLATE_MIN_PAGES
    clusters: list[TopicCluster] = []
    titles = {e.url: f"{e.title} {e.h1}".lower() for e in extracts}
    for key, pages in term_pages.items():
        if len(pages) < _MIN_CLUSTER_PAGES:
            continue
        if apply_df_filter and len(pages) / len(extracts) > _BOILERPLATE_DF:
            continue

        pillar_url = next((url for url in pages if key in titles.get(url, "")), "")

        normalized_pages = {_normalize_page_url(url) for url in pages}
        interlinked = sum(
            1 for url in pages if page_links.get(url, set()) & (normalized_pages - {_normalize_page_url(url)})
        )
        clusters.append(
            TopicCluster(
                topic=term_display[key],
                pages=pages,
                pages_count=len(pages),
                pillar_url=pillar_url,
                interlink_ratio=round(interlinked / len(pages), 2),
            )
        )

    clusters.sort(key=lambda c: (c.pages_count, c.interlink_ratio), reverse=True)
    return clusters[:_MAX_CLUSTERS]


def _find_orphan_pages(urls: list[str], page_links: dict[str, set[str]]) -> list[str]:
    """Pages with zero inbound internal links from the other analyzed pages.

    The homepage is excluded — it is reachable by definition (URL bar,
    external links, browser bookmark) and does not need in-site links
    pointing back to it the way a deep content page does.
    """
    inbound: set[str] = set()
    for source_url, links in page_links.items():
        for target in links:
            if target != _normalize_page_url(source_url):
                inbound.add(target)

    orphans = []
    for url in urls:
        normalized = _normalize_page_url(url)
        if normalized.endswith("/"):  # homepage (root path normalizes to ".../")
            continue
        if normalized not in inbound:
            orphans.append(url)
    return orphans


def _score(clusters: list[TopicCluster]) -> int:
    if not clusters:
        return 0
    coverage = min(clusters[0].pages_count / _COVERAGE_TARGET, 1.0) * _W_COVERAGE
    interlink = (sum(c.interlink_ratio for c in clusters) / len(clusters)) * _W_INTERLINK
    pillars = (sum(1 for c in clusters if c.pillar_url) / len(clusters)) * _W_PILLARS
    breadth = min(len(clusters) / _BREADTH_TARGET, 1.0) * _W_BREADTH
    return round(coverage + interlink + pillars + breadth)


def _recommendations(clusters: list[TopicCluster], pages_analyzed: int) -> list[str]:
    recs: list[str] = []
    if not clusters:
        recs.append(
            f"No recurring topic found across {pages_analyzed} pages — AI engines reward focused, "
            "multi-page coverage. Pick your core topics and cover each with several pages."
        )
        return recs

    best = clusters[0]
    if best.pages_count < _COVERAGE_TARGET:
        recs.append(
            f"Strongest topic '{best.topic}' has only {best.pages_count} pages — "
            f"add {_COVERAGE_TARGET - best.pages_count} supporting pages (guides, FAQs, comparisons) "
            "to build entity authority."
        )
    for cluster in clusters:
        if not cluster.pillar_url:
            recs.append(
                f"Topic '{cluster.topic}' has no pillar page — create one whose title and H1 "
                "state the topic explicitly, then link the cluster pages to it."
            )
            break  # one pillar recommendation is enough; the text report shows the rest
    weak_links = [c for c in clusters if c.interlink_ratio < 0.5]
    if weak_links:
        recs.append(
            f"{len(weak_links)} cluster(s) are poorly interlinked (e.g. '{weak_links[0].topic}') — "
            "link related pages to each other (hub-and-spoke) so crawlers see them as one entity."
        )
    return recs


def run_topic_authority(
    sitemap_url: str,
    *,
    max_pages: int = _DEFAULT_MAX_PAGES,
    brand: str = "",
) -> TopicAuthorityResult:
    """Analyze site-level topical authority from a sitemap.

    Args:
        sitemap_url: URL of the sitemap XML.
        max_pages: Maximum number of pages to fetch and analyze.
        brand: Brand name to exclude from topic clustering (identity, not topic).

    Returns:
        TopicAuthorityResult with clusters, authority score, and recommendations.
    """
    entries = fetch_sitemap(sitemap_url)
    if not entries:
        return TopicAuthorityResult(checked=True, skipped_reason="Sitemap empty or unreachable")

    seen: set[str] = set()
    urls: list[str] = []
    for entry in entries:
        if entry.url not in seen:
            seen.add(entry.url)
            urls.append(entry.url)
            if len(urls) >= max_pages:
                break

    extracts: list[PageTermExtract] = []
    page_links: dict[str, set[str]] = {}
    for url in urls:
        resp, err = fetch_url(url)
        if not resp or err:
            continue
        soup = BeautifulSoup(resp.text, "html.parser")
        extracts.append(extract_page_terms(soup, url=url))
        page_links[url] = _extract_internal_links(soup, url)

    if not extracts:
        return TopicAuthorityResult(checked=True, skipped_reason="No pages could be fetched")

    clusters = _build_clusters(extracts, page_links, brand=brand)
    orphans = _find_orphan_pages([e.url for e in extracts], page_links)
    recommendations = _recommendations(clusters, len(extracts))
    if orphans:
        preview = ", ".join(orphans[:3]) + (f" (+{len(orphans) - 3} more)" if len(orphans) > 3 else "")
        recommendations.append(
            f"{len(orphans)} page(s) have no internal links pointing to them (orphan pages) — "
            f"crawlers following links may never discover them: {preview}"
        )
    return TopicAuthorityResult(
        checked=True,
        pages_analyzed=len(extracts),
        clusters=clusters,
        authority_score=_score(clusters),
        recommendations=recommendations,
        orphan_pages=orphans,
    )
