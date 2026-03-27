"""Test per Negative Signals Detection."""

from __future__ import annotations

from bs4 import BeautifulSoup

from geo_optimizer.core.audit import audit_negative_signals
from geo_optimizer.models.results import ContentResult, MetaResult, SchemaResult


def _content(word_count=500, h1="Test Page", heading_count=3, has_h1=True):
    return ContentResult(word_count=word_count, h1_text=h1, heading_count=heading_count, has_h1=has_h1)


def _meta():
    return MetaResult(has_title=True, title_text="Test", description_text="Test description")


class TestNegativeSignals:
    def test_clean_page(self):
        """Pagina pulita → severity clean."""
        words = " ".join(["content"] * 200)
        html = f'<html><body><main><h1>Test Page</h1><p>{words}</p><span class="author">John Doe</span></main></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        result = audit_negative_signals(soup, html, _content(), _meta(), SchemaResult())
        assert result.checked is True
        assert result.severity in ("clean", "low")

    def test_cta_overload(self):
        """Troppi CTA → detected."""
        ctas = " ".join(["Buy now! Sign up! Free trial! Get started! Subscribe! Order now!"] * 3)
        html = f"<html><body><main><h1>Shop</h1><p>{ctas}</p></main></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = audit_negative_signals(soup, html, _content(word_count=100), _meta(), SchemaResult())
        assert result.cta_density_high is True
        assert result.cta_count >= 6

    def test_popup_detection(self):
        """Modal/popup classes → detected."""
        html = '<html><body><div class="modal-overlay"><p>Subscribe!</p></div><main><p>Content</p></main></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        result = audit_negative_signals(soup, html, _content(), _meta(), SchemaResult())
        assert result.has_popup_signals is True

    def test_thin_content(self):
        """< 300 parole con H1 complesso → thin."""
        html = "<html><body><h1>Complete Guide to SEO</h1><p>Short content.</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = audit_negative_signals(
            soup, html, _content(word_count=50, h1="Complete Guide to SEO"), _meta(), SchemaResult()
        )
        assert result.is_thin_content is True

    def test_broken_links(self):
        """Link vuoti → detected."""
        links = "".join(['<a href="#">link</a><a href="javascript:void(0)">x</a>'] * 3)
        html = f"<html><body><main>{links}<p>Content</p></main></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = audit_negative_signals(soup, html, _content(), _meta(), SchemaResult())
        assert result.broken_links_count >= 4
        assert result.has_broken_links is True

    def test_keyword_stuffing(self):
        """Parola ripetuta > 3% → stuffing detected."""
        # "optimization" è la parola più frequente, > 3% del totale
        text = " ".join(["optimization"] * 30 + ["apple"] * 10 + ["banana"] * 10 + ["cherry"] * 10)
        html = f"<html><body><main><h1>Test</h1><p>{text}</p></main></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = audit_negative_signals(soup, html, _content(word_count=60), _meta(), SchemaResult())
        assert result.has_keyword_stuffing is True
        assert result.stuffed_word == "optimization"

    def test_author_from_schema(self):
        """Person schema → has_author_signal."""
        html = "<html><body><main><p>Content</p></main></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        schema = SchemaResult(raw_schemas=[{"@type": "Person", "name": "John"}])
        result = audit_negative_signals(soup, html, _content(), _meta(), schema)
        assert result.has_author_signal is True

    def test_author_from_html(self):
        """class=author nel HTML → has_author_signal."""
        html = '<html><body><main><p>Content</p><span class="author-name">Jane</span></main></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        result = audit_negative_signals(soup, html, _content(), _meta(), SchemaResult())
        assert result.has_author_signal is True

    def test_boilerplate_high(self):
        """Boilerplate > 60% → high."""
        nav = "nav " * 300
        content = "real " * 50
        html = f"<html><body><nav>{nav}</nav><main>{content}</main><footer>{nav}</footer></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = audit_negative_signals(soup, html, _content(), _meta(), SchemaResult())
        assert result.boilerplate_ratio > 0.5

    def test_mixed_signals(self):
        """H1 promette, contenuto scarso → mixed."""
        html = "<html><body><main><h1>The Ultimate Complete Guide</h1><p>Short.</p></main></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = audit_negative_signals(
            soup,
            html,
            _content(word_count=200, h1="The Ultimate Complete Guide"),
            _meta(),
            SchemaResult(),
        )
        assert result.has_mixed_signals is True

    def test_none_soup(self):
        """None soup → unchecked."""
        result = audit_negative_signals(None, "", _content(), _meta(), SchemaResult())
        assert result.checked is False

    def test_severity_high(self):
        """4+ segnali negativi → high severity."""
        ctas = "Buy now! Sign up! Free trial! Subscribe! Order now! Act now!"
        links = '<a href="#">x</a>' * 5
        text = " ".join(["keyword"] * 30 + ["other"] * 50)
        html = f"<html><body><div class='modal'>popup</div>{links}<h1>Complete Guide</h1><p>{ctas} {text}</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = audit_negative_signals(
            soup, html, _content(word_count=100, h1="Complete Guide"), _meta(), SchemaResult()
        )
        assert result.signals_found >= 4
        assert result.severity == "high"
