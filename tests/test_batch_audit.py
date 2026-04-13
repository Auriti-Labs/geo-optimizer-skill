"""Test per l'orchestratore batch dell'audit GEO."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from geo_optimizer.core.batch_audit import run_batch_audit_async
from geo_optimizer.models.results import AuditResult, SitemapUrl


def _make_audit_result(url: str, score: int, band: str, breakdown: dict[str, int]) -> AuditResult:
    """Crea un AuditResult minimo per i test batch."""
    return AuditResult(
        url=url,
        score=score,
        band=band,
        http_status=200,
        page_size=1000,
        score_breakdown=breakdown,
        recommendations=["fix-a", "fix-b"],
    )


class TestBatchAudit:
    """Test per `run_batch_audit_async` e aggregazione risultati."""

    @patch("geo_optimizer.core.batch_audit.asyncio.to_thread", new_callable=AsyncMock)
    @patch("geo_optimizer.core.batch_audit.fetch_sitemap")
    @patch("geo_optimizer.core.batch_audit.run_full_audit_async")
    def test_run_batch_audit_async_aggregates_scores(
        self,
        mock_run_full_audit_async,
        mock_fetch_sitemap,
        mock_to_thread,
    ):
        """La sitemap viene auditata e aggregata in un risultato batch coerente."""
        mock_to_thread.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)
        mock_fetch_sitemap.return_value = [
            SitemapUrl(url="https://example.com/"),
            SitemapUrl(url="https://example.com/blog"),
            SitemapUrl(url="https://example.com/"),
        ]
        mock_run_full_audit_async.side_effect = [
            _make_audit_result(
                "https://example.com/",
                80,
                "good",
                {"robots": 18, "llms": 12, "schema": 10},
            ),
            _make_audit_result(
                "https://example.com/blog",
                60,
                "foundation",
                {"robots": 18, "llms": 8, "schema": 6},
            ),
        ]

        result = asyncio.run(run_batch_audit_async("https://example.com/sitemap.xml", max_urls=10, concurrency=2))

        assert result.sitemap_url == "https://example.com/sitemap.xml"
        assert result.discovered_urls == 3
        assert result.audited_urls == 2
        assert result.successful_urls == 2
        assert result.failed_urls == 0
        assert result.average_score == 70.0
        assert result.average_band == "good"
        assert result.band_counts == {"good": 1, "foundation": 1}
        assert result.average_score_breakdown["robots"] == 18.0
        assert result.average_score_breakdown["llms"] == 10.0
        assert result.top_pages[0].url == "https://example.com/"
        assert result.worst_pages[0].url == "https://example.com/blog"

    @patch("geo_optimizer.core.batch_audit.asyncio.to_thread", new_callable=AsyncMock)
    @patch("geo_optimizer.core.batch_audit.fetch_sitemap", return_value=[])
    def test_run_batch_audit_async_raises_when_sitemap_is_empty(self, mock_fetch_sitemap, mock_to_thread):
        """Una sitemap senza URL produce un errore esplicito."""
        mock_to_thread.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)
        try:
            asyncio.run(run_batch_audit_async("https://example.com/sitemap.xml"))
        except ValueError as exc:
            assert str(exc) == "No URLs found in sitemap"
        else:  # pragma: no cover - ramo difensivo
            raise AssertionError("Expected ValueError for empty sitemap")

        mock_fetch_sitemap.assert_called_once()

    @patch("geo_optimizer.core.batch_audit.asyncio.to_thread", new_callable=AsyncMock)
    @patch("geo_optimizer.core.batch_audit.fetch_sitemap")
    @patch("geo_optimizer.core.batch_audit.run_full_audit")
    def test_run_batch_audit_async_uses_sync_path_with_cache(
        self,
        mock_run_full_audit,
        mock_fetch_sitemap,
        mock_to_thread,
    ):
        """Con cache attiva il batch usa il path sincrono per rispettare il caching HTTP."""
        mock_to_thread.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)
        mock_fetch_sitemap.return_value = [SitemapUrl(url="https://example.com/")]
        mock_run_full_audit.return_value = _make_audit_result(
            "https://example.com/",
            77,
            "good",
            {"robots": 18, "llms": 11},
        )

        result = asyncio.run(run_batch_audit_async("https://example.com/sitemap.xml", use_cache=True))

        assert result.average_score == 77.0
        mock_run_full_audit.assert_called_once_with(
            "https://example.com/",
            use_cache=True,
            project_config=None,
        )
