"""
Test per geo_optimizer.cli.ci_formatter — output SARIF e JUnit.

Verifica che gli output CI siano validi e contengano le informazioni attese.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

from geo_optimizer.cli.ci_formatter import format_audit_junit, format_audit_sarif
from geo_optimizer.models.results import (
    AuditResult,
    BrandEntityResult,
    ContentResult,
    LlmsTxtResult,
    MetaResult,
    RobotsResult,
    SchemaResult,
)


def _make_result(**overrides) -> AuditResult:
    """Crea un AuditResult per i test."""
    result = AuditResult(
        url="https://example.com",
        score=45,
        band="foundation",
        robots=RobotsResult(
            found=True,
            bots_allowed=["GPTBot"],
            bots_missing=["ClaudeBot"],
            bots_blocked=["Bytespider"],
            citation_bots_ok=False,
        ),
        llms=LlmsTxtResult(found=False),
        schema=SchemaResult(has_website=True),
        meta=MetaResult(has_title=True, has_description=False),
        content=ContentResult(has_h1=True, word_count=150),
        recommendations=["Create /llms.txt", "Add meta description"],
        http_status=200,
        page_size=5000,
    )
    for key, value in overrides.items():
        parts = key.split(".")
        obj = result
        for part in parts[:-1]:
            obj = getattr(obj, part)
        setattr(obj, parts[-1], value)
    return result


class TestSarifFormatter:
    """Test per output SARIF."""

    def test_sarif_json_valido(self):
        """Output SARIF è JSON valido con schema corretto."""
        result = _make_result()
        output = format_audit_sarif(result)
        data = json.loads(output)

        assert data["version"] == "2.1.0"
        assert "$schema" in data
        assert len(data["runs"]) == 1

    def test_sarif_contiene_tool_info(self):
        """SARIF contiene informazioni sul tool."""
        result = _make_result()
        data = json.loads(format_audit_sarif(result))
        driver = data["runs"][0]["tool"]["driver"]

        assert driver["name"] == "GEO Optimizer"
        assert "rules" in driver
        assert len(driver["rules"]) == 5

    def test_sarif_contiene_findings(self):
        """SARIF contiene risultati per check falliti."""
        result = _make_result()
        data = json.loads(format_audit_sarif(result))
        results = data["runs"][0]["results"]

        # Deve avere findings per llms.txt mancante, meta description mancante, ecc.
        assert len(results) > 0
        rule_ids = {r["ruleId"] for r in results}
        assert "geo/llms-txt" in rule_ids  # llms.txt non trovato

    def test_sarif_contiene_score(self):
        """SARIF contiene lo score GEO nelle proprietà."""
        result = _make_result()
        data = json.loads(format_audit_sarif(result))
        props = data["runs"][0]["invocations"][0]["properties"]

        assert props["geoScore"] == 45
        assert props["geoBand"] == "foundation"

    def test_sarif_sito_ottimizzato_pochi_findings(self):
        """Sito ottimizzato produce pochi o zero findings."""
        result = _make_result(
            **{
                "score": 95,
                "band": "excellent",
                "robots.citation_bots_ok": True,
                "robots.bots_missing": [],
                "robots.bots_blocked": [],
                "llms.found": True,
                "llms.has_h1": True,
                "llms.has_sections": True,
                "llms.has_links": True,
                "schema.has_website": True,
                "schema.has_organization": True,
                "schema.has_faq": True,
                "meta.has_title": True,
                "meta.has_description": True,
                "meta.has_canonical": True,
                "meta.has_og_title": True,
                "meta.has_og_description": True,
                "content.has_h1": True,
                "content.has_numbers": True,
                "content.has_links": True,
                "content.word_count": 500,
            }
        )
        data = json.loads(format_audit_sarif(result))
        results = data["runs"][0]["results"]

        # Sito ottimizzato: zero o pochissimi findings
        assert len(results) <= 2


class TestJunitFormatter:
    """Test per output JUnit XML."""

    def test_junit_xml_valido(self):
        """Output JUnit è XML valido e parsabile."""
        result = _make_result()
        output = format_audit_junit(result)

        # Deve essere parsabile come XML
        root = ET.fromstring(output)
        assert root.tag == "testsuites"

    def test_junit_contiene_test_suites(self):
        """JUnit contiene 6 test suite (5 originali + brand_entity v4.3)."""
        result = _make_result()
        root = ET.fromstring(format_audit_junit(result))

        testsuites = root.findall("testsuite")
        assert len(testsuites) == 6

    def test_junit_contiene_failures(self):
        """JUnit contiene failures per check non superati."""
        result = _make_result()
        root = ET.fromstring(format_audit_junit(result))

        total_failures = int(root.get("failures", "0"))
        assert total_failures > 0

    def test_junit_contiene_score_property(self):
        """JUnit contiene lo score GEO come property."""
        result = _make_result()
        root = ET.fromstring(format_audit_junit(result))

        props = root.find("properties")
        assert props is not None
        score_prop = props.find(".//property[@name='geo.score']")
        assert score_prop is not None
        assert score_prop.get("value") == "45"

    def test_junit_sito_ottimizzato_zero_failures(self):
        """Sito ottimizzato produce zero failures in JUnit."""
        result = _make_result(
            **{
                "score": 95,
                "robots.found": True,
                "robots.citation_bots_ok": True,
                "robots.bots_missing": [],
                "robots.bots_blocked": [],
                "llms.found": True,
                "llms.has_h1": True,
                "llms.has_sections": True,
                "llms.has_links": True,
                "schema.has_website": True,
                "schema.has_organization": True,
                "schema.has_faq": True,
                "schema.has_article": True,
                "meta.has_title": True,
                "meta.has_description": True,
                "meta.has_canonical": True,
                "meta.has_og_title": True,
                "meta.has_og_description": True,
                "content.has_h1": True,
                "content.has_numbers": True,
                "content.has_links": True,
                "content.word_count": 500,
            }
        )
        # v4.3: sito ottimizzato ha brand_entity con segnali forti (score >= 50%)
        result.brand_entity = BrandEntityResult(
            brand_name_consistent=True,
            kg_pillar_count=3,
            has_about_link=True,
            has_contact_info=True,
            has_geo_schema=True,
            faq_depth=3,
        )
        root = ET.fromstring(format_audit_junit(result))

        total_failures = int(root.get("failures", "0"))
        assert total_failures == 0
