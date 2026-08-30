from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from geo_optimizer.models.config import (
    ARTICLE_TYPES,
    SCHEMA_ORG_REQUIRED,
    SCHEMA_RAW_SCHEMAS_CAP,
    SCHEMA_RICHNESS_HIGH,
    SCHEMA_RICHNESS_LOW,
    SCHEMA_RICHNESS_MED,
)
from geo_optimizer.models.results import SchemaResult
from geo_optimizer.utils.jsonld import iter_jsonld_objects

if TYPE_CHECKING:
    from bs4 import BeautifulSoup

_logger = logging.getLogger(__name__)


def audit_schema(soup: BeautifulSoup | None, url: str) -> SchemaResult:
    """Check JSON-LD schema on homepage. Returns SchemaResult."""
    result = SchemaResult()
    if soup is None:
        return result

    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    if not scripts:
        return result

    def _count_parse_error(exc: Exception) -> None:
        _logger.debug("Invalid JSON schema ignored: %s", exc)
        result.json_parse_errors += 1  # fix #399: track errors for recommendations

    for schema in iter_jsonld_objects(soup, on_parse_error=_count_parse_error):
        try:
            schema_type = schema.get("@type", "unknown")
            if isinstance(schema_type, list):
                schema_types = schema_type
            else:
                schema_types = [schema_type]

            # Add the raw schema (cap at 50 to prevent memory bloat — fix #191)
            if len(result.raw_schemas) < SCHEMA_RAW_SCHEMAS_CAP:
                result.raw_schemas.append(schema)

            for t in schema_types:
                result.found_types.append(t)

                if t == "WebSite":
                    result.has_website = True
                elif t == "WebApplication":
                    result.has_webapp = True
                elif t == "FAQPage":
                    result.has_faq = True
                elif t in ARTICLE_TYPES:
                    result.has_article = True
                elif t == "Organization":
                    result.has_organization = True
                elif t == "HowTo":
                    result.has_howto = True
                elif t in ("Person",):
                    result.has_person = True
                elif t == "Product":
                    result.has_product = True

                # Any valid schema type (not unknown) counts
                if t != "unknown":
                    result.any_schema_found = True

            # Check the sameAs property
            same_as = schema.get("sameAs", [])
            if isinstance(same_as, str):
                same_as = [same_as]
            if same_as:
                result.has_sameas = True
                result.sameas_urls.extend(same_as[:10])  # cap at 10

            # Check dateModified
            if schema.get("dateModified"):
                result.has_date_modified = True

        except (AttributeError, TypeError) as exc:
            # Defensive: a malformed-but-parseable JSON-LD object shaped unexpectedly
            # (fix #81). Actual JSON parse failures are counted by iter_jsonld_objects's
            # on_parse_error above, before a schema object like this one exists.
            _logger.debug("Invalid JSON schema ignored: %s", exc)
            result.json_parse_errors += 1  # fix #399: track errors for recommendations

    # Schema richness (Growth Marshal Feb 2026): count attributes per schema
    # Generic schema (@type + name + url = 3 attrs) performs WORSE than no schema
    # Rich schema (5+ attributes) → 61.7% citation rate vs 41.6% generic
    _GENERIC_KEYS = {"@context", "@type", "@id"}
    attr_counts = []
    for schema_obj in result.raw_schemas:
        # Count only relevant attributes (excluding @context, @type, @id)
        relevant_attrs = [k for k in schema_obj if k not in _GENERIC_KEYS]
        attr_counts.append(len(relevant_attrs))

    if attr_counts:
        result.avg_attributes_per_schema = round(sum(attr_counts) / len(attr_counts), 1)
        # Graduated scoring: 0pt generic, 1pt minimal, 2pt medium, 3pt rich (#394)
        avg = result.avg_attributes_per_schema
        if avg >= SCHEMA_RICHNESS_HIGH:
            result.schema_richness_score = 3
        elif avg >= SCHEMA_RICHNESS_MED:
            result.schema_richness_score = 2
        elif avg >= SCHEMA_RICHNESS_LOW:
            result.schema_richness_score = 1
        else:
            result.schema_richness_score = 0

    # Schema completeness (gap #3): check required fields per SCHEMA_ORG_REQUIRED
    for schema_obj in result.raw_schemas:
        schema_type_raw = schema_obj.get("@type", "unknown")
        types_to_check = schema_type_raw if isinstance(schema_type_raw, list) else [schema_type_raw]
        for t in types_to_check:
            t_lower = t.lower()
            if t_lower in SCHEMA_ORG_REQUIRED:
                missing = [f for f in SCHEMA_ORG_REQUIRED[t_lower] if f not in schema_obj]
                if missing and t not in result.incomplete_schema_types:
                    result.schema_missing_fields[t] = missing
                    result.incomplete_schema_types.append(t)

    # #232: E-commerce GEO Profile — analyze Product schema richness
    if result.has_product:
        for schema_obj in result.raw_schemas:
            schema_type = schema_obj.get("@type", "")
            types = schema_type if isinstance(schema_type, list) else [schema_type]
            if "Product" in types:
                offers = schema_obj.get("offers") or schema_obj.get("offer", {})
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                if not isinstance(offers, dict):
                    offers = {}
                result.ecommerce_signals = {
                    "has_price": bool(offers.get("price") or offers.get("lowPrice")),
                    "has_availability": bool(offers.get("availability")),
                    "has_brand": bool(schema_obj.get("brand")),
                    "has_image": bool(schema_obj.get("image")),
                    "has_reviews": bool(schema_obj.get("aggregateRating") or schema_obj.get("review")),
                }
                result.ecommerce_signals["complete"] = all(
                    result.ecommerce_signals[k] for k in result.ecommerce_signals if k != "complete"
                )
                break

    return result
