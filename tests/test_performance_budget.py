"""Tests for audit performance budget (#290)."""

from __future__ import annotations

import logging
from unittest.mock import Mock, patch

from geo_optimizer.core.audit import run_full_audit
from geo_optimizer.models.config import AUDIT_TIMEOUT_SECONDS


class TestPerformanceBudget:
    """Verify audit_duration_ms tracking and budget warning."""

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_audit_result_has_duration(self, mock_fetch):
        """run_full_audit populates audit_duration_ms."""
        mock_fetch.return_value = (None, "Connection refused")
        result = run_full_audit("https://example.com")
        assert result.audit_duration_ms is not None
        assert result.audit_duration_ms >= 0

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_mocked_audit_completes_under_2s(self, mock_fetch):
        """A fully-mocked audit must complete well under the 10s budget."""
        html = "<html><head><title>T</title></head><body><p>Hello</p></body></html>"
        mock_fetch.return_value = (Mock(status_code=200, text=html, headers={}), None)
        result = run_full_audit("https://example.com")
        assert result.audit_duration_ms < 2000, f"Audit took {result.audit_duration_ms}ms, expected < 2000ms"

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_budget_warning_logged_when_exceeded(self, mock_fetch, caplog):
        """Warning is logged when audit exceeds AUDIT_TIMEOUT_SECONDS."""
        html = "<html><head><title>T</title></head><body><p>Hello</p></body></html>"
        mock_fetch.return_value = (Mock(status_code=200, text=html, headers={}), None)
        with patch("geo_optimizer.core.audit.AUDIT_TIMEOUT_SECONDS", 0), caplog.at_level(logging.WARNING, logger="geo_optimizer.core.audit"):
            run_full_audit("https://example.com")
        assert any("exceeded" in r.message.lower() for r in caplog.records)

    def test_audit_timeout_constant_is_10(self):
        """AUDIT_TIMEOUT_SECONDS defaults to 10."""
        assert AUDIT_TIMEOUT_SECONDS == 10
