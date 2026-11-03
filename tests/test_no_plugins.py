"""`geo audit --no-plugins` must keep installed check plugins out of the audit.

The CLI used to skip only its own early `load_entry_points()` call, while
`_build_audit_result` loaded and ran every `geo_optimizer.checks` entry point
unconditionally (fix #460), so the flag had no effect.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from geo_optimizer.cli.main import cli
from geo_optimizer.core.audit import _build_audit_result
from geo_optimizer.core.registry import CheckRegistry, CheckResult
from geo_optimizer.models.results import (
    AuditResult,
    ContentResult,
    LlmsTxtResult,
    MetaResult,
    RobotsResult,
    SchemaResult,
)


class _FakePlugin:
    name = "fake_plugin"
    description = "test plugin"
    max_score = 10

    def run(self, url, soup=None, **kwargs):
        return CheckResult(name=self.name, score=10, passed=True)


@pytest.fixture(autouse=True)
def _clean_registry():
    CheckRegistry.clear()
    yield
    CheckRegistry.clear()


def _build(**kwargs):
    return _build_audit_result(
        "https://example.com",
        RobotsResult(),
        LlmsTxtResult(),
        SchemaResult(),
        MetaResult(),
        ContentResult(),
        200,
        100,
        **kwargs,
    )


def test_build_without_plugins_neither_loads_nor_runs_them():
    CheckRegistry.register(_FakePlugin())  # e.g. loaded earlier in the same process
    with patch.object(CheckRegistry, "load_entry_points") as load:
        result = _build(load_plugins=False)
    load.assert_not_called()
    assert "fake_plugin" not in (result.extra_checks or {})


def test_build_default_still_loads_and_runs_plugins():
    CheckRegistry.register(_FakePlugin())
    with patch.object(CheckRegistry, "load_entry_points") as load:
        result = _build()
    load.assert_called_once()
    assert result.extra_checks["fake_plugin"]["score"] == 10


@patch.dict("sys.modules", {"httpx": None})
@patch("geo_optimizer.cli.audit_cmd.run_full_audit")
def test_cli_no_plugins_reaches_the_audit(mock_audit):
    mock_audit.return_value = AuditResult(url="https://example.com", score=50, band="foundation")
    with patch.object(CheckRegistry, "load_entry_points") as load:
        result = CliRunner().invoke(cli, ["audit", "--url", "https://example.com", "--no-plugins"])
    assert result.exit_code == 0, result.output
    load.assert_not_called()
    assert mock_audit.call_args.kwargs["load_plugins"] is False


@patch.dict("sys.modules", {"httpx": None})
@patch("geo_optimizer.cli.audit_cmd.run_full_audit")
def test_cli_default_loads_plugins(mock_audit):
    mock_audit.return_value = AuditResult(url="https://example.com", score=50, band="foundation")
    with patch.object(CheckRegistry, "load_entry_points") as load:
        result = CliRunner().invoke(cli, ["audit", "--url", "https://example.com"])
    assert result.exit_code == 0, result.output
    load.assert_called_once()
    assert mock_audit.call_args.kwargs.get("load_plugins", True) is True


@patch("geo_optimizer.cli.audit_cmd.validate_public_url", return_value=(True, None))
@patch("geo_optimizer.cli.audit_cmd.run_batch_audit")
def test_cli_no_plugins_reaches_the_sitemap_batch(mock_batch, _validate):
    mock_batch.side_effect = RuntimeError("stop")
    CliRunner().invoke(cli, ["audit", "--sitemap", "https://example.com/sitemap.xml", "--no-plugins"])
    assert mock_batch.call_args.kwargs["load_plugins"] is False
