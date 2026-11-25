"""Third-party check plugins are opt-in for the MCP server and geo-web (GEO_ENABLE_PLUGINS)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from geo_optimizer.core.registry import server_plugins_enabled


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, False), ("", False), ("0", False), ("no", False), ("1", True), ("true", True), (" On ", True)],
)
def test_server_plugins_enabled_reads_the_env(monkeypatch, value, expected):
    """Plugins stay off unless GEO_ENABLE_PLUGINS is explicitly truthy."""
    monkeypatch.delenv("GEO_ENABLE_PLUGINS", raising=False)
    if value is not None:
        monkeypatch.setenv("GEO_ENABLE_PLUGINS", value)
    assert server_plugins_enabled() is expected


def test_mcp_geo_audit_does_not_load_plugins_by_default(monkeypatch):
    """geo_audit passes load_plugins=False to the engine unless the operator opted in."""
    pytest.importorskip("mcp")
    from geo_optimizer.mcp.server import geo_audit

    monkeypatch.delenv("GEO_ENABLE_PLUGINS", raising=False)
    result = MagicMock()
    with (
        patch("geo_optimizer.core.audit.run_full_audit", return_value=result) as audit,
        patch("geo_optimizer.mcp.server._to_json", return_value=json.dumps({"ok": True})),
    ):
        geo_audit("https://example.com")
    assert audit.call_args.kwargs["load_plugins"] is False

    monkeypatch.setenv("GEO_ENABLE_PLUGINS", "1")
    with (
        patch("geo_optimizer.core.audit.run_full_audit", return_value=result) as audit,
        patch("geo_optimizer.mcp.server._to_json", return_value=json.dumps({"ok": True})),
    ):
        geo_audit("https://example.com")
    assert audit.call_args.kwargs["load_plugins"] is True


def test_web_audit_does_not_load_plugins_by_default(monkeypatch):
    """POST /api/audit runs the engine with load_plugins=False unless the operator opted in."""
    from starlette.testclient import TestClient

    from geo_optimizer.web.app import _audit_cache, _rate_limit_store, app
    from tests.test_web_app import _make_mock_audit_result

    monkeypatch.delenv("GEO_ENABLE_PLUGINS", raising=False)
    _audit_cache.clear()
    _rate_limit_store.clear()
    with patch("geo_optimizer.core.audit.run_full_audit", return_value=_make_mock_audit_result()) as audit:
        TestClient(app).post("/api/audit", json={"url": "https://example.com"})
    assert audit.call_args.kwargs["load_plugins"] is False
