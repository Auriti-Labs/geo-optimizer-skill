"""The sync fetcher against a hostile server on loopback, with no external traffic.

Most fetcher tests mock ``requests`` or ``socket``. These run the real ``fetch_url`` end to end
against a throwaway HTTP server on 127.0.0.1:

- DNS names go through a fake resolver to a public-looking address (``PUBLIC_IP``);
- every ``socket.connect`` is recorded, and a connect to ``PUBLIC_IP`` is rewritten to the local
  listener, so a request that is allowed reaches the server and one that is not never does;
- a connect to anything else is refused, so a test cannot reach the network by mistake.

They cover the pinning against a resolver that changes its answer, URL forms whose host is read
differently by ``urlparse`` and by urllib3, redirects to private addresses, and bodies that exceed
the size cap after decoding (gzip) or have no length (chunked).
"""

from __future__ import annotations

import gzip
import re
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import geo_optimizer.utils.http as http_module
from geo_optimizer.utils.http import fetch_url
from geo_optimizer.utils.validators import _check_ip_blocked

PUBLIC_IP = "93.184.216.34"
NUMERIC_HOST = re.compile(r"^[0-9a-fA-Fx.:\[\]]+$")
MB = 1024 * 1024


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    hits: list[str] = []
    port = 0

    def do_GET(self):  # noqa: N802 - http.server API
        self.hits.append(self.path)
        if self.path == "/gzip-bomb":
            body = gzip.compress(b"\0" * (30 * MB))
            self._send(200, body, {"Content-Encoding": "gzip"})
        elif self.path == "/chunked":
            self.send_response(200)
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            try:
                for _ in range(4):
                    self.wfile.write(b"%x\r\n" % MB + b"x" * MB + b"\r\n")
                self.wfile.write(b"0\r\n\r\n")
            except (BrokenPipeError, ConnectionResetError):
                pass  # the client stopped reading at the cap: expected
        elif self.path == "/to-private":
            self._send(302, b"", {"Location": f"http://127.0.0.1:{self.port}/secret"})
        elif self.path == "/loop":
            self._send(302, b"", {"Location": "/loop"})
        else:
            self._send(200, b"ok")

    def _send(self, status: int, body: bytes, headers: dict | None = None):
        self.send_response(status)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *args):  # silence the test output
        pass


class _QuietServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):  # the client resetting at the cap is expected
        pass


@pytest.fixture()
def server(monkeypatch):
    """Local listener plus the fake resolver and the connect guard. Yields a namespace."""
    handler = type("Handler", (_Handler,), {"hits": []})
    httpd = _QuietServer(("127.0.0.1", 0), handler)
    handler.port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True).start()

    resolved: list[str] = []  # the answers the fake resolver hands out, in order
    real_getaddrinfo = http_module._original_getaddrinfo

    def fake_getaddrinfo(host, port, *args, **kwargs):
        if isinstance(host, str) and NUMERIC_HOST.match(host):
            return real_getaddrinfo(host, port, *args, **kwargs)  # IP literals: no DNS involved
        answer = resolved.pop(0) if len(resolved) > 1 else (resolved[0] if resolved else PUBLIC_IP)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (answer, port or 0))]

    requested: list[str] = []
    real_connect = socket.socket.connect

    def guarded_connect(self, address):
        ip = address[0] if isinstance(address, tuple) else address
        requested.append(ip)
        if ip == PUBLIC_IP:  # an allowed connection reaches the local server
            return real_connect(self, ("127.0.0.1", address[1]))
        raise ConnectionRefusedError(f"test guard: {ip} refused")

    monkeypatch.setattr(http_module, "_original_getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    # A refused connection is retried with 1, 2 and 4 s of backoff: keep the tests fast.
    monkeypatch.setattr(http_module.time, "sleep", lambda _seconds: None)

    class Namespace:
        port = handler.port
        hits = handler.hits
        answers = resolved
        connects = requested

    yield Namespace
    httpd.shutdown()
    httpd.server_close()


# ─── URL forms read differently by urlparse and urllib3 ──────────────────────


@pytest.mark.parametrize(
    "template",
    [
        "http://127.0.0.1:{p}/",
        "http://127.0.0.1\\.wild.test:{p}/",
        "http://wild.test\\@127.0.0.1:{p}/",
        "http://wild.test#@127.0.0.1:{p}/",
        "http://127.1:{p}/",
        "http://0x7f.1:{p}/",
        "http://2130706433:{p}/",
        "http://[::ffff:127.0.0.1]:{p}/",
        "http://[::127.0.0.1]:{p}/",
        "http://[64:ff9b::7f00:1]:{p}/",
    ],
)
def test_no_url_form_reaches_loopback(server, template):
    fetch_url(template.format(p=server.port), timeout=2)
    # The listener is reachable only through PUBLIC_IP (the pinned, validated address). A connect to
    # a loopback address would mean the request was sent there after validation passed.
    assert not any(ip.startswith("127.") for ip in server.connects), server.connects


@pytest.mark.parametrize(
    "ip",
    ["::127.0.0.1", "64:ff9b::7f00:1", "64:ff9b::a00:1", "64:ff9b::a9fe:a9fe", "2002:7f00:1::1", "2002:a9fe:a9fe::1"],
)
def test_ipv6_forms_that_embed_a_private_ipv4_are_blocked(ip):
    assert _check_ip_blocked(ip)[0] is True


# ─── DNS pinning ─────────────────────────────────────────────────────────────


def test_connection_uses_the_validated_address_when_the_resolver_changes_its_answer(server):
    """Validation resolves to a public IP; a second resolution would give loopback (DNS rebinding)."""
    server.answers[:] = [PUBLIC_IP, "127.0.0.1"]
    response, error = fetch_url(f"http://rebind.test:{server.port}/", timeout=3)

    assert error is None and response is not None and response.status_code == 200
    assert server.connects == [PUBLIC_IP]
    assert server.hits == ["/"]


# ─── Redirects ───────────────────────────────────────────────────────────────


def test_redirect_to_a_private_address_is_refused_and_never_requested(server):
    response, error = fetch_url(f"http://wild.test:{server.port}/to-private", timeout=3)

    assert response is None and error is not None
    assert "/secret" not in server.hits
    assert server.connects == [PUBLIC_IP]


def test_redirect_loop_stops(server):
    response, error = fetch_url(f"http://wild.test:{server.port}/loop", timeout=3)

    assert response is None and error is not None
    assert len(server.hits) <= 12  # bounded by the redirect limit, not by the server


# ─── Size cap ────────────────────────────────────────────────────────────────


def test_gzip_body_is_capped_after_decoding(server):
    """A small compressed body that expands past the cap must be refused (decompression bomb)."""
    response, error = fetch_url(f"http://wild.test:{server.port}/gzip-bomb", timeout=10, max_size=1 * MB)

    assert response is None
    assert error is not None and "too large" in error.lower()


def test_chunked_body_without_length_is_capped(server):
    response, error = fetch_url(f"http://wild.test:{server.port}/chunked", timeout=10, max_size=1 * MB)

    assert response is None
    assert error is not None and "too large" in error.lower()
