"""
Trust Stack Score — 5-layer trust signal aggregation (#273).

Aggregates trust signals from already-executed sub-audits. Zero HTTP fetches.

Layers:
1. Technical Trust  — HTTPS, security headers (HSTS, CSP, X-Frame-Options)
2. Identity Trust   — authorship, Organization schema, about/contact
3. Social Trust     — sameAs, reviews, social profiles
4. Academic Trust   — citations, statistics, authoritative sources
5. Consistency Trust — brand consistency, no mixed signals, dates
"""

from __future__ import annotations

import re

from geo_optimizer.models.config import (
    ACADEMIC_AUTHORITY_DOMAINS,
    ACADEMIC_STATISTICS_MIN_MATCHES,
    REFERENCES_HEADING_PATTERNS,
    SOCIAL_PROOF_DOMAINS,
    TRUST_STACK_GRADE_BANDS,
)
from geo_optimizer.models.results import (
    BrandEntityResult,
    ContentResult,
    MetaResult,
    NegativeSignalsResult,
    SchemaResult,
    TrustLayerScore,
    TrustStackResult,
)

# Regex for original statistics in text (#450: reduced false positives)
# Percentages match any number; contextual keywords require
# N >= 10 or a phrase like "secondo uno studio" / "according to a study"
_STATISTICS_RE = re.compile(
    r"\d+[\.,]?\d*\s*(?:%|percent(?:uale)?)"
    r"|(?:\d{2,}[\.,]?\d*)\s+(?:studi[oe]?|ricerch[ae]|surveys?|reports?)\b"
    r"|(?:secondo\s+(?:(?:un[oa]?|il|lo|la|i|gli|le)\s+)?(?:studio|ricerca|survey|report))\b"
    r"|(?:according\s+to\s+(?:(?:a|the)\s+)?(?:study|research|survey|report))\b",
    re.IGNORECASE,
)


# ─── Layer 1: Technical Trust ─────────────────────────────────────────────────


def _score_technical(base_url: str, response_headers: dict[str, str]) -> TrustLayerScore:
    """Evaluate technical trust: HTTPS + security headers."""
    layer = TrustLayerScore(name="technical", label="Technical Trust")
    headers = {k.lower(): v for k, v in response_headers.items()}

    # HTTPS (+2 points — fundamental for trust)
    if base_url.startswith("https://"):
        layer.score += 2
        layer.signals_found.append("HTTPS")
    else:
        layer.signals_missing.append("HTTPS not enabled")

    # HSTS (+1)
    if "strict-transport-security" in headers:
        layer.score += 1
        layer.signals_found.append("HSTS")
    else:
        layer.signals_missing.append("Strict-Transport-Security header missing")

    # CSP (+1)
    if "content-security-policy" in headers:
        layer.score += 1
        layer.signals_found.append("CSP")
    else:
        layer.signals_missing.append("Content-Security-Policy header missing")

    # X-Frame-Options or CSP frame-ancestors are equivalent (#395)
    csp_value = headers.get("content-security-policy", "")
    if "x-frame-options" in headers or "frame-ancestors" in csp_value.lower():
        layer.score += 1
        layer.signals_found.append("X-Frame-Options")
    else:
        layer.signals_missing.append("X-Frame-Options header missing")

    layer.score = min(layer.score, 5)
    return layer


# ─── Layer 2: Identity Trust ─────────────────────────────────────────────────


def _score_identity(
    brand_entity: BrandEntityResult,
    schema: SchemaResult,
    negative_signals: NegativeSignalsResult,
) -> TrustLayerScore:
    """Evaluate identity trust: who is behind the site."""
    layer = TrustLayerScore(name="identity", label="Identity Trust")

    # Consistent brand (+1)
    if brand_entity.brand_name_consistent:
        layer.score += 1
        layer.signals_found.append("Brand name consistent")
    else:
        layer.signals_missing.append("Inconsistent brand name across title/H1/schema")

    # About page (+1)
    if brand_entity.has_about_link:
        layer.score += 1
        layer.signals_found.append("About page")
    else:
        layer.signals_missing.append("No about page link found")

    # Contact info (+1)
    if brand_entity.has_contact_info:
        layer.score += 1
        layer.signals_found.append("Contact info")
    else:
        layer.signals_missing.append("No contact information in schema")

    # Organization schema (+1)
    if schema.has_organization:
        layer.score += 1
        layer.signals_found.append("Organization schema")
    else:
        layer.signals_missing.append("No Organization JSON-LD schema")

    # Identifiable author (+1)
    if negative_signals.has_author_signal or schema.has_person:
        layer.score += 1
        layer.signals_found.append("Author identified")
    else:
        layer.signals_missing.append("No author attribution found")

    layer.score = min(layer.score, 5)
    return layer


# ─── Layer 3: Social Trust ────────────────────────────────────────────────────


def _detect_testimonials(soup) -> bool:
    """Detect reviews/testimonials in the DOM."""
    # Look for common CSS classes for testimonials/reviews
    for cls_name in ["review", "testimonial", "testimony", "recensione"]:
        if soup.find(attrs={"class": lambda c, _cn=cls_name: c and _cn in str(c).lower()}):
            return True
    # Schema itemprop review
    if soup.find(attrs={"itemprop": "review"}):
        return True
    # Blockquote with substantial text (possible testimonial)
    for bq in soup.find_all("blockquote"):
        text = bq.get_text(strip=True)
        if len(text.split()) >= 20:
            return True
    return False


def _detect_social_links(soup) -> list[str]:
    """Detect unique social domains linked in the DOM (used for Social Trust layer)."""
    found_domains: list[str] = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].lower()
        for domain in SOCIAL_PROOF_DOMAINS:
            if domain in href and domain not in found_domains:
                found_domains.append(domain)
    return found_domains


def _count_social_links(soup) -> int:
    """Count total <a> tags pointing to social media domains (fix #390).

    Unlike _detect_social_links (which returns unique domains), this counts
    every individual link, matching the cardinality of external_links_count.
    """
    count = 0
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].lower()
        if any(domain in href for domain in SOCIAL_PROOF_DOMAINS):
            count += 1
    return count


def _score_social(
    schema: SchemaResult,
    brand_entity: BrandEntityResult,
    soup,
) -> TrustLayerScore:
    """Evaluate social trust: external presence and reputation."""
    layer = TrustLayerScore(name="social", label="Social Trust")

    # sameAs present (+1)
    if schema.has_sameas and len(schema.sameas_urls) >= 1:
        layer.score += 1
        layer.signals_found.append(f"sameAs links ({len(schema.sameas_urls)})")
    else:
        layer.signals_missing.append("No sameAs links in schema")

    # Multiple sameAs 3+ (+1)
    if len(schema.sameas_urls) >= 3:
        layer.score += 1
        layer.signals_found.append("Multiple sameAs (3+)")

    # KG pillar (+1)
    if brand_entity.kg_pillar_count >= 1:
        layer.score += 1
        layer.signals_found.append(f"KG pillars ({brand_entity.kg_pillar_count}/4)")
    else:
        layer.signals_missing.append("No Knowledge Graph pillar links")

    # Testimonials/reviews in the DOM (+1)
    if _detect_testimonials(soup):
        layer.score += 1
        layer.signals_found.append("Reviews/testimonials")
    else:
        layer.signals_missing.append("No reviews or testimonials found")

    # Social profile links (+1)
    social_links = _detect_social_links(soup)
    if social_links:
        layer.score += 1
        layer.signals_found.append(f"Social profiles ({', '.join(social_links[:3])})")
    else:
        layer.signals_missing.append("No social media profile links")

    layer.score = min(layer.score, 5)
    return layer


# ─── Layer 4: Academic Trust ──────────────────────────────────────────────────


def _detect_authoritative_links(soup) -> list[str]:
    """Detect links to authoritative academic sources."""
    found: list[str] = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].lower()
        for domain in ACADEMIC_AUTHORITY_DOMAINS:
            if domain in href and domain not in found:
                found.append(domain)
    return found


def _detect_references_section(soup) -> bool:
    """Detect a References/Sources section via headings."""
    for tag in soup.find_all(["h2", "h3", "h4"]):
        heading_text = tag.get_text(strip=True).lower()
        if any(pattern in heading_text for pattern in REFERENCES_HEADING_PATTERNS):
            return True
    return False


def _count_statistics(soup) -> int:
    """Count statistical patterns in the page text."""
    body = soup.find("body")
    if not body:
        return 0
    text = body.get_text(separator=" ", strip=True)
    return len(_STATISTICS_RE.findall(text))


def _score_academic(content: ContentResult, soup) -> TrustLayerScore:
    """Evaluate academic trust: data, citations, sources."""
    layer = TrustLayerScore(name="academic", label="Academic Trust")

    # Cited data/numbers (+1)
    if content.has_numbers and content.numbers_count >= 3:
        layer.score += 1
        layer.signals_found.append(f"Numbers cited ({content.numbers_count})")
    else:
        layer.signals_missing.append("Few or no statistics/numbers in content")

    # External source links (+1) — fix #390: exclude social links from the count
    # Social links belong in Social Trust, not Academic Trust.
    # Use _count_social_links (counts individual <a> tags) to match the
    # cardinality of content.external_links_count.
    social_link_count = _count_social_links(soup) if soup else 0
    academic_external_count = max(content.external_links_count - social_link_count, 0)
    if academic_external_count >= 2:
        layer.score += 1
        layer.signals_found.append(f"External sources ({academic_external_count} non-social links)")
    else:
        layer.signals_missing.append("Few external source links")

    # Links to authoritative sources (+1)
    auth_links = _detect_authoritative_links(soup)
    if auth_links:
        layer.score += 1
        layer.signals_found.append(f"Authoritative sources ({', '.join(auth_links[:3])})")
    else:
        layer.signals_missing.append("No links to authoritative sources (DOI, PubMed, Scholar)")

    # References/Sources section (+1)
    if _detect_references_section(soup):
        layer.score += 1
        layer.signals_found.append("References section")
    else:
        layer.signals_missing.append("No References/Sources section")

    # Original statistics (+1)
    stats_count = _count_statistics(soup)
    if stats_count >= ACADEMIC_STATISTICS_MIN_MATCHES:
        layer.score += 1
        layer.signals_found.append(f"Original statistics ({stats_count} patterns)")
    else:
        layer.signals_missing.append("No original research data patterns")

    layer.score = min(layer.score, 5)
    layer.details["authoritative_domains"] = auth_links
    # statistics_count = specific statistical patterns from regex (_count_statistics)
    # numbers_count = generic number counter from citability
    layer.details["statistics_count"] = stats_count
    layer.details["numbers_count"] = content.numbers_count
    return layer


# ─── Layer 5: Consistency Trust ───────────────────────────────────────────────


def _score_consistency(
    brand_entity: BrandEntityResult,
    negative_signals: NegativeSignalsResult,
    schema: SchemaResult,
) -> TrustLayerScore:
    """Evaluate consistency: no contradictions between signals."""
    layer = TrustLayerScore(name="consistency", label="Consistency Trust")

    # Consistent brand (+2 — most important signal)
    if brand_entity.brand_name_consistent:
        layer.score += 2
        layer.signals_found.append("Brand name consistent across title/H1/schema")
    else:
        layer.signals_missing.append("Inconsistent brand naming")

    # No mixed signals (+1)
    if not negative_signals.has_mixed_signals:
        layer.score += 1
        layer.signals_found.append("No mixed signals")
    else:
        layer.signals_missing.append(f"Mixed signals: {negative_signals.mixed_signal_detail}")

    # Schema description ≈ meta description (+1)
    if brand_entity.schema_desc_matches_meta:
        layer.score += 1
        layer.signals_found.append("Schema description matches meta")
    else:
        layer.signals_missing.append("Schema description differs from meta description")

    # dateModified present (+1)
    if schema.has_date_modified:
        layer.score += 1
        layer.signals_found.append("dateModified present")
    else:
        layer.signals_missing.append("No dateModified in schema")

    layer.score = min(layer.score, 5)
    return layer


# ─── Composite grading ───────────────────────────────────────────────────────


def _compute_grade(composite_score: int) -> tuple[str, str]:
    """Compute grade and trust_level from the composite score (0-25)."""
    for threshold, grade, level in TRUST_STACK_GRADE_BANDS:
        if composite_score >= threshold:
            return grade, level
    return "F", "low"


# ─── Orchestrator ─────────────────────────────────────────────────────────────


def audit_trust_stack(
    soup,
    base_url: str,
    response_headers: dict[str, str],
    brand_entity: BrandEntityResult,
    schema: SchemaResult,
    meta: MetaResult,
    content: ContentResult,
    negative_signals: NegativeSignalsResult,
) -> TrustStackResult:
    """Aggregate trust signals across 5 layers.

    Zero HTTP fetches — works exclusively on data already available from sub-audits.

    Args:
        soup: BeautifulSoup of the HTML document.
        base_url: Normalized site URL.
        response_headers: HTTP headers from the homepage response.
        brand_entity: brand & entity audit result.
        schema: JSON-LD schema audit result.
        meta: meta tags audit result.
        content: content audit result.
        negative_signals: negative signals audit result.

    Returns:
        TrustStackResult with per-layer and composite scores.
    """
    result = TrustStackResult(checked=True)

    # Compute the 5 layers
    result.technical = _score_technical(base_url, response_headers)
    result.identity = _score_identity(brand_entity, schema, negative_signals)
    result.social = _score_social(schema, brand_entity, soup)
    result.academic = _score_academic(content, soup)
    result.consistency = _score_consistency(brand_entity, negative_signals, schema)

    # Composite score
    result.composite_score = sum(
        layer.score for layer in [result.technical, result.identity, result.social, result.academic, result.consistency]
    )
    result.grade, result.trust_level = _compute_grade(result.composite_score)

    return result
