"""
GEO Audit — Meta Tags sub-audit.

Extracted from core/audit.py for maintainability (#402).
"""

from __future__ import annotations

from geo_optimizer.models.results import MetaResult


def audit_meta_tags(soup, url: str) -> MetaResult:
    """Check SEO/GEO meta tags. Returns MetaResult."""
    result = MetaResult()

    # Fix H-8: guard against None soup
    if soup is None:
        return result

    # Title
    title_tag = soup.find("title")
    if title_tag and title_tag.text.strip():
        result.has_title = True
        result.title_text = title_tag.text.strip()
        result.title_length = len(result.title_text)

    # Meta description
    desc = soup.find("meta", attrs={"name": "description"})
    if desc and desc.get("content", "").strip():
        result.has_description = True
        result.description_text = desc["content"].strip()
        result.description_length = len(result.description_text)

    # Canonical
    canonical = soup.find("link", attrs={"rel": "canonical"})
    if canonical and canonical.get("href"):
        result.has_canonical = True
        result.canonical_url = canonical["href"]

    # Open Graph
    og_title = soup.find("meta", attrs={"property": "og:title"})
    og_desc = soup.find("meta", attrs={"property": "og:description"})
    og_image = soup.find("meta", attrs={"property": "og:image"})

    if og_title and og_title.get("content"):
        result.has_og_title = True

    if og_desc and og_desc.get("content"):
        result.has_og_description = True

    if og_image and og_image.get("content"):
        result.has_og_image = True

    return result
