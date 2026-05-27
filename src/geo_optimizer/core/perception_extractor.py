"""AI Perception Extractor — deterministic extraction of what AI systems would perceive.

Aggregates brand, schema, citability, trust, and factual signals from an AuditResult
into a PerceptionSnapshot. Pure function — no LLM calls, no I/O, no print.

IMPORTANT: The output is always labeled as 'simulated perception', not real AI output.
"""

from __future__ import annotations

from geo_optimizer.models.results import AuditResult, PerceptionSnapshot


def extract_perception(audit_result: AuditResult) -> PerceptionSnapshot:
    """Extract a deterministic AI perception snapshot from an AuditResult.

    All sub-results are optional — missing results produce empty/None fields.
    The disclaimer field is always populated.
    """
    snapshot = PerceptionSnapshot(url=audit_result.url, mode="deterministic")

    _extract_brand_entity(snapshot, audit_result)
    _extract_schema_types(snapshot, audit_result)
    _extract_citability(snapshot, audit_result)
    _extract_trust(snapshot, audit_result)
    _extract_factual_claims(snapshot, audit_result)
    _extract_missing_signals(snapshot, audit_result)
    _build_ai_readable_summary(snapshot, audit_result)

    return snapshot


# ── Brand & entity ────────────────────────────────────────────────────────────


def _extract_brand_entity(snapshot: PerceptionSnapshot, audit: AuditResult) -> None:
    brand = getattr(audit, "brand_entity", None)
    if brand is None:
        return
    if brand.names_found:
        snapshot.brand_name = brand.names_found[0]
    # Entity type from schema if available
    schema = getattr(audit, "schema", None)
    if schema is not None and schema.found_types:
        org_types = {"Organization", "LocalBusiness", "Corporation", "NGO"}
        person_types = {"Person", "Author"}
        product_types = {"Product", "SoftwareApplication", "WebApplication"}
        found = set(schema.found_types)
        if found & org_types:
            snapshot.brand_entity_type = next(iter(found & org_types))
        elif found & person_types:
            snapshot.brand_entity_type = next(iter(found & person_types))
        elif found & product_types:
            snapshot.brand_entity_type = next(iter(found & product_types))

    # Detected services from schema ecommerce/product signals
    if schema is not None and getattr(schema, "ecommerce_signals", None):
        snapshot.detected_services = list(schema.ecommerce_signals)


# ── Schema types present ──────────────────────────────────────────────────────


def _extract_schema_types(snapshot: PerceptionSnapshot, audit: AuditResult) -> None:
    schema = getattr(audit, "schema", None)
    if schema is not None:
        snapshot.schema_types_present = list(schema.found_types or [])


# ── Citability: grade + citation-worthy facts ─────────────────────────────────


def _extract_citability(snapshot: PerceptionSnapshot, audit: AuditResult) -> None:
    citability = getattr(audit, "citability", None)
    if citability is None:
        return
    snapshot.citability_grade = getattr(citability, "grade", None)
    # Citation-worthy facts: methods that passed with high signal
    methods = getattr(citability, "methods", []) or []
    for method in methods:
        name = getattr(method, "name", "")
        score = getattr(method, "score", 0)
        max_score = getattr(method, "max_score", 1) or 1
        if score / max_score >= 0.8 and name:
            snapshot.citation_worthy_facts.append(name)


# ── Trust score ───────────────────────────────────────────────────────────────


def _extract_trust(snapshot: PerceptionSnapshot, audit: AuditResult) -> None:
    trust = getattr(audit, "trust_stack", None)
    if trust is None:
        return
    composite = getattr(trust, "composite_score", None)
    if composite is not None:
        snapshot.trust_score = float(composite)


# ── Factual claims ────────────────────────────────────────────────────────────


def _extract_factual_claims(snapshot: PerceptionSnapshot, audit: AuditResult) -> None:
    factual = getattr(audit, "factual_accuracy", None)
    if factual is None:
        return
    supported = getattr(factual, "supported_claims", []) or []
    unsupported = getattr(factual, "unsupported_claims", []) or []
    snapshot.supported_claims = [str(c) for c in supported]
    snapshot.unsupported_claims = [str(c) for c in unsupported]


# ── Missing authority signals ─────────────────────────────────────────────────


def _extract_missing_signals(snapshot: PerceptionSnapshot, audit: AuditResult) -> None:
    missing = []
    brand = getattr(audit, "brand_entity", None)
    if brand is not None:
        if not brand.has_about_link:
            missing.append("No /about page linked")
        if not brand.has_contact_info:
            missing.append("No contact information in schema")
        if brand.kg_pillar_count == 0:
            missing.append("No Knowledge Graph pillar URLs (Wikipedia, Wikidata, etc.)")
    schema = getattr(audit, "schema", None)
    if schema is not None:
        if not schema.has_faq:
            missing.append("No FAQPage schema")
        if not schema.has_article:
            missing.append("No Article/BlogPosting schema")
    snapshot.missing_authority_signals = missing


# ── AI-readable summary ───────────────────────────────────────────────────────


def _build_ai_readable_summary(snapshot: PerceptionSnapshot, audit: AuditResult) -> None:
    parts = []
    if snapshot.brand_name:
        entity_label = snapshot.brand_entity_type or "entity"
        parts.append(f"{snapshot.brand_name} is a {entity_label}")
    if snapshot.main_topic:
        parts.append(f"focused on {snapshot.main_topic}")
    if snapshot.detected_services:
        parts.append(f"offering: {', '.join(snapshot.detected_services[:3])}")
    if snapshot.schema_types_present:
        parts.append(f"schema types: {', '.join(snapshot.schema_types_present[:4])}")
    if snapshot.citability_grade:
        parts.append(f"citability grade: {snapshot.citability_grade}")
    if not parts:
        snapshot.ai_readable_summary = None
        return
    snapshot.ai_readable_summary = ". ".join(parts) + "."
