"""Tests for geo drift — semantic drift between saved snapshots.

History store is patched at the command's import site — no real SQLite, no network.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from geo_optimizer.cli.main import cli
from geo_optimizer.models.results import HistoryEntry, HistoryResult


def _history(entries: list[HistoryEntry]) -> HistoryResult:
    return HistoryResult(url="https://example.com", entries=entries)


def _entry(score: int, ts: str, breakdown: dict | None = None) -> HistoryEntry:
    return HistoryEntry(
        url="https://example.com",
        timestamp=ts,
        score=score,
        band="foundation",
        score_breakdown=breakdown or {"robots": 10, "schema": 8},
    )


def _run(entries, *args):
    store = MagicMock()
    store.build_history_result.return_value = _history(entries)
    with patch("geo_optimizer.cli.drift_cmd.HistoryStore", return_value=store):
        return CliRunner().invoke(cli, ["drift", "--url", "https://example.com", *args])


class TestDriftCmd:
    def test_requires_two_snapshots(self):
        result = _run([_entry(50, "2026-06-10")])
        assert result.exit_code == 1
        assert "at least 2 saved snapshots" in result.output

    def test_detects_critical_drop(self):
        # newest first: 30 now, 60 before → -30 = critical
        entries = [
            _entry(30, "2026-06-11", {"robots": 0, "schema": 2}),
            _entry(60, "2026-06-10", {"robots": 14, "schema": 8}),
        ]
        result = _run(entries)
        assert result.exit_code == 0  # no --fail-on → informational
        assert "CRITICAL" in result.output
        assert "-30" in result.output
        assert "robots" in result.output

    def test_no_drift_is_clean(self):
        entries = [_entry(60, "2026-06-11"), _entry(60, "2026-06-10")]
        result = _run(entries)
        assert result.exit_code == 0
        assert "No significant drift" in result.output

    def test_fail_on_warning_exits_2(self):
        entries = [
            _entry(54, "2026-06-11"),
            _entry(60, "2026-06-10"),
        ]  # -6 → warning
        result = _run(entries, "--fail-on", "warning")
        assert result.exit_code == 2

    def test_fail_on_critical_passes_for_warning(self):
        entries = [_entry(54, "2026-06-11"), _entry(60, "2026-06-10")]
        result = _run(entries, "--fail-on", "critical")
        assert result.exit_code == 0

    def test_json_output_contract(self):
        entries = [
            _entry(40, "2026-06-11", {"robots": 5, "schema": 2}),
            _entry(60, "2026-06-10", {"robots": 14, "schema": 8}),
        ]
        result = _run(entries, "--format", "json")
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["before"]["score"] == 60
        assert payload["after"]["score"] == 40
        assert payload["drift"]["score_delta"] == -20
        assert payload["drift"]["severity"] == "critical"
        assert payload["drift"]["category_deltas"]["robots"] == -9
