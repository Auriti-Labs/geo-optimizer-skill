"""Test per WebMCP Readiness Check (#233)."""

from __future__ import annotations

from bs4 import BeautifulSoup

from geo_optimizer.core.audit import audit_webmcp_readiness
from geo_optimizer.models.results import SchemaResult


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
