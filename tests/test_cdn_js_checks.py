"""Tests for CDN AI Crawler Check (#225) and JS Rendering Check (#226)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

from geo_optimizer.core.audit import audit_cdn_ai_crawler, audit_js_rendering

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
        # GPTBot, OAI-SearchBot, PerplexityBot, Claude-SearchBot, Googlebot, Applebot
        assert len(result.bot_results) == 6

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
                resp.text = "<html><body>Checking your browser before accessing the site. Please wait... cf-browser-verification Ray ID: abc123</body></html>"
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

    @staticmethod
    def _session(browser_text: str, bot_text: str, bot_status: int = 200):
        session = MagicMock()

        def side_effect(url, **kwargs):
            ua = kwargs.get("headers", {}).get("User-Agent", "")
            resp = MagicMock()
            resp.headers = {}
            if "Mozilla/5.0 (Windows" in ua:
                resp.status_code, resp.text = 200, browser_text
            else:
                resp.status_code, resp.text = bot_status, bot_text
            return resp

        session.get.side_effect = side_effect
        return session

    @patch("geo_optimizer.utils.validators.resolve_and_validate_url", return_value=(True, None, ["93.184.216.34"]))
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_a_full_page_that_contains_challenge_words_is_not_a_challenge(self, mock_session_factory, mock_validate):
        """Measured on en.wikipedia.org: every AI user agent got HTTP 200 and the same 490 KB as the browser, and the
        words 'blocked' and 'forbidden' sit in ordinary markup. That is the page, not a challenge."""
        page = "<html><script>var cfg = {'blocked': false, 'forbidden': []};</script>" + "x" * 8000 + "</html>"
        mock_session_factory.return_value = self._session(page, page)

        result = audit_cdn_ai_crawler("https://example.com")

        assert result.checked is True
        assert all(b["challenge_detected"] is False for b in result.bot_results)
        assert result.any_blocked is False and result.block_pattern == "none"

    @patch("geo_optimizer.utils.validators.resolve_and_validate_url", return_value=(True, None, ["93.184.216.34"]))
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_a_small_challenge_page_in_place_of_the_page_is_still_a_challenge(
        self, mock_session_factory, mock_validate
    ):
        challenge = "<html>Just a moment... Checking your browser before accessing the site.</html>"
        mock_session_factory.return_value = self._session("x" * 8000, challenge)

        result = audit_cdn_ai_crawler("https://example.com")

        assert all(b["challenge_detected"] is True for b in result.bot_results)
        assert result.block_pattern == "blanket"

    @patch("geo_optimizer.utils.validators.resolve_and_validate_url", return_value=(True, None, ["93.184.216.34"]))
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_challenge_words_with_an_error_status_stay_a_block(self, mock_session_factory, mock_validate):
        page = "<html>Access denied. Forbidden. " + "x" * 8000 + "</html>"
        mock_session_factory.return_value = self._session("x" * 8040, page, bot_status=403)

        result = audit_cdn_ai_crawler("https://example.com")

        assert all(b["blocked"] is True and b["challenge_detected"] is True for b in result.bot_results)

    def test_the_delivery_rule(self):
        from geo_optimizer.core.audit_cdn import _delivers_the_page

        assert _delivers_the_page(200, 1000, 200, 1000)
        assert _delivers_the_page(200, 700, 200, 1000) and _delivers_the_page(200, 1500, 200, 1000)
        assert not _delivers_the_page(200, 699, 200, 1000) and not _delivers_the_page(200, 1501, 200, 1000)
        assert not _delivers_the_page(403, 1000, 200, 1000)  # an error status is never a delivery
        assert not _delivers_the_page(200, 1000, 403, 1000)  # no baseline: the browser was refused too
        assert not _delivers_the_page(200, 1000, 200, 0)

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

    @patch("geo_optimizer.utils.validators.resolve_and_validate_url", return_value=(True, None, ["93.184.216.34"]))
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_oversized_body_stops_streaming_at_the_cap(self, mock_session_factory, mock_validate):
        """The body is streamed and reading stops just past 5 MB instead of downloading it whole."""
        chunks_read = 0

        def endless_body(chunk_size):
            nonlocal chunks_read
            while True:
                chunks_read += 1
                yield b"x" * chunk_size

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.side_effect = endless_body
        mock_session.get.return_value = mock_response
        mock_session_factory.return_value = mock_session

        result = audit_cdn_ai_crawler("https://example.com")

        assert result.error == "Response too large for CDN check"
        assert result.checked is False
        assert mock_session.get.call_args.kwargs["stream"] is True
        assert mock_session.get.call_count == 1  # no bot request after the oversized baseline
        chunk_size = mock_response.iter_content.call_args.kwargs["chunk_size"]
        assert chunks_read == 5 * 1024 * 1024 // chunk_size + 1
        mock_response.close.assert_called_once()

    @patch("geo_optimizer.utils.validators.resolve_and_validate_url", return_value=(True, None, ["93.184.216.34"]))
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_body_error_mid_stream_closes_the_response(self, mock_session_factory, mock_validate):
        """A read error while streaming closes the response before the check gives up."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.side_effect = TimeoutError("read timed out")
        mock_session.get.return_value = mock_response
        mock_session_factory.return_value = mock_session

        result = audit_cdn_ai_crawler("https://example.com")

        assert result.checked is False
        mock_response.close.assert_called_once()
