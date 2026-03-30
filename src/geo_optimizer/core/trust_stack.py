"""
Trust Stack Score — aggregazione 5-layer trust signals (#273).

Aggrega segnali di fiducia da sub-audit già eseguiti. Zero fetch HTTP.

Layer:
1. Technical Trust  — HTTPS, security headers (HSTS, CSP, X-Frame-Options)
2. Identity Trust   — authorship, Organization schema, about/contact
3. Social Trust     — sameAs, recensioni, profili social
4. Academic Trust   — citazioni, statistiche, fonti autorevoli
5. Consistency Trust — coerenza brand, no mixed signals, date
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

# Regex per statistiche originali nel testo
_STATISTICS_RE = re.compile(
    r"\d+[\.,]?\d*\s*(?:%|percent|percentuale|studio|ricerca|survey|report|according to|secondo)",
    re.IGNORECASE,
)


# ─── Layer 1: Technical Trust ─────────────────────────────────────────────────


def _score_technical(base_url: str, response_headers: dict[str, str]) -> TrustLayerScore:
    """Valuta fiducia tecnica: HTTPS + security headers."""
    layer = TrustLayerScore(name="technical", label="Technical Trust")
    headers = {k.lower(): v for k, v in response_headers.items()}

    # HTTPS (+2 punti — fondamentale per trust)
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

    # X-Frame-Options (+1)
    if "x-frame-options" in headers:
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
    """Valuta fiducia identitaria: chi c'è dietro al sito."""
    layer = TrustLayerScore(name="identity", label="Identity Trust")

    # Brand coerente (+1)
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

    # Autore identificabile (+1)
    if negative_signals.has_author_signal or schema.has_person:
        layer.score += 1
        layer.signals_found.append("Author identified")
    else:
        layer.signals_missing.append("No author attribution found")

    layer.score = min(layer.score, 5)
    return layer


# ─── Layer 3: Social Trust ────────────────────────────────────────────────────


def _detect_testimonials(soup) -> bool:
    """Rileva review/testimonial nel DOM."""
    # Cerca classi CSS comuni per testimonial/review
    for cls_name in ["review", "testimonial", "testimony", "recensione"]:
        if soup.find(attrs={"class": lambda c, _cn=cls_name: c and _cn in str(c).lower()}):
            return True
    # Schema itemprop review
    if soup.find(attrs={"itemprop": "review"}):
        return True
    # Blockquote con testo sostanziale (possibile testimonial)
    for bq in soup.find_all("blockquote"):
        text = bq.get_text(strip=True)
        if len(text.split()) >= 20:
            return True
    return False


def _detect_social_links(soup) -> list[str]:
    """Rileva link a profili social nel DOM."""
    found_domains: list[str] = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].lower()
        for domain in SOCIAL_PROOF_DOMAINS:
            if domain in href and domain not in found_domains:
                found_domains.append(domain)
    return found_domains


def _score_social(
    schema: SchemaResult,
    brand_entity: BrandEntityResult,
    soup,
) -> TrustLayerScore:
    """Valuta fiducia sociale: presenza e reputazione esterna."""
    layer = TrustLayerScore(name="social", label="Social Trust")

    # sameAs presenti (+1)
    if schema.has_sameas and len(schema.sameas_urls) >= 1:
        layer.score += 1
        layer.signals_found.append(f"sameAs links ({len(schema.sameas_urls)})")
    else:
        layer.signals_missing.append("No sameAs links in schema")

    # sameAs multipli 3+ (+1)
    if len(schema.sameas_urls) >= 3:
        layer.score += 1
        layer.signals_found.append("Multiple sameAs (3+)")

    # KG pillar (+1)
    if brand_entity.kg_pillar_count >= 1:
        layer.score += 1
        layer.signals_found.append(f"KG pillars ({brand_entity.kg_pillar_count}/4)")
    else:
        layer.signals_missing.append("No Knowledge Graph pillar links")

    # Testimonial/review nel DOM (+1)
    if _detect_testimonials(soup):
        layer.score += 1
        layer.signals_found.append("Reviews/testimonials")
    else:
        layer.signals_missing.append("No reviews or testimonials found")

    # Link a profili social (+1)
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
    """Rileva link a fonti accademiche autorevoli."""
    found: list[str] = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].lower()
        for domain in ACADEMIC_AUTHORITY_DOMAINS:
            if domain in href and domain not in found:
                found.append(domain)
    return found


def _detect_references_section(soup) -> bool:
    """Rileva sezione References/Fonti tramite heading."""
    for tag in soup.find_all(["h2", "h3", "h4"]):
        heading_text = tag.get_text(strip=True).lower()
        if any(pattern in heading_text for pattern in REFERENCES_HEADING_PATTERNS):
            return True
    return False


def _count_statistics(soup) -> int:
    """Conta pattern statistici nel testo della pagina."""
    body = soup.find("body")
    if not body:
        return 0
    text = body.get_text(separator=" ", strip=True)
    return len(_STATISTICS_RE.findall(text))


def _score_academic(content: ContentResult, soup) -> TrustLayerScore:
    """Valuta fiducia accademica: dati, citazioni, fonti."""
    layer = TrustLayerScore(name="academic", label="Academic Trust")

    # Dati/numeri citati (+1)
    if content.has_numbers and content.numbers_count >= 3:
        layer.score += 1
        layer.signals_found.append(f"Statistics cited ({content.numbers_count})")
    else:
        layer.signals_missing.append("Few or no statistics/numbers in content")

    # Link a fonti esterne (+1)
    if content.external_links_count >= 2:
        layer.score += 1
        layer.signals_found.append(f"External sources ({content.external_links_count} links)")
    else:
        layer.signals_missing.append("Few external source links")

    # Link a fonti autorevoli (+1)
    auth_links = _detect_authoritative_links(soup)
    if auth_links:
        layer.score += 1
        layer.signals_found.append(f"Authoritative sources ({', '.join(auth_links[:3])})")
    else:
        layer.signals_missing.append("No links to authoritative sources (DOI, PubMed, Scholar)")

    # Sezione References/Fonti (+1)
    if _detect_references_section(soup):
        layer.score += 1
        layer.signals_found.append("References section")
    else:
        layer.signals_missing.append("No References/Sources section")

    # Statistiche originali (+1)
    stats_count = _count_statistics(soup)
    if stats_count >= ACADEMIC_STATISTICS_MIN_MATCHES:
        layer.score += 1
        layer.signals_found.append(f"Original statistics ({stats_count} patterns)")
    else:
        layer.signals_missing.append("No original research data patterns")

    layer.score = min(layer.score, 5)
    layer.details["authoritative_domains"] = auth_links
    layer.details["statistics_count"] = stats_count
    return layer


# ─── Layer 5: Consistency Trust ───────────────────────────────────────────────


def _score_consistency(
    brand_entity: BrandEntityResult,
    negative_signals: NegativeSignalsResult,
    schema: SchemaResult,
) -> TrustLayerScore:
    """Valuta coerenza: nessuna contraddizione tra segnali."""
    layer = TrustLayerScore(name="consistency", label="Consistency Trust")

    # Brand coerente (+2 — segnale più importante)
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

    # dateModified presente (+1)
    if schema.has_date_modified:
        layer.score += 1
        layer.signals_found.append("dateModified present")
    else:
        layer.signals_missing.append("No dateModified in schema")

    layer.score = min(layer.score, 5)
    return layer


# ─── Grading composito ───────────────────────────────────────────────────────


def _compute_grade(composite_score: int) -> tuple[str, str]:
    """Calcola grade e trust_level dal punteggio composito (0-25)."""
    for threshold, grade, level in TRUST_STACK_GRADE_BANDS:
        if composite_score >= threshold:
            return grade, level
    return "F", "low"


# ─── Orchestratore ────────────────────────────────────────────────────────────


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
    """Aggrega segnali di fiducia su 5 layer.

    Zero fetch HTTP — lavora esclusivamente su dati già disponibili dai sub-audit.

    Args:
        soup: BeautifulSoup del documento HTML.
        base_url: URL normalizzato del sito.
        response_headers: headers HTTP della risposta homepage.
        brand_entity: risultato audit brand & entity.
        schema: risultato audit schema JSON-LD.
        meta: risultato audit meta tags.
        content: risultato audit contenuto.
        negative_signals: risultato audit segnali negativi.

    Returns:
        TrustStackResult con score per layer e composito.
    """
    result = TrustStackResult(checked=True)

    # Calcola i 5 layer
    result.technical = _score_technical(base_url, response_headers)
    result.identity = _score_identity(brand_entity, schema, negative_signals)
    result.social = _score_social(schema, brand_entity, soup)
    result.academic = _score_academic(content, soup)
    result.consistency = _score_consistency(brand_entity, negative_signals, schema)

    # Composito
    result.composite_score = sum(
        layer.score for layer in [result.technical, result.identity, result.social, result.academic, result.consistency]
    )
    result.grade, result.trust_level = _compute_grade(result.composite_score)

    return result
