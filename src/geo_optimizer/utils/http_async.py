"""
Async HTTP client with httpx for parallel fetch.

Speeds up the audit by fetching robots.txt, llms.txt and homepage in parallel
(2-3x speedup over sequential fetch with requests).

Anti-SSRF protections, aligned with the sync stack in utils/http.py:
- every URL, including each redirect hop, is validated with
  resolve_and_validate_url() before it is requested (fix #179);
- DNS pinning: the TCP connection goes to the IP validated above, never to a
  second DNS answer. The hostname is still used for TLS SNI, certificate
  verification and the Host header;
- the body is streamed with a byte counter and dropped as soon as it exceeds
  max_size; redirect bodies are never read.

Requires httpx as an optional dependency:
    pip install geo-optimizer-skill[async]
"""

from __future__ import annotations

import asyncio
import contextvars
import logging
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any
from urllib.parse import urljoin

from geo_optimizer.models.config import get_headers
from geo_optimizer.utils.http import MAX_RESPONSE_SIZE

_logger = logging.getLogger(__name__)

# Maximum number of redirects to follow manually
_MAX_REDIRECTS = 10

_REDIRECT_STATUSES = (301, 302, 303, 307, 308)

# Host -> IP validati per il task corrente. Una ContextVar e' isolata per task
# asyncio: con asyncio.gather ogni fetch vede solo i propri pin, anche se le
# richieste condividono lo stesso client e lo stesso event loop.
_EMPTY_PINS: Mapping[str, str] = MappingProxyType({})
_pinned_hosts: contextvars.ContextVar[Mapping[str, str]] = contextvars.ContextVar("_pinned_hosts", default=_EMPTY_PINS)

# Classe del network backend creata alla prima richiesta: httpcore e' una
# dipendenza opzionale (extra [async]) e non va importata a livello di modulo.
_pinned_backend_cls: type | None = None


def is_httpx_available() -> bool:
    """Check whether httpx is installed."""
    try:
        import httpx  # noqa: F401

        return True
    except ImportError:
        return False


def _get_pinned_backend_cls() -> type:
    """Restituisce (e crea alla prima chiamata) il network backend con DNS pinning.

    Il backend avvolge quello di default di httpcore e sostituisce l'host con
    l'IP validato al momento di aprire il socket. httpcore passa poi l'hostname
    originale a ``start_tls`` come ``server_hostname``, quindi SNI e verifica
    del certificato restano legati al nome, non all'IP.

    Returns:
        Sottoclasse di ``httpcore.AsyncNetworkBackend``.
    """
    global _pinned_backend_cls
    if _pinned_backend_cls is not None:
        return _pinned_backend_cls

    import httpcore

    class _PinnedNetworkBackend(httpcore.AsyncNetworkBackend):
        """Network backend che apre le connessioni TCP solo verso IP validati."""

        def __init__(self, inner: httpcore.AsyncNetworkBackend) -> None:
            self._inner = inner

        async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
            pinned_ip = _pinned_hosts.get().get(host.lower())
            if pinned_ip is None:
                # Fail closed: un host mai validato non viene risolto via DNS.
                raise httpcore.ConnectError(f"No validated IP for host {host!r}: connection refused (anti-SSRF)")
            return await self._inner.connect_tcp(
                pinned_ip,
                port,
                timeout=timeout,
                local_address=local_address,
                socket_options=socket_options,
            )

        async def connect_unix_socket(self, path, timeout=None, socket_options=None):
            raise httpcore.ConnectError("Unix sockets are not allowed (anti-SSRF)")

        async def sleep(self, seconds: float) -> None:
            await self._inner.sleep(seconds)

    _pinned_backend_cls = _PinnedNetworkBackend
    return _pinned_backend_cls


def _install_pinned_backend(transport) -> bool:
    """Installa il backend con DNS pinning su un transport httpx a connessione diretta.

    Si modifica solo un ``httpcore.AsyncConnectionPool`` esatto: i pool dei proxy
    (``AsyncHTTPProxy`` ne e' una sottoclasse, ``AsyncSOCKSProxy`` no) aprono la
    connessione verso il proxy, che non ha un pin e verrebbe rifiutato.

    Args:
        transport: Transport httpx (``client._transport`` o un valore di ``client._mounts``).

    Returns:
        True se il backend e' stato installato.

    Raises:
        RuntimeError: Se un pool diretto non espone il network backend atteso.
    """
    import httpcore

    pool = getattr(transport, "_pool", None)
    if type(pool) is not httpcore.AsyncConnectionPool:
        return False
    inner_backend = getattr(pool, "_network_backend", None)
    if inner_backend is None:
        raise RuntimeError("httpx transport layout changed: cannot install the DNS-pinning network backend")
    if not isinstance(inner_backend, _get_pinned_backend_cls()):
        pool._network_backend = _get_pinned_backend_cls()(inner_backend)  # noqa: SLF001
    return True


def _create_pinned_client(timeout: float):
    """Crea un httpx.AsyncClient le cui connessioni dirette usano il DNS pinning.

    Il client nasce con le impostazioni di default di httpx, quindi rispetta
    HTTP(S)_PROXY, ALL_PROXY e NO_PROXY come prima. Poi il backend con pinning
    viene installato su ogni pool che si connette direttamente all'host: il
    transport principale e i mount senza proxy. Una richiesta che httpx manda
    direttamente (NO_PROXY, o uno schema senza proxy, es. http:// con il solo
    HTTPS_PROXY) resta quindi legata all'IP validato. Le richieste via proxy no:
    li' il DNS lo risolve il proxy, come per requests nel percorso sincrono.

    httpx non espone un parametro per il network backend: lo si sostituisce nel
    pool di httpcore. Se la struttura interna cambia in una versione futura, la
    funzione solleva un errore invece di creare un client senza pinning.

    Args:
        timeout: Timeout in secondi per connessione e lettura.

    Returns:
        httpx.AsyncClient con redirect manuali e pinning sulle connessioni dirette.

    Raises:
        RuntimeError: Se il transport principale non ha la struttura attesa.
    """
    import httpx

    client = httpx.AsyncClient(
        headers=get_headers(),
        follow_redirects=False,  # Manual redirect with SSRF revalidation (fix #179)
        timeout=httpx.Timeout(timeout),
    )
    # Nessuna connessione e' ancora aperta: se l'installazione fallisce il client
    # viene semplicemente scartato.
    if not _install_pinned_backend(client._transport):  # noqa: SLF001
        raise RuntimeError("httpx default transport is not a direct connection pool: cannot pin DNS")
    for mounted in client._mounts.values():  # noqa: SLF001
        if mounted is not None:
            _install_pinned_backend(mounted)
    return client


def _pin_host(url: str, ips: list[str] | None) -> None:
    """Registra l'IP validato per l'host di ``url`` nel contesto del task corrente.

    Args:
        url: URL appena validato.
        ips: IP restituiti da resolve_and_validate_url() (si usa il primo).
    """
    import httpx

    if not ips:
        return
    # httpcore riceve l'host in forma ASCII (IDNA/punycode, minuscolo): stessa chiave qui.
    host = httpx.URL(url).raw_host.decode("ascii").lower()
    pins = dict(_pinned_hosts.get())
    pins[host] = ips[0]
    _pinned_hosts.set(MappingProxyType(pins))


async def _read_limited(response, max_size: int) -> str | None:
    """Legge il body in streaming fermandosi oltre ``max_size``.

    Il conteggio avviene sui byte decodificati (dopo gzip/br), quindi vale
    anche contro i body compressi che si espandono in memoria.

    Args:
        response: httpx.Response aperta con ``client.stream()``.
        max_size: Limite in byte.

    Returns:
        None se il body e' stato letto, altrimenti il messaggio di errore.
    """
    chunks: list[bytes] = []
    total = 0
    async for chunk in response.aiter_bytes():
        total += len(chunk)
        if total > max_size:
            return f"Response too large: >{max_size} bytes (max: {max_size})"
        chunks.append(chunk)
    # Stesso campo che httpx valorizza in aread(): rende disponibili .content e .text
    response._content = b"".join(chunks)  # noqa: SLF001
    return None


async def fetch_url_async(
    url: str,
    client=None,
    timeout: int = 10,
    max_size: int = MAX_RESPONSE_SIZE,
    headers: dict[str, str] | None = None,
) -> tuple[object | None, str | None]:
    """Async fetch of a URL with httpx.

    Implements full anti-SSRF validation:
    - Each URL is checked with resolve_and_validate_url() before fetching
    - Connections go to the validated IP (DNS pinning) when the client was
      created by this module
    - Redirects are followed manually with SSRF revalidation on each hop
    - The body is streamed and dropped as soon as it exceeds max_size

    Args:
        url: URL to download.
        client: Optional httpx.AsyncClient (reuses connections). Pass a client
            from fetch_urls_async() or _create_pinned_client(): a plain
            httpx.AsyncClient does not apply DNS pinning.
        timeout: Timeout in seconds.
        max_size: Maximum response size in bytes.
        headers: Optional per-request headers.

    Returns:
        Tuple (response, error_msg) — response is None on error.
    """
    from geo_optimizer.utils.validators import resolve_and_validate_url

    # Fix #414: use resolve_and_validate_url for DNS pinning (prevents TOCTOU rebinding)
    ok, reason, pinned_ips = resolve_and_validate_url(url)
    if not ok:
        return None, f"Unsafe URL: {reason}"

    import httpx

    own_client = client is None
    # I pin valgono solo per questa chiamata: il token ripristina lo stato precedente.
    pins_token = _pinned_hosts.set(_pinned_hosts.get())

    try:
        _pin_host(url, pinned_ips)

        if own_client:
            client = _create_pinned_client(timeout)

        current_url = url
        for _ in range(_MAX_REDIRECTS):
            async with client.stream("GET", current_url, headers=headers) as r:
                if r.status_code not in _REDIRECT_STATUSES:
                    content_length = r.headers.get("content-length")
                    if content_length:
                        try:
                            if int(content_length) > max_size:
                                return None, f"Response too large: {int(content_length)} bytes (max: {max_size})"
                        except (ValueError, TypeError):
                            pass

                    error = await _read_limited(r, max_size)
                    if error:
                        return None, error
                    return r, None

                # Redirect: the body is never read (fix #197), only the Location header
                location = r.headers.get("location", "").strip()

            if not location:
                return None, "Redirect without Location header"

            # Resolve relative and protocol-relative locations (RFC 3986)
            location = urljoin(current_url, location)

            ok_redir, reason_redir, redir_ips = resolve_and_validate_url(location)
            if not ok_redir:
                return None, f"Redirect to unsafe URL: {reason_redir}"

            # Pin the revalidated target before the next hop connects (TOCTOU fix)
            _pin_host(location, redir_ips)
            current_url = location

        return None, f"Too many redirects (max: {_MAX_REDIRECTS})"

    except httpx.TimeoutException:
        return None, f"Timeout ({timeout}s)"
    except httpx.ConnectError as e:
        _logger.warning("Async connection failed for %s: %s", url, e)
        return None, "Connection failed"
    except Exception as e:
        _logger.warning("Async fetch unexpected error for %s: %s", url, e)
        return None, "Unexpected error during fetch"
    finally:
        _pinned_hosts.reset(pins_token)
        if own_client and client:
            await client.aclose()


async def fetch_urls_async(
    urls: list[str],
    timeout: int = 10,
    max_size: int = MAX_RESPONSE_SIZE,
) -> dict[str, tuple[Any, str | None]]:
    """Parallel fetch of multiple URLs with a single httpx client.

    Args:
        urls: List of URLs to download.
        timeout: Timeout per individual request.
        max_size: Maximum size per response.

    Returns:
        Dict {url: (response, error_msg)} for each URL.
    """
    results = {}

    try:
        client = _create_pinned_client(timeout)
    except RuntimeError as e:
        # Fail closed ma senza far cadere l'audit: ogni URL riporta l'errore
        _logger.error("Cannot create a DNS-pinned HTTP client: %s", e)
        return dict.fromkeys(urls, (None, "HTTP client unavailable (DNS pinning)"))

    async with client:
        tasks = {url: fetch_url_async(url, client=client, timeout=timeout, max_size=max_size) for url in urls}

        gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for url, result in zip(tasks.keys(), gathered, strict=True):
            if isinstance(result, Exception):
                results[url] = (None, str(result))
            else:
                results[url] = result

    return results
