"""Tests for POST /api/logs/analyze endpoint."""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest

pytest.importorskip("fastapi", reason="FastAPI non installato")
pytest.importorskip("httpx", reason="httpx non installato")

from starlette.testclient import TestClient

from geo_optimizer.models.results import BotStats, CrawledPage, LogAnalysisResult
from geo_optimizer.web.app import app

# ─── Fixtures ─────────────────────────────────────────────────────────────────

_FAKE_RESULT = LogAnalysisResult(
    checked=True,
    log_file="/tmp/test.log",
    total_lines=100,
    ai_requests=10,
    date_range_start="2026-01-01",
    date_range_end="2026-01-31",
    bots=[BotStats(bot_name="GPTBot", visits=8, unique_pages=5)],
    top_pages=[CrawledPage(path="/", total_visits=5, bots=["GPTBot"])],
)

_SAMPLE_LOG = b'127.0.0.1 - - [01/Jan/2026:00:00:00 +0000] "GET / HTTP/1.1" 200 1234 "-" "GPTBot/1.0"\n'


# ─── Tests ────────────────────────────────────────────────────────────────────


def test_upload_returns_200_and_log_result():
    with patch("geo_optimizer.core.log_analyzer.analyze_log_file", return_value=_FAKE_RESULT):
        client = TestClient(app, raise_server_exceptions=True)
        resp = client.post(
            "/api/logs/analyze",
            files={"file": ("access.log", io.BytesIO(_SAMPLE_LOG), "text/plain")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["checked"] is True
    assert data["ai_requests"] == 10
    assert len(data["bots"]) == 1
    assert data["bots"][0]["bot_name"] == "GPTBot"


def test_upload_missing_file_returns_400():
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/logs/analyze", data={})
    assert resp.status_code == 400
    assert "file" in resp.json()["detail"].lower()


def test_upload_too_large_returns_413():
    big_content = b"x" * (11 * 1024 * 1024)  # 11 MB
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(
        "/api/logs/analyze",
        files={"file": ("big.log", io.BytesIO(big_content), "text/plain")},
        headers={"Content-Length": str(len(big_content))},
    )
    assert resp.status_code == 413


def test_upload_analyzer_error_returns_500():
    with patch(
        "geo_optimizer.core.log_analyzer.analyze_log_file",
        side_effect=ValueError("bad format"),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/logs/analyze",
            files={"file": ("bad.log", io.BytesIO(b"garbage"), "text/plain")},
        )
    assert resp.status_code == 500


def test_upload_requires_auth_when_token_set(monkeypatch):
    monkeypatch.setenv("GEO_API_TOKEN", "secret123")
    import importlib

    import geo_optimizer.web.app as appmod
    importlib.reload(appmod)
    from geo_optimizer.web.app import app as reloaded_app

    client = TestClient(reloaded_app, raise_server_exceptions=False)
    resp = client.post(
        "/api/logs/analyze",
        files={"file": ("access.log", io.BytesIO(_SAMPLE_LOG), "text/plain")},
    )
    assert resp.status_code == 401

    monkeypatch.delenv("GEO_API_TOKEN", raising=False)
