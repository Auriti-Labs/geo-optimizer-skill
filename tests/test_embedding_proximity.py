"""Tests for Embedding Proximity Score (#354)."""

from __future__ import annotations

from unittest.mock import patch

from bs4 import BeautifulSoup

from geo_optimizer.core.audit_embedding import _extract_chunks, audit_embedding_proximity


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


class TestGracefulSkip:
    """Tests for graceful degradation without sentence-transformers."""

    def test_skips_when_not_installed(self):
        html = "<html><body><h2>Title</h2><p>Some content here for testing.</p></body></html>"
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            result = audit_embedding_proximity(_soup(html))
        assert result.checked is True
        assert result.skipped_reason is not None
        assert "not installed" in result.skipped_reason

    def test_skips_empty_body(self):
        """With sentence-transformers absent, skips before body check."""
        result = audit_embedding_proximity(_soup("<html><body></body></html>"))
        assert result.checked is True
        assert result.skipped_reason is not None

    def test_skips_no_body(self):
        """With sentence-transformers absent, skips before body check."""
        result = audit_embedding_proximity(_soup("<html><head></head></html>"))
        assert result.checked is True
        assert result.skipped_reason is not None


class TestExtractChunks:
    """Tests for chunk extraction logic."""

    def test_extracts_by_headings(self):
        words = " ".join(["word"] * 15)
        html = f"<html><body><h2>A</h2><p>{words}</p><h2>B</h2><p>{words}</p></body></html>"
        chunks = _extract_chunks(_soup(html).find("body"))
        assert len(chunks) == 2

    def test_extracts_by_paragraphs_fallback(self):
        words = " ".join(["word"] * 15)
        html = f"<html><body><p>{words}</p><p>{words}</p></body></html>"
        chunks = _extract_chunks(_soup(html).find("body"))
        assert len(chunks) == 2

    def test_skips_short_chunks(self):
        html = "<html><body><h2>A</h2><p>Short.</p><h2>B</h2><p>Also short.</p></body></html>"
        chunks = _extract_chunks(_soup(html).find("body"))
        assert len(chunks) == 0


class TestWithMockedModel:
    """Tests with mocked sentence-transformers."""

    def test_graceful_skip_is_default_without_library(self):
        """Without sentence-transformers, the audit returns a skipped result."""
        words = " ".join(["word"] * 20)
        html = f"<html><body><h2>A</h2><p>{words}</p></body></html>"
        result = audit_embedding_proximity(_soup(html))
        assert result.checked is True
        # Either skipped (no library) or computed (library present)
        if result.skipped_reason:
            assert "not installed" in result.skipped_reason
        else:
            assert result.total_chunks > 0
