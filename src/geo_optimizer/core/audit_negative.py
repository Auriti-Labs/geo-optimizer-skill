"""Audit Negative Signals — negative signals that reduce AI citability.

Extracted from audit.py — separation of concerns.
Based on UC Berkeley EMNLP 2024 and LLM-perspective analysis.
Zero HTTP fetches by default; the internal-link verification
(``check_internal_links``) is opt-in and is the only part that hits the network.
"""

from __future__ import annotations

import re
from collections import Counter
from urllib.parse import urljoin, urlparse

from geo_optimizer.models.config import (
    BOILERPLATE_RATIO_THRESHOLD,
    CONTENT_MIN_WORDS,
    EMPTY_LINKS_THRESHOLD,
    KEYWORD_STUFFING_MIN_COUNT,
    KEYWORD_STUFFING_THRESHOLD,
    LINK_CHECK_BROKEN_STATUS,
    LINK_CHECK_BROKEN_THRESHOLD,
    LINK_CHECK_MAX_REQUESTS,
    LINK_CHECK_SAMPLES_CAP,
    LINK_CHECK_TIMEOUT_SECONDS,
    MIXED_SIGNALS_WORD_THRESHOLD,
)
from geo_optimizer.models.results import ContentResult, MetaResult, NegativeSignalsResult, SchemaResult
from geo_optimizer.utils.jsonld import schema_types as jsonld_types
from geo_optimizer.utils.stopwords import brand_words, page_language, stop_words_for

# Placeholder hrefs: present in the DOM but pointing nowhere. No request needed.
EMPTY_HREFS = frozenset(
    {
        "",
        "#",
        "javascript:void(0)",
        "javascript:;",
        "javascript:void(0);",
    }
)

# Schemes that are never fetched (not web resources).
_NON_HTTP_SCHEMES = ("mailto:", "tel:", "sms:", "javascript:", "data:", "file:", "ftp:")


def internal_link_targets(soup, base_url: str) -> list[str]:
    """Absolute, de-duplicated same-host http(s) link targets found in ``soup``.

    External hosts are excluded on purpose: ``check_internal_links`` must never
    issue requests towards third-party sites. The page's own URL is dropped too
    (it has just been fetched), and fragments are stripped so ``/a`` and
    ``/a#top`` count as one target.

    Args:
        soup: BeautifulSoup of the page.
        base_url: URL the page was fetched from — defines "internal".

    Returns:
        Ordered list of absolute URLs on the same host as ``base_url``.
    """
    if soup is None or not base_url:
        return []

    base_parsed = urlparse(base_url)
    base_host = (base_parsed.hostname or "").lower()
    if not base_host:
        return []
    self_url = base_parsed._replace(fragment="").geturl()

    targets: list[str] = []
    seen = {self_url, self_url.rstrip("/")}
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href or href in EMPTY_HREFS or href.startswith("#"):
            continue
        if href.lower().startswith(_NON_HTTP_SCHEMES):
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            continue
        # Same host only — a different hostname (including a different subdomain)
        # is an external link and is left untouched.
        if (parsed.hostname or "").lower() != base_host:
            continue
        absolute = parsed._replace(fragment="").geturl()
        if absolute in seen or absolute.rstrip("/") in seen:
            continue
        seen.add(absolute)
        targets.append(absolute)
    return targets


def check_internal_links(
    soup,
    base_url: str,
    *,
    max_checks: int = LINK_CHECK_MAX_REQUESTS,
) -> tuple[int, list[str]]:
    """Verify that internal links resolve, and return ``(broken_count, broken_urls)``.

    THIS EMITS HTTP REQUESTS — call it only when the user opted in
    (``geo audit --check-links``). Returns data, never prints.

    Every URL goes through ``fetch_url()``, which validates it anti-SSRF with
    ``resolve_and_validate_url()`` and pins the resolved IP. Only ``base_url``'s
    own host is contacted. A 404/410 is broken; a 403/429/5xx, a timeout or a
    rejected URL is *unverifiable* and is NOT counted as broken.

    Args:
        soup: BeautifulSoup of the page.
        base_url: URL the page was fetched from.
        max_checks: Hard cap on the number of requests.

    Returns:
        (number of broken links found, list of broken URLs)
    """
    from geo_optimizer.utils.http import fetch_url

    broken: list[str] = []
    for target in internal_link_targets(soup, base_url)[:max_checks]:
        r, err = fetch_url(target, timeout=LINK_CHECK_TIMEOUT_SECONDS)
        if r is None or err:
            continue  # unverifiable (timeout, connection error, unsafe URL) — not broken
        status = getattr(r, "status_code", None)
        if status in LINK_CHECK_BROKEN_STATUS:
            broken.append(target)
    return len(broken), broken


def audit_negative_signals(
    soup,
    raw_html,
    content_result: ContentResult,
    meta_result: MetaResult,
    schema_result: SchemaResult,
    soup_clean=None,
    *,
    base_url: str | None = None,
    check_links: bool = False,
) -> NegativeSignalsResult:
    """Detect negative signals that reduce AI citability.

    Based on UC Berkeley EMNLP 2024 and LLM-perspective analysis.
    Zero HTTP fetches unless ``check_links`` is True (opt-in link verification).

    Args:
        soup: BeautifulSoup of the page.
        raw_html: Raw HTML (not used directly, available for future extensions).
        content_result: Already-computed ContentResult.
        meta_result: Already-computed MetaResult.
        schema_result: Already-computed SchemaResult.
        soup_clean: (optional) BeautifulSoup with script/style/noscript/template
            removed. Used for all text extraction so stylesheet, inline-script
            and <noscript> fallback text never count as page copy (#537). Falls
            back to ``soup`` when not provided.
        base_url: URL the page was fetched from. Required for ``check_links``.
        check_links: If True, internal links are actually fetched and the
            ``broken_links_*`` fields are populated. Default False leaves them
            ``None`` — "not verified", not "zero broken links".

    Returns:
        NegativeSignalsResult with detected negative signals.
    """
    result = NegativeSignalsResult()
    if soup is None:
        return result

    result.checked = True

    # Text extraction runs on the cleaned tree when available; DOM-structure
    # checks (popups, empty links, author markup) stay on the raw ``soup``.
    text_soup = soup_clean if soup_clean is not None else soup

    # ── 1. CTA density (self-promotional) ───────────────────────
    # Aggressive CTA patterns
    cta_patterns = re.compile(
        r"\b(buy now|sign up|subscribe|get started|free trial|order now|"
        r"act now|limited time|don.t miss|hurry|compra ora|iscriviti|"
        r"prova gratis|acquista|registrati|offerta limitata)\b",
        re.IGNORECASE,
    )
    text = text_soup.get_text(separator=" ", strip=True)
    cta_matches = cta_patterns.findall(text)
    result.cta_count = len(cta_matches)
    # > 5 CTAs on a page = excessive
    word_count = content_result.word_count if content_result.word_count > 0 else max(len(text.split()), 1)
    if result.cta_count > 5 or (word_count > 0 and result.cta_count / word_count > 0.01):
        result.cta_density_high = True

    # ── 2. Popup/interstitial in DOM ─────────────────────────────
    popup_classes = ["modal", "popup", "overlay", "interstitial", "lightbox", "cookie-banner"]
    for cls in popup_classes:
        elements = soup.find_all(attrs={"class": lambda c, _cls=cls: c and _cls in str(c).lower()})
        if elements:
            result.popup_indicators.append(cls)
    # Also check data-* attributes
    for attr in ["data-modal", "data-popup", "data-overlay"]:
        if soup.find(attrs={attr: True}):
            result.popup_indicators.append(attr)
    result.has_popup_signals = len(result.popup_indicators) > 0

    # ── 3. Thin content ──────────────────────────────────────────
    # < 300 words AND an H1 that promises substantial content
    if content_result.word_count < CONTENT_MIN_WORDS:
        h1 = content_result.h1_text.lower() if content_result.h1_text else ""
        # H1 that promises complex content
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

    # ── 4a. Link vuoti/placeholder (nessuna richiesta HTTP) ──────
    # Counts hrefs that point nowhere in the markup itself. It does NOT verify
    # that any target resolves: that is 4b, and it only runs on request.
    empty_count = 0
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if href in EMPTY_HREFS:
            empty_count += 1
    result.empty_links_count = empty_count
    result.has_empty_links = empty_count > EMPTY_LINKS_THRESHOLD

    # ── 4b. Link interni rotti (opt-in, emette richieste HTTP) ───
    # Left as None when not requested: "not verified" must stay distinguishable
    # from "zero broken links".
    if check_links and base_url:
        candidates = internal_link_targets(soup, base_url)
        broken_count, broken_urls = check_internal_links(soup, base_url, max_checks=LINK_CHECK_MAX_REQUESTS)
        result.broken_links_count = broken_count
        result.has_broken_links = broken_count > LINK_CHECK_BROKEN_THRESHOLD
        result.broken_link_samples = broken_urls[:LINK_CHECK_SAMPLES_CAP]
        result.links_checked_count = min(len(candidates), LINK_CHECK_MAX_REQUESTS)
        result.links_check_truncated = len(candidates) > LINK_CHECK_MAX_REQUESTS

    # ── 5. Keyword stuffing ──────────────────────────────────────
    # Runs on `text` (from text_soup), so SSR'd CSS-in-JS <style> blocks and
    # inline scripts cannot inflate token frequency (#537). Note: the word
    # regex below is Latin-only, so CJK pages get no stuffing detection yet.
    # Function words of the page language and the page's own brand are not keywords (#607).
    # A declared language without a list skips the check rather than counting its function words.
    stop_words = stop_words_for(page_language(soup))
    # Any Unicode letter (not just Latin), so non-Latin pages are not measured on a shrunken denominator
    words = re.findall(r"\b[^\W\d_]{4,}\b", text.lower())
    if stop_words is not None and len(words) > 50:
        excluded = stop_words | brand_words(soup)
        freq = Counter(w for w in words if w not in excluded)
        total = len(words)
        for word, count in freq.most_common(3):
            density = count / total
            # Single-word density above threshold (SEMrush 2025: > 2.5%) = stuffing
            if density > KEYWORD_STUFFING_THRESHOLD and count >= KEYWORD_STUFFING_MIN_COUNT:
                result.has_keyword_stuffing = True
                result.stuffed_word = word
                result.stuffed_density = round(density * 100, 1)
                break

    # ── 6. Missing author signal ─────────────────────────────────
    # Look for Person schema
    from geo_optimizer.core.audit_brand import _flatten_graph

    for raw_schema in schema_result.raw_schemas:
        schemas_to_check = _flatten_graph(raw_schema) if isinstance(raw_schema, dict) else []
        for s in schemas_to_check:
            if "Person" in jsonld_types(s.get("@type")):
                result.has_author_signal = True
                break
            # nested author
            if s.get("author"):
                result.has_author_signal = True
                break
        if result.has_author_signal:
            break

    # Also check rel=author or class=author in HTML
    if not result.has_author_signal and (
        soup.find("a", rel="author") or soup.find(attrs={"class": lambda c: c and "author" in str(c).lower()})
    ):
        result.has_author_signal = True

    # ── 7. Boilerplate ratio ─────────────────────────────────────
    # Content in <main>, <article>, role="main" vs total. Runs on text_soup so
    # the ratio is not skewed by stylesheet/script/noscript text (#537).
    main_content = text_soup.find("main") or text_soup.find("article") or text_soup.find(attrs={"role": "main"})
    total_text_len = len(text)
    if main_content and total_text_len > 0:
        main_text_len = len(main_content.get_text(separator=" ", strip=True))
        result.boilerplate_ratio = round(1.0 - (main_text_len / total_text_len), 2)
    elif total_text_len > 0:
        # No <main>/<article> — estimate from nav+footer. Only the outermost
        # region counts: a <nav> inside a <header> was counted twice, which
        # pushed the ratio above 1.0.
        chrome = ["nav", "footer", "header"]
        nav_footer_len = 0
        for tag in text_soup.find_all(chrome):
            if tag.find_parent(chrome) is None:
                nav_footer_len += len(tag.get_text(separator=" ", strip=True))
        if nav_footer_len > 0:
            result.boilerplate_ratio = round(min(nav_footer_len / total_text_len, 1.0), 2)
    result.boilerplate_high = result.boilerplate_ratio > BOILERPLATE_RATIO_THRESHOLD

    # ── 8. Mixed signals ─────────────────────────────────────────
    # H1 promises a lot, but the content is thin
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
    if any(w in h1 for w in big_promise_words) and content_result.word_count < MIXED_SIGNALS_WORD_THRESHOLD:
        result.has_mixed_signals = True
        result.mixed_signal_detail = f"H1 promises depth but only {content_result.word_count} words"

    # ── Summary ──────────────────────────────────────────────────
    negatives = [
        result.cta_density_high,
        result.has_popup_signals,
        result.is_thin_content,
        # Signal 4 stays one signal: placeholder hrefs, or a verified broken
        # target when the opt-in check ran (None → False, nothing assumed).
        result.has_empty_links or bool(result.has_broken_links),
        result.has_keyword_stuffing,
        not result.has_author_signal,  # missing author = negative signal
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
