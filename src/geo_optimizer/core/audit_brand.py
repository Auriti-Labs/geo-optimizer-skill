"""Audit Brand & Entity — brand identity signals for AI perception.

Extracted from audit.py — separation of concerns.
Works only on already-fetched data, zero HTTP requests.
"""

from __future__ import annotations

from collections import Counter

from geo_optimizer.models.config import ABOUT_LINK_PATTERNS, BRAND_LEGAL_SUFFIXES, KG_PILLAR_DOMAINS
from geo_optimizer.models.results import BrandEntityResult, ContentResult, MetaResult, SchemaResult


def _flatten_graph(raw_schema: dict) -> list[dict]:
    """Extract schemas from @graph if present, otherwise return as single-item list (#412)."""
    if "@graph" in raw_schema:
        return list(raw_schema["@graph"])
    return [raw_schema]


def _normalize_brand_name(name: str) -> str:
    """Normalize a brand name for comparison by stripping legal suffixes (#397).

    Strips leading/trailing whitespace, lowercases, then removes any legal suffix
    (e.g. "Inc.", "Ltd.", "GmbH", "S.r.l.") from the END of the name.
    The suffix must appear as a standalone trailing token — it is NOT removed
    when it appears in the middle (e.g. "The Inc. Company" is unchanged).

    Args:
        name: Raw brand name (e.g. "Apple Inc.", "Auriti S.r.l.").

    Returns:
        Normalized name without trailing legal suffix (e.g. "apple", "auriti").
    """
    normalized = name.strip().lower()
    # Strip trailing punctuation (comma, period not part of suffix) before matching
    normalized = normalized.rstrip(",")
    for suffix in BRAND_LEGAL_SUFFIXES:
        # Match suffix at end, preceded by a space (to avoid mid-name removal)
        if normalized.endswith(" " + suffix):
            normalized = normalized[: -(len(suffix) + 1)].strip()
            break
    return normalized


def audit_brand_entity(
    soup, schema_result: SchemaResult, meta_result: MetaResult, content_result: ContentResult
) -> BrandEntityResult:
    """Analyze brand identity and entity signals for AI perception (v4.3).

    Works only on already-fetched data, zero HTTP requests.

    Args:
        soup: BeautifulSoup of the homepage.
        schema_result: Already-computed SchemaResult.
        meta_result: Already-computed MetaResult.
        content_result: Already-computed ContentResult.

    Returns:
        BrandEntityResult with brand/entity signals populated.
    """
    result = BrandEntityResult()
    if soup is None:
        return result

    # ── 1. Entity Coherence ──────────────────────────────────────
    # Collect brand names from different sources
    names = []

    # H1
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        h1_text = h1.get_text(strip=True)
        # Take the first part before common separators
        for sep in (" — ", " - ", " | ", " · "):
            if sep in h1_text:
                h1_text = h1_text.split(sep)[0].strip()
                break
        if h1_text:
            names.append(h1_text)

    # Title tag
    if meta_result.title_text:
        title_name = meta_result.title_text
        for sep in (" — ", " - ", " | ", " · "):
            if sep in title_name:
                title_name = title_name.split(sep)[0].strip()
                break
        if title_name:
            names.append(title_name)

    # og:title
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content", ""):
        og_name = og_title["content"]
        for sep in (" — ", " - ", " | ", " · "):
            if sep in og_name:
                og_name = og_name.split(sep)[0].strip()
                break
        if og_name:
            names.append(og_name)

    # Schema Organization name
    for raw_schema in schema_result.raw_schemas:
        schemas_to_check = _flatten_graph(raw_schema)
        for s in schemas_to_check:
            s_type = s.get("@type", "")
            if isinstance(s_type, list):
                s_type = s_type[0] if s_type else ""
            if s_type == "Organization" and s.get("name"):
                names.append(s["name"])

    result.names_found = names[:10]

    # Consistency: at least 2 names, most-frequent one appears 2+ times after legal suffix removal (#397)
    if len(names) >= 2:
        lower_names = [_normalize_brand_name(n) for n in names]
        freq = Counter(lower_names)
        most_common_name, most_common_count = freq.most_common(1)[0]
        if most_common_count >= 2:
            result.brand_name_consistent = True

    # Schema description vs meta description
    if meta_result.description_text:
        meta_desc_lower = meta_result.description_text.lower()[:100]
        for raw_schema in schema_result.raw_schemas:
            schemas_to_check = []
            if "@graph" in raw_schema:
                schemas_to_check.extend(raw_schema["@graph"])
            else:
                schemas_to_check.append(raw_schema)
            for s in schemas_to_check:
                schema_desc = s.get("description", "")
                if schema_desc and isinstance(schema_desc, str):
                    schema_desc_lower = schema_desc.lower()[:100]
                    # Sovrapposizione significativa: almeno 30 caratteri in comune
                    if meta_desc_lower[:30] in schema_desc_lower or schema_desc_lower[:30] in meta_desc_lower:
                        result.schema_desc_matches_meta = True
                        break

    # ── 2. Knowledge Graph Readiness ─────────────────────────────
    for url in schema_result.sameas_urls:
        url_lower = url.lower()
        for domain in KG_PILLAR_DOMAINS:
            if domain in url_lower:
                result.kg_pillar_urls.append(url)
                if "wikipedia.org" in url_lower:
                    result.has_wikipedia = True
                elif "wikidata.org" in url_lower:
                    result.has_wikidata = True
                elif "linkedin.com" in url_lower:
                    result.has_linkedin = True
                elif "crunchbase.com" in url_lower:
                    result.has_crunchbase = True
                break
    result.kg_pillar_count = sum(
        [
            result.has_wikipedia,
            result.has_wikidata,
            result.has_linkedin,
            result.has_crunchbase,
        ]
    )

    # ── 3. About/Contact Signals ─────────────────────────────────
    # Look for /about link in the page
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].lower()
        if any(pattern in href for pattern in ABOUT_LINK_PATTERNS):
            result.has_about_link = True
            break

    # Look for Organization with address/telephone/email or Person with jobTitle
    for raw_schema in schema_result.raw_schemas:
        schemas_to_check = _flatten_graph(raw_schema)
        for s in schemas_to_check:
            s_type = s.get("@type", "")
            if isinstance(s_type, list):
                s_type = s_type[0] if s_type else ""
            if s_type == "Organization" and (
                s.get("address") or s.get("telephone") or s.get("email") or s.get("contactPoint")
            ):
                result.has_contact_info = True
            elif s_type == "Person" and (s.get("jobTitle") or s.get("hasCredential") or s.get("alumniOf")):
                result.has_contact_info = True

    # ── 4. Geographic Identity ───────────────────────────────────
    # Tag hreflang
    hreflang_tags = soup.find_all("link", attrs={"rel": "alternate", "hreflang": True})
    result.hreflang_count = len(hreflang_tags)
    result.has_hreflang = result.hreflang_count > 0

    # Geo signals from Schema (address, areaServed, LocalBusiness)
    for raw_schema in schema_result.raw_schemas:
        schemas_to_check = _flatten_graph(raw_schema)
        for s in schemas_to_check:
            s_type = s.get("@type", "")
            if isinstance(s_type, list):
                s_type = s_type[0] if s_type else ""
            if s_type == "LocalBusiness" or s.get("areaServed") or (s_type == "Organization" and s.get("address")):
                result.has_geo_schema = True
                break

    # ── 5. Topic Authority ───────────────────────────────────────
    # FAQ depth from FAQPage schema
    for raw_schema in schema_result.raw_schemas:
        schemas_to_check = _flatten_graph(raw_schema)
        for s in schemas_to_check:
            s_type = s.get("@type", "")
            if isinstance(s_type, list):
                s_type = s_type[0] if s_type else ""
            if s_type == "FAQPage":
                main_entity = s.get("mainEntity", [])
                if isinstance(main_entity, list):
                    result.faq_depth += len(main_entity)

    # Article/BlogPosting with dateModified
    result.has_recent_articles = schema_result.has_date_modified and (
        schema_result.has_article or any(t in ("BlogPosting", "NewsArticle") for t in schema_result.found_types)
    )

    return result
