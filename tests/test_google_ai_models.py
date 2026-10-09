from __future__ import annotations

from unittest.mock import MagicMock

from geo_optimizer.core.audit_robots import _audit_robots_from_response
from geo_optimizer.models.config import GOOGLE_AI_POINTS, GOOGLE_DOC_URLS
from geo_optimizer.models.results import AuditResult, GoogleAiReadinessResult


def test_google_ai_points_total_20_and_every_check_has_a_source():
    assert sum(GOOGLE_AI_POINTS.values()) == 20
    assert set(GOOGLE_AI_POINTS) <= set(GOOGLE_DOC_URLS)
    assert all(u.startswith("https://developers.google.com/") for u in GOOGLE_DOC_URLS.values())


def test_audit_result_defaults_are_v1_and_empty():
    r = AuditResult(url="https://x.test")
    assert r.score_version == 1 and r.score_max == {}
    assert isinstance(r.google_ai, GoogleAiReadinessResult) and r.google_ai.checked is False


def test_robots_collects_absolute_sitemaps_only():
    resp = MagicMock(
        status_code=200,
        text="User-agent: *\nAllow: /\nSitemap: https://x.test/sitemap.xml\nsitemap: /rel.xml\n",
    )
    assert _audit_robots_from_response(resp).sitemaps == ["https://x.test/sitemap.xml"]
