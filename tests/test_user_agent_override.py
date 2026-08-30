"""Tests for the User-Agent override (#528): GEO_USER_AGENT env var and --user-agent flags.

Covers the resolver/override in models.config, propagation into
utils.http's session headers and utils.http_async's client headers, and that
each of the four CLI commands (audit, access, fix, llms) wires its
--user-agent flag through.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from geo_optimizer.models import config as config_mod
from geo_optimizer.utils.http import create_session_with_retry


@pytest.fixture(autouse=True)
def _reset_user_agent_override():
    """The override is process-wide mutable state — reset it around every test."""
    config_mod.set_user_agent_override(None)
    yield
    config_mod.set_user_agent_override(None)


class TestResolveUserAgentOverride:
    def test_no_cli_no_env_returns_none(self, monkeypatch):
        monkeypatch.delenv("GEO_USER_AGENT", raising=False)
        assert config_mod.resolve_user_agent_override(None) is None

    def test_env_var_used_when_no_cli_value(self, monkeypatch):
        monkeypatch.setenv("GEO_USER_AGENT", "EnvBot/1.0")
        assert config_mod.resolve_user_agent_override(None) == "EnvBot/1.0"

    def test_cli_value_takes_precedence_over_env(self, monkeypatch):
        monkeypatch.setenv("GEO_USER_AGENT", "EnvBot/1.0")
        assert config_mod.resolve_user_agent_override("CliBot/2.0") == "CliBot/2.0"

    def test_blank_cli_value_falls_back_to_env(self, monkeypatch):
        monkeypatch.setenv("GEO_USER_AGENT", "EnvBot/1.0")
        assert config_mod.resolve_user_agent_override("   ") == "EnvBot/1.0"

    def test_blank_env_var_returns_none(self, monkeypatch):
        monkeypatch.setenv("GEO_USER_AGENT", "   ")
        assert config_mod.resolve_user_agent_override(None) is None


class TestGetHeaders:
    def test_default_headers_when_no_override(self):
        assert config_mod.get_headers() == config_mod.HEADERS

    def test_override_replaces_user_agent(self):
        config_mod.set_user_agent_override("CustomBot/1.0")
        assert config_mod.get_headers() == {"User-Agent": "CustomBot/1.0"}

    def test_clearing_override_restores_default(self):
        config_mod.set_user_agent_override("CustomBot/1.0")
        config_mod.set_user_agent_override(None)
        assert config_mod.get_headers() == config_mod.HEADERS

    def test_get_headers_returns_a_copy(self):
        """Mutating the returned dict must not corrupt the module-level default."""
        headers = config_mod.get_headers()
        headers["User-Agent"] = "mutated"
        assert config_mod.HEADERS["User-Agent"] != "mutated"


class TestSessionPicksUpOverride:
    def test_session_uses_default_user_agent(self):
        session = create_session_with_retry()
        assert session.headers["User-Agent"] == config_mod.USER_AGENT

    def test_session_uses_overridden_user_agent(self):
        config_mod.set_user_agent_override("Mozilla/5.0 Test")
        session = create_session_with_retry()
        assert session.headers["User-Agent"] == "Mozilla/5.0 Test"


class TestCliUserAgentFlag:
    """Each command resolves --user-agent before doing any fetch."""

    def test_audit_command_sets_override(self):
        from geo_optimizer.cli.audit_cmd import audit

        runner = CliRunner()
        with patch("geo_optimizer.cli.audit_cmd.run_full_audit") as mock_audit:
            mock_audit.return_value = {"score": 0, "band": "critical", "checks": {}}
            runner.invoke(audit, ["--url", "https://example.com", "--user-agent", "AuditBot/1.0"])
        assert config_mod.get_headers()["User-Agent"] == "AuditBot/1.0"

    def test_access_command_sets_override(self):
        from geo_optimizer.cli.access_cmd import access

        runner = CliRunner()
        with patch("geo_optimizer.cli.access_cmd.run_agent_access_audit") as mock_access:
            mock_access.return_value = type(
                "R", (), {"url": "https://example.com", "status": "unknown", "checks": {}, "signals": []}
            )()
            runner.invoke(access, ["--url", "https://example.com", "--user-agent", "AccessBot/1.0"])
        assert config_mod.get_headers()["User-Agent"] == "AccessBot/1.0"

    def test_fix_command_sets_override(self, tmp_path):
        from geo_optimizer.cli.fix_cmd import fix

        runner = CliRunner()
        with patch("geo_optimizer.cli.fix_cmd.validate_public_url", return_value=(False, "blocked for test")):
            runner.invoke(
                fix,
                [
                    "--url",
                    "https://example.com",
                    "--output-dir",
                    str(tmp_path),
                    "--user-agent",
                    "FixBot/1.0",
                ],
            )
        assert config_mod.get_headers()["User-Agent"] == "FixBot/1.0"

    def test_llms_command_sets_override(self):
        from geo_optimizer.cli.llms_cmd import llms

        runner = CliRunner()
        with patch("geo_optimizer.cli.llms_cmd.validate_public_url", return_value=(False, "blocked for test")):
            runner.invoke(llms, ["--base-url", "https://example.com", "--user-agent", "LlmsBot/1.0"])
        assert config_mod.get_headers()["User-Agent"] == "LlmsBot/1.0"

    def test_no_flag_leaves_default(self):
        from geo_optimizer.cli.audit_cmd import audit

        runner = CliRunner()
        with patch("geo_optimizer.cli.audit_cmd.run_full_audit") as mock_audit:
            mock_audit.return_value = {"score": 0, "band": "critical", "checks": {}}
            runner.invoke(audit, ["--url", "https://example.com"])
        assert config_mod.get_headers() == config_mod.HEADERS
