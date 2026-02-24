#!/usr/bin/env python3
"""
JSON-LD Schema Validator
Validates schema.org JSON-LD structures for common types.

Author: Juan Camilo Auriti
Created: 2026-02-21
"""

import json
from typing import Dict, List, Tuple, Optional


# Required fields for each schema.org type
SCHEMA_ORG_REQUIRED = {
    "website": ["@context", "@type", "url", "name"],
    "webpage": ["@context", "@type", "url", "name"],
    "organization": ["@context", "@type", "name", "url"],
    "person": ["@context", "@type", "name"],
    "faqpage": ["@context", "@type", "mainEntity"],
    "article": ["@context", "@type", "headline", "author"],
    "breadcrumblist": ["@context", "@type", "itemListElement"],
    "product": ["@context", "@type", "name", "description"],
    "localbusiness": ["@context", "@type", "name", "address"],
    "webapplication": ["@context", "@type", "name", "url"],
}


def validate_jsonld(
    schema_dict: Dict,
    schema_type: Optional[str] = None,
    strict: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Validate a JSON-LD schema structure.
    
    Args:
        schema_dict (dict): The parsed JSON-LD schema
        schema_type (str, optional): Expected schema type (e.g., 'website', 'faqpage')
        strict (bool): If True, fail on warnings. If False, only fail on critical errors.
    
    Returns:
        tuple: (is_valid, error_message)
            - is_valid (bool): True if valid, False otherwise
            - error_message (str): Error description if invalid, None if valid
    
    Examples:
        >>> schema = {"@context": "https://schema.org", "@type": "WebSite", "url": "...", "name": "..."}
        >>> validate_jsonld(schema, "website")
        (True, None)
        
        >>> bad_schema = {"@type": "WebSite"}
        >>> validate_jsonld(bad_schema, "website")
        (False, "Missing required field: @context")
    """
    # Check if input is a dictionary
    if not isinstance(schema_dict, dict):
        return False, f"Schema must be a dict, got {type(schema_dict).__name__}"
    
    # Validate @context
    context = schema_dict.get("@context")
    if not context:
        return False, "Missing required field: @context"
    
    valid_contexts = ["https://schema.org", "http://schema.org"]
    if isinstance(context, str):
        if context not in valid_contexts:
            return False, f"@context must be 'https://schema.org', got '{context}'"
    elif isinstance(context, list):
        # Multiple contexts — validate first one
        if not context or context[0] not in valid_contexts:
            return False, f"@context[0] must be 'https://schema.org', got '{context[0] if context else 'empty list'}'"
    else:
        return False, f"@context must be string or array, got {type(context).__name__}"
    
    # Validate @type
    schema_type_field = schema_dict.get("@type")
    if not schema_type_field:
        return False, "Missing required field: @type"
    
    # Normalize @type (can be string or array)
    if isinstance(schema_type_field, list):
        primary_type = schema_type_field[0] if schema_type_field else None
    else:
        primary_type = schema_type_field
    
    if not primary_type:
        return False, "@type is empty"
    
    # If schema_type is provided, validate specific requirements
    if schema_type:
        schema_type_normalized = schema_type.lower()
        primary_type_normalized = primary_type.lower()
        
        # Check if type matches (case-insensitive)
        if primary_type_normalized != schema_type_normalized:
            return False, f"Expected @type '{schema_type}', got '{primary_type}'"
        
        # Check required fields for this type
        required_fields = SCHEMA_ORG_REQUIRED.get(schema_type_normalized, ["@context", "@type"])
        missing_fields = [f for f in required_fields if f not in schema_dict]
        
        if missing_fields:
            return False, f"Missing required fields for {primary_type}: {', '.join(missing_fields)}"
    
    # Validate URL fields format (if present)
    url_fields = ["url", "sameAs", "logo", "image"]
    for field in url_fields:
        value = schema_dict.get(field)
        if value:
            if isinstance(value, str):
                urls_to_check = [value]
            elif isinstance(value, list):
                urls_to_check = value
            else:
                continue
            
            for url in urls_to_check:
                if isinstance(url, str) and not url.startswith(("http://", "https://", "/")):
                    if strict:
                        return False, f"Invalid URL format in '{field}': '{url}' (must start with http://, https://, or /)"
                    # In non-strict mode, this is just a warning (we return True but could log)
    
    # All validations passed
    return True, None


def validate_jsonld_string(
    json_string: str,
    schema_type: Optional[str] = None,
    strict: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Validate a JSON-LD schema from a string.
    
    Args:
        json_string (str): JSON-LD as string
        schema_type (str, optional): Expected schema type
        strict (bool): Strict validation mode
    
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        schema_dict = json.loads(json_string)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    
    return validate_jsonld(schema_dict, schema_type, strict)


def get_required_fields(schema_type: str) -> List[str]:
    """
    Get list of required fields for a schema type.
    
    Args:
        schema_type (str): Schema type (e.g., 'website', 'faqpage')
    
    Returns:
        list: Required field names
    """
    return SCHEMA_ORG_REQUIRED.get(schema_type.lower(), ["@context", "@type"])
