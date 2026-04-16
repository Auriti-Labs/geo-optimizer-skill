"""
Term extraction from a single page for cross-page coherence analysis (#253).

Extracts title, H1, definition patterns, key terms, and language
without any external NLP dependency.
"""

from __future__ import annotations

import re
from collections import Counter

from geo_optimizer.models.results import PageTermExtract

# "X is ...", "X are ...", "X refers to ...", "X means ..."
_DEFINITION_RE = re.compile(
    r"([A-Z][A-Za-z\s\-]{2,40})\b(?:is|are|refers?\s+to|means?|describes?)\b\s+(.{10,120}?)[.]",
)

# Capitalized multi-word terms (likely proper nouns / technical terms)
_TERM_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")

_MIN_TERM_FREQ = 2


def extract_page_terms(soup, url: str = "") -> PageTermExtract:
    """Extract terminology signals from a parsed HTML page.

    Args:
        soup: BeautifulSoup of the HTML document.
        url: Page URL for reference.

    Returns:
        PageTermExtract with title, h1, definitions, key_terms, language.
    """
    title = ""
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)

    h1 = ""
    h1_tag = soup.find("h1")
    if h1_tag:
        h1 = h1_tag.get_text(strip=True)

    lang = ""
    html_tag = soup.find("html")
    if html_tag:
        lang = (html_tag.get("lang") or "").strip().lower()

    body = soup.find("body")
    body_text = body.get_text(separator=" ", strip=True) if body else ""

    definitions = [m.group(0) for m in _DEFINITION_RE.finditer(body_text)]

    term_counts = Counter(_TERM_RE.findall(body_text))
    key_terms = sorted(
        [t for t, c in term_counts.items() if c >= _MIN_TERM_FREQ],
        key=lambda t: term_counts[t],
        reverse=True,
    )

    return PageTermExtract(
        url=url,
        title=title,
        h1=h1,
        definitions=definitions[:20],
        key_terms=key_terms[:30],
        language=lang,
    )
