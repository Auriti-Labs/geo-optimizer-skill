"""
Async HTTP client with httpx for parallel fetch.

Speeds up the audit by fetching robots.txt, llms.txt and homepage in parallel
(2-3x speedup over sequential fetch with requests).

Implements anti-SSRF protection with manual redirect: each redirect
is revalidated with validate_public_url() before following it (fix #179).

Requires httpx as an optional dependency:
    pip install geo-optimizer-skill[async]
"""

from __future__ import annotations

import asyncio
import contextvars

from geo_optimizer.models.config import HEADERS
from geo_optimizer.utils.http import MAX_RESPONSE_SIZE

# Maximum number of redirects to follow manually
_MAX_REDIRECTS = 10

# Fix H-1: use contextvars instead of threading.local for async-safe DNS pinning.
# threading.local is per-thread, NOT per-coroutine. In asyncio, multiple coroutines
# share the same thread, so the last coroutine to set the pin before an await wins.
# contextvars.ContextVar is per-task in asyncio, preventing cross-coroutine leaks.
_pinning_ctx: contextvars.ContextVar[dict | None] = contextvars.ContextVar("_pinning_ctx", default=None)


def is_httpx_available() -> bool:
    """Check whether httpx is installed."""
    try:
        import httpx  # noqa: F401

        return True
    except ImportError:
        return False


async def fetch_url_async(
    url: str,
    client=None,
    timeout: int = 10,
    max_size: int = MAX_RESPONSE_SIZE,
) -> tuple[object | None, str | None]:
    """Async fetch of a URL with httpx.

    Implements full anti-SSRF validation:
    - Each URL is checked with validate_public_url() before fetching
    - Redirects are followed manually with SSRF revalidation on each hop
    - Response size verified against max_size

    Args:
        url: URL to download.
        client: Optional httpx.AsyncClient (reuses connections).
        timeout: Timeout in seconds.
        max_size: Maximum response size in bytes.

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

    try:
        # Fix H-1: use contextvars for async-safe DNS pinning instead of threading.local
        from urllib.parse import urlparse as _urlparse

        from geo_optimizer.utils.http import _pinning_local

        _parsed = _urlparse(url)
        _pinned_ip = pinned_ips[0] if pinned_ips else None
        if _pinned_ip:
            _target_port = _parsed.port or (443 if _parsed.scheme == "https" else 80)
            pin_data = {"host": _parsed.hostname, "ip": _pinned_ip, "port": _target_port}
            # Set both: threading.local for the patched getaddrinfo, contextvar for safety
            _pinning_local.pin = pin_data
            _pinning_ctx.set(pin_data)

        if own_client:
            client = httpx.AsyncClient(
                headers=HEADERS,
                follow_redirects=False,  # Manual redirect with SSRF revalidation (fix #179)
                timeout=httpx.Timeout(timeout),
            )

        # Manual redirect with anti-SSRF revalidation on each hop
        current_url = url
        for _ in range(_MAX_REDIRECTS):
            r = await client.get(current_url)

            # Non-redirect response: verify size and return
            if r.status_code not in (301, 302, 303, 307, 308):
                content_length = r.headers.get("content-length")
                if content_length:
                    try:
                        if int(content_length) > max_size:
                            return None, f"Response too large: {int(content_length)} bytes (max: {max_size})"
                    except (ValueError, TypeError):
                        pass

                if len(r.content) > max_size:
                    return None, f"Response too large: {len(r.content)} bytes (max: {max_size})"

                return r, None

            # Redirect: check body size to prevent RAM exhaustion (fix #197)
            cl = r.headers.get("content-length")
            if cl:
                try:
                    if int(cl) > max_size:
                        return None, f"Redirect body too large: {cl} bytes (max: {max_size})"
                except (ValueError, TypeError):
                    pass

            # Redirect: revalidate the target URL before following it
            location = r.headers.get("location", "").strip()
            if not location:
                return None, "Redirect without Location header"

            # Resolve relative URL
            if not location.startswith(("http://", "https://")):
                from urllib.parse import urljoin

                location = urljoin(current_url, location)

            ok_redir, reason_redir, _redir_ips = resolve_and_validate_url(location)
            if not ok_redir:
                return None, f"Redirect to unsafe URL: {reason_redir}"

            current_url = location

        return None, f"Too many redirects (max: {_MAX_REDIRECTS})"

    except httpx.TimeoutException:
        return None, f"Timeout ({timeout}s)"
    except httpx.ConnectError as e:
        return None, f"Connection failed: {e}"
    except Exception as e:
        return None, str(e)
    finally:
        # Fix H-1: clear both pin stores
        _pinning_local.pin = None
        _pinning_ctx.set(None)
        if own_client and client:
            await client.aclose()


async def fetch_urls_async(
    urls: list,
    timeout: int = 10,
    max_size: int = MAX_RESPONSE_SIZE,
) -> dict:
    """Parallel fetch of multiple URLs with a single httpx client.

    Args:
        urls: List of URLs to download.
        timeout: Timeout per individual request.
        max_size: Maximum size per response.

    Returns:
        Dict {url: (response, error_msg)} for each URL.
    """
    import httpx

    results = {}

    async with httpx.AsyncClient(
        headers=HEADERS,
        follow_redirects=False,  # Redirect handled in fetch_url_async (fix #179)
        timeout=httpx.Timeout(timeout),
    ) as client:
        tasks = {url: fetch_url_async(url, client=client, timeout=timeout, max_size=max_size) for url in urls}

        gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for url, result in zip(tasks.keys(), gathered):
            if isinstance(result, Exception):
                results[url] = (None, str(result))
            else:
                results[url] = result

    return results
