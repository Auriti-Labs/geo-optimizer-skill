"""Audit WebMCP Readiness — agent-readiness signals for AI and MCP (#233).

Extracted from audit.py — separation of concerns.
Zero HTTP fetches — works only on already-available data.
"""

from __future__ import annotations

import json  # noqa: F401 (available for future extensions)
import re  # noqa: F401 (available for future extensions)

from geo_optimizer.models.results import WebMcpResult


def _extract_actions(schema_obj, action_types: set) -> None:
    """Extract potentialAction from a JSON-LD schema object (recursive).

    Args:
        schema_obj: Schema object (dict, list or primitive value).
        action_types: Set to add found action types to.
    """
    if isinstance(schema_obj, dict):
        # Support @graph (Yoast SEO, RankMath)
        if "@graph" in schema_obj:
            for item in schema_obj["@graph"]:
                _extract_actions(item, action_types)
            return

        potential = schema_obj.get("potentialAction")
        if potential:
            if isinstance(potential, dict):
                action_type = potential.get("@type", "")
                if action_type:
                    action_types.add(action_type)
            elif isinstance(potential, list):
                for action in potential:
                    if isinstance(action, dict):
                        action_type = action.get("@type", "")
                        if action_type:
                            action_types.add(action_type)
    elif isinstance(schema_obj, list):
        for item in schema_obj:
            _extract_actions(item, action_types)


def audit_webmcp_readiness(soup, raw_html: str, schema_result) -> WebMcpResult:
    """Check WebMCP readiness and agent-readiness signals (#233).

    Analyzes:
    1. WebMCP API: registerTool(), toolname/tooldescription attributes
    2. Schema potentialAction: SearchAction, BuyAction, OrderAction
    3. Accessible forms: form with label + aria-label/placeholder
    4. OpenAPI: link to /api-docs, /swagger, openapi.json

    Zero HTTP fetches — works only on already-available data.

    Args:
        soup: BeautifulSoup of the page.
        raw_html: Raw HTML of the page.
        schema_result: SchemaResult with the JSON-LD schemas found.

    Returns:
        WebMcpResult with detected readiness signals.
    """
    result = WebMcpResult()
    if soup is None or not raw_html:
        return result

    result.checked = True

    # ── 1. WebMCP Detection ──────────────────────────────────────
    # API imperativa: navigator.modelContext.registerTool()
    if "modelContext" in raw_html and "registerTool" in raw_html:
        result.has_register_tool = True

    # API dichiarativa: attributi toolname/tooldescription sugli elementi HTML
    tool_elements = soup.find_all(attrs={"toolname": True})
    if tool_elements:
        result.has_tool_attributes = True
        result.tool_count = len(tool_elements)

    # ── 2. Schema potentialAction ────────────────────────────────
    action_types: set = set()
    for raw_schema in schema_result.raw_schemas:
        _extract_actions(raw_schema, action_types)

    if action_types:
        result.has_potential_action = True
        result.potential_actions = sorted(action_types)

    # ── 3. Accessible forms (agent-usable) ──────────────────────
    forms = soup.find_all("form")
    labeled_count = 0
    for form in forms:
        # A form is "agent-usable" if it has:
        # - at least 1 input with an associated label OR aria-label OR descriptive placeholder
        # - an action or method defined
        inputs = form.find_all(["input", "select", "textarea"])
        has_labels = False
        for inp in inputs:
            inp_type = (inp.get("type") or "text").lower()
            if inp_type in ("hidden", "submit", "button"):
                continue
            # Label associated via for/id
            inp_id = inp.get("id")
            if inp_id and form.find("label", attrs={"for": inp_id}):
                has_labels = True
                break
            # aria-label or placeholder
            if inp.get("aria-label") or inp.get("placeholder"):
                has_labels = True
                break
        if has_labels and len(inputs) > 0:
            labeled_count += 1

    if labeled_count > 0:
        result.has_labeled_forms = True
        result.labeled_forms_count = labeled_count

    # ── 4. OpenAPI/Swagger detection ─────────────────────────────
    openapi_patterns = ["/api-docs", "/swagger", "openapi.json", "openapi.yaml", "swagger.json"]
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].lower()
        if any(pattern in href for pattern in openapi_patterns):
            result.has_openapi = True
            break
    # Also check link tags
    if not result.has_openapi:
        for link in soup.find_all("link", href=True):
            href = link["href"].lower()
            if any(pattern in href for pattern in openapi_patterns):
                result.has_openapi = True
                break

    # ── Readiness level ──────────────────────────────────────────
    webmcp_signals = sum([result.has_register_tool, result.has_tool_attributes])
    agent_signals = sum([result.has_potential_action, result.has_labeled_forms, result.has_openapi])

    if webmcp_signals > 0 and agent_signals >= 2:
        result.readiness_level = "advanced"
        result.agent_ready = True
    elif webmcp_signals > 0 or agent_signals >= 2:
        result.readiness_level = "ready"
        result.agent_ready = True
    elif agent_signals >= 1:
        result.readiness_level = "basic"
    else:
        result.readiness_level = "none"

    return result
