"""Audit Negative Signals — negative signals that reduce AI citability.

Extracted from audit.py — separation of concerns.
Based on UC Berkeley EMNLP 2024 and LLM-perspective analysis.
Zero HTTP fetches — works only on already-available data.
"""

from __future__ import annotations

import re
from collections import Counter

from geo_optimizer.models.config import KEYWORD_STUFFING_THRESHOLD
from geo_optimizer.models.results import ContentResult, MetaResult, NegativeSignalsResult, SchemaResult


def audit_negative_signals(
    soup, raw_html, content_result: ContentResult, meta_result: MetaResult, schema_result: SchemaResult
) -> NegativeSignalsResult:
    """Detect negative signals that reduce AI citability.

    Based on UC Berkeley EMNLP 2024 and LLM-perspective analysis.
    Zero HTTP fetches — works only on already-available data.

    Args:
        soup: BeautifulSoup of the page.
        raw_html: Raw HTML (not used directly, available for future extensions).
        content_result: Already-computed ContentResult.
        meta_result: Already-computed MetaResult.
        schema_result: Already-computed SchemaResult.

    Returns:
        NegativeSignalsResult with detected negative signals.
    """
    result = NegativeSignalsResult()
    if soup is None:
        return result

    result.checked = True

    # ── 1. CTA density (self-promotional) ───────────────────────
    # Aggressive CTA patterns
    cta_patterns = re.compile(
        r"\b(buy now|sign up|subscribe|get started|free trial|order now|"
        r"act now|limited time|don.t miss|hurry|compra ora|iscriviti|"
        r"prova gratis|acquista|registrati|offerta limitata)\b",
        re.IGNORECASE,
    )
    text = soup.get_text(separator=" ", strip=True)
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
    if content_result.word_count < 300:
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

    # ── 4. Link rotti/vuoti ──────────────────────────────────────
    broken_count = 0
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if href in ("", "#", "javascript:void(0)", "javascript:;", "javascript:void(0);"):
            broken_count += 1
    result.broken_links_count = broken_count
    result.has_broken_links = broken_count > 3

    # ── 5. Keyword stuffing ──────────────────────────────────────
    # Calculate word frequency (excluding stop words and short words)
    stop_words = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "it",
        "this",
        "that",
        "not",
        "no",
        "as",
        "by",
        "from",
        "il",
        "la",
        "le",
        "lo",
        "gli",
        "un",
        "una",
        "di",
        "da",
        "del",
        "che",
        "per",
        "con",
        "su",
        "al",
        "dei",
        "nel",
        "è",
        "sono",
        "ha",
        "hanno",
        "più",
        "anche",
        "come",
        "se",
        "non",
        "i",
    }
    words = re.findall(r"\b[a-zA-ZÀ-ÿ]{4,}\b", text.lower())
    if len(words) > 50:
        freq = Counter(w for w in words if w not in stop_words)
        total = len(words)
        for word, count in freq.most_common(3):
            density = count / total
            # Single-word density above threshold (SEMrush 2025: > 2.5%) = stuffing
            if density > KEYWORD_STUFFING_THRESHOLD and count >= 5:
                result.has_keyword_stuffing = True
                result.stuffed_word = word
                result.stuffed_density = round(density * 100, 1)
                break

    # ── 6. Missing author signal ─────────────────────────────────
    # Look for Person schema
    for raw_schema in schema_result.raw_schemas:
        schemas_to_check = []
        if isinstance(raw_schema, dict) and "@graph" in raw_schema:
            schemas_to_check.extend(raw_schema["@graph"])
        elif isinstance(raw_schema, dict):
            schemas_to_check.append(raw_schema)
        for s in schemas_to_check:
            s_type = s.get("@type", "")
            if isinstance(s_type, list):
                s_type = s_type[0] if s_type else ""
            if s_type == "Person":
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
    # Content in <main>, <article>, role="main" vs total
    main_content = soup.find("main") or soup.find("article") or soup.find(attrs={"role": "main"})
    total_text_len = len(text)
    if main_content and total_text_len > 0:
        main_text_len = len(main_content.get_text(separator=" ", strip=True))
        result.boilerplate_ratio = round(1.0 - (main_text_len / total_text_len), 2)
    elif total_text_len > 0:
        # No <main>/<article> — estimate from nav+footer
        nav_footer_len = 0
        for tag in soup.find_all(["nav", "footer", "header"]):
            nav_footer_len += len(tag.get_text(separator=" ", strip=True))
        if nav_footer_len > 0:
            result.boilerplate_ratio = round(nav_footer_len / total_text_len, 2)
    result.boilerplate_high = result.boilerplate_ratio > 0.6

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
    if any(w in h1 for w in big_promise_words) and content_result.word_count < 1000:
        result.has_mixed_signals = True
        result.mixed_signal_detail = f"H1 promises depth but only {content_result.word_count} words"

    # ── Summary ──────────────────────────────────────────────────
    negatives = [
        result.cta_density_high,
        result.has_popup_signals,
        result.is_thin_content,
        result.has_broken_links,
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
