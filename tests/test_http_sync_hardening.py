"""Test di regressione per lo stack HTTP sincrono (utils/http.py).

Copre quattro difetti:
- una Response reale in streaming veniva letta per intero tramite ``.content``
  prima del controllo su max_size;
- retry annidati (@with_retry sopra il Retry di urllib3) sugli errori di connessione;
- Retry-After del server rispettato senza limite;
- redirect relativi e protocol-relative risolti senza urljoin.

Nessuna richiesta di rete: le risposte sono oggetti requests.Response costruiti a mano.
"""

from __future__ import annotations

import io
from unittest.mock import Mock, patch

import pytest
import requests
from urllib3.response import HTTPResponse

from geo_optimizer.utils import http as http_mod
from geo_optimizer.utils.http import fetch_url

_PUBLIC_IP = ["93.184.216.34"]


class _CountingBytesIO(io.BytesIO):
    """BytesIO che registra quanti byte sono stati effettivamente letti."""

    def __init__(self, data: bytes):
        super().__init__(data)
        self.bytes_read = 0

    def read(self, size: int | None = -1) -> bytes:
        chunk = super().read(size)
        self.bytes_read += len(chunk)
        return chunk


def _real_streaming_response(body: bytes, headers: dict | None = None) -> requests.Response:
    """Response reale come la restituisce session.get(stream=True): body non ancora letto."""
    response = requests.Response()
    response.status_code = 200
    response.raw = _CountingBytesIO(body)
    response.headers.update(headers or {})
    response.url = "https://example.com/"
    return response


def _resolve_ok(url):
    return True, None, _PUBLIC_IP


class TestStreamingSizeLimit:
    """Il limite max_size deve valere durante il download, non dopo."""

    def test_fetch_url_real_response_over_limit_stops_reading_early(self):
        max_size = 64 * 1024
        response = _real_streaming_response(b"x" * (max_size * 20))  # niente Content-Length

        with (
            patch("geo_optimizer.utils.validators.resolve_and_validate_url", side_effect=_resolve_ok),
            patch.object(http_mod, "_execute_request", return_value=response),
        ):
            result, error = fetch_url("https://example.com/", max_size=max_size)

        assert result is None
        assert "Response too large" in error
        # Lettura interrotta al superamento del limite (un chunk di margine),
        # invece di scaricare tutto il body in memoria.
        assert response.raw.bytes_read <= max_size + http_mod._CHUNK_SIZE

    def test_fetch_url_real_response_under_limit_returns_body(self):
        body = "<html><body>Caffè</body></html>".encode()
        response = _real_streaming_response(body, {"Content-Type": "text/html"})

        with (
            patch("geo_optimizer.utils.validators.resolve_and_validate_url", side_effect=_resolve_ok),
            patch.object(http_mod, "_execute_request", return_value=response),
        ):
            result, error = fetch_url("https://example.com/")

        assert error is None
        assert result.content == body
        # Content-Type senza charset: requests assumerebbe ISO-8859-1 ("CaffÃ¨")
        assert result.encoding == "utf-8"
        assert "Caffè" in result.text

    def test_fetch_url_legacy_mock_with_content_attribute_still_works(self):
        legacy = Mock()
        legacy.status_code = 200
        legacy.headers = {}
        legacy._content = False
        legacy.content = b"legacy body"

        with (
            patch("geo_optimizer.utils.validators.resolve_and_validate_url", side_effect=_resolve_ok),
            patch.object(http_mod, "_execute_request", return_value=legacy),
        ):
            result, error = fetch_url("https://example.com/")

        assert error is None
        assert result is legacy


class TestGuessEncoding:
    def test_guess_encoding_non_utf8_body_uses_detection(self):
        response = Mock(apparent_encoding="windows-1252")

        assert http_mod._guess_encoding(response, "Café".encode("cp1252")) == "windows-1252"

    def test_guess_encoding_utf8_body_skips_detection(self):
        response = Mock()
        type(response).apparent_encoding = property(lambda self: (_ for _ in ()).throw(AssertionError("scan")))

        assert http_mod._guess_encoding(response, "Café".encode()) == "utf-8"


class TestRetryPolicy:
    def test_fetch_session_does_not_retry_connection_errors_twice(self):
        captured = {}

        def _capture(**kwargs):
            session = requests.Session()
            captured.update(kwargs)
            return session

        response = _real_streaming_response(b"ok")
        with (
            patch("geo_optimizer.utils.validators.resolve_and_validate_url", side_effect=_resolve_ok),
            patch.object(http_mod, "create_session_with_retry", side_effect=_capture),
            patch.object(http_mod, "_execute_request", return_value=response),
        ):
            fetch_url("https://example.com/")

        # @with_retry gestisce gia' timeout/ConnectionError: urllib3 non deve ripeterli
        assert captured["connection_retries"] == 0

    def test_create_session_connection_retries_zero_disables_connect_and_read(self):
        session = http_mod.create_session_with_retry(connection_retries=0)
        retries = session.get_adapter("https://example.com").max_retries

        assert retries.connect == 0
        assert retries.read == 0
        # i retry sugli status (429/5xx) restano attivi
        assert retries.total == 3
        session.close()

    def test_create_session_default_keeps_connection_retries(self):
        session = http_mod.create_session_with_retry()
        retries = session.get_adapter("https://example.com").max_retries

        assert retries.connect is None  # limitato solo da total
        session.close()

    def test_retry_after_header_is_capped(self):
        retry = http_mod._CappedRetry(total=3)
        response = HTTPResponse(body=b"", headers={"Retry-After": "21600"}, status=429)

        assert retry.get_retry_after(response) == http_mod._MAX_RETRY_AFTER_SECONDS

    def test_retry_after_header_below_cap_is_kept(self):
        retry = http_mod._CappedRetry(total=3)
        response = HTTPResponse(body=b"", headers={"Retry-After": "2"}, status=429)

        assert retry.get_retry_after(response) == 2

    def test_capped_retry_survives_increment(self):
        retry = http_mod._CappedRetry(total=3, status_forcelist=[429])
        response = HTTPResponse(body=b"", headers={"Retry-After": "21600"}, status=429)

        nxt = retry.increment(method="GET", url="/", response=response)

        assert isinstance(nxt, http_mod._CappedRetry)


class TestRedirectResolution:
    def _run_redirect(self, start_url: str, location: str) -> list[str]:
        validated: list[str] = []

        def _resolve(url):
            validated.append(url)
            return True, None, _PUBLIC_IP

        redirect = Mock(status_code=302, headers={"Location": location})
        final = Mock(status_code=200, headers={}, _content=b"ok")
        with (
            patch("geo_optimizer.utils.validators.resolve_and_validate_url", side_effect=_resolve),
            patch.object(http_mod, "_execute_request", side_effect=[redirect, final]),
        ):
            result, error = fetch_url(start_url)

        assert error is None
        return validated

    def test_redirect_protocol_relative_location_changes_host(self):
        validated = self._run_redirect("https://example.com/a", "//other.example.org/b")

        assert validated[-1] == "https://other.example.org/b"

    def test_redirect_relative_path_resolves_against_current_directory(self):
        validated = self._run_redirect("https://example.com/docs/index.html", "page.html")

        assert validated[-1] == "https://example.com/docs/page.html"

    def test_redirect_parent_path_is_normalised(self):
        validated = self._run_redirect("https://example.com/docs/guide/", "../faq")

        assert validated[-1] == "https://example.com/docs/faq"

    def test_redirect_absolute_path_keeps_host(self):
        validated = self._run_redirect("https://example.com/docs/x", "/login")

        assert validated[-1] == "https://example.com/login"


class TestBodyReadErrors:
    def test_fetch_url_error_while_streaming_returns_error_instead_of_raising(self):
        response = _real_streaming_response(b"")
        response.iter_content = Mock(side_effect=requests.exceptions.ChunkedEncodingError("truncated"))
        response.close = Mock()

        with (
            patch("geo_optimizer.utils.validators.resolve_and_validate_url", side_effect=_resolve_ok),
            patch.object(http_mod, "_execute_request", return_value=response),
        ):
            result, error = fetch_url("https://example.com/")

        assert result is None
        assert error == "Error while reading response body"
        response.close.assert_called_once()


class TestRedirectValidationWithRealValidator:
    """I target dei redirect passano dal validatore reale, non da un mock permissivo."""

    @pytest.mark.parametrize(
        "location",
        [
            "javascript:alert(1)",
            "file:///etc/passwd",
            "//127.0.0.1/admin",
            "//169.254.169.254/latest/meta-data/",
            "http://10.0.0.1/",
            "//user@127.0.0.1/",
        ],
    )
    def test_redirect_to_unsafe_target_is_refused(self, location):
        from geo_optimizer.utils.validators import resolve_and_validate_url as real_resolve

        def _resolve(url):
            # solo l'URL iniziale e' simulato: i target del redirect usano il validatore reale
            if url == "https://example.com/start":
                return True, None, _PUBLIC_IP
            return real_resolve(url)

        redirect = Mock(status_code=302, headers={"Location": location})
        with (
            patch("geo_optimizer.utils.validators.resolve_and_validate_url", side_effect=_resolve),
            patch.object(http_mod, "_execute_request", return_value=redirect) as execute,
        ):
            result, error = fetch_url("https://example.com/start")

        assert result is None
        assert error.startswith("Redirect to unsafe URL")
        assert execute.call_count == 1  # il target non viene mai richiesto

    def test_redirect_to_invalid_idna_host_returns_error(self):
        from geo_optimizer.utils.validators import resolve_and_validate_url

        ok, error, ips = resolve_and_validate_url("https://a..com/")

        assert ok is False
        assert ips == []
