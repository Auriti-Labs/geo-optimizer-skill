"""Tests for CDN AI Crawler Check (#225) and JS Rendering Check (#226)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from geo_optimizer.core.audit import audit_cdn_ai_crawler, audit_js_rendering
from geo_optimizer.models.results import CdnAiCrawlerResult, JsRenderingResult


# ─── JS Rendering Check (#226) ──────────────────────────────────────────────


class TestJsRenderingCheck:
    """Tests for audit_js_rendering()."""

    def test_ssr_page_passes(self):
        """A well-rendered SSR page should NOT be flagged as JS-dependent."""
        # Need enough words to pass the 100-word threshold
        paragraphs = " ".join(["word"] * 150)
        html = f"""
        <html lang="en">
        <head><title>Test Page</title></head>
        <body>
            <h1>Welcome to Our Site</h1>
            <h2>About Us</h2>
            <p>{paragraphs}</p>
            <h2>Our Services</h2>
            <p>We offer consulting development and maintenance services.</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = audit_js_rendering(soup, html)

        assert result.checked is True
        assert result.js_dependent is False
        assert result.raw_word_count > 100
        assert result.raw_heading_count >= 3

    def test_spa_empty_root_detected(self):
        """A React SPA with empty #root should be flagged."""
        html = """
        <html>
        <head><title>React App</title></head>
        <body>
            <div id="root"></div>
            <script src="/static/js/main.chunk.js"></script>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = audit_js_rendering(soup, html)

        assert result.checked is True
        assert result.js_dependent is True
        assert result.has_empty_root is True
        assert result.raw_word_count < 100

    def test_vue_spa_detected(self):
        """A Vue SPA with empty #app should be flagged."""
        html = """
        <html>
        <head><title>Vue App</title></head>
        <body>
            <div id="app" data-v-12345></div>
            <script src="/js/app.js"></script>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = audit_js_rendering(soup, html)

        assert result.checked is True
        assert result.js_dependent is True
        assert result.framework_detected == "vue"

    def test_nextjs_ssr_passes(self):
        """A Next.js page with SSR content should pass."""
        words = " ".join(["content"] * 120)
        html = f"""
        <html>
        <head><title>Next App</title></head>
        <body>
            <div id="__next">
                <h1>Server Rendered Page</h1>
                <h2>Section Two</h2>
                <p>{words}</p>
            </div>
            <script src="/_next/static/chunks/main.js"></script>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = audit_js_rendering(soup, html)

        assert result.checked is True
        assert result.js_dependent is False
        assert result.framework_detected == "next.js"

    def test_noscript_content_detected(self):
        """<noscript> fallback content should be detected."""
        html = """
        <html>
        <head><title>App</title></head>
        <body>
            <div id="root"></div>
            <noscript>You need to enable JavaScript to run this app. Please enable JavaScript in your browser settings.</noscript>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = audit_js_rendering(soup, html)

        assert result.checked is True
        assert result.has_noscript_content is True

    def test_empty_input_returns_unchecked(self):
        """Empty/None inputs should return unchecked result."""
        result = audit_js_rendering(None, "")
        assert result.checked is False

    def test_astro_detected(self):
        """Astro framework should be detected with enough SSG content."""
        words = " ".join(["word"] * 120)
        html = f"""
        <html>
        <head><title>Astro Site</title>
        <link rel="stylesheet" href="/_astro/index.abc123.css">
        </head>
        <body>
            <h1>Static Astro Site</h1>
            <p>{words}</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = audit_js_rendering(soup, html)

        assert result.checked is True
        assert result.framework_detected == "astro"
        assert result.js_dependent is False

    def test_critically_low_content(self):
        """Page with < 50 words should be flagged."""
        html = """
        <html>
        <head><title>Empty</title></head>
        <body><p>Loading</p></body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = audit_js_rendering(soup, html)

        assert result.checked is True
        assert result.js_dependent is True
        assert result.raw_word_count < 50


# ─── CDN AI Crawler Check (#225) ─────────────────────────────────────────────


class TestCdnAiCrawlerCheck:
    """Tests for audit_cdn_ai_crawler()."""

    @patch("geo_optimizer.utils.validators.resolve_and_validate_url", return_value=(True, None, ["93.184.216.34"]))
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_no_block_all_pass(self, mock_session_factory, mock_validate):
        """When all bots get 200 with similar content, no block detected."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "x" * 5000
        mock_response.headers = {"Content-Type": "text/html"}
        mock_session.get.return_value = mock_response
        mock_session_factory.return_value = mock_session

        result = audit_cdn_ai_crawler("https://example.com")

        assert result.checked is True
        assert result.any_blocked is False
        assert len(result.bot_results) == 3  # GPTBot, ClaudeBot, PerplexityBot

    @patch("geo_optimizer.utils.validators.resolve_and_validate_url", return_value=(True, None, ["93.184.216.34"]))
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_bot_403_detected(self, mock_session_factory, mock_validate):
        """403 for AI bot should be detected as blocked."""
        mock_session = MagicMock()

        def side_effect(url, **kwargs):
            ua = kwargs.get("headers", {}).get("User-Agent", "")
            resp = MagicMock()
            resp.headers = {}
            if "GPTBot" in ua:
                resp.status_code = 403
                resp.text = "Forbidden"
            else:
                resp.status_code = 200
                resp.text = "x" * 5000
            return resp

        mock_session.get.side_effect = side_effect
        mock_session_factory.return_value = mock_session

        result = audit_cdn_ai_crawler("https://example.com")

        assert result.checked is True
        assert result.any_blocked is True
        gptbot = next(b for b in result.bot_results if b["bot"] == "GPTBot")
        assert gptbot["blocked"] is True

    @patch("geo_optimizer.utils.validators.resolve_and_validate_url", return_value=(True, None, ["93.184.216.34"]))
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_cloudflare_challenge_detected(self, mock_session_factory, mock_validate):
        """Cloudflare challenge page should be detected."""
        mock_session = MagicMock()

        def side_effect(url, **kwargs):
            ua = kwargs.get("headers", {}).get("User-Agent", "")
            resp = MagicMock()
            if "GPTBot" in ua:
                resp.status_code = 200
                resp.text = '<html><body>Checking your browser before accessing the site. Please wait... cf-browser-verification Ray ID: abc123</body></html>'
                resp.headers = {"cf-ray": "abc123-CDG", "server": "cloudflare"}
            else:
                resp.status_code = 200
                resp.text = "x" * 5000
                resp.headers = {"cf-ray": "abc123-CDG", "server": "cloudflare"}
            return resp

        mock_session.get.side_effect = side_effect
        mock_session_factory.return_value = mock_session

        result = audit_cdn_ai_crawler("https://example.com")

        assert result.checked is True
        assert result.cdn_detected == "cloudflare"
        gptbot = next(b for b in result.bot_results if b["bot"] == "GPTBot")
        assert gptbot["challenge_detected"] is True

    @patch("geo_optimizer.utils.validators.resolve_and_validate_url", return_value=(True, None, ["93.184.216.34"]))
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_content_length_mismatch_detected(self, mock_session_factory, mock_validate):
        """Bot receiving <30% of browser content should be detected as blocked."""
        mock_session = MagicMock()

        def side_effect(url, **kwargs):
            ua = kwargs.get("headers", {}).get("User-Agent", "")
            resp = MagicMock()
            resp.status_code = 200
            resp.headers = {}
            if "Mozilla/5.0 (Windows" in ua:
                resp.text = "x" * 10000  # Full page
            else:
                resp.text = "x" * 500  # Tiny block page (5% of browser)
            return resp

        mock_session.get.side_effect = side_effect
        mock_session_factory.return_value = mock_session

        result = audit_cdn_ai_crawler("https://example.com")

        assert result.checked is True
        assert result.any_blocked is True

    @patch("geo_optimizer.utils.validators.resolve_and_validate_url", return_value=(True, None, ["93.184.216.34"]))
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_cdn_headers_detected(self, mock_session_factory, mock_validate):
        """CDN headers should be captured."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "x" * 5000
        mock_response.headers = {"X-Vercel-Id": "cdg1::abc", "Server": "Vercel"}
        mock_session.get.return_value = mock_response
        mock_session_factory.return_value = mock_session

        result = audit_cdn_ai_crawler("https://example.com")

        assert result.checked is True
        assert "x-vercel-id" in result.cdn_headers
