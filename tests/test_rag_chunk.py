"""Tests for RAG Chunk Readiness audit (#353)."""

from __future__ import annotations

from bs4 import BeautifulSoup

from geo_optimizer.core.audit_rag import audit_rag_readiness


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


class TestRagChunkReadiness:
    """Tests for audit_rag_readiness()."""

    def test_empty_body(self):
        result = audit_rag_readiness(_soup("<html><body></body></html>"))
        assert result.checked is True
        assert result.total_sections == 0
        assert result.chunk_readiness_score == 0

    def test_no_body(self):
        result = audit_rag_readiness(_soup("<html><head><title>T</title></head></html>"))
        assert result.checked is True
        assert result.total_sections == 0

    def test_single_section_no_headings(self):
        text = " ".join(["word"] * 120)
        result = audit_rag_readiness(_soup(f"<html><body><p>{text}</p></body></html>"))
        assert result.checked is True
        assert result.total_sections == 1
        assert result.avg_section_words > 0

    def test_multiple_sections_in_range(self):
        section = " ".join(["word"] * 120)
        html = "<html><body>"
        for i in range(5):
            html += f"<h2>Section {i}</h2><p>{section}</p>"
        html += "</body></html>"
        result = audit_rag_readiness(_soup(html))
        assert result.checked is True
        assert result.total_sections == 5
        assert result.sections_in_range == 5
        assert result.chunk_readiness_score >= 50

    def test_sections_too_long(self):
        section = " ".join(["word"] * 500)
        html = "<html><body>"
        for i in range(3):
            html += f"<h2>Section {i}</h2><p>{section}</p>"
        html += "</body></html>"
        result = audit_rag_readiness(_soup(html))
        assert result.sections_in_range == 0
        assert result.avg_section_words > 400

    def test_definition_opening_detected(self):
        html = "<html><body><p>Machine learning is a subset of artificial intelligence.</p></body></html>"
        result = audit_rag_readiness(_soup(html))
        assert result.has_definition_opening is True

    def test_heading_boundary_ratio(self):
        section = " ".join(["word"] * 50)
        html = f"<html><body><h2>A</h2><p>{section}</p><h2>B</h2><p>{section}</p></body></html>"
        result = audit_rag_readiness(_soup(html))
        assert result.heading_as_boundary_ratio == 1.0

    def test_anchor_sentences_counted(self):
        sentences = ". ".join(
            [f"This is a self-contained factual statement number {i} about an important topic" for i in range(6)]
        )
        html = f"<html><body><p>{sentences}.</p></body></html>"
        result = audit_rag_readiness(_soup(html))
        assert result.anchor_sentences >= 1

    def test_score_max_100(self):
        """Score never exceeds 100."""
        section = " ".join(["word"] * 120)
        html = "<html><body>"
        html += "<p>Machine learning is a subset of artificial intelligence that enables systems to learn.</p>"
        for i in range(10):
            html += f"<h2>Section {i}</h2><p>{section}</p>"
        html += "</body></html>"
        result = audit_rag_readiness(_soup(html))
        assert result.chunk_readiness_score <= 100

    def test_uses_soup_clean_when_provided(self):
        html = "<html><body><script>var x=1;</script><h2>Title</h2><p>Content here.</p></body></html>"
        soup = _soup(html)
        import copy

        soup_clean = copy.deepcopy(soup)
        for tag in soup_clean(["script", "style"]):
            tag.decompose()
        result = audit_rag_readiness(soup, soup_clean)
        assert result.checked is True
