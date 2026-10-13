"""
Test per geo_optimizer.utils.http_async.

Verifica fetch_url_async e fetch_urls_async con un vero httpx.AsyncClient
collegato a httpx.MockTransport, e il network backend con DNS pinning tramite
httpcore.AsyncMockBackend. Zero chiamate HTTP reali e nessun socket aperto.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch
from urllib.parse import urlparse

import pytest

# Skip se httpx non disponibile
httpx = pytest.importorskip("httpx", reason="httpx non installato (pip install httpx)")
httpcore = pytest.importorskip("httpcore", reason="httpcore non installato")

from geo_optimizer.utils import http_async  # noqa: E402
from geo_optimizer.utils.http import MAX_RESPONSE_SIZE  # noqa: E402
from geo_optimizer.utils.http_async import _MAX_REDIRECTS, fetch_url_async, fetch_urls_async  # noqa: E402

_PUBLIC_IP = "93.184.216.34"


@pytest.fixture(autouse=True)
def _mock_async_url_validation(monkeypatch):
    """Rende deterministica la validazione URL nei test async offline."""

    def _fake_resolve(url):
        host = (urlparse(url).hostname or "").lower()
        if host in {"localhost", "192.168.1.1", "10.0.0.1", "127.0.0.1"}:
            return False, "blocked for test", []
        return True, None, [_PUBLIC_IP]

    def _fake_validate(url):
        ok, reason, _ips = _fake_resolve(url)
        return ok, reason

    monkeypatch.setattr("geo_optimizer.utils.validators.resolve_and_validate_url", _fake_resolve)
    monkeypatch.setattr("geo_optimizer.utils.validators.validate_public_url", _fake_validate)


# ─── Helper ──────────────────────────────────────────────────────────────────


def _client(handler) -> httpx.AsyncClient:
    """Vero AsyncClient con trasporto simulato: ``handler(request) -> httpx.Response``."""
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)


def _own_client(handler):
    """Sostituisce il client che fetch_url_async/fetch_urls_async creano da soli."""
    return patch.object(http_async, "_create_pinned_client", side_effect=lambda timeout: _client(handler))


class _ChunkStream(httpx.AsyncByteStream):
    """Body in streaming che conta quanti chunk sono stati effettivamente consumati."""

    def __init__(self, chunk: bytes, count: int):
        self.chunk = chunk
        self.count = count
        self.consumed = 0

    async def __aiter__(self):
        for _ in range(self.count):
            self.consumed += 1
            yield self.chunk


# ─── Test: fetch_url_async — happy path ──────────────────────────────────────


def test_fetch_url_async_happy_path_restituisce_risposta_e_none():
    """fetch_url_async con URL pubblico e risposta 200 restituisce (response, None)."""

    async def _run():
        async with _client(lambda request: httpx.Response(200, content=b"<html>Ciao</html>")) as client:
            return await fetch_url_async("https://example.com", client=client)

    resp, err = asyncio.run(_run())

    assert err is None
    assert resp.status_code == 200
    assert resp.content == b"<html>Ciao</html>"
    assert resp.text == "<html>Ciao</html>"


def test_fetch_url_async_happy_path_proprio_client_creato():
    """fetch_url_async senza client esterno crea il proprio client e lo chiude."""
    with _own_client(lambda request: httpx.Response(200, content=b"<html>Ok</html>")) as factory:
        resp, err = asyncio.run(fetch_url_async("https://example.com"))

    assert err is None
    assert resp.content == b"<html>Ok</html>"
    factory.assert_called_once()


# ─── Test: SSRF — URL iniziale non sicuro ─────────────────────────────────────


def test_fetch_url_async_url_privato_restituisce_errore():
    """fetch_url_async blocca URL verso IP privati prima del fetch."""
    resp, err = asyncio.run(fetch_url_async("http://192.168.1.1"))

    assert resp is None
    assert "Unsafe URL" in err


def test_fetch_url_async_passa_headers_a_ogni_hop_di_redirect():
    seen: list[tuple[str, str | None]] = []

    def handler(request):
        seen.append((request.url.path, request.headers.get("accept")))
        if request.url.path == "/start":
            return httpx.Response(301, headers={"location": "/next"})
        return httpx.Response(200, content=b"ok")

    async def _run():
        async with _client(handler) as client:
            return await fetch_url_async(
                "https://example.com/start", client=client, headers={"Accept": "text/markdown"}
            )

    response, error = asyncio.run(_run())

    assert error is None
    assert response.content == b"ok"
    assert seen == [("/start", "text/markdown"), ("/next", "text/markdown")]


def test_fetch_url_async_url_non_sicuro_senza_client_non_esegue_richieste():
    with patch.object(http_async, "_create_pinned_client") as factory:
        response, error = asyncio.run(fetch_url_async("http://127.0.0.1/"))

    assert response is None
    assert "Unsafe URL" in error
    factory.assert_not_called()


# ─── Test: redirect ──────────────────────────────────────────────────────────


def test_fetch_url_async_redirect_verso_ip_privato_restituisce_errore():
    """fetch_url_async blocca redirect che puntano verso reti interne (anti-SSRF)."""
    requested: list[str] = []

    def handler(request):
        requested.append(str(request.url))
        return httpx.Response(301, headers={"location": "http://10.0.0.1/secret"})

    with _own_client(handler):
        resp, err = asyncio.run(fetch_url_async("https://example.com"))

    assert resp is None
    assert "Redirect to unsafe URL" in err
    assert requested == ["https://example.com"]  # il target interno non viene mai richiesto


def test_fetch_url_async_troppi_redirect_restituisce_errore():
    """fetch_url_async restituisce errore dopo il numero massimo di redirect."""
    with _own_client(lambda request: httpx.Response(302, headers={"location": "https://example.com/next"})):
        resp, err = asyncio.run(fetch_url_async("https://example.com"))

    assert resp is None
    assert str(_MAX_REDIRECTS) in err


def test_fetch_url_async_redirect_senza_location_restituisce_errore():
    """fetch_url_async gestisce redirect senza header Location."""
    with _own_client(lambda request: httpx.Response(301)):
        resp, err = asyncio.run(fetch_url_async("https://example.com"))

    assert resp is None
    assert "Location" in err


def test_fetch_url_async_redirect_body_non_viene_letto():
    """Il body di un 3xx non viene mai scaricato, nemmeno se enorme (fix #197)."""
    body = _ChunkStream(b"x" * 1024, count=100_000)

    def handler(request):
        if request.url.path == "/":
            return httpx.Response(302, headers={"location": "/dest"}, stream=body)
        return httpx.Response(200, content=b"ok")

    with _own_client(handler):
        resp, err = asyncio.run(fetch_url_async("https://example.com/"))

    assert err is None
    assert resp.content == b"ok"
    assert body.consumed == 0


def test_fetch_url_async_redirect_protocol_relative_cambia_host():
    requested: list[str] = []

    def handler(request):
        requested.append(str(request.url))
        if request.url.host == "example.com":
            return httpx.Response(301, headers={"location": "//other.example.org/b"})
        return httpx.Response(200, content=b"ok")

    with _own_client(handler):
        resp, err = asyncio.run(fetch_url_async("https://example.com/a"))

    assert err is None
    assert requested[-1] == "https://other.example.org/b"


# ─── Test: errori di rete ────────────────────────────────────────────────────


def test_fetch_url_async_timeout_restituisce_errore_con_secondi():
    """fetch_url_async gestisce httpx.TimeoutException e include i secondi."""

    def handler(request):
        raise httpx.ReadTimeout("timeout", request=request)

    with _own_client(handler):
        resp, err = asyncio.run(fetch_url_async("https://example.com", timeout=10))

    assert resp is None
    assert err == "Timeout (10s)"


def test_fetch_url_async_connect_error_restituisce_errore():
    """fetch_url_async gestisce httpx.ConnectError."""

    def handler(request):
        raise httpx.ConnectError("Connection refused", request=request)

    with _own_client(handler):
        resp, err = asyncio.run(fetch_url_async("https://example.com"))

    assert resp is None
    assert err == "Connection failed"


# ─── Test: limite di dimensione ──────────────────────────────────────────────


def test_fetch_url_async_risposta_troppo_grande_restituisce_errore():
    """fetch_url_async rifiuta risposte con body superiore a max_size."""
    with _own_client(lambda request: httpx.Response(200, content=b"x" * (MAX_RESPONSE_SIZE + 1))):
        resp, err = asyncio.run(fetch_url_async("https://example.com"))

    assert resp is None
    assert "too large" in err.lower()


def test_fetch_url_async_body_in_streaming_si_ferma_al_limite():
    """Senza Content-Length il body si legge a chunk e la lettura si ferma oltre max_size."""
    body = _ChunkStream(b"x" * 1024, count=10_000)  # ~10 MB disponibili
    max_size = 8 * 1024

    with _own_client(lambda request: httpx.Response(200, stream=body)):
        resp, err = asyncio.run(fetch_url_async("https://example.com", max_size=max_size))

    assert resp is None
    assert "too large" in err.lower()
    # 8 chunk entro il limite + quello che lo supera: il resto non viene mai scaricato
    assert body.consumed == 9


def test_fetch_url_async_content_length_troppo_grande_restituisce_errore():
    """fetch_url_async rifiuta risposte con Content-Length > max_size senza leggere il body."""
    body = _ChunkStream(b"x", count=10)

    with _own_client(
        lambda request: httpx.Response(200, headers={"content-length": str(MAX_RESPONSE_SIZE + 1)}, stream=body)
    ):
        resp, err = asyncio.run(fetch_url_async("https://example.com"))

    assert resp is None
    assert "too large" in err.lower()
    assert body.consumed == 0


# ─── Test: fetch_urls_async ──────────────────────────────────────────────────


def test_fetch_urls_async_mix_successo_e_fallimento():
    """fetch_urls_async gestisce correttamente URL che riescono e URL che falliscono."""
    url_ok = "https://example.com"
    url_privato = "http://127.0.0.1"

    with _own_client(lambda request: httpx.Response(200, content=b"<html>Ok</html>")):
        results = asyncio.run(fetch_urls_async([url_ok, url_privato]))

    resp_ok, err_ok = results[url_ok]
    assert err_ok is None
    assert resp_ok.content == b"<html>Ok</html>"

    resp_fail, err_fail = results[url_privato]
    assert resp_fail is None
    assert "Unsafe URL" in err_fail


def test_fetch_urls_async_lista_vuota_restituisce_dict_vuoto():
    """fetch_urls_async con lista vuota restituisce dizionario vuoto."""
    with _own_client(lambda request: httpx.Response(200)):
        results = asyncio.run(fetch_urls_async([]))

    assert results == {}


# ─── Test: DNS pinning (network backend) ─────────────────────────────────────


class _RecordingBackend(httpcore.AsyncMockBackend):
    """Backend httpcore simulato che registra host di connessione e SNI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connected_to: list[tuple[str, int]] = []
        self.sni: list[str | None] = []

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        self.connected_to.append((host, port))
        stream = await super().connect_tcp(host, port, timeout, local_address, socket_options)
        backend = self

        class _Stream(type(stream)):
            async def start_tls(self, ssl_context, server_hostname=None, timeout=None):
                backend.sni.append(server_hostname)
                return self

        stream.__class__ = _Stream
        return stream


_OK_RESPONSE = [b"HTTP/1.1 200 OK\r\n", b"Content-Length: 2\r\n", b"\r\n", b"ok"]


def _pinned_test_client(inner: httpcore.AsyncNetworkBackend) -> httpx.AsyncClient:
    """Client con lo stesso backend di _create_pinned_client, sopra un backend simulato."""
    transport = httpx.AsyncHTTPTransport()
    transport._pool._network_backend = http_async._get_pinned_backend_cls()(inner)
    return httpx.AsyncClient(transport=transport, follow_redirects=False)


def test_pinned_backend_connette_all_ip_validato_e_usa_hostname_per_tls():
    inner = _RecordingBackend(list(_OK_RESPONSE))

    async def _run():
        async with _pinned_test_client(inner) as client:
            return await fetch_url_async("https://pinned-host.example/", client=client)

    resp, err = asyncio.run(_run())

    assert err is None
    assert resp.content == b"ok"
    # TCP verso l'IP validato, non verso una nuova risoluzione DNS dell'host
    assert inner.connected_to == [(_PUBLIC_IP, 443)]
    # SNI e verifica del certificato restano legati al nome host
    assert inner.sni == ["pinned-host.example"]


def test_pinned_backend_rifiuta_host_non_validato():
    """Fail closed: senza un IP validato per l'host la connessione non parte."""
    inner = _RecordingBackend(list(_OK_RESPONSE))

    async def _run():
        async with _pinned_test_client(inner) as client:
            with pytest.raises(httpx.ConnectError, match="No validated IP"):
                await client.get("https://never-validated.example/")

    asyncio.run(_run())

    assert inner.connected_to == []


def test_pinned_backend_rifiuta_unix_socket():
    backend = http_async._get_pinned_backend_cls()(_RecordingBackend([]))

    with pytest.raises(httpcore.ConnectError):
        asyncio.run(backend.connect_unix_socket("/var/run/docker.sock"))


def test_pinned_backend_pin_isolati_tra_task_concorrenti():
    """Con asyncio.gather ogni task usa solo il proprio pin, anche con un client condiviso."""
    ips = {"a.example": "93.184.216.10", "b.example": "93.184.216.20"}

    def _resolve(url):
        return True, None, [ips[urlparse(url).hostname]]

    inner = _RecordingBackend([*_OK_RESPONSE, *_OK_RESPONSE])

    async def _run():
        async with _pinned_test_client(inner) as client:
            return await asyncio.gather(
                fetch_url_async("http://a.example/", client=client),
                fetch_url_async("http://b.example/", client=client),
            )

    with patch("geo_optimizer.utils.validators.resolve_and_validate_url", side_effect=_resolve):
        results = asyncio.run(_run())

    assert all(err is None for _resp, err in results)
    assert sorted(inner.connected_to) == [("93.184.216.10", 80), ("93.184.216.20", 80)]


def test_pin_ripristinato_dopo_la_chiamata():
    asyncio.run(fetch_url_async("http://192.168.1.1/"))  # esce subito: URL non sicuro

    with _own_client(lambda request: httpx.Response(200, content=b"ok")):
        asyncio.run(fetch_url_async("https://example.com/"))

    assert dict(http_async._pinned_hosts.get()) == {}


def test_create_pinned_client_installa_il_backend(monkeypatch):
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.delenv(var, raising=False)

    async def _run():
        client = http_async._create_pinned_client(5)
        try:
            return client._transport._pool._network_backend
        finally:
            await client.aclose()

    backend = asyncio.run(_run())

    # Se un aggiornamento di httpx cambia la struttura interna, questo test fallisce in CI
    assert isinstance(backend, http_async._get_pinned_backend_cls())


_PROXY_VARS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
)


def _clear_proxy_env(monkeypatch):
    for var in _PROXY_VARS:
        monkeypatch.delenv(var, raising=False)


def test_create_pinned_client_con_proxy_mantiene_il_proxy(monkeypatch):
    """Con HTTPS_PROXY il mount https:// passa dal proxy e il pool del proxy non viene toccato."""
    _clear_proxy_env(monkeypatch)
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.internal:3128")

    async def _run():
        client = http_async._create_pinned_client(5)
        try:
            proxied = [t for t in client._mounts.values() if t is not None]
            return client._transport._pool, [t._pool for t in proxied]
        finally:
            await client.aclose()

    direct_pool, proxy_pools = asyncio.run(_run())

    pinned_cls = http_async._get_pinned_backend_cls()
    assert isinstance(direct_pool._network_backend, pinned_cls)
    assert proxy_pools and all(isinstance(p, httpcore.AsyncHTTPProxy) for p in proxy_pools)
    assert not any(isinstance(p._network_backend, pinned_cls) for p in proxy_pools)


def test_richiesta_diretta_con_proxy_configurato_resta_pinnata(monkeypatch):
    """Solo HTTPS_PROXY: un URL http:// va diretto e deve connettersi all'IP validato."""
    _clear_proxy_env(monkeypatch)
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.internal:3128")
    inner = _RecordingBackend(list(_OK_RESPONSE))

    async def _run():
        client = http_async._create_pinned_client(5)
        client._transport._pool._network_backend._inner = inner  # backend simulato sotto il pin
        async with client:
            return await fetch_url_async("http://rebind.example/", client=client)

    resp, err = asyncio.run(_run())

    assert err is None
    assert inner.connected_to == [(_PUBLIC_IP, 80)]


def test_no_proxy_wildcard_mantiene_il_pinning(monkeypatch):
    _clear_proxy_env(monkeypatch)
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.internal:3128")
    monkeypatch.setenv("NO_PROXY", "*")

    async def _run():
        client = http_async._create_pinned_client(5)
        try:
            return client._transport._pool._network_backend, list(client._mounts.values())
        finally:
            await client.aclose()

    backend, mounts = asyncio.run(_run())

    assert isinstance(backend, http_async._get_pinned_backend_cls())
    assert all(t is None for t in mounts)  # nessun proxy: tutto passa dal transport pinnato


def test_fetch_urls_async_client_non_creabile_restituisce_errori(monkeypatch):
    """Se il pinning non si puo' installare l'audit non cade: ogni URL riporta l'errore."""
    with patch.object(http_async, "_create_pinned_client", side_effect=RuntimeError("layout changed")):
        results = asyncio.run(fetch_urls_async(["https://example.com/a", "https://example.com/b"]))

    assert set(results) == {"https://example.com/a", "https://example.com/b"}
    assert all(resp is None and "DNS pinning" in err for resp, err in results.values())
