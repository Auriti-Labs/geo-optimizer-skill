"""Test that schema.org Organization subtypes (LocalBusiness and friends) are
recognized as satisfying the Organization schema and contact-info checks.

Before this fix, `audit_schema.py` and `audit_brand.py` both matched only the
literal string "Organization", so a JSON-LD node typed "LocalBusiness" (the
schema.org-recommended, more specific type for exactly the small-business
audience this tool targets) was scored as having no Organization schema at
all — even when it already had name/url/logo/telephone/email set.
"""

from __future__ import annotations

import json

from bs4 import BeautifulSoup

from geo_optimizer.core.audit import audit_brand_entity
from geo_optimizer.core.audit_schema import audit_schema
from geo_optimizer.models.config import ORGANIZATION_TYPES
from geo_optimizer.models.results import ContentResult, MetaResult

LOCAL_BUSINESS_SCHEMA = {
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    "name": "Acme Plumbing",
    "url": "https://acme-plumbing.example/",
    "logo": "https://acme-plumbing.example/logo.png",
    "telephone": "+1-555-0100",
    "email": "hello@acme-plumbing.example",
}


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def _schema_html(schema_dict: dict) -> str:
    blob = json.dumps(schema_dict)
    return f'<html><head><script type="application/ld+json">{blob}</script></head><body></body></html>'


class TestOrganizationTypesConstant:
    def test_includes_bare_organization(self):
        assert "Organization" in ORGANIZATION_TYPES

    def test_includes_local_business_and_common_subtypes(self):
        for expected in ("LocalBusiness", "Restaurant", "ProfessionalService", "Dentist", "Store"):
            assert expected in ORGANIZATION_TYPES


class TestAuditSchemaRecognizesOrganizationSubtypes:
    def test_local_business_counts_as_organization(self):
        """A LocalBusiness node with name/url/logo should satisfy has_organization."""
        result = audit_schema(_soup(_schema_html(LOCAL_BUSINESS_SCHEMA)), "https://acme-plumbing.example/")
        assert result.has_organization is True

    def test_bare_organization_still_counts(self):
        """Regression guard: the original literal-string match must keep working."""
        schema = {**LOCAL_BUSINESS_SCHEMA, "@type": "Organization"}
        result = audit_schema(_soup(_schema_html(schema)), "https://acme-plumbing.example/")
        assert result.has_organization is True

    def test_restaurant_counts_as_organization(self):
        schema = {**LOCAL_BUSINESS_SCHEMA, "@type": "Restaurant"}
        result = audit_schema(_soup(_schema_html(schema)), "https://acme-plumbing.example/")
        assert result.has_organization is True

    def test_unrelated_type_does_not_count(self):
        schema = {**LOCAL_BUSINESS_SCHEMA, "@type": "Recipe"}
        result = audit_schema(_soup(_schema_html(schema)), "https://acme-plumbing.example/")
        assert result.has_organization is False


class TestAuditBrandRecognizesOrganizationContactInfo:
    def test_local_business_telephone_counts_as_contact_info(self):
        """A LocalBusiness with telephone/email should satisfy has_contact_info,
        even with no /about link and no knowledge-graph presence, so the effect
        of this fix in isolation is visible."""
        html = _schema_html(LOCAL_BUSINESS_SCHEMA)
        soup = _soup(html)
        schema_result = audit_schema(soup, "https://acme-plumbing.example/")
        result = audit_brand_entity(soup, schema_result, MetaResult(), ContentResult())
        assert result.has_contact_info is True

    def test_bare_organization_still_counts(self):
        html = _schema_html({**LOCAL_BUSINESS_SCHEMA, "@type": "Organization"})
        soup = _soup(html)
        schema_result = audit_schema(soup, "https://acme-plumbing.example/")
        result = audit_brand_entity(soup, schema_result, MetaResult(), ContentResult())
        assert result.has_contact_info is True

    def test_local_business_without_contact_fields_does_not_count(self):
        schema = {k: v for k, v in LOCAL_BUSINESS_SCHEMA.items() if k not in ("telephone", "email")}
        html = _schema_html(schema)
        soup = _soup(html)
        schema_result = audit_schema(soup, "https://acme-plumbing.example/")
        result = audit_brand_entity(soup, schema_result, MetaResult(), ContentResult())
        assert result.has_contact_info is False
