"""Test per il fix CDN/WAF di llms.txt (blocked_by_cdn + retry browser-like).

Copre: 403->retry 200, 403->retry 403, 406, non-403 senza retry, fallback HTML,
warning "blocked", e il ramo blocked_by_cdn in generate_llms_fix.
Stile AAA, mock su fetch_url, nessuna rete reale (AGENTS.md).
"""
from unittest.mock import MagicMock, patch

from geo_optimizer.core.audit_llms import (
    _audit_llms_from_response,
    _browser_like_headers,
    audit_llms_txt,
)
from geo_optimizer.core.fixer import generate_llms_fix
from geo_optimizer.models.results import LlmsTxtResult

LLMS_FULL_SPEC = """\
# My Project

> A comprehensive tool for optimizing websites for AI search engines.
> Built with Python and FastAPI.

## Features

- [Home](https://example.com/)
- [About](https://example.com/about)

## Optional

- [FAQ](https://example.com/faq)
"""


def _mock_resp(status: int, text: str = "", content_type: str = "text/plain"):
    r = MagicMock()
    r.status_code = status
    r.text = text
    r.headers = {"Content-Type": content_type}
    return r


class TestLlmsBlockedByCdn:
    """audit_llms_txt: comportamento su 403/406 con retry browser-like."""

    @patch("geo_optimizer.core.audit_llms.fetch_url")
    def test_403_then_retry_200_recover_content(self, mock_fetch):
        """403 poi retry 200 -> blocked_by_cdn True e contenuto recuperato."""
        first_403 = _mock_resp(403)
        retry_200 = _mock_resp(200, LLMS_FULL_SPEC)
        full_404 = _mock_resp(404)
        mock_fetch.side_effect = [
            (first_403, None),  # fetch iniziale /llms.txt -> 403
            (retry_200, None),  # retry browser-like -> 200
            (full_404, None),  # /llms-full.txt -> 404
        ]

        result = audit_llms_txt("https://example.com")

        assert result.blocked_by_cdn is True
        assert result.found is True
        assert result.has_h1 is True
        assert any("CDN" in w for w in result.validation_warnings)
        # secondo fetch (retry) avvenuto
        assert mock_fetch.call_count >= 2

    @patch("geo_optimizer.core.audit_llms.fetch_url")
    def test_403_then_retry_403_not_found_but_blocked(self, mock_fetch):
        """403 poi retry 403 -> found False ma blocked_by_cdn True."""
        first_403 = _mock_resp(403)
        retry_403 = _mock_resp(403)
        mock_fetch.side_effect = [
            (first_403, None),
            (retry_403, None),
        ]

        result = audit_llms_txt("https://example.com")

        assert result.blocked_by_cdn is True
        assert result.found is False
        assert mock_fetch.call_count == 2

    @patch("geo_optimizer.core.audit_llms.fetch_url")
    def test_406_triggers_blocked_and_retry(self, mock_fetch):
        """406 attiva blocked_by_cdn e retry (secondo codice bloccante)."""
        first_406 = _mock_resp(406)
        retry_200 = _mock_resp(200, LLMS_FULL_SPEC)
        full_404 = _mock_resp(404)
        mock_fetch.side_effect = [
            (first_406, None),
            (retry_200, None),
            (full_404, None),
        ]

        result = audit_llms_txt("https://example.com")

        assert result.blocked_by_cdn is True
        assert result.found is True

    @patch("geo_optimizer.core.audit_llms.fetch_url")
    def test_non_403_does_not_set_blocked_or_retry(self, mock_fetch):
        """404 (non-403/406) -> nessun blocked e nessun retry extra."""
        err404 = _mock_resp(404)
        mock_fetch.side_effect = [(err404, None)]

        result = audit_llms_txt("https://example.com")

        assert result.blocked_by_cdn is False
        assert result.found is False
        assert mock_fetch.call_count == 1

    @patch("geo_optimizer.core.audit_llms.fetch_url")
    def test_retry_fallback_failure_adds_warning(self, mock_fetch):
        """403 poi retry fallisce -> blocked True, found False, warning su retry fallito."""
        first_403 = _mock_resp(403)
        mock_fetch.side_effect = [
            (first_403, None),
            (None, "Unsafe URL"),  # retry fallisce (errore)
        ]

        result = audit_llms_txt("https://example.com")

        assert result.blocked_by_cdn is True
        assert result.found is False
        assert any("retry failed" in w for w in result.validation_warnings)

    @patch("geo_optimizer.core.audit_llms.fetch_url")
    def test_retry_html_fallback_not_treated_as_llms(self, mock_fetch):
        """403 poi retry 200 con HTML (fallback WAF) -> non è llms.txt valido."""
        first_403 = _mock_resp(403)
        html_fallback = _mock_resp(200, "<html><body>challenge</body></html>", "text/html")
        mock_fetch.side_effect = [
            (first_403, None),
            (html_fallback, None),
        ]

        result = audit_llms_txt("https://example.com")

        assert result.blocked_by_cdn is True
        assert result.found is False
        assert any("HTML page" in w for w in result.validation_warnings)


class TestBrowserLikeHeaders:
    """browser_like_headers contiene una real browser UA."""

    def test_contains_mozilla_browser_ua(self):
        headers = _browser_like_headers()
        assert "User-Agent" in headers
        assert "Mozilla/5.0" in headers["User-Agent"]
        assert "(compatible;" not in headers["User-Agent"]  # non firma da bot


class TestAuditLlmsFromResponseBlocked:
    """_audit_llms_from_response: il flusso usato dal main audit."""

    def test_403_sets_blocked_and_warning(self):
        r = _mock_resp(403)
        result = _audit_llms_from_response(r)
        assert result.blocked_by_cdn is True
        assert result.found is False
        assert any("CDN" in w for w in result.validation_warnings)

    def test_406_sets_blocked(self):
        r = _mock_resp(406)
        result = _audit_llms_from_response(r)
        assert result.blocked_by_cdn is True
        assert result.found is False


class TestGenerateLlmsFixBlocked:
    """generate_llms_fix: ramo blocked_by_cdn."""

    def _result(self, blocked=False, found=False):
        result = MagicMock()
        result.llms = LlmsTxtResult(
            found=found,
            has_h1=False,
            has_sections=False,
            has_links=False,
            blocked_by_cdn=blocked,
        )
        return result

    @patch(
        "geo_optimizer.core.llms_generator.discover_sitemap",
        return_value=None,
    )
    @patch(
        "geo_optimizer.core.llms_generator.fetch_sitemap",
        return_value=[],
    )
    def test_blocked_by_cdn_uses_llms_generator_not_empty(self, mock_sitemap, mock_discover):
        """blocked_by_cdn non crea un file vuoto: generate_llms_fix genera contenuto dal sitemap."""
        result = MagicMock()
        result.llms = LlmsTxtResult(
            found=False,
            has_h1=False,
            has_sections=False,
            has_links=False,
            blocked_by_cdn=True,
        )

        fix = generate_llms_fix(result, "https://example.com")

        assert fix is not None
        assert fix.category == "llms"
        assert fix.content  # contenuto non vuoto, non un artefatto vuoto
        # la descrizione include la nota CDN per avvisare che il blocco può nascondere un file reale
        assert "CDN" in fix.description


def _real_resp(status: int, text: str = ""):
    """Vera requests.Response: a differenza di MagicMock è falsy sui 4xx (__bool__ == ok)."""
    import requests

    r = requests.Response()
    r.status_code = status
    r._content = text.encode("utf-8")
    r.encoding = "utf-8"
    r.headers["Content-Type"] = "text/plain"
    return r


class TestFalsyRequestsResponse:
    """Regressione: `if not r` scartava il 403 di requests prima del ramo CDN/WAF."""

    @patch("geo_optimizer.core.audit_llms.fetch_url")
    def test_audit_llms_txt_real_403_is_flagged_and_retried(self, mock_fetch):
        mock_fetch.side_effect = [
            (_real_resp(403), None),
            (_real_resp(200, LLMS_FULL_SPEC), None),
            (_real_resp(200, "full"), None),
        ]

        result = audit_llms_txt("https://example.com")

        assert result.blocked_by_cdn is True
        assert result.found is True
        assert result.has_full is True

    @patch("geo_optimizer.core.audit_llms.fetch_url")
    def test_from_response_real_403_recovers_file_and_full(self, mock_fetch):
        mock_fetch.return_value = (_real_resp(200, LLMS_FULL_SPEC), None)

        result = _audit_llms_from_response(
            _real_resp(403), r_full=_real_resp(200, "full"), url="https://example.com/llms.txt"
        )

        assert result.blocked_by_cdn is True
        assert result.found is True
        assert result.has_full is True
