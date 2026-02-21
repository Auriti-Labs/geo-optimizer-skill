"""
Unit tests for schema_validator.py

Tests JSON-LD schema validation logic.

Author: Juan Camilo Auriti
"""

import sys
from pathlib import Path

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from schema_validator import validate_jsonld, validate_jsonld_string, get_required_fields


def test_valid_website_schema():
    """Test validation of valid WebSite schema."""
    schema = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "url": "https://example.com",
        "name": "Example Site"
    }
    
    is_valid, error = validate_jsonld(schema, "website")
    assert is_valid is True
    assert error is None


def test_missing_context():
    """Test validation fails when @context is missing."""
    schema = {
        "@type": "WebSite",
        "url": "https://example.com",
        "name": "Example"
    }
    
    is_valid, error = validate_jsonld(schema)
    assert is_valid is False
    assert "@context" in error


def test_missing_type():
    """Test validation fails when @type is missing."""
    schema = {
        "@context": "https://schema.org",
        "url": "https://example.com",
        "name": "Example"
    }
    
    is_valid, error = validate_jsonld(schema)
    assert is_valid is False
    assert "@type" in error


def test_invalid_context_url():
    """Test validation fails for invalid @context URL."""
    schema = {
        "@context": "http://wrong-domain.com",
        "@type": "WebSite",
        "url": "https://example.com",
        "name": "Example"
    }
    
    is_valid, error = validate_jsonld(schema)
    assert is_valid is False
    assert "schema.org" in error


def test_missing_required_field_for_type():
    """Test validation fails when required field is missing for specific type."""
    schema = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Example"
        # Missing 'url' which is required for WebSite
    }
    
    is_valid, error = validate_jsonld(schema, "website")
    assert is_valid is False
    assert "url" in error


def test_array_context():
    """Test validation with array @context (multiple contexts)."""
    schema = {
        "@context": ["https://schema.org", "https://www.w3.org/ns/activitystreams"],
        "@type": "WebSite",
        "url": "https://example.com",
        "name": "Example"
    }
    
    is_valid, error = validate_jsonld(schema, "website")
    assert is_valid is True
    assert error is None


def test_array_type():
    """Test validation with array @type (multiple types)."""
    schema = {
        "@context": "https://schema.org",
        "@type": ["WebSite", "SearchAction"],
        "url": "https://example.com",
        "name": "Example"
    }
    
    is_valid, error = validate_jsonld(schema, "website")
    assert is_valid is True
    assert error is None


def test_faqpage_schema():
    """Test validation of FAQPage schema."""
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": "What is GEO?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Generative Engine Optimization"
                }
            }
        ]
    }
    
    is_valid, error = validate_jsonld(schema, "faqpage")
    assert is_valid is True
    assert error is None


def test_organization_schema():
    """Test validation of Organization schema."""
    schema = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "Example Inc",
        "url": "https://example.com"
    }
    
    is_valid, error = validate_jsonld(schema, "organization")
    assert is_valid is True
    assert error is None


def test_invalid_url_format_strict():
    """Test validation fails on invalid URL format in strict mode."""
    schema = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "url": "not-a-url",  # Invalid URL
        "name": "Example"
    }
    
    is_valid, error = validate_jsonld(schema, "website", strict=True)
    assert is_valid is False
    assert "Invalid URL format" in error


def test_invalid_url_format_non_strict():
    """Test validation passes on invalid URL format in non-strict mode (warning only)."""
    schema = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "url": "not-a-url",  # Invalid URL but in non-strict mode
        "name": "Example"
    }
    
    is_valid, error = validate_jsonld(schema, "website", strict=False)
    # Should pass in non-strict mode (just a warning)
    assert is_valid is True


def test_validate_jsonld_string_valid():
    """Test validation from JSON string."""
    json_str = '{"@context": "https://schema.org", "@type": "WebSite", "url": "https://example.com", "name": "Example"}'
    
    is_valid, error = validate_jsonld_string(json_str, "website")
    assert is_valid is True
    assert error is None


def test_validate_jsonld_string_invalid_json():
    """Test validation fails on malformed JSON string."""
    json_str = '{"@context": "https://schema.org", "@type": "WebSite"'  # Missing closing brace
    
    is_valid, error = validate_jsonld_string(json_str)
    assert is_valid is False
    assert "Invalid JSON" in error


def test_get_required_fields_website():
    """Test get_required_fields for WebSite type."""
    fields = get_required_fields("website")
    assert "@context" in fields
    assert "@type" in fields
    assert "url" in fields
    assert "name" in fields


def test_get_required_fields_unknown_type():
    """Test get_required_fields for unknown type returns defaults."""
    fields = get_required_fields("unknown-type")
    assert "@context" in fields
    assert "@type" in fields
    assert len(fields) == 2  # Only default fields


def test_schema_not_dict():
    """Test validation fails when schema is not a dict."""
    is_valid, error = validate_jsonld("not-a-dict")
    assert is_valid is False
    assert "must be a dict" in error


def test_empty_type():
    """Test validation fails when @type is empty."""
    schema = {
        "@context": "https://schema.org",
        "@type": []  # Empty array
    }
    
    is_valid, error = validate_jsonld(schema)
    assert is_valid is False
    assert "@type" in error  # Either "empty" or "Missing" is fine
