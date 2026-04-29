"""
Test per i fix di sicurezza SSRF (issues #71, #94, #73, #101).

Copre:
- #71 SSRF DNS Rebinding TOCTOU: resolve_and_validate_url restituisce IP pinnati
- #94/#73 SSRF via HTTP Redirect: redirect verso reti private bloccati
- #101 Body streaming: size check durante il download, non dopo
"""

import socket
from unittest.mock import MagicMock, Mock, call, patch

import pytest
import requests

from geo_optimizer.utils.http import (
    MAX_RESPONSE_SIZE,
    _MAX_REDIRECTS,
    _PinnedIPAdapter,
    _stream_response,
    fetch_url,
)
from geo_optimizer.utils.validators import resolve_and_validate_url, validate_public_url


# ============================================================================
# #71 — DNS Rebinding TOCTOU: resolve_and_validate_url
# ============================================================================


class TestResolveAndValidateUrl:
    """resolve_and_validate_url risolve DNS una volta sola e restituisce gli IP."""

    def test_url_pubblica_restituisce_ip(self):
        """URL pubblica valida restituisce lista IP non vuota."""
        with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
            ok, err, ips = resolve_and_validate_url("https://example.com")
            assert ok is True
            assert err is None
            assert ips == ["93.184.216.34"]

    def test_url_privata_restituisce_lista_vuota(self):
        """URL con IP privato restituisce lista IP vuota e errore."""
        with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("10.0.0.1", 0))]
            ok, err, ips = resolve_and_validate_url("https://evil.example.com")
            assert ok is False
            assert "non-public" in err.lower()
            assert ips == []

    def test_dns_unresolvable_rejected(self):
        """DNS unresolvable → ok=False, prevents TOCTOU (#427)."""
        with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
            mock_dns.side_effect = socket.gaierror("Name resolution failed")
            ok, err, ips = resolve_and_validate_url("https://nonexistent.example.com")
            assert ok is False
            assert "DNS resolution failed" in err
            assert ips == []

    def test_dns_risolto_una_sola_volta(self):
        """Verifica che getaddrinfo venga chiamato una volta sola."""
        with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
            resolve_and_validate_url("https://example.com")
            # DNS risolto esattamente una volta — nessuna seconda chiamata
            assert mock_dns.call_count == 1

    def test_ip_multipli_tutti_pubblici(self):
        """Più IP risolti, tutti pubblici → tutti restituiti."""
        with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("93.184.216.34", 0)),
                (2, 1, 6, "", ("93.184.216.35", 0)),
            ]
            ok, err, ips = resolve_and_validate_url("https://example.com")
            assert ok is True
            assert len(ips) == 2
            assert "93.184.216.34" in ips
            assert "93.184.216.35" in ips

    def test_un_ip_privato_blocca_tutto(self):
        """Se anche un solo IP è privato, la richiesta viene bloccata."""
        with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("93.184.216.34", 0)),  # pubblico
                (2, 1, 6, "", ("192.168.1.1", 0)),  # privato
            ]
            ok, err, ips = resolve_and_validate_url("https://evil.example.com")
            assert ok is False
            assert ips == []

    def test_url_con_schema_non_valido(self):
        """Schema non consentito → errore, lista IP vuota."""
        ok, err, ips = resolve_and_validate_url("file:///etc/passwd")
        assert ok is False
        assert ips == []

    def test_url_con_credenziali_embedded(self):
        """URL con credenziali → errore, lista IP vuota."""
        ok, err, ips = resolve_and_validate_url("https://user:pass@example.com")
        assert ok is False
        assert ips == []

    def test_validate_public_url_backward_compat(self):
        """validate_public_url continua a restituire (bool, Optional[str])."""
        with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
            result = validate_public_url("https://example.com")
            # Deve essere una tupla di 2 elementi, non 3
            assert len(result) == 2
            ok, err = result
            assert ok is True
            assert err is None


# ============================================================================
# #94/#73 — SSRF via HTTP Redirect
# ============================================================================


class TestRedirectSsrfProtection:
    """fetch_url segue redirect manualmente e rivalida ogni hop."""

    @patch("geo_optimizer.utils.validators.socket.getaddrinfo")
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_redirect_verso_ip_privato_bloccato(self, mock_create, mock_dns):
        """Redirect verso IP privato viene bloccato prima della connessione."""
        mock_session = MagicMock()

        redirect_response = Mock()
        redirect_response.status_code = 301
        redirect_response.headers = {"Location": "http://internal.corp/secret"}
        redirect_response.close = Mock()

        mock_session.get.return_value = redirect_response
        mock_create.return_value = mock_session

        def dns_side_effect(host, port, *args, **kwargs):
            if host == "example.com":
                return [(2, 1, 6, "", ("93.184.216.34", 0))]
            elif host == "internal.corp":
                return [(2, 1, 6, "", ("192.168.1.50", 0))]
            return [(2, 1, 6, "", ("8.8.8.8", 0))]

        mock_dns.side_effect = dns_side_effect

        resp, err = fetch_url("https://example.com/page")
        assert resp is None
        assert err is not None
        assert "unsafe" in err.lower() or "non-public" in err.lower()

    @patch("geo_optimizer.utils.validators.socket.getaddrinfo")
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_redirect_verso_localhost_bloccato(self, mock_create, mock_dns):
        """Redirect verso localhost viene bloccato."""
        mock_session = MagicMock()

        redirect_response = Mock()
        redirect_response.status_code = 302
        redirect_response.headers = {"Location": "http://localhost/admin"}
        redirect_response.close = Mock()

        mock_session.get.return_value = redirect_response
        mock_create.return_value = mock_session

        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]

        resp, err = fetch_url("https://example.com/page")
        assert resp is None
        assert err is not None
        # localhost è bloccato per hostname, non per IP
        assert "unsafe" in err.lower() or "not allowed" in err.lower()

    @patch("geo_optimizer.utils.validators.socket.getaddrinfo")
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_redirect_pubblico_accettato(self, mock_create, mock_dns):
        """Redirect verso URL pubblica viene seguito normalmente."""
        mock_session = MagicMock()

        redirect_response = Mock()
        redirect_response.status_code = 301
        redirect_response.headers = {"Location": "https://www.example.com/new-page"}
        redirect_response.close = Mock()

        final_response = Mock()
        final_response.status_code = 200
        final_response.headers = {}
        final_response._content = b"Hello World"
        final_response._content_consumed = False

        mock_session.get.side_effect = [redirect_response, final_response]
        mock_create.return_value = mock_session

        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]

        resp, err = fetch_url("https://example.com/page")
        assert resp is not None
        assert err is None

    @patch("geo_optimizer.utils.validators.socket.getaddrinfo")
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_troppi_redirect_bloccati(self, mock_create, mock_dns):
        """Loop di redirect supera il limite e viene bloccato."""
        mock_session = MagicMock()

        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]

        def make_redirect(n):
            r = Mock()
            r.status_code = 302
            r.headers = {"Location": f"https://example.com/page-{n}"}
            r.close = Mock()
            return r

        mock_session.get.side_effect = [make_redirect(i) for i in range(_MAX_REDIRECTS + 2)]
        mock_create.return_value = mock_session

        resp, err = fetch_url("https://example.com/start")
        assert resp is None
        assert err is not None
        assert "redirect" in err.lower()

    @patch("geo_optimizer.utils.validators.socket.getaddrinfo")
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_redirect_senza_location_bloccato(self, mock_create, mock_dns):
        """Redirect senza Location header viene bloccato."""
        mock_session = MagicMock()

        redirect_response = Mock()
        redirect_response.status_code = 301
        redirect_response.headers = {}  # Nessun Location
        redirect_response.close = Mock()

        mock_session.get.return_value = redirect_response
        mock_create.return_value = mock_session

        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]

        resp, err = fetch_url("https://example.com/page")
        assert resp is None
        assert "Location" in err or "location" in err.lower()

    @patch("geo_optimizer.utils.validators.socket.getaddrinfo")
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_redirect_relativo_risolto_correttamente(self, mock_create, mock_dns):
        """Redirect con path relativo viene risolto rispetto all'host corrente."""
        mock_session = MagicMock()

        redirect_response = Mock()
        redirect_response.status_code = 301
        redirect_response.headers = {"Location": "/new-path"}  # Relativo
        redirect_response.close = Mock()

        final_response = Mock()
        final_response.status_code = 200
        final_response.headers = {}
        final_response._content = b"content"
        final_response._content_consumed = False

        mock_session.get.side_effect = [redirect_response, final_response]
        mock_create.return_value = mock_session

        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]

        resp, err = fetch_url("https://example.com/old-path")
        assert resp is not None
        assert err is None
        # Verifica che la seconda get sia stata chiamata con l'URL corretto
        second_call_url = mock_session.get.call_args_list[1][0][0]
        assert second_call_url == "https://example.com/new-path"


# ============================================================================
# #101 — Body streaming con size check in-progress
# ============================================================================


class TestBodyStreamingSizeCheck:
    """fetch_url usa streaming per verificare il limite di dimensione durante il download."""

    def test_stream_response_entro_limite(self):
        """Body entro il limite viene letto correttamente."""
        mock_resp = Mock()
        mock_resp.iter_content.return_value = [b"Hello", b" ", b"World"]

        content, err = _stream_response(mock_resp, max_size=1024)
        assert content == b"Hello World"
        assert err is None

    def test_stream_response_supera_limite(self):
        """Body che supera il limite interrompe lo streaming."""
        mock_resp = Mock()
        # Chunk da 100 byte ognuno, limite 250 → deve bloccarsi al 3° chunk
        mock_resp.iter_content.return_value = [b"x" * 100, b"x" * 100, b"x" * 100, b"x" * 100]

        content, err = _stream_response(mock_resp, max_size=250)
        assert content is None
        assert err is not None
        assert "too large" in err.lower()

    def test_stream_response_chunk_vuoti_ignorati(self):
        """Chunk vuoti vengono saltati nel conteggio."""
        mock_resp = Mock()
        mock_resp.iter_content.return_value = [b"", b"data", b"", b"more"]

        content, err = _stream_response(mock_resp, max_size=1024)
        assert content == b"datamore"
        assert err is None

    @patch("geo_optimizer.utils.validators.socket.getaddrinfo")
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_fetch_url_usa_streaming(self, mock_create, mock_dns):
        """fetch_url usa stream=True nella chiamata a session.get()."""
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]

        mock_session = MagicMock()
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.headers = {}
        mock_resp._content = b"OK"
        mock_resp._content_consumed = False

        mock_session.get.return_value = mock_resp
        mock_create.return_value = mock_session

        fetch_url("https://example.com")

        # Verifica che stream=True sia stato passato
        call_kwargs = mock_session.get.call_args[1]
        assert call_kwargs.get("stream") is True

    @patch("geo_optimizer.utils.validators.socket.getaddrinfo")
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_content_length_grande_bloccato_prima_dello_stream(self, mock_create, mock_dns):
        """Content-Length > max_size interrompe prima di scaricare il body."""
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]

        mock_session = MagicMock()
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Length": str(MAX_RESPONSE_SIZE + 1)}
        mock_resp.close = Mock()
        mock_resp.iter_content = Mock()  # Non deve essere chiamato

        mock_session.get.return_value = mock_resp
        mock_create.return_value = mock_session

        resp, err = fetch_url("https://example.com", max_size=1024)
        assert resp is None
        assert "too large" in err.lower()
        # iter_content non deve essere stato chiamato (check preventivo)
        mock_resp.iter_content.assert_not_called()

    @patch("geo_optimizer.utils.validators.socket.getaddrinfo")
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_fetch_url_blocca_url_non_sicura(self, mock_create, mock_dns):
        """fetch_url blocca URL con IP privato prima della connessione."""
        mock_dns.return_value = [(2, 1, 6, "", ("192.168.1.1", 0))]

        resp, err = fetch_url("https://evil.example.com")
        assert resp is None
        assert "unsafe" in err.lower() or err is not None
        # La sessione non deve essere stata creata
        mock_create.assert_not_called()


# ============================================================================
# _PinnedIPAdapter — DNS pinning
# ============================================================================


class TestPinnedIPAdapter:
    """_PinnedIPAdapter forza la connessione all'IP pre-risolto."""

    def test_adapter_senza_ip_usa_dns_normale(self):
        """Con lista IP vuota, il comportamento è quello standard."""
        adapter = _PinnedIPAdapter([])
        assert adapter._pinned_ip is None

    def test_adapter_con_ip_imposta_ip_pinnato(self):
        """Con lista IP non vuota, usa il primo IP."""
        adapter = _PinnedIPAdapter(["93.184.216.34", "93.184.216.35"])
        assert adapter._pinned_ip == "93.184.216.34"

    def test_adapter_ipv6_sets_pinned_ip(self):
        """IPv6 address is accepted as pinned IP."""
        adapter = _PinnedIPAdapter(["2606:2800:220:1:248:1893:25c8:1946"])
        assert adapter._pinned_ip == "2606:2800:220:1:248:1893:25c8:1946"
