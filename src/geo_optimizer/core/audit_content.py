from __future__ import annotations

import re
from urllib.parse import urlparse

from geo_optimizer.models.results import ContentResult


def audit_content_quality(soup, url: str, soup_clean=None) -> ContentResult:
    """Check content quality for GEO. Returns ContentResult.

    Args:
        soup: BeautifulSoup dell'HTML originale.
        url: URL della pagina.
        soup_clean: (optional) BeautifulSoup pre-cleaned (no script/style).
                    Se fornito, evita il re-parse dell'HTML (fix #285).
    """
    import copy

    result = ContentResult()

    # Fix H-8: guard against None soup (defensive — called from plugins/tests)
    if soup is None:
        return result

    # H1
    h1 = soup.find("h1")
    if h1:
        result.has_h1 = True
        result.h1_text = h1.text.strip()

    # Headings
    headings = soup.find_all(["h1", "h2", "h3", "h4"])
    result.heading_count = len(headings)

    # Fix #285: use pre-computed soup_clean if available, otherwise create a copy
    # Use copy.deepcopy() instead of BS(str(soup)) to avoid costly re-parsing
    if soup_clean is None:
        soup_clean = copy.deepcopy(soup)
        for tag in soup_clean(["script", "style"]):
            tag.decompose()

    # Fix #107: separator=" " prevents word concatenation from adjacent tags
    # Example: <span>Hello</span><span>World</span> → "Hello World" instead of "HelloWorld"
    body_text = soup_clean.get_text(separator=" ", strip=True)
    numbers = re.findall(r"\b\d+[%\u20ac$\u00a3]|\b\d+\.\d+|\b\d{3,}\b", body_text)
    result.numbers_count = len(numbers)
    if len(numbers) >= 3:
        result.has_numbers = True

    # Word count
    words = body_text.split()
    result.word_count = len(words)

    # External links (citations)
    parsed = urlparse(url)
    base_domain = parsed.netloc
    all_links = soup.find_all("a", href=True)
    # Fix F-08: guard against empty base_domain (malformed URL)
    if base_domain:
        external_links = [
            link for link in all_links if link["href"].startswith("http") and base_domain not in link["href"]
        ]
    else:
        external_links = [link for link in all_links if link["href"].startswith("http")]
    result.external_links_count = len(external_links)
    if external_links:
        result.has_links = True

    # Heading hierarchy: both H2 and H3 present
    h2_tags = soup_clean.find_all("h2")
    h3_tags = soup_clean.find_all("h3")
    if h2_tags and h3_tags:
        result.has_heading_hierarchy = True

    # Lists or tables
    lists = soup_clean.find_all(["ul", "ol", "table"])
    if lists:
        result.has_lists_or_tables = True

    # Front-loading: first 30% of text has substantial content with concrete data
    # Fix #306: threshold was computed incorrectly (always >= 50 for pages >= 50 words)
    if words:
        soglia_30 = max(len(words) * 30 // 100, 1)
        first_30pct = words[:soglia_30]
        # First 30% must have at least 50 words AND contain numbers/statistics
        if len(first_30pct) >= 50:
            numeri_nel_30pct = sum(1 for w in first_30pct if re.search(r"\d", w))
            if numeri_nel_30pct >= 1:
                result.has_front_loading = True

    return result
