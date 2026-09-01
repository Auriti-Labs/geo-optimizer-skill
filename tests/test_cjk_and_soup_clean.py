"""Regression tests for #537.

Two measurement defects:
  1. audit_negative_signals read the raw soup, so <style>/<noscript> text could
     count toward keyword-stuffing / boilerplate.
  2. Word counts used str.split(), which under-counts CJK text ~10x, making the
     content word-count and front-loading gates unreachable for Chinese /
     Japanese / Korean pages.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

from geo_optimizer.core.audit import audit_content_quality, audit_llms_txt, audit_negative_signals
from geo_optimizer.models.results import ContentResult, MetaResult, SchemaResult
from geo_optimizer.utils.text import count_words, has_cjk, tokenize_words

# A normal-length Chinese paragraph (no inter-word spaces).
ZH_SENTENCE = "人工智能搜索正在改变网站获得流量的方式。"
ZH_ARTICLE = ZH_SENTENCE * 15  # ~285 CJK codepoints


def _content(word_count=500, h1="Test Page", heading_count=3, has_h1=True):
    return ContentResult(word_count=word_count, h1_text=h1, heading_count=heading_count, has_h1=has_h1)


def _meta():
    return MetaResult(has_title=True, title_text="Test", description_text="Test description")


class TestTokenizer:
    def test_latin_matches_str_split(self):
        for s in ["hello world", "a,b c", "  spaced   out  ", "café résumé señor", ""]:
            assert tokenize_words(s) == s.split()
            assert count_words(s) == len(s.split())

    def test_cjk_codepoints_count_individually(self):
        assert count_words("AI搜索") == 3  # "AI" + 搜 + 索
        assert count_words("人工智能") == 4
        assert count_words("2026年10月") == 4  # 2026 + 年 + 10 + 月
        # A ~19-ideograph sentence tokenizes to roughly that many units,
        # vs 1 for str.split().
        assert count_words(ZH_SENTENCE) >= 18
        assert len(ZH_SENTENCE.split()) == 1

    def test_has_cjk(self):
        assert has_cjk("こんにちは") is True
        assert has_cjk("안녕하세요") is True
        assert has_cjk("plain english") is False
        assert has_cjk("") is False


class TestContentWordCountCJK:
    def test_chinese_article_word_count_is_realistic(self):
        html = f"<html><body><main><h1>关于我们</h1><p>{ZH_ARTICLE}</p></main></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = audit_content_quality(soup, "https://example.cn/")
        # Whitespace split would give ~1; CJK-aware gives a few hundred.
        assert result.word_count > 200

    def test_chinese_article_can_reach_front_loading(self):
        # Numbers up front so the front-loading "contains a digit" check passes.
        body = "2026年 " + ZH_ARTICLE * 3
        html = f"<html><body><main><h1>数据报告</h1><p>{body}</p></main></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = audit_content_quality(soup, "https://example.cn/")
        assert result.has_front_loading is True

    def test_latin_word_count_unchanged(self):
        body = " ".join(["content"] * 400)
        html = f"<html><body><main><p>{body}</p></main></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = audit_content_quality(soup, "https://example.com/")
        assert result.word_count == 400


class TestContentSoupCleanExtras:
    def test_noscript_and_template_excluded_from_word_count(self):
        noise = " ".join(["fallback"] * 300)
        real = " ".join(["realcopy"] * 40)
        html = (
            f"<html><body><main><p>{real}</p>"
            f"<noscript>{noise}</noscript><template>{noise}</template></main></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        result = audit_content_quality(soup, "https://example.com/")
        assert result.word_count == 40


class TestNegativeSignalsStyleLeak:
    def test_style_text_does_not_trigger_stuffing_with_soup_clean(self):
        css = ".foo{display:flex;flex-direction:column}.bar{color:red}" * 200
        copy_text = "we help teams ship faster and measure the results carefully "
        html = (
            f"<html><head><style>{css}</style></head>"
            f"<body><main><h1>Product</h1><p>{copy_text * 6}</p></main></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        soup_clean = BeautifulSoup(html, "html.parser")
        for tag in soup_clean(["script", "style", "noscript", "template"]):
            tag.decompose()
        result = audit_negative_signals(
            soup, html, _content(word_count=60), _meta(), SchemaResult(), soup_clean=soup_clean
        )
        assert result.has_keyword_stuffing is False

    def test_noscript_menu_not_counted_as_boilerplate_with_soup_clean(self):
        menu = "home about pricing contact blog careers login signup " * 40
        real = "real article body sentence " * 40
        html = (
            f"<html><body><noscript>{menu}</noscript>"
            f"<main>{real}</main></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        soup_clean = BeautifulSoup(html, "html.parser")
        for tag in soup_clean(["script", "style", "noscript", "template"]):
            tag.decompose()
        clean = audit_negative_signals(
            soup, html, _content(), _meta(), SchemaResult(), soup_clean=soup_clean
        )
        assert clean.boilerplate_ratio <= 0.1

    def test_backward_compatible_without_soup_clean(self):
        html = "<html><body><main><h1>Test Page</h1><p>ordinary body copy here</p></main></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = audit_negative_signals(soup, html, _content(), _meta(), SchemaResult())
        assert result.checked is True


class TestLlmsTxtWordCountCJK:
    @patch("geo_optimizer.core.audit_llms.fetch_url")
    def test_chinese_llms_txt_word_count(self, mock_fetch):
        content = "# 我的项目\n\n> " + ZH_SENTENCE * 30 + "\n\n## 文档\n- [指南](https://example.cn/docs)\n"
        resp = MagicMock()
        resp.status_code = 200
        resp.text = content
        full_404 = MagicMock()
        full_404.status_code = 404
        mock_fetch.side_effect = [(resp, None), (full_404, None)]

        result = audit_llms_txt("https://example.cn")
        assert result.found is True
        # str.split would report a handful of tokens; CJK-aware reports hundreds.
        assert result.word_count > 100
