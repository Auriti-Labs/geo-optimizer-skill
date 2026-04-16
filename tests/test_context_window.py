"""Tests for Context Window Optimization audit (#370)."""

from __future__ import annotations

import copy

from bs4 import BeautifulSoup

from geo_optimizer.core.audit_context_window import audit_context_window


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


class TestContextWindowAudit:
    """Tests for audit_context_window()."""

    def test_empty_body(self):
        result = audit_context_window(_soup("<html><body></body></html>"))
        assert result.checked is True
        assert result.total_words == 0
        assert result.context_efficiency_score == 0

    def test_no_body(self):
        result = audit_context_window(_soup("<html><head><title>T</title></head></html>"))
        assert result.checked is True
        assert result.total_words == 0

    def test_none_soup(self):
        result = audit_context_window(None)
        assert result.checked is True
        assert result.total_words == 0

    def test_basic_content_word_count(self):
        text = " ".join(["word"] * 200)
        result = audit_context_window(_soup(f"<html><body><p>{text}</p></body></html>"))
        assert result.checked is True
        assert result.total_words == 200
        assert result.total_tokens_estimate == int(200 * 1.3)

    def test_token_estimation(self):
        text = " ".join(["hello"] * 100)
        result = audit_context_window(_soup(f"<html><body><p>{text}</p></body></html>"))
        assert result.total_tokens_estimate == 130  # 100 * 1.3

    def test_front_loading_high(self):
        """Key info in first 30% should give high front_loaded_ratio."""
        front = "According to research, 85% of users prefer this approach. In 2024, data shows improvement."
        back = " ".join(["generic content word"] * 200)
        html = f"<html><body><p>{front}</p><p>{back}</p></body></html>"
        result = audit_context_window(_soup(html))
        assert result.front_loaded_ratio > 0

    def test_front_loading_zero_no_key_info(self):
        """Content with no key info patterns should have 0 front_loaded_ratio."""
        text = " ".join(["bland"] * 100)
        result = audit_context_window(_soup(f"<html><body><p>{text}</p></body></html>"))
        assert result.front_loaded_ratio == 0.0

    def test_filler_ratio_detected(self):
        """Boilerplate patterns should increase filler_ratio."""
        filler = "Click here to subscribe. Read more about our privacy policy. All rights reserved. "
        text = filler * 10 + " ".join(["content"] * 50)
        result = audit_context_window(_soup(f"<html><body><p>{text}</p></body></html>"))
        assert result.filler_ratio > 0

    def test_filler_ratio_clean_content(self):
        """Clean content without boilerplate should have low filler_ratio."""
        text = " ".join(["Machine learning enables systems to learn from data automatically"] * 20)
        result = audit_context_window(_soup(f"<html><body><p>{text}</p></body></html>"))
        assert result.filler_ratio <= 0.02

    def test_optimal_for_short_content(self):
        """Short content should fit all platforms."""
        text = " ".join(["word"] * 50)
        result = audit_context_window(_soup(f"<html><body><p>{text}</p></body></html>"))
        assert "rag_chunk" in result.optimal_for
        assert "chatgpt" in result.optimal_for
        assert "claude" in result.optimal_for

    def test_optimal_for_long_content(self):
        """Very long content should not fit RAG chunk."""
        text = " ".join(["word"] * 5000)
        result = audit_context_window(_soup(f"<html><body><p>{text}</p></body></html>"))
        assert "rag_chunk" not in result.optimal_for
        assert "claude" in result.optimal_for  # 200k tokens, still fits

    def test_truncation_risk_none(self):
        text = " ".join(["word"] * 50)
        result = audit_context_window(_soup(f"<html><body><p>{text}</p></body></html>"))
        assert result.truncation_risk == "none"

    def test_truncation_risk_low(self):
        text = " ".join(["word"] * 500)
        result = audit_context_window(_soup(f"<html><body><p>{text}</p></body></html>"))
        assert result.truncation_risk == "low"

    def test_truncation_risk_medium(self):
        text = " ".join(["word"] * 3000)
        result = audit_context_window(_soup(f"<html><body><p>{text}</p></body></html>"))
        assert result.truncation_risk == "medium"

    def test_truncation_risk_high(self):
        text = " ".join(["word"] * 10000)
        result = audit_context_window(_soup(f"<html><body><p>{text}</p></body></html>"))
        assert result.truncation_risk == "high"

    def test_score_max_100(self):
        """Score should never exceed 100."""
        front = "According to 2024 research, 95% of data shows step 1 is critical. "
        text = front * 50
        result = audit_context_window(_soup(f"<html><body><p>{text}</p></body></html>"))
        assert result.context_efficiency_score <= 100

    def test_score_zero_empty(self):
        result = audit_context_window(_soup("<html><body></body></html>"))
        assert result.context_efficiency_score == 0

    def test_uses_soup_clean_when_provided(self):
        html = "<html><body><script>var x=1;</script><p>Real content here.</p></body></html>"
        soup = _soup(html)
        soup_clean = copy.deepcopy(soup)
        for tag in soup_clean(["script", "style"]):
            tag.decompose()
        result = audit_context_window(soup, soup_clean)
        assert result.checked is True
        # soup_clean should not include script text
        assert result.total_words < 10

    def test_key_info_tokens_capped(self):
        """key_info_tokens should not exceed total_tokens_estimate."""
        text = "In 2024, 95% of users reported 100% satisfaction. " * 100
        result = audit_context_window(_soup(f"<html><body><p>{text}</p></body></html>"))
        assert result.key_info_tokens <= result.total_tokens_estimate

    def test_filler_ratio_capped_at_one(self):
        """filler_ratio should not exceed 1.0."""
        filler = "click here read more subscribe sign up cookie privacy policy all rights reserved " * 50
        result = audit_context_window(_soup(f"<html><body><p>{filler}</p></body></html>"))
        assert result.filler_ratio <= 1.0

    def test_well_optimized_content_high_score(self):
        """Content with key info front-loaded and no filler should score well."""
        front = (
            "Machine learning is a method of data analysis. "
            "According to 2024 research, 85% of companies use ML. "
            "Step 1 involves data collection from multiple sources. "
        )
        body = "This technology enables automated analytical model building. " * 30
        html = f"<html><body><p>{front}</p><p>{body}</p></body></html>"
        result = audit_context_window(_soup(html))
        assert result.context_efficiency_score >= 30
