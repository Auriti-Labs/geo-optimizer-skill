"""
Test per geo_optimizer.utils.http_async.

Verifica fetch_url_async e fetch_urls_async con mock httpx completi.
Zero chiamate HTTP reali — tutto simulato con unittest.mock.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Skip se httpx non disponibile
pytest.importorskip("httpx", reason="httpx non installato (pip install httpx)")

from geo_optimizer.utils.http_async import _MAX_REDIRECTS, fetch_url_async, fetch_urls_async
from geo_optimizer.utils.http import MAX_RESPONSE_SIZE


# ─── Helper: risposta httpx mock ─────────────────────────────────────────────


def _mock_response(status_code: int = 200, content: bytes = b"<html>ok</html>", headers: dict | None = None) -> MagicMock:
    """Costruisce un mock di httpx.Response con i campi necessari."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    resp.text = content.decode("utf-8", errors="replace")
    resp.headers = headers or {}
    return resp


# ─── Test: fetch_url_async — happy path ──────────────────────────────────────


def test_fetch_url_async_happy_path_restituisce_risposta_e_none():
    """fetch_url_async con URL pubblico e risposta 200 restituisce (response, None)."""
    # Arrange
    mock_resp = _mock_response(200, b"<html>Ciao</html>")

    async def _run():
        with patch("geo_optimizer.utils.validators.validate_public_url", return_value=(True, None)):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client.get = AsyncMock(return_value=mock_resp)
                mock_client._transport = MagicMock()  # impedisce la creazione di un nuovo client
                mock_client_cls.return_value = mock_client
                mock_client.aclose = AsyncMock()

                resp, err = await fetch_url_async("https://example.com", client=mock_client)

        return resp, err

    resp, err = asyncio.run(_run())

    # Assert
    assert err is None
    assert resp is mock_resp


def test_fetch_url_async_happy_path_proprio_client_creato():
    """fetch_url_async senza client esterno crea il proprio httpx.AsyncClient."""
    # Arrange
    mock_resp = _mock_response(200, b"<html>Ok</html>")

    async def _run():
        with patch("geo_optimizer.utils.validators.validate_public_url", return_value=(True, None)):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_inst = AsyncMock()
                mock_client_inst.get = AsyncMock(return_value=mock_resp)
                mock_client_inst.aclose = AsyncMock()
                # Attributo mancante: forza la creazione di un nuovo client
                del mock_client_inst._transport
                mock_client_cls.return_value = mock_client_inst

                resp, err = await fetch_url_async("https://example.com")

        return resp, err

    resp, err = asyncio.run(_run())

    # Assert
    assert err is None
    assert resp is mock_resp


# ─── Test: SSRF — URL iniziale non sicuro ─────────────────────────────────────


def test_fetch_url_async_url_privato_restituisce_errore():
    """fetch_url_async blocca URL verso IP privati prima del fetch."""
    # Arrange / Act
    resp, err = asyncio.run(fetch_url_async("http://192.168.1.1"))

    # Assert
    assert resp is None
    assert err is not None
    assert "Unsafe URL" in err


# ─── Test: redirect verso IP privato (SSRF su redirect) ──────────────────────


def test_fetch_url_async_redirect_verso_ip_privato_restituisce_errore():
    """fetch_url_async blocca redirect che puntano verso reti interne (anti-SSRF)."""
    # Arrange
    redirect_resp = _mock_response(
        status_code=301,
        headers={"location": "http://10.0.0.1/secret"},
    )

    async def _run():
        # Prima validazione: URL pubblico ok
        # Seconda validazione (redirect target): non sicuro
        validate_results = [(True, None), (False, "Private IP")]
        call_count = 0

        def _validate(url):
            nonlocal call_count
            result = validate_results[min(call_count, len(validate_results) - 1)]
            call_count += 1
            return result

        with patch("geo_optimizer.utils.validators.validate_public_url", side_effect=_validate):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_inst = AsyncMock()
                mock_client_inst.get = AsyncMock(return_value=redirect_resp)
                mock_client_inst.aclose = AsyncMock()
                mock_client_cls.return_value = mock_client_inst

                resp, err = await fetch_url_async("https://example.com")

        return resp, err

    resp, err = asyncio.run(_run())

    # Assert
    assert resp is None
    assert err is not None
    assert "unsafe" in err.lower() or "Redirect" in err


# ─── Test: troppi redirect ────────────────────────────────────────────────────


def test_fetch_url_async_troppi_redirect_restituisce_errore():
    """fetch_url_async restituisce errore dopo il numero massimo di redirect."""
    # Arrange: ogni risposta è un redirect valido verso se stesso
    redirect_resp = _mock_response(
        status_code=302,
        headers={"location": "https://example.com/next"},
    )

    async def _run():
        with patch("geo_optimizer.utils.validators.validate_public_url", return_value=(True, None)):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_inst = AsyncMock()
                # Restituisce sempre redirect — forza il superamento del limite
                mock_client_inst.get = AsyncMock(return_value=redirect_resp)
                mock_client_inst.aclose = AsyncMock()
                mock_client_cls.return_value = mock_client_inst

                resp, err = await fetch_url_async("https://example.com")

        return resp, err

    resp, err = asyncio.run(_run())

    # Assert
    assert resp is None
    assert err is not None
    assert str(_MAX_REDIRECTS) in err


# ─── Test: redirect senza Location header ─────────────────────────────────────


def test_fetch_url_async_redirect_senza_location_restituisce_errore():
    """fetch_url_async gestisce redirect senza header Location."""
    # Arrange
    redirect_resp = _mock_response(status_code=301, headers={})

    async def _run():
        with patch("geo_optimizer.utils.validators.validate_public_url", return_value=(True, None)):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_inst = AsyncMock()
                mock_client_inst.get = AsyncMock(return_value=redirect_resp)
                mock_client_inst.aclose = AsyncMock()
                mock_client_cls.return_value = mock_client_inst

                resp, err = await fetch_url_async("https://example.com")

        return resp, err

    resp, err = asyncio.run(_run())

    # Assert
    assert resp is None
    assert err is not None
    assert "Location" in err or "location" in err.lower()


# ─── Test: TimeoutException ───────────────────────────────────────────────────


def test_fetch_url_async_timeout_restituisce_errore_con_secondi():
    """fetch_url_async gestisce httpx.TimeoutException e include i secondi."""
    import httpx

    async def _run():
        with patch("geo_optimizer.utils.validators.validate_public_url", return_value=(True, None)):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_inst = AsyncMock()
                mock_client_inst.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
                mock_client_inst.aclose = AsyncMock()
                mock_client_cls.return_value = mock_client_inst

                resp, err = await fetch_url_async("https://example.com", timeout=10)

        return resp, err

    resp, err = asyncio.run(_run())

    # Assert
    assert resp is None
    assert err is not None
    assert "10s" in err or "Timeout" in err


# ─── Test: ConnectError ───────────────────────────────────────────────────────


def test_fetch_url_async_connect_error_restituisce_errore():
    """fetch_url_async gestisce httpx.ConnectError."""
    import httpx

    async def _run():
        with patch("geo_optimizer.utils.validators.validate_public_url", return_value=(True, None)):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_inst = AsyncMock()
                mock_client_inst.get = AsyncMock(
                    side_effect=httpx.ConnectError("Connection refused")
                )
                mock_client_inst.aclose = AsyncMock()
                mock_client_cls.return_value = mock_client_inst

                resp, err = await fetch_url_async("https://example.com")

        return resp, err

    resp, err = asyncio.run(_run())

    # Assert
    assert resp is None
    assert err is not None
    assert "Connection" in err or "connect" in err.lower()


# ─── Test: risposta troppo grande (body) ──────────────────────────────────────


def test_fetch_url_async_risposta_troppo_grande_restituisce_errore():
    """fetch_url_async rifiuta risposte con body superiore a max_size."""
    # Arrange: content > max_size
    corpo_enorme = b"x" * (MAX_RESPONSE_SIZE + 1)
    mock_resp = _mock_response(200, corpo_enorme)

    async def _run():
        with patch("geo_optimizer.utils.validators.validate_public_url", return_value=(True, None)):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_inst = AsyncMock()
                mock_client_inst.get = AsyncMock(return_value=mock_resp)
                mock_client_inst.aclose = AsyncMock()
                mock_client_cls.return_value = mock_client_inst

                resp, err = await fetch_url_async("https://example.com")

        return resp, err

    resp, err = asyncio.run(_run())

    # Assert
    assert resp is None
    assert err is not None
    assert "too large" in err.lower() or "large" in err.lower()


# ─── Test: risposta troppo grande (Content-Length header) ─────────────────────


def test_fetch_url_async_content_length_troppo_grande_restituisce_errore():
    """fetch_url_async rifiuta risposte con Content-Length > max_size."""
    # Arrange: content piccolo ma Content-Length dichiarato enorme
    mock_resp = _mock_response(
        200,
        b"piccolo",
        headers={"content-length": str(MAX_RESPONSE_SIZE + 1)},
    )

    async def _run():
        with patch("geo_optimizer.utils.validators.validate_public_url", return_value=(True, None)):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_inst = AsyncMock()
                mock_client_inst.get = AsyncMock(return_value=mock_resp)
                mock_client_inst.aclose = AsyncMock()
                mock_client_cls.return_value = mock_client_inst

                resp, err = await fetch_url_async("https://example.com")

        return resp, err

    resp, err = asyncio.run(_run())

    # Assert
    assert resp is None
    assert err is not None
    assert "too large" in err.lower() or "large" in err.lower()


# ─── Test: fetch_urls_async — mix successo/fallimento ─────────────────────────


def test_fetch_urls_async_mix_successo_e_fallimento():
    """fetch_urls_async gestisce correttamente URL che riescono e URL che falliscono."""
    # Arrange
    mock_resp_ok = _mock_response(200, b"<html>Ok</html>")

    # URL di test
    url_ok = "https://example.com"
    url_privato = "http://127.0.0.1"

    async def _run():
        # validate_public_url: ok per example.com, fallisce per 127.0.0.1
        def _validate(url):
            if "127.0.0.1" in url:
                return False, "Private IP"
            return True, None

        with patch("geo_optimizer.utils.validators.validate_public_url", side_effect=_validate):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_inst = AsyncMock()
                mock_client_inst.get = AsyncMock(return_value=mock_resp_ok)
                mock_client_inst.aclose = AsyncMock()
                # Supporta context manager
                mock_client_inst.__aenter__ = AsyncMock(return_value=mock_client_inst)
                mock_client_inst.__aexit__ = AsyncMock(return_value=None)
                mock_client_cls.return_value = mock_client_inst

                results = await fetch_urls_async([url_ok, url_privato])

        return results

    results = asyncio.run(_run())

    # Assert
    assert url_ok in results
    assert url_privato in results

    # URL pubblico: successo
    resp_ok, err_ok = results[url_ok]
    assert err_ok is None
    assert resp_ok is not None

    # URL privato: fallimento per SSRF
    resp_fail, err_fail = results[url_privato]
    assert resp_fail is None
    assert err_fail is not None
    assert "Unsafe URL" in err_fail


def test_fetch_urls_async_lista_vuota_restituisce_dict_vuoto():
    """fetch_urls_async con lista vuota restituisce dizionario vuoto."""
    async def _run():
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_inst = AsyncMock()
            mock_client_inst.__aenter__ = AsyncMock(return_value=mock_client_inst)
            mock_client_inst.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client_inst

            return await fetch_urls_async([])

    results = asyncio.run(_run())

    # Assert
    assert results == {}
