from __future__ import annotations

import json
import logging

from geo_optimizer.models.config import ARTICLE_TYPES, SCHEMA_RICHNESS_HIGH, SCHEMA_RICHNESS_LOW, SCHEMA_RICHNESS_MED
from geo_optimizer.models.results import SchemaResult


def audit_schema(soup, url: str) -> SchemaResult:
    """Check JSON-LD schema on homepage. Returns SchemaResult."""
    result = SchemaResult()

    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    if not scripts:
        return result

    for script in scripts:
        try:
            # script.string can be None if the tag has multiple child nodes
            raw = script.string
            if not raw:
                raw = script.get_text()
            if not raw or not raw.strip():
                continue
            # Size limit: prevent DoS from oversized JSON-LD (fix #182)
            if len(raw) > 512 * 1024:
                logging.debug("JSON-LD too large (%d bytes), skipping", len(raw))
                continue
            data = json.loads(raw)
            # Fix: support @graph format (used by Yoast SEO, RankMath, etc.)
            if isinstance(data, dict) and "@graph" in data:
                schemas = data["@graph"] if isinstance(data["@graph"], list) else [data["@graph"]]
            elif isinstance(data, list):
                schemas = data
            else:
                schemas = [data]

            for schema in schemas:
                schema_type = schema.get("@type", "unknown")
                if isinstance(schema_type, list):
                    schema_types = schema_type
                else:
                    schema_types = [schema_type]

                # Add the raw schema (cap at 50 to prevent memory bloat — fix #191)
                if len(result.raw_schemas) < 50:
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

        except json.JSONDecodeError as exc:
            # Parsing failed: log at debug (not critical, third-party scripts) — fix #81
            logging.debug("Invalid JSON schema ignored: %s", exc)
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

    # #232: E-commerce GEO Profile — analyze Product schema richness
    if result.has_product:
        for schema_obj in result.raw_schemas:
            schema_type = schema_obj.get("@type", "")
            types = schema_type if isinstance(schema_type, list) else [schema_type]
            if "Product" in types:
                offers = schema_obj.get("offers") or schema_obj.get("offer", {})
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
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
