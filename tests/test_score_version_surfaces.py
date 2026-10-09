"""Superfici CLI e core sensibili alla versione della rubrica."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET

import pytest
from unittest.mock import patch

from click.testing import CliRunner

from geo_optimizer.cli.ci_formatter import format_audit_junit, format_audit_sarif
from geo_optimizer.cli.formatters import (
    format_audit_diff_text,
    format_audit_json,
    format_audit_text,
    format_batch_audit_text,
)
from geo_optimizer.cli.github_formatter import format_audit_github
from geo_optimizer.cli.html_formatter import format_audit_html
from geo_optimizer.cli.main import cli
from geo_optimizer.cli.rich_formatter import format_audit_rich
from geo_optimizer.cli.scoring_helpers import categories, category_max, category_score
from geo_optimizer.core.diffing import build_audit_diff
from geo_optimizer.core.fixer import run_all_fixes
from geo_optimizer.core.gap_analysis import build_gap_analysis
from geo_optimizer.core.monitor import build_passive_monitor_result
from geo_optimizer.models.config import CATEGORY_MAX, CATEGORY_MAX_V2
from geo_optimizer.models.results import (
    AuditResult,
    BatchAuditPageResult,
    BatchAuditResult,
    BrandEntityResult,
    GoogleAiReadinessResult,
    MetaResult,
    ReadinessCheck,
)


def _v2() -> AuditResult:
    check = ReadinessCheck(
        "G-SNIPPET",
        "fail",
        0,
        5,
        "nosnippet",
        "https://developers.google.com/x",
    )
    return AuditResult(
        url="https://x.test",
        score=50,
        score_version=2,
        score_max=dict(CATEGORY_MAX_V2),
        score_breakdown={
            "google_ai": 15,
            "llms": 6,
            "meta": 11,
            "robots": 0,
            "schema": 0,
            "content": 0,
            "signals": 0,
            "ai_discovery": 0,
            "brand_entity": 0,
        },
        google_ai=GoogleAiReadinessResult(
            checked=True,
            points=15,
            max_points=20,
            final_url="https://x.test/",
            checks=[check],
        ),
    )


def test_helpers_read_from_result() -> None:
    result = _v2()
    assert category_score(result, "llms") == 6
    assert category_max(result, "llms") == 6
    assert categories(result) == list(CATEGORY_MAX_V2)

    old = AuditResult(url="https://x.test")
    assert category_max(old, "llms") == CATEGORY_MAX["llms"]


def test_json_carries_version_google_ai_and_v2_max() -> None:
    data = json.loads(format_audit_json(_v2()))

    assert data["score_version"] == 2
    assert data["checks"]["llms_txt"]["max"] == 6
    assert data["checks"]["google_ai"]["score"] == 15
    assert data["checks"]["google_ai"]["max"] == 20
    assert data["checks"]["google_ai"]["passed"] is False
    assert data["google_ai"]["checks"][0]["id"] == "G-SNIPPET"


def test_text_google_section_and_v2_llms_label_are_version_aware() -> None:
    old_output = format_audit_text(AuditResult(url="https://x.test"))
    v2_output = format_audit_text(_v2())

    assert "Google AI" not in old_output
    assert "GOOGLE AI SEARCH" in v2_output
    assert "G-SNIPPET" in v2_output
    assert "✗" in v2_output
    assert "(Other AI agents · not used by Google Search)" in v2_output


def test_sarif_rule_per_google_check_with_help_uri() -> None:
    sarif = json.loads(format_audit_sarif(_v2()))
    run = sarif["runs"][0]
    rules = {rule["id"]: rule for rule in run["tool"]["driver"]["rules"]}
    google_results = [item for item in run["results"] if item["ruleId"] == "G-SNIPPET"]

    assert rules["G-SNIPPET"]["helpUri"] == "https://developers.google.com/x"
    assert google_results[0]["level"] == "error"


def test_junit_has_failure_for_failed_google_check() -> None:
    root = ET.fromstring(format_audit_junit(_v2()))
    google_case = root.find(".//testcase[@name='G-SNIPPET']")

    assert google_case is not None
    assert google_case.find("failure") is not None


def test_html_uses_result_maxima_for_v1_and_v2() -> None:
    assert "6/6" in format_audit_html(_v2())
    assert "0/18" in format_audit_html(AuditResult(url="https://x.test"))


def test_github_uses_result_maxima_for_v1_and_v2() -> None:
    assert "llms.txt (Other AI agents · not used by Google Search): 6/6" in format_audit_github(_v2())
    assert "llms.txt: 0/18" in format_audit_github(AuditResult(url="https://x.test"))


def test_rich_uses_result_maxima_for_v1_and_v2() -> None:
    ansi = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
    v2_output = ansi.sub("", format_audit_rich(_v2(), width=120))
    old_output = ansi.sub("", format_audit_rich(AuditResult(url="https://x.test"), width=120))

    assert "6/6" in v2_output
    assert "0/18" in old_output


def test_diff_uses_after_result_maxima_and_reports_version_mismatch() -> None:
    before = AuditResult(
        url="https://before.test",
        score_version=1,
        score_breakdown={"llms": 12},
    )
    after = _v2()

    diff = build_audit_diff(before, after)
    llms_delta = next(item for item in diff.category_deltas if item.category == "llms")

    assert llms_delta.max_score == 6
    assert diff.version_mismatch is True
    assert "scores use different rubric versions" in format_audit_diff_text(diff)


def test_gap_analysis_uses_weaker_result_scoring_version() -> None:
    weaker = AuditResult(
        url="https://weaker.test",
        score=10,
        score_version=2,
        score_max=dict(CATEGORY_MAX_V2),
        meta=MetaResult(has_title=False),
    )
    stronger = AuditResult(
        url="https://stronger.test",
        score=20,
        score_version=2,
        score_max=dict(CATEGORY_MAX_V2),
        meta=MetaResult(has_title=True),
    )

    gap = build_gap_analysis(weaker, stronger)
    title_action = next(action for action in gap.action_plan if action.title == "Add a title tag")

    assert title_action.impact_points == 5


def test_monitor_normalizes_brand_score_with_result_version_maximum() -> None:
    result = AuditResult(
        url="https://x.test",
        score_version=2,
        score_max=dict(CATEGORY_MAX_V2),
        score_breakdown={"brand_entity": 12},
        brand_entity=BrandEntityResult(brand_name_consistent=True),
    )

    monitor = build_passive_monitor_result(result)
    entity_signal = next(signal for signal in monitor.signals if signal.key == "entity_strength")

    assert entity_signal.score == entity_signal.max_score == 15


def test_fix_projection_uses_audit_result_scoring_version() -> None:
    result = AuditResult(
        url="https://x.test",
        score=0,
        score_version=2,
        score_max=dict(CATEGORY_MAX_V2),
    )

    plan = run_all_fixes(result.url, audit_result=result, only={"meta"})

    assert plan.score_estimated_after == 11


def test_diff_across_versions_lists_no_improved_or_regressed():
    from geo_optimizer.core.diffing import build_audit_diff

    v1 = AuditResult(url="https://x.test", score=40, score_breakdown={"llms": 18})
    diff = build_audit_diff(v1, _v2())
    assert diff.version_mismatch is True
    assert diff.improved_categories == [] and diff.regressed_categories == []


def test_sarif_rule_without_source_has_no_help_uri():
    r = _v2()
    r.google_ai.checks[0].source_url = ""
    rules = json.loads(format_audit_sarif(r))["runs"][0]["tool"]["driver"]["rules"]
    assert all(rule.get("helpUri", "x") for rule in rules)


@patch.dict("sys.modules", {"httpx": None})
@patch("geo_optimizer.cli.audit_cmd.validate_public_url", return_value=(True, ""))
@patch("geo_optimizer.cli.audit_cmd.run_full_audit")
def test_cli_score_version_flag_reaches_core(mock_audit, _validate):
    mock_audit.return_value = AuditResult(url="https://x.test", score_version=1)

    result = CliRunner().invoke(
        cli,
        ["audit", "--url", "https://x.test", "--format", "json", "--score-version", "1"],
    )

    assert result.exit_code == 0, result.output
    assert mock_audit.call_args.kwargs["score_version"] == 1


@patch("geo_optimizer.utils.validators.validate_public_url", return_value=(True, ""))
@patch("geo_optimizer.core.audit.run_full_audit")
def test_mcp_score_version_reaches_core(mock_audit, _validate):
    # mcp e' un extra opzionale (geo-optimizer-skill[mcp]): su CI senza extra
    # il modulo non c'e' e il test salta invece di fallire (pattern di
    # test_mcp.py / test_mcp_server.py).
    pytest.importorskip("mcp", reason="mcp non installato (pip install geo-optimizer-skill[mcp])")
    from geo_optimizer.mcp import server

    mock_audit.return_value = AuditResult(url="https://x.test", score_version=1)

    with patch.object(server, "_normalize_url", return_value="https://x.test"):
        output = server.geo_audit("https://x.test", score_version=1)

    assert '"score_version": 1' in output
    assert mock_audit.call_args.kwargs["score_version"] == 1


def test_batch_text_uses_v2_page_maxima():
    page = BatchAuditPageResult(
        url="https://x.test",
        score=50,
        score_breakdown={"llms": 6, "google_ai": 10},
        score_version=2,
        score_max=dict(CATEGORY_MAX_V2),
    )
    batch = BatchAuditResult(
        sitemap_url="https://x.test/sitemap.xml",
        audited_urls=1,
        successful_urls=1,
        average_score=50.0,
        average_score_breakdown={"llms": 6.0, "google_ai": 10.0},
        pages=[page],
    )

    output = format_batch_audit_text(batch)

    assert "llms.txt: 6.00/6" in output
    assert "Google AI Search: 10.00/20" in output


@patch("geo_optimizer.core.batch_audit._async_runtime_available", return_value=True)
@patch("geo_optimizer.core.batch_audit.run_full_audit_async")
def test_batch_score_version_reaches_page_audits(mock_audit, _runtime):
    from geo_optimizer.core.batch_audit import _audit_single_url

    async def fake_audit(*args, **kwargs):
        return _v2()

    mock_audit.side_effect = fake_audit

    import asyncio

    result = asyncio.run(_audit_single_url("https://x.test", use_cache=False, project_config=None, score_version=1))

    assert mock_audit.call_args.kwargs["score_version"] == 1
    assert result.score_max == CATEGORY_MAX_V2


def test_history_never_compares_scores_across_rubric_versions(tmp_path):
    import sqlite3

    from geo_optimizer.core.history import HistoryStore

    db = tmp_path / "tracking.db"
    # DB creato prima della rubric v2: schema originale senza score_version (niente DROP COLUMN, SQLite < 3.35)
    cols = ", ".join(
        f"{c}_score INTEGER NOT NULL"
        for c in ("robots", "llms", "schema", "meta", "content", "signals", "ai_discovery", "brand_entity")
    )
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE audit_history (id INTEGER PRIMARY KEY AUTOINCREMENT, canonical_url TEXT NOT NULL, "
            "domain TEXT NOT NULL, recorded_at TEXT NOT NULL, score INTEGER NOT NULL, band TEXT NOT NULL, "
            f"http_status INTEGER NOT NULL, recommendations_count INTEGER NOT NULL, {cols})"
        )
    store = HistoryStore(db)
    HistoryStore(db)  # seconda inizializzazione: migrazione idempotente

    old = AuditResult(url="https://x.test", score=90, score_version=1, timestamp="2026-10-01T00:00:00+00:00")
    store.save_audit_result(old)
    new = AuditResult(url="https://x.test", score=60, score_version=2, timestamp="2026-10-09T00:00:00+00:00")
    entry = store.save_audit_result(new)
    history = store.build_history_result("https://x.test")

    assert entry.delta is None
    assert history.regression_detected is False and history.score_delta is None
    assert [e.score_version for e in history.entries] == [2, 1]

    worse = AuditResult(url="https://x.test", score=50, score_version=2, timestamp="2026-10-10T00:00:00+00:00")
    store.save_audit_result(worse)
    assert store.build_history_result("https://x.test").regression_detected is True


def test_history_migration_tolerates_concurrent_add_column(tmp_path, monkeypatch):
    import sqlite3

    from geo_optimizer.core import history

    db = tmp_path / "tracking.db"
    history.HistoryStore(db)
    real_connect = sqlite3.connect

    class _RacingConn(sqlite3.Connection):
        def execute(self, sql, *args):
            if sql.startswith("PRAGMA table_info"):
                return iter([])  # simula: colonna non ancora vista, ma un altro processo l'ha appena aggiunta
            return super().execute(sql, *args)

    monkeypatch.setattr(history.sqlite3, "connect", lambda p: real_connect(p, factory=_RacingConn))
    history.HistoryStore(db)  # non deve sollevare "duplicate column"


def test_mcp_geo_audit_rejects_unknown_score_version():
    import pytest

    server = pytest.importorskip("geo_optimizer.mcp.server")
    with patch("geo_optimizer.utils.validators.validate_public_url", return_value=(True, "")):
        for bad in (3, 0, True):
            assert "score_version must be 1 or 2" in server.geo_audit("https://x.test", score_version=bad)


def test_drift_ignores_snapshots_of_different_rubric_versions():
    from geo_optimizer.core.drift_detector import compute_semantic_drift
    from geo_optimizer.models.results import HistoryEntry

    old = HistoryEntry(url="https://x.test", timestamp="t1", score=90, score_breakdown={"llms": 18}, score_version=1)
    new = HistoryEntry(url="https://x.test", timestamp="t2", score=60, score_breakdown={"llms": 6}, score_version=2)
    drift = compute_semantic_drift(old, new)
    assert drift.severity == "none" and drift.score_delta == 0
