"""
CI/CD output formatters — SARIF and JUnit for pipeline integration.

SARIF (Static Analysis Results Interchange Format):
    OASIS standard for static analysis results. Compatible with
    GitHub Code Scanning, GitLab SAST, Azure DevOps, SonarQube.

JUnit XML:
    De facto standard for test results in CI/CD. Compatible with
    GitHub Actions, GitLab CI, Jenkins, CircleCI, Azure DevOps.
"""

from __future__ import annotations

import json
from xml.etree.ElementTree import Element, SubElement, tostring

from geo_optimizer.cli.scoring_helpers import (
    brand_entity_score,
    content_score,
    llms_score,
    meta_score,
    robots_score,
    schema_score,
)
from geo_optimizer.models.config import SCORING
from geo_optimizer.models.results import AuditResult

# Per-category max scores computed dynamically from SCORING (avoids hardcoding — v4.3)
_MAX_ROBOTS = SCORING["robots_found"] + SCORING["robots_citation_ok"]
_MAX_LLMS = (
    SCORING["llms_found"]
    + SCORING["llms_h1"]
    + SCORING["llms_blockquote"]
    + SCORING["llms_sections"]
    + SCORING["llms_links"]
    + SCORING["llms_depth"]
    + SCORING["llms_depth_high"]
    + SCORING["llms_full"]
)
_MAX_SCHEMA = (
    SCORING["schema_any_valid"]
    + SCORING["schema_richness"]
    + SCORING["schema_faq"]
    + SCORING["schema_article"]
    + SCORING["schema_organization"]
    + SCORING["schema_website"]
    + SCORING["schema_sameas"]
)
_MAX_META = SCORING["meta_title"] + SCORING["meta_description"] + SCORING["meta_canonical"] + SCORING["meta_og"]
_MAX_CONTENT = (
    SCORING["content_h1"]
    + SCORING["content_numbers"]
    + SCORING["content_links"]
    + SCORING["content_word_count"]
    + SCORING["content_heading_hierarchy"]
    + SCORING["content_lists_or_tables"]
    + SCORING["content_front_loading"]
)
_MAX_BRAND_ENTITY = (
    SCORING["brand_entity_coherence"]
    + SCORING["brand_kg_readiness"]
    + SCORING["brand_geo_identity"]
    + SCORING["brand_topic_authority"]
    + 2  # about_link (1pt) + contact_info (1pt) — scored inline in scoring.py
)

# ─── SARIF ────────────────────────────────────────────────────────────────────


def format_audit_sarif(result: AuditResult) -> str:
    """Format audit result as SARIF v2.1.0 JSON.

    Each failed check becomes a SARIF "result" with:
    - ruleId matching the check category
    - level: error (critical), warning (foundation), note (good)
    - message with recommendation
    """
    rules = []
    results = []

    # Map each check category to SARIF rules and results
    checks = [
        ("geo/robots-txt", "robots.txt AI Bot Access", _robots_findings(result)),
        ("geo/llms-txt", "llms.txt AI Index File", _llms_findings(result)),
        ("geo/schema-jsonld", "JSON-LD Schema Markup", _schema_findings(result)),
        ("geo/meta-tags", "SEO Meta Tags", _meta_findings(result)),
        ("geo/content-quality", "Content Quality", _content_findings(result)),
    ]

    for rule_id, rule_name, findings in checks:
        rules.append(
            {
                "id": rule_id,
                "name": rule_name,
                "shortDescription": {"text": rule_name},
            }
        )

        for finding in findings:
            results.append(
                {
                    "ruleId": rule_id,
                    "level": finding["level"],
                    "message": {"text": finding["message"]},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": result.url},
                            }
                        }
                    ],
                }
            )

    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "GEO Optimizer",
                        "informationUri": "https://github.com/auriti-labs/geo-optimizer-skill",
                        "version": _get_version(),
                        "rules": rules,
                    }
                },
                "results": results,
                "invocations": [
                    {
                        "executionSuccessful": True,
                        "properties": {
                            "geoScore": result.score,
                            "geoBand": result.band,
                        },
                    }
                ],
            }
        ],
    }

    return json.dumps(sarif, indent=2, ensure_ascii=False)


def _get_version() -> str:
    """Get GEO Optimizer version."""
    try:
        from geo_optimizer import __version__

        return __version__
    except ImportError:
        return "unknown"


def _level_for_score(category_score: int, max_score: int) -> str:
    """Map score to SARIF level."""
    ratio = category_score / max_score if max_score > 0 else 0
    if ratio >= 0.8:
        return "note"
    if ratio >= 0.4:
        return "warning"
    return "error"


def _robots_findings(result: AuditResult) -> list[dict]:
    findings = []
    if not result.robots.found:
        findings.append({"level": "error", "message": "robots.txt not found — AI bots cannot determine access rules"})
    elif result.robots.bots_blocked:
        findings.append(
            {
                "level": "warning",
                "message": f"AI bots blocked in robots.txt: {', '.join(result.robots.bots_blocked)}",
            }
        )
    if result.robots.bots_missing:
        findings.append(
            {
                "level": "warning",
                "message": f"AI bots not configured in robots.txt: {', '.join(result.robots.bots_missing[:5])}",
            }
        )
    if not result.robots.citation_bots_ok:
        findings.append(
            {
                "level": "error",
                "message": "Critical citation bots (OAI-SearchBot, ClaudeBot, PerplexityBot) not properly configured",
            }
        )
    return findings


def _llms_findings(result: AuditResult) -> list[dict]:
    findings = []
    if not result.llms.found:
        findings.append({"level": "error", "message": "llms.txt not found — essential for AI search indexing"})
    else:
        if not result.llms.has_h1:
            findings.append({"level": "warning", "message": "llms.txt missing H1 header"})
        if not result.llms.has_sections:
            findings.append({"level": "warning", "message": "llms.txt missing H2 sections"})
        if not result.llms.has_links:
            findings.append({"level": "warning", "message": "llms.txt missing markdown links"})
    return findings


def _schema_findings(result: AuditResult) -> list[dict]:
    findings = []
    if not result.schema.has_website:
        findings.append({"level": "error", "message": "WebSite JSON-LD schema missing on homepage"})
    if not result.schema.has_organization:
        findings.append({"level": "warning", "message": "Organization JSON-LD schema missing"})
    if not result.schema.has_faq:
        findings.append({"level": "note", "message": "FAQPage schema not found — recommended for Q&A content"})
    return findings


def _meta_findings(result: AuditResult) -> list[dict]:
    findings = []
    if not result.meta.has_title:
        findings.append({"level": "error", "message": "Page title missing"})
    if not result.meta.has_description:
        findings.append({"level": "error", "message": "Meta description missing"})
    if not result.meta.has_canonical:
        findings.append({"level": "warning", "message": "Canonical URL not set"})
    if not (result.meta.has_og_title and result.meta.has_og_description):
        findings.append({"level": "warning", "message": "Open Graph tags incomplete"})
    return findings


def _content_findings(result: AuditResult) -> list[dict]:
    findings = []
    if not result.content.has_h1:
        findings.append({"level": "warning", "message": "H1 heading missing on homepage"})
    if not result.content.has_numbers:
        findings.append({"level": "note", "message": "No statistics or numerical data found (+33% AI visibility)"})
    if not result.content.has_links:
        findings.append({"level": "note", "message": "No external links to authoritative sources (+27% AI visibility)"})
    if result.content.word_count < 300:
        findings.append(
            {
                "level": "warning",
                "message": f"Content too short ({result.content.word_count} words, minimum 300 recommended)",
            }
        )
    return findings


# ─── JUnit XML ────────────────────────────────────────────────────────────────


def format_audit_junit(result: AuditResult) -> str:
    """Format audit result as JUnit XML.

    Each check category becomes a test suite. Failed checks become
    test failures with the recommendation as message.
    """
    testsuites = Element("testsuites")
    testsuites.set("name", "GEO Optimizer Audit")
    # Fix #430: initial value overwritten at line 316 with actual count
    testsuites.set("tests", "0")

    categories = [
        ("robots_txt", "Robots.txt AI Bot Access", robots_score(result), _MAX_ROBOTS, _robots_findings(result)),
        ("llms_txt", "llms.txt AI Index File", llms_score(result), _MAX_LLMS, _llms_findings(result)),
        ("schema_jsonld", "JSON-LD Schema Markup", schema_score(result), _MAX_SCHEMA, _schema_findings(result)),
        ("meta_tags", "SEO Meta Tags", meta_score(result), _MAX_META, _meta_findings(result)),
        ("content_quality", "Content Quality", content_score(result), _MAX_CONTENT, _content_findings(result)),
        ("brand_entity", "Brand & Entity Signals", brand_entity_score(result), _MAX_BRAND_ENTITY, []),
    ]

    total_failures = 0
    total_tests = 0

    for cat_id, cat_name, score, max_score, findings in categories:
        testsuite = SubElement(testsuites, "testsuite")
        testsuite.set("name", cat_name)
        testsuite.set("tests", str(1 + len(findings)))

        errors = [f for f in findings if f["level"] == "error"]

        testsuite.set("failures", str(len(errors)))
        testsuite.set("errors", "0")

        # Main score test case
        testcase = SubElement(testsuite, "testcase")
        testcase.set("name", f"{cat_name} Score")
        testcase.set("classname", f"geo.audit.{cat_id}")
        testcase.set("time", "0")

        if score < max_score * 0.5:
            failure = SubElement(testcase, "failure")
            failure.set("message", f"Score {score}/{max_score} below 50% threshold")
            failure.set("type", "GEOScoreFailure")
            total_failures += 1

        # Individual finding test cases
        for finding in findings:
            tc = SubElement(testsuite, "testcase")
            tc.set("name", finding["message"][:80])
            tc.set("classname", f"geo.audit.{cat_id}")
            tc.set("time", "0")

            if finding["level"] == "error":
                fail = SubElement(tc, "failure")
                fail.set("message", finding["message"])
                fail.set("type", "GEOCheckFailure")
                total_failures += 1
            elif finding["level"] == "warning":
                # JUnit doesn't have warnings — use system-out
                sysout = SubElement(tc, "system-out")
                sysout.text = f"WARNING: {finding['message']}"

        total_tests += 1 + len(findings)

    testsuites.set("tests", str(total_tests))
    testsuites.set("failures", str(total_failures))
    testsuites.set("errors", "0")

    # Add overall score as property
    props = SubElement(testsuites, "properties")
    prop_score = SubElement(props, "property")
    prop_score.set("name", "geo.score")
    prop_score.set("value", str(result.score))
    prop_band = SubElement(props, "property")
    prop_band.set("name", "geo.band")
    prop_band.set("value", result.band)

    xml_content = tostring(testsuites, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_content
