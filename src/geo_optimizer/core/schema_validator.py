"""
JSON-LD Schema Validator.

Validates schema.org JSON-LD structures for common types.
"""

import json
from typing import Dict, List, Optional, Tuple

from geo_optimizer.models.config import SCHEMA_ORG_REQUIRED


def validate_jsonld(
    schema_dict: Dict,
    schema_type: Optional[str] = None,
    strict: bool = False,
) -> Tuple[bool, Optional[str]]:
    """
    Validate a JSON-LD schema structure.

    Args:
        schema_dict: The parsed JSON-LD schema
        schema_type: Expected schema type (e.g., 'website', 'faqpage')
        strict: If True, fail on warnings. If False, only fail on critical errors.

    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(schema_dict, dict):
        return False, f"Schema must be a dict, got {type(schema_dict).__name__}"

    context = schema_dict.get("@context")
    if not context:
        return False, "Missing required field: @context"

    valid_contexts = ["https://schema.org", "http://schema.org"]
    if isinstance(context, str):
        if context not in valid_contexts:
            return False, f"@context must be 'https://schema.org', got '{context}'"
    elif isinstance(context, list):
        if not context or context[0] not in valid_contexts:
            first = context[0] if context else "empty list"
            return False, f"@context[0] must be 'https://schema.org', got '{first}'"
    else:
        return False, f"@context must be string or array, got {type(context).__name__}"

    schema_type_field = schema_dict.get("@type")
    if not schema_type_field:
        return False, "Missing required field: @type"

    if isinstance(schema_type_field, list):
        primary_type = schema_type_field[0] if schema_type_field else None
    else:
        primary_type = schema_type_field

    if not primary_type:
        return False, "@type is empty"

    if schema_type:
        schema_type_normalized = schema_type.lower()
        primary_type_normalized = primary_type.lower()

        if primary_type_normalized != schema_type_normalized:
            return False, f"Expected @type '{schema_type}', got '{primary_type}'"

        required_fields = SCHEMA_ORG_REQUIRED.get(
            schema_type_normalized, ["@context", "@type"]
        )
        missing_fields = [f for f in required_fields if f not in schema_dict]
        if missing_fields:
            return False, (
                f"Missing required fields for {primary_type}: "
                f"{', '.join(missing_fields)}"
            )

    url_fields = ["url", "sameAs", "logo", "image"]
    for fld in url_fields:
        value = schema_dict.get(fld)
        if value:
            if isinstance(value, str):
                urls_to_check = [value]
            elif isinstance(value, list):
                urls_to_check = value
            else:
                continue

            for url in urls_to_check:
                if isinstance(url, str) and not url.startswith(
                    ("http://", "https://", "/")
                ):
                    if strict:
                        return False, (
                            f"Invalid URL format in '{fld}': '{url}' "
                            f"(must start with http://, https://, or /)"
                        )

    return True, None


def validate_jsonld_string(
    json_string: str,
    schema_type: Optional[str] = None,
    strict: bool = False,
) -> Tuple[bool, Optional[str]]:
    """Validate a JSON-LD schema from a string."""
    try:
        schema_dict = json.loads(json_string)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"

    return validate_jsonld(schema_dict, schema_type, strict)


def get_required_fields(schema_type: str) -> List[str]:
    """Get list of required fields for a schema type."""
    return SCHEMA_ORG_REQUIRED.get(schema_type.lower(), ["@context", "@type"])
