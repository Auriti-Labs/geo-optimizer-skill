"""Test della dashboard rich di `geo audit` (design v3) e del progresso reale on_step."""

from __future__ import annotations

import asyncio
import re
from unittest.mock import AsyncMock, Mock, patch

import pytest

pytest.importorskip("rich")

from geo_optimizer.cli.audit_cmd import _default_format  # noqa: E402
from geo_optimizer.cli.rich_formatter import format_audit_rich  # noqa: E402
from geo_optimizer.core.audit import run_full_audit, run_full_audit_async  # noqa: E402
from geo_optimizer.models.config import AUDIT_STEPS  # noqa: E402
from geo_optimizer.models.results import AuditResult, LlmsTxtResult, RobotsResult  # noqa: E402

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_LABELS = (
    "Robots.txt",
    "llms.txt",
    "Schema JSON-LD",
    "Meta tags",
    "Content",
    "Signals",
    "AI discovery",
    "Brand & entity",
)
_HTML = "<html lang='en'><head><title>T</title></head><body><h1>Hi</h1><p>Hello</p></body></html>"


def _result() -> AuditResult:
    r = AuditResult(url="https://example.com", score=72, band="good", http_status=200, page_size=20480)
    r.robots = RobotsResult(found=True, bots_allowed=["GPTBot", "ClaudeBot"], citation_bots_ok=True)
    r.llms = LlmsTxtResult(found=True, word_count=900, sections_count=4)
    r.recommendations = [f"Fix number {i}" for i in range(1, 9)]
    return r


def _plain(result: AuditResult, **kw) -> str:
    return _ANSI.sub("", format_audit_rich(result, width=100, **kw))


def test_dashboard_shows_score_and_all_categories():
    out = _plain(_result())
    assert "72" in out and "GOOD" in out
    for label in _LABELS:
        assert label in out
    assert "~900 words · 4 sections" in out


def test_dashboard_is_compact_and_english():
    out = _plain(_result())
    assert len(out.splitlines()) <= 35
    assert "Fix number 5" in out and "Fix number 6" not in out
    assert "+3 more with --verbose" in out
    for italian in ("parole", "sezioni", "Punteggio", "mancante", "Aggiungi"):
        assert italian not in out


def test_verbose_appends_cards_and_all_fixes():
    out = _plain(_result(), verbose=True)
    assert "Fix number 8" in out
    assert "╭" in out  # le card per categoria sono Panel arrotondati
    assert "--verbose for every check" not in out


def test_error_result_is_flagged():
    out = _plain(AuditResult(url="https://down.example", error="HTTP 503"))
    assert "Audit failed: HTTP 503" in out


@pytest.mark.parametrize(
    ("tty", "sitemap", "output_file", "no_color", "expected"),
    [
        (True, None, None, "", "rich"),
        (False, None, None, "", "text"),
        (True, "https://e.com/sitemap.xml", None, "", "text"),
        (True, None, "report.txt", "", "text"),
        (True, None, None, "1", "text"),
    ],
)
def test_default_format(monkeypatch, tty, sitemap, output_file, no_color, expected):
    monkeypatch.setenv("NO_COLOR", no_color)
    monkeypatch.setattr("sys.stdout.isatty", lambda: tty, raising=False)
    assert _default_format(sitemap, output_file) == expected


def test_on_step_order_sync():
    steps: list[str] = []
    page = Mock(status_code=200, text=_HTML, headers={})
    with (
        patch("geo_optimizer.core.audit.fetch_url", return_value=(page, None)),
        patch("geo_optimizer.core.audit.check_markdown_negotiation", return_value=True),
        patch("geo_optimizer.core.audit.audit_cdn_ai_crawler") as cdn,
    ):
        cdn.return_value.checked = False
        result = run_full_audit("https://example.com", on_step=steps.append)
    assert result.ai_discovery.has_markdown is True
    assert steps == list(AUDIT_STEPS)


def test_on_step_order_async():
    steps: list[str] = []
    page = Mock(status_code=200, text=_HTML, headers={})

    async def _fetch(urls, *a, **kw):
        return dict.fromkeys(urls, (page, None))

    with (
        patch("geo_optimizer.utils.http_async.fetch_urls_async", AsyncMock(side_effect=_fetch)),
        patch("geo_optimizer.core.audit.check_markdown_negotiation_async", AsyncMock(return_value=True)),
        patch("geo_optimizer.core.audit.asyncio.to_thread", AsyncMock(return_value=Mock(checked=False))),
        patch("geo_optimizer.core.audit.audit_cdn_ai_crawler") as cdn,
    ):
        cdn.return_value.checked = False
        result = asyncio.run(run_full_audit_async("https://example.com", on_step=steps.append))
    assert result.ai_discovery.has_markdown is True
    assert steps == list(AUDIT_STEPS)


def _fake_audit(url, use_cache=False, project_config=None, on_step=None):
    for step in AUDIT_STEPS:
        if on_step:
            on_step(step)
    return _result()


@patch.dict("sys.modules", {"httpx": None})
def test_cli_output_file_from_config_stays_plain_text(tmp_path, monkeypatch):
    """Review: audit.output da config veniva letto dopo la scelta del formato → ANSI nel file."""
    pytest.importorskip("yaml")
    from click.testing import CliRunner

    from geo_optimizer.cli.main import cli

    monkeypatch.chdir(tmp_path)
    (tmp_path / "geo.yml").write_text("audit:\n  output: out.txt\n", encoding="utf-8")
    with (
        patch("geo_optimizer.cli.audit_cmd.run_full_audit", side_effect=_fake_audit),
        patch("geo_optimizer.cli.audit_cmd.validate_public_url", return_value=(True, None)),
        # simula un TTY: rich salvo file/sitemap
        patch(
            "geo_optimizer.cli.audit_cmd._default_format",
            side_effect=lambda sitemap, output_file: "text" if output_file or sitemap else "rich",
        ),
    ):
        res = CliRunner().invoke(cli, ["audit", "--url", "https://example.com", "--config", "geo.yml"])

    assert res.exit_code == 0, res.output
    assert "\x1b[" not in (tmp_path / "out.txt").read_text(encoding="utf-8")


@patch.dict("sys.modules", {"httpx": None})
def test_cli_text_format_prints_real_steps():
    from click.testing import CliRunner

    from geo_optimizer.cli.main import cli

    with (
        patch("geo_optimizer.cli.audit_cmd.run_full_audit", side_effect=_fake_audit),
        patch("geo_optimizer.cli.audit_cmd.validate_public_url", return_value=(True, None)),
    ):
        res = CliRunner().invoke(cli, ["audit", "--url", "https://example.com", "--format", "text"])

    assert res.exit_code == 0
    for step in AUDIT_STEPS:
        assert f"⏳ {step}..." in res.output


@patch.dict("sys.modules", {"httpx": None})
def test_cli_verbose_keeps_third_party_logs_quiet():
    """--verbose impostava il root logger a DEBUG: httpx/httpcore/urllib3 inondavano il terminale."""
    import logging

    from click.testing import CliRunner

    from geo_optimizer.cli.main import cli

    pkg_logger = logging.getLogger("geo_optimizer")
    old_level = pkg_logger.level
    try:
        with (
            patch("geo_optimizer.cli.audit_cmd.run_full_audit", side_effect=_fake_audit),
            patch("geo_optimizer.cli.audit_cmd.validate_public_url", return_value=(True, None)),
            patch("geo_optimizer.cli.audit_cmd.logging.basicConfig") as basic,
        ):
            res = CliRunner().invoke(cli, ["audit", "--url", "https://example.com", "--format", "text", "--verbose"])

        assert res.exit_code == 0, res.output
        basic.assert_called_once_with(level=logging.WARNING)
        assert pkg_logger.level == logging.DEBUG
    finally:
        pkg_logger.setLevel(old_level)
