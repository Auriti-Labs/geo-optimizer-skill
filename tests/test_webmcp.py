"""Test per WebMCP Readiness Check (#233)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from bs4 import BeautifulSoup

from geo_optimizer.core.audit import audit_webmcp_readiness
from geo_optimizer.core.audit_ai_discovery import _audit_ai_discovery_from_responses
from geo_optimizer.models.results import AiDiscoveryResult, SchemaResult


def _schema_with_action(action_type="SearchAction"):
    """Schema con potentialAction."""
    return SchemaResult(
        raw_schemas=[
            {
                "@type": "WebSite",
                "name": "Test",
                "potentialAction": {"@type": action_type, "target": "https://example.com/search?q={query}"},
            }
        ],
        found_types=["WebSite"],
        any_schema_found=True,
    )


class TestWebMcpReadiness:
    """Test per audit_webmcp_readiness()."""

    def test_empty_page(self):
        """Pagina vuota → checked ma nessun segnale."""
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        result = audit_webmcp_readiness(soup, "<html><body></body></html>", SchemaResult())
        assert result.checked is True
        assert result.readiness_level == "none"
        assert result.agent_ready is False

    def test_register_tool_detected(self):
        """navigator.modelContext.registerTool() nel JS → detected."""
        html = '<html><body><script>navigator.modelContext.registerTool({name:"search"})</script></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        result = audit_webmcp_readiness(soup, html, SchemaResult())
        assert result.has_register_tool is True

    def test_toolname_attributes_detected(self):
        """Attributi toolname/tooldescription → detected."""
        html = '<html><body><form toolname="search" tooldescription="Search the site"><input name="q"></form></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        result = audit_webmcp_readiness(soup, html, SchemaResult())
        assert result.has_tool_attributes is True
        assert result.tool_count == 1

    def test_potential_action_detected(self):
        """Schema potentialAction → detected."""
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        schema = _schema_with_action("SearchAction")
        result = audit_webmcp_readiness(soup, "<html><body></body></html>", schema)
        assert result.has_potential_action is True
        assert "SearchAction" in result.potential_actions

    def test_labeled_forms_detected(self):
        """Form con label accessibili → detected."""
        html = """<html><body>
        <form action="/search">
            <label for="q">Cerca</label>
            <input id="q" type="text" name="q">
            <button type="submit">Go</button>
        </form>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = audit_webmcp_readiness(soup, html, SchemaResult())
        assert result.has_labeled_forms is True
        assert result.labeled_forms_count == 1

    def test_openapi_link_detected(self):
        """Link a OpenAPI/Swagger → detected."""
        html = '<html><body><a href="/api-docs">API Documentation</a></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        result = audit_webmcp_readiness(soup, html, SchemaResult())
        assert result.has_openapi is True

    def test_readiness_none(self):
        """Nessun segnale → none."""
        soup = BeautifulSoup("<html><body><p>Hello</p></body></html>", "html.parser")
        result = audit_webmcp_readiness(soup, "<html><body><p>Hello</p></body></html>", SchemaResult())
        assert result.readiness_level == "none"
        assert result.agent_ready is False

    def test_readiness_basic(self):
        """Solo 1 agent signal → basic."""
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        schema = _schema_with_action()
        result = audit_webmcp_readiness(soup, "<html><body></body></html>", schema)
        assert result.readiness_level == "basic"
        assert result.agent_ready is False

    def test_readiness_ready(self):
        """2 agent signals → ready."""
        html = """<html><body>
        <form action="/s"><label for="q">Search</label><input id="q" name="q"></form>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        schema = _schema_with_action()
        result = audit_webmcp_readiness(soup, html, schema)
        assert result.readiness_level == "ready"
        assert result.agent_ready is True

    def test_readiness_advanced(self):
        """WebMCP + 2 agent signals → advanced."""
        html = """<html><body>
        <form toolname="search" tooldescription="Search"><label for="q">Query</label><input id="q" name="q"></form>
        <a href="/api-docs">API</a>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        schema = _schema_with_action()
        result = audit_webmcp_readiness(soup, html, schema)
        assert result.readiness_level == "advanced"
        assert result.agent_ready is True

    def test_none_soup_returns_unchecked(self):
        """None soup → unchecked."""
        result = audit_webmcp_readiness(None, "", SchemaResult())
        assert result.checked is False

    def test_graph_format_actions(self):
        """potentialAction in @graph format → detected."""
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        schema = SchemaResult(
            raw_schemas=[
                {
                    "@graph": [
                        {"@type": "WebSite", "potentialAction": {"@type": "SearchAction"}},
                        {"@type": "Organization", "name": "Test"},
                    ]
                }
            ],
            found_types=["WebSite", "Organization"],
            any_schema_found=True,
        )
        result = audit_webmcp_readiness(soup, "<html><body></body></html>", schema)
        assert result.has_potential_action is True
        assert "SearchAction" in result.potential_actions

    def test_multiple_actions(self):
        """Multiple potentialAction → tutti estratti."""
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        schema = SchemaResult(
            raw_schemas=[
                {
                    "@type": "WebSite",
                    "potentialAction": [
                        {"@type": "SearchAction"},
                        {"@type": "BuyAction"},
                    ],
                }
            ],
            found_types=["WebSite"],
            any_schema_found=True,
        )
        result = audit_webmcp_readiness(soup, "<html><body></body></html>", schema)
        assert "SearchAction" in result.potential_actions
        assert "BuyAction" in result.potential_actions

    def test_form_with_aria_label(self):
        """Form con input aria-label → labeled."""
        html = """<html><body>
        <form action="/search">
            <input type="text" name="q" aria-label="Cerca nel sito">
        </form>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = audit_webmcp_readiness(soup, html, SchemaResult())
        assert result.has_labeled_forms is True

    def test_form_hidden_only_not_labeled(self):
        """Form con solo input hidden → non labeled."""
        html = """<html><body>
        <form action="/track">
            <input type="hidden" name="token" value="abc">
            <button type="submit">Send</button>
        </form>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        result = audit_webmcp_readiness(soup, html, SchemaResult())
        assert result.has_labeled_forms is False


def _mock_response(status_code: int, text: str = ""):
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    return r


class TestWebMcpDeclaration:
    """#535: registerTool() calls made by external bundled JS are invisible to the
    static HTML scan. A "webmcp" block in /ai/summary.json is credited as a
    documented discovery signal instead, using data already fetched for the
    AI-discovery check (no extra HTTP request).
    """

    def test_summary_json_declares_available_webmcp(self):
        """/ai/summary.json with webmcp.available=true is parsed into AiDiscoveryResult."""
        summary = json.dumps(
            {
                "name": "Example Site",
                "description": "A site with WebMCP tools registered by bundled JS.",
                "webmcp": {
                    "available": True,
                    "api": "document.modelContext",
                    "tools": ["search", "book", "cancel", "status", "support"],
                },
            }
        )
        ai_disc = _audit_ai_discovery_from_responses(None, _mock_response(200, summary), None, None)
        assert ai_disc.has_webmcp_declaration is True
        assert ai_disc.webmcp_declared_tool_count == 5

    def test_summary_json_without_webmcp_block(self):
        summary = json.dumps({"name": "Example Site", "description": "No WebMCP block here at all."})
        ai_disc = _audit_ai_discovery_from_responses(None, _mock_response(200, summary), None, None)
        assert ai_disc.has_webmcp_declaration is False
        assert ai_disc.webmcp_declared_tool_count == 0

    def test_webmcp_available_false_not_credited(self):
        summary = json.dumps(
            {
                "name": "Example Site",
                "description": "Declares the block but is not live yet.",
                "webmcp": {"available": False},
            }
        )
        ai_disc = _audit_ai_discovery_from_responses(None, _mock_response(200, summary), None, None)
        assert ai_disc.has_webmcp_declaration is False

    def test_declaration_credited_as_partial_readiness(self):
        """The exact #535 repro shape: static scan finds nothing, but the site
        publishes a webmcp discovery block — readiness should move off "none"."""
        html = "<html><body><p>No inline registerTool() call — it's in a bundled JS file.</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        ai_disc = AiDiscoveryResult(has_webmcp_declaration=True, webmcp_declared_tool_count=5)

        result = audit_webmcp_readiness(soup, html, SchemaResult(), ai_disc)

        assert result.has_register_tool is False  # still not detected in raw HTML
        assert result.has_webmcp_declaration is True
        assert result.declared_tool_count == 5
        assert result.readiness_level != "none"
        assert result.agent_ready is True

    def test_no_ai_discovery_passed_keeps_previous_behavior(self):
        """Omitting ai_discovery (default None) must not change existing callers."""
        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = audit_webmcp_readiness(soup, html, SchemaResult())
        assert result.has_webmcp_declaration is False
        assert result.declared_tool_count == 0
        assert result.readiness_level == "none"

    def test_declaration_alone_does_not_imply_advanced(self):
        """A discovery declaration with no other agent-readiness signal is "ready", not "advanced"."""
        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        ai_disc = AiDiscoveryResult(has_webmcp_declaration=True, webmcp_declared_tool_count=2)

        result = audit_webmcp_readiness(soup, html, SchemaResult(), ai_disc)

        assert result.readiness_level == "ready"
