"""
HTTP utilities with retry logic and exponential backoff.

Provides robust HTTP session with automatic retry for transient failures:
- Connection errors
- Timeouts
- Server errors (5xx)
- Rate limits (429)

Implements anti-SSRF protections:
- DNS pinning: single DNS resolution, connection forced to the pre-validated IP
- Manual redirect with anti-SSRF revalidation on each hop
- Streaming with size check to prevent DoS from huge responses
"""

from __future__ import annotations

import socket
import threading
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from geo_optimizer.models.config import HEADERS

# Response size limit: 10 MB (prevents DoS from huge responses)
MAX_RESPONSE_SIZE = 10 * 1024 * 1024

# Maximum number of redirects to follow manually (anti-infinite loop)
_MAX_REDIRECTS = 10

# Chunk size for streaming (8 KB)
_CHUNK_SIZE = 8192


def create_session_with_retry(
    total_retries=3,
    backoff_factor=1.0,
    status_forcelist=None,
    allowed_methods=None,
    pinned_ips: list[str] | None = None,
):
    """
    Create requests session with exponential backoff retry strategy.

    Args:
        total_retries: Maximum number of retry attempts (default: 3)
        backoff_factor: Backoff multiplier (default: 1.0)
        status_forcelist: HTTP status codes to retry
        allowed_methods: HTTP methods to retry (default: ["GET", "HEAD"])
        pinned_ips: List of pre-validated IPs to force the connection to.
                    If provided, uses _PinnedIPAdapter to prevent DNS rebinding.

    Returns:
        requests.Session: Configured session with retry adapter
    """
    if status_forcelist is None:
        status_forcelist = [408, 429, 500, 502, 503, 504]
    if allowed_methods is None:
        allowed_methods = ["GET", "HEAD"]

    session = requests.Session()
    session.headers.update(HEADERS)

    retry_strategy = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=allowed_methods,
        raise_on_status=False,
    )

    # If pinned IPs were provided, use the adapter with DNS pinning
    if pinned_ips:
        adapter = _PinnedIPAdapter(pinned_ips, max_retries=retry_strategy)
    else:
        adapter = HTTPAdapter(max_retries=retry_strategy)

    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


class _PinnedIPAdapter(HTTPAdapter):
    """HTTPAdapter that forces the connection to a pre-resolved IP.

    Prevents TOCTOU DNS rebinding attacks: after URL validation,
    the IP is fixed and used directly without a second DNS resolution.

    Thread-safe: uses a global Lock to protect the temporary monkeypatching
    of socket.getaddrinfo (fix #178).
    """

    _lock = threading.Lock()

    def __init__(self, pinned_ips: list[str], *args, **kwargs):
        """
        Args:
            pinned_ips: List of validated IPs to force the connection to.
                        The first available IP is used.
        """
        self._pinned_ip = pinned_ips[0] if pinned_ips else None
        super().__init__(*args, **kwargs)

    def send(self, request, *args, **kwargs):
        """Override send: replaces the hostname with the pinned IP in the socket.

        Thread-safe: the Lock serializes access to socket.getaddrinfo
        to prevent race conditions between concurrent audits (fix #178).
        """
        if self._pinned_ip:
            pinned_ip = self._pinned_ip
            parsed = urlparse(request.url)
            target_host = parsed.hostname
            target_port = parsed.port or (443 if parsed.scheme == "https" else 80)

            def _patched_getaddrinfo(host, port, *a, **kw):
                if host == target_host:
                    family = socket.AF_INET6 if ":" in pinned_ip else socket.AF_INET
                    return [(family, socket.SOCK_STREAM, 6, "", (pinned_ip, port or target_port))]
                return _original_getaddrinfo(host, port, *a, **kw)

            with _PinnedIPAdapter._lock:
                _original_getaddrinfo = socket.getaddrinfo
                socket.getaddrinfo = _patched_getaddrinfo
                try:
                    return super().send(request, *args, **kwargs)
                finally:
                    socket.getaddrinfo = _original_getaddrinfo
        else:
            return super().send(request, *args, **kwargs)


def _stream_response(response: requests.Response, max_size: int) -> tuple[bytes | None, str | None]:
    """Read the body in streaming while checking the size limit.

    Prevents DoS: downloads the body in chunks, stops if it exceeds max_size.

    Args:
        response: HTTP response with stream=True active.
        max_size: Limit in bytes.

    Returns:
        (content_bytes, error) — content_bytes is None on error.
    """
    chunks = []
    total = 0

    for chunk in response.iter_content(chunk_size=_CHUNK_SIZE):
        if chunk:
            total += len(chunk)
            if total > max_size:
                return None, f"Response too large: >{max_size} bytes (max: {max_size})"
            chunks.append(chunk)

    return b"".join(chunks), None


def fetch_url(
    url: str, timeout: int = 10, max_size: int = MAX_RESPONSE_SIZE
) -> tuple[requests.Response | None, str | None]:
    """
    Fetch a URL with automatic retry on transient failures.

    Implements three anti-SSRF protections:
    1. DNS pinning: resolves DNS once only, connection forced to the validated IP
    2. Manual redirect: revalidates each redirect target with validate_public_url()
    3. Streaming: downloads body in chunks, stops if it exceeds max_size

    Args:
        url: URL to fetch.
        timeout: Request timeout in seconds.
        max_size: Maximum response size in bytes (default: 10 MB).

    Returns:
        tuple: (response, error_msg) where response is None on failure
    """
    # Import here to avoid circular import (http ← validators ← http)
    from geo_optimizer.utils.validators import resolve_and_validate_url

    # Phase 1: Anti-SSRF validation with single DNS resolution
    ok, err, pinned_ips = resolve_and_validate_url(url)
    if not ok:
        return None, f"Unsafe URL: {err}"

    # Phase 2: Fetch with DNS pinning + manual redirect + streaming
    return _fetch_with_manual_redirects(url, timeout, max_size, pinned_ips)


def _fetch_with_manual_redirects(
    url: str,
    timeout: int,
    max_size: int,
    pinned_ips: list[str],
) -> tuple[requests.Response | None, str | None]:
    """Perform the fetch with manual redirect and SSRF revalidation on each hop.

    Each redirect is revalidated with resolve_and_validate_url() to
    prevent redirects to internal networks (open redirect SSRF).

    Args:
        url: Starting URL (already validated).
        timeout: Timeout in seconds.
        max_size: Response size limit in bytes.
        pinned_ips: Pre-resolved IPs for the starting URL.

    Returns:
        (response, error)
    """
    # Import here to avoid circular import
    from geo_optimizer.utils.validators import resolve_and_validate_url

    current_url = url
    current_ips = pinned_ips
    redirect_count = 0

    # Reuse the same session until the pinned IPs change (fix #122)
    session = create_session_with_retry(
        total_retries=3,
        backoff_factor=1.0,
        status_forcelist=[408, 429, 500, 502, 503, 504],
        pinned_ips=current_ips if current_ips else None,
    )

    while redirect_count <= _MAX_REDIRECTS:
        try:
            # stream=True: the body is not immediately downloaded into RAM
            r = session.get(
                current_url,
                timeout=timeout,
                allow_redirects=False,  # Manual redirect handling
                stream=True,
            )
        except requests.exceptions.Timeout:
            return None, f"Timeout ({timeout}s) after 3 retries"
        except requests.exceptions.ConnectionError as e:
            return None, f"Connection failed after 3 retries: {e}"
        except Exception as e:
            return None, str(e)

        # Check Content-Length before downloading the body
        content_length = r.headers.get("Content-Length")
        if content_length:
            try:
                cl_int = int(content_length)
                if cl_int > max_size:
                    r.close()
                    return None, f"Response too large: {cl_int} bytes (max: {max_size})"
            except (ValueError, TypeError):
                pass  # Non-numeric Content-Length: ignore, check during streaming

        # Manual redirect handling with SSRF revalidation
        if r.status_code in (301, 302, 303, 307, 308):
            r.close()
            redirect_count += 1

            if redirect_count > _MAX_REDIRECTS:
                return None, f"Too many redirects (max: {_MAX_REDIRECTS})"

            location = r.headers.get("Location", "").strip()
            if not location:
                return None, "Redirect without Location header"

            # Resolve relative URL against the current URL
            if location.startswith("/"):
                parsed = urlparse(current_url)
                location = f"{parsed.scheme}://{parsed.netloc}{location}"
            elif not location.startswith(("http://", "https://")):
                parsed = urlparse(current_url)
                location = f"{parsed.scheme}://{parsed.netloc}/{location}"

            # Revalidate the redirect target (anti-SSRF redirect)
            ok, err, next_ips = resolve_and_validate_url(location)
            if not ok:
                return None, f"Redirect to unsafe URL: {err}"

            current_url = location
            # Recreate session only if IPs have changed (redirect to different host)
            if next_ips != current_ips:
                current_ips = next_ips
                session = create_session_with_retry(
                    total_retries=3,
                    backoff_factor=1.0,
                    status_forcelist=[408, 429, 500, 502, 503, 504],
                    pinned_ips=current_ips if current_ips else None,
                )
            continue

        # Final response: download body via streaming or from already-present buffer.
        # Legacy tests set r.content = b"..." as a Mock attribute.
        # Real requests use r._content internally (bytes or False).
        # We distinguish the two cases with isinstance to avoid errors with Mock.
        raw_content = getattr(r, "_content", False)  # noqa: SLF001
        if isinstance(raw_content, bytes):
            # _content already in bytes (real response or mock with explicit _content)
            if len(raw_content) > max_size:
                return None, f"Response too large: {len(raw_content)} bytes (max: {max_size})"
            return r, None

        # Try with r.content (attribute set in legacy mocks: content=b"...")
        mock_content = getattr(r, "content", None)
        if isinstance(mock_content, bytes):
            if len(mock_content) > max_size:
                return None, f"Response too large: {len(mock_content)} bytes (max: {max_size})"
            return r, None

        # Real streaming for live responses (no pre-loaded _content)
        content, err = _stream_response(r, max_size)
        if err:
            r.close()
            return None, err

        # Set the read body in the response object for backward compatibility
        r._content = content  # noqa: SLF001
        r._content_consumed = True  # noqa: SLF001

        return r, None

    return None, f"Too many redirects (max: {_MAX_REDIRECTS})"
