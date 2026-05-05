"""
Tests for MCP server tools not covered by test_mcp.py.

This file fills coverage gaps for:
- geo_citability fetch error path
- geo_compare (happy and error paths)
- geo_negative_signals (happy path)

 Richiede: pip install geo-optimizer-skill[mcp]
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

# Skip se mcp non installato
pytest.importorskip("mcp", reason="mcp non installato (pip install geo-optimizer-skill[mcp])")

from geo_optimizer.mcp.server import (
    geo_citability,
    geo_compare,
    geo_negative_signals,
)


@pytest.fixture(autouse=True)
def _mock_mcp_url_validation(monkeypatch):
    """Rende deterministica la validazione URL nei test MCP."""

    def _fake_validate(url):
        from urllib.parse import urlparse

        host = (urlparse(url).hostname or "").lower()
        if host.endswith("example.com"):
            return True, None
        if host in {"localhost", "169.254.169.254", "192.168.0.1", "10.0.0.1"}:
            return False, "blocked for test"
        return True, None

    monkeypatch.setattr("geo_optimizer.utils.validators.validate_public_url", _fake_validate)


# ─── Tests: geo_citability (fetch error path already in test_mcp.py, but test_fetch_error missing) ───


class TestGeoCitabilityToolAdditional:
    """Test geo_citability fetch error path (not covered by test_mcp.py)."""

    @patch("geo_optimizer.utils.http.fetch_url")
    @patch("geo_optimizer.core.citability.audit_citability")
    def test_citability_fetch_error(self, mock_citability, mock_fetch):
        """geo_citability con fetch_url che ritorna errore restituisce messaggio di errore."""
        mock_fetch.return_value = (None, "Connection error")
        result = geo_citability("https://example.com")
        assert "error" in result
        assert "Connection error" in result


# ─── Tests: geo_compare (not covered by test_mcp.py) ──────────────────────────


class TestGeoCompareToolAdditional:
    """Test geo_compare (not covered by test_mcp.py)."""

    @patch("geo_optimizer.core.audit.run_full_audit")
    def test_compare_success_two_urls(self, mock_audit):
        """geo_compare con due URLs validi ritorna comparison con punteggi."""
        mock_result1 = MagicMock()
        mock_result1.score = 70
        mock_result1.band = "good"
        mock_result1.score_breakdown = {"robots": 16, "llms": 12, "schema": 14}
        mock_result1.recommendations = ["add llms.txt"]

        mock_result2 = MagicMock()
        mock_result2.score = 85
        mock_result2.band = "excellent"
        mock_result2.score_breakdown = {"robots": 18, "llms": 16, "schema": 16}
        mock_result2.recommendations = []

        mock_audit.side_effect = [mock_result1, mock_result2]
        result = geo_compare("https://example.com,https://example.org")
        data = json.loads(result)
        assert "comparison" in data
        assert len(data["comparison"]) == 2
        assert any(item["score"] == 70 for item in data["comparison"])
        assert any(item["score"] == 85 for item in data["comparison"])

    @patch("geo_optimizer.core.audit.run_full_audit")
    def test_compare_error_invalid_url(self, mock_audit):
        """geo_compare gestisce URL invalidi e restituisce error per quelli."""
        mock_result = MagicMock()
        mock_result.score = 80
        mock_result.band = "good"
        mock_result.score_breakdown = {"robots": 16, "llms": 14, "schema": 16}
        mock_result.recommendations = []

        mock_audit.return_value = mock_result
        result = geo_compare("http://localhost:8080,https://example.com")
        data = json.loads(result)
        assert len(data["comparison"]) == 2
        # One entry has error (localhost), one has score (example.com)
        has_error = any("error" in item for item in data["comparison"])
        has_score = any("score" in item for item in data["comparison"])
        assert has_error
        assert has_score


# ─── Tests: geo_negative_signals (not covered by test_mcp.py) ─────────────────


class TestGeoNegativeSignalsTool:
    """Test geo_negative_signals (not covered by test_mcp.py)."""

    @patch("geo_optimizer.core.audit.run_full_audit")
    def test_negative_signals_success(self, mock_audit):
        """geo_negative_signals ritorna negative signals analysis."""
        neg_signals = {
            "checked": True,
            "cta_density_high": False,
            "cta_count": 1,
            "has_popup_signals": False,
            "popup_indicators": [],
            "is_thin_content": False,
            "severity": "low",
        }
        mock_result = MagicMock()
        mock_result.negative_signals = neg_signals
        mock_audit.return_value = mock_result
        result = geo_negative_signals("https://example.com")
        data = json.loads(result)
        assert "checked" in data
        assert data["checked"] is True
        assert "cta_count" in data
        assert data["cta_count"] == 1
        assert "has_popup_signals" in data
        assert "severity" in data
        assert data["severity"] == "low"
