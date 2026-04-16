"""Test per history/tracking locale GEO."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from geo_optimizer.core.history import HistoryStore, canonicalize_history_url
from geo_optimizer.models.results import AuditResult

_NOW = datetime.now(timezone.utc)


def _ts(days_ago: int) -> str:
    """Return an ISO timestamp *days_ago* days before now."""
    return (_NOW - timedelta(days=days_ago)).isoformat()


def _make_result(url: str, timestamp: str, score: int, band: str) -> AuditResult:
    """Crea un AuditResult minimo per i test di tracking."""
    return AuditResult(
        url=url,
        timestamp=timestamp,
        score=score,
        band=band,
        http_status=200,
        page_size=1024,
        recommendations=["fix-a", "fix-b"],
        score_breakdown={
            "robots": 18,
            "llms": 12,
            "schema": 10,
            "meta": 11,
            "content": 8,
            "signals": 4,
            "ai_discovery": 3,
            "brand_entity": 5,
        },
    )


class TestHistoryStore:
    """Test per salvataggio snapshot, trend e retention."""

    def test_save_and_read_history(self, tmp_path):
        """Gli snapshot vengono salvati e letti in ordine corretto con delta."""
        store = HistoryStore(Path(tmp_path / "tracking.db"))
        store.save_audit_result(_make_result("https://example.com/", _ts(14), 65, "foundation"))
        store.save_audit_result(_make_result("https://example.com", _ts(7), 78, "good"))

        result = store.build_history_result("https://example.com")

        assert result.total_snapshots == 2
        assert result.latest_score == 78
        assert result.previous_score == 65
        assert result.score_delta == 13
        assert result.regression_detected is False
        assert result.entries[0].delta == 13

    def test_prune_old_entries_respects_retention(self, tmp_path):
        """La retention rimuove snapshot più vecchi della finestra configurata."""
        store = HistoryStore(Path(tmp_path / "tracking.db"))
        store.save_audit_result(_make_result("https://example.com", "2025-01-15T12:00:00+00:00", 40, "foundation"))
        store.save_audit_result(_make_result("https://example.com", "2099-01-15T12:00:00+00:00", 80, "good"))

        store.prune_old_entries(retention_days=90)
        result = store.build_history_result("https://example.com", retention_days=90)

        assert result.total_snapshots == 1
        assert result.latest_score == 80


def test_canonicalize_history_url_normalizes_host_and_root():
    """La URL storica viene canonicalizzata in modo stabile."""
    assert canonicalize_history_url("HTTPS://Example.COM/") == "https://example.com/"
    assert canonicalize_history_url("https://example.com/path/") == "https://example.com/path"
