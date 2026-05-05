"""
Test for async audit path and edge cases.

Covers run_full_audit_async(), _audit_robots_from_response(),
_audit_llms_from_response(), and async/sync parity (fix #194).
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

pytest.importorskip("httpx", reason="httpx not installed (pip install geo-optimizer-skill[async])")

from geo_optimizer.core.audit import (
    _audit_llms_from_response,
    _audit_robots_from_response,
)
from geo_optimizer.models.config import AI_BOTS

# ============================================================================
# _audit_robots_from_response
# ============================================================================


class TestAuditRobotsFromResponse:
    """Tests for the async-path robots.txt parser."""

    def test_none_response_returns_empty(self):
        result = _audit_robots_from_response(None)
        assert result.found is False
        assert result.bots_allowed == []

    def test_non_200_returns_empty(self):
        r = Mock(status_code=404, text="Not found")
        result = _audit_robots_from_response(r)
        assert result.found is False

    def test_valid_robots_parses_bots(self):
        r = Mock(
            status_code=200,
            text="User-agent: GPTBot\nAllow: /\n\nUser-agent: ClaudeBot\nAllow: /\n",
        )
        result = _audit_robots_from_response(r)
        assert result.found is True
        assert "GPTBot" in result.bots_allowed
        assert "ClaudeBot" in result.bots_allowed

    def test_custom_bots_parameter(self):
        """extra_bots from config are checked when passed."""
        custom_bots = {**AI_BOTS, "MyCustomBot": "Custom bot"}
        r = Mock(
            status_code=200,
            text="User-agent: *\nAllow: /\n",
        )
        result = _audit_robots_from_response(r, bots=custom_bots)
        assert result.found is True
        # All bots including custom should be in some list
        assert len(result.bots_allowed) + len(result.bots_missing) + len(result.bots_blocked) > 0


# ============================================================================
# _audit_llms_from_response
# ============================================================================


class TestAuditLlmsFromResponse:
    """Tests for the async-path llms.txt parser."""

    def test_none_response_returns_empty(self):
        result = _audit_llms_from_response(None)
        assert result.found is False
        assert result.has_full is False

    def test_valid_llms_parses_structure(self):
        r = Mock(
            status_code=200,
            text="# My Site\n\n> Description\n\n## Section\n\n- [Link](https://example.com)\n",
        )
        result = _audit_llms_from_response(r)
        assert result.found is True
        assert result.has_h1 is True
        assert result.has_description is True
        assert result.has_sections is True
        assert result.has_links is True

    def test_has_full_with_response(self):
        """has_full is True when r_full is a valid 200 response."""
        r = Mock(status_code=200, text="# Site\n")
        r_full = Mock(status_code=200, text="Full content here")
        result = _audit_llms_from_response(r, r_full=r_full)
        assert result.has_full is True

    def test_has_full_without_response(self):
        """has_full is False when r_full is None."""
        r = Mock(status_code=200, text="# Site\n")
        result = _audit_llms_from_response(r, r_full=None)
        assert result.has_full is False

    def test_has_full_404(self):
        """has_full is False when r_full is 404."""
        r = Mock(status_code=200, text="# Site\n")
        r_full = Mock(status_code=404, text="Not found")
        result = _audit_llms_from_response(r, r_full=r_full)
        assert result.has_full is False

    def test_bom_stripped(self):
        """BOM UTF-8 is stripped from llms.txt content."""
        r = Mock(status_code=200, text="\ufeff# Site With BOM\n")
        result = _audit_llms_from_response(r)
        assert result.has_h1 is True


# ============================================================================
# SSRF validation (sync wrappers for async functions)
# ============================================================================


class TestAsyncSSRFValidation:
    """Tests for SSRF protection in the async fetch path (sync verification)."""

    def test_validate_public_url_blocks_metadata(self):
        """validate_public_url blocks cloud metadata IPs used by async path."""
        from geo_optimizer.utils.validators import validate_public_url

        ok, err = validate_public_url("http://169.254.169.254/metadata")
        assert ok is False

    def test_validate_public_url_blocks_localhost(self):
        from geo_optimizer.utils.validators import validate_public_url

        ok, err = validate_public_url("http://localhost:8080")
        assert ok is False
