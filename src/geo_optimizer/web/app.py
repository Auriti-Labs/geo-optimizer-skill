"""
FastAPI app for GEO Optimizer Web Demo.

Main endpoints:
    GET  /              — Homepage with audit form
    POST /api/audit     — Run audit and return JSON
    GET  /api/audit     — Run audit via query param
    GET  /report/{id}   — Temporary HTML report (TTL 1h, in-memory)
    GET  /badge          — Dynamic SVG badge
    GET  /health        — Health check
"""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import logging
import os
import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from geo_optimizer import __version__

logger = logging.getLogger(__name__)

# Regex to validate report_id: exactly 32 lowercase hex characters
# matching the output of sha256().hexdigest()[:32] (fix #210)
_HEX_ID_RE = re.compile(r"^[0-9a-f]{32}$")

app = FastAPI(
    title="GEO Optimizer",
    description="Audit your website's visibility to AI search engines",
    version=__version__,
    docs_url="/docs",
    redoc_url=None,
)


# ─── Middleware: POST body size limit ─────────────────────────────────────────
_MAX_BODY_BYTES = 4 * 1024  # 4 KB — prevents DoS from unlimited POST bodies


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects POST requests with body larger than _MAX_BODY_BYTES (fix #102)."""

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST":
            content_length = request.headers.get("content-length")
            if content_length is not None:
                try:
                    length_bytes = int(content_length)
                except (ValueError, TypeError):
                    return JSONResponse(
                        status_code=400,
                        content={"detail": "Invalid Content-Length header."},
                    )
                if length_bytes > _MAX_BODY_BYTES:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": f"Body too large. Limit: {_MAX_BODY_BYTES} bytes."},
                    )
            else:
                # Fix #411: enforce size limit on chunked/streaming bodies without Content-Length
                try:
                    body = await request.body()
                    if len(body) > _MAX_BODY_BYTES:
                        return JSONResponse(
                            status_code=413,
                            content={"detail": f"Body too large. Limit: {_MAX_BODY_BYTES} bytes."},
                        )
                except Exception:
                    return JSONResponse(status_code=400, content={"detail": "Failed to read request body."})
        return await call_next(request)


# ─── Middleware: Security Headers ─────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds HTTP security headers to all responses.

    Fix #75: uses nonce for inline scripts instead of 'unsafe-inline'.
    The nonce is generated per response and inserted into the CSP
    and the HTML page via request.state.
    """

    async def dispatch(self, request: Request, call_next):
        # Generate cryptographically secure nonce for each request
        nonce = secrets.token_urlsafe(16)
        # Make the nonce accessible to endpoints (e.g. homepage)
        request.state.csp_nonce = nonce
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Fix #315: HSTS — force HTTPS for 1 year on all subdomains
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Use 'nonce-{value}' instead of 'unsafe-inline' for XSS protection (fix #75)
        # Note #287: style-src uses 'unsafe-inline' because all <style> tags are hardcoded
        # in templates (not user-controllable). Removing it would require nonce on every style tag.
        response.headers["Content-Security-Policy"] = (
            f"default-src 'self'; script-src 'self' 'nonce-{nonce}'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; frame-ancestors 'none'; "
            "object-src 'none'; base-uri 'self'; form-action 'self'"
        )
        # Fix #413: restrict browser API access
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), usb=(), "
            "accelerometer=(), gyroscope=(), magnetometer=()"
        )
        return response


app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# CORS: configurable via ALLOWED_ORIGINS env var (fix #183)
# Default "*" for public demo. In production set ALLOWED_ORIGINS=https://yourdomain.com
_ALLOWED_ORIGINS = list(filter(None, os.environ.get("ALLOWED_ORIGINS", "*").split(",")))
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=3600,
)

# ─── Optional Bearer token authentication (fix #93) ──────────────────────────
# If GEO_API_TOKEN is set, POST /api/audit requests require
# the "Authorization: Bearer <token>" header. If not set, no auth.
_API_TOKEN: str | None = os.environ.get("GEO_API_TOKEN") or None

if _API_TOKEN and "*" in _ALLOWED_ORIGINS:
    logging.getLogger(__name__).warning(
        "GEO_API_TOKEN is set but CORS allows all origins (*). "
        "Set ALLOWED_ORIGINS to restrict cross-origin access."
    )


def _verify_bearer_token(request: Request) -> bool:
    """Verify the Bearer token if GEO_API_TOKEN is configured.

    Returns True if:
    - GEO_API_TOKEN is not set (public demo)
    - The token in the Authorization header matches GEO_API_TOKEN

    Returns False if the token is wrong or missing.
    """
    # No token configured: open access
    if _API_TOKEN is None:
        return True

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False

    # Secure comparison against timing attacks
    provided_token = auth_header[len("Bearer ") :]
    return secrets.compare_digest(provided_token, _API_TOKEN)


# ─── In-memory rate limiter ───────────────────────────────────────────────────
_rate_limit_store: dict = {}  # {ip: [timestamp, ...]}
_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_MAX_REQUESTS = 30  # requests per window per IP
_RATE_LIMIT_MAX_IPS = 10000  # maximum number of tracked IPs
_rate_limit_lock = asyncio.Lock()  # race condition protection on _rate_limit_store

# ─── Proxy trust: list of trusted proxy CIDRs/IPs ─────────────────────────────
# Configurable via TRUSTED_PROXIES environment variable (CSV of IPs/CIDRs).
# X-Forwarded-For is read only if the proxy is trusted (fix #68).
_TRUSTED_PROXIES: set[str] = set(filter(None, os.environ.get("TRUSTED_PROXIES", "").split(",")))


def _get_client_ip(request: Request) -> str:
    """Extract the real client IP from the request.

    - If request.client is None (proxy/test environments), returns "unknown" (fix #95).
    - If the proxy is trusted, reads X-Forwarded-For (fix #68).
    - Otherwise uses request.client.host directly.
    """
    # Fix #95: request.client can be None in proxy/test environments
    proxy_ip = request.client.host if request.client else None

    if proxy_ip is None:
        return "unknown"

    # Fix #68: read X-Forwarded-For only if the proxy is in the trusted list
    if proxy_ip in _TRUSTED_PROXIES:
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        if forwarded_for:
            # Take the first IP in the chain (original client IP)
            real_ip = forwarded_for.split(",")[0].strip()
            # Fix #14: validate that it is a valid IP format
            import ipaddress as _ipaddress

            try:
                _ipaddress.ip_address(real_ip)
                return real_ip
            except ValueError:
                pass  # Invalid IP, fall back to proxy_ip

    return proxy_ip


def _evict_oldest_rate_limit_entries(count: int = 1) -> None:
    """Remove the `count` oldest entries from the rate limit store (LRU eviction).

    Fix #70/#99: instead of _rate_limit_store.clear() which resets everything,
    we remove only the entries with the oldest last request.
    """
    if not _rate_limit_store:
        return
    # Sort by last request timestamp (the most recent in the array)
    sorted_keys = sorted(
        _rate_limit_store,
        key=lambda ip: _rate_limit_store[ip][-1] if _rate_limit_store[ip] else 0,
    )
    for key in sorted_keys[:count]:
        _rate_limit_store.pop(key, None)


async def _check_rate_limit(client_ip: str) -> bool:
    """Check rate limit for IP. Returns True if allowed.

    Fix race condition: uses asyncio.Lock to make the read-modify-write
    operation on the shared _rate_limit_store dict atomic (fix #209).
    Fix #312: unknown IP receives a stricter limit (5 req/min) instead of the normal one.
    """
    # Fix #312: stricter limit for unknown IP (prevents bypass with client None)
    max_requests = 5 if client_ip == "unknown" else _RATE_LIMIT_MAX_REQUESTS
    async with _rate_limit_lock:
        now = time.time()
        timestamps = _rate_limit_store.get(client_ip, [])
        # Remove timestamps outside the time window
        timestamps = [t for t in timestamps if (now - t) < _RATE_LIMIT_WINDOW]
        if len(timestamps) >= max_requests:
            _rate_limit_store[client_ip] = timestamps
            return False
        timestamps.append(now)
        _rate_limit_store[client_ip] = timestamps
        # Fix #70/#99: LRU eviction — remove only the oldest entries, not everything
        if len(_rate_limit_store) > _RATE_LIMIT_MAX_IPS:
            entries_to_remove = len(_rate_limit_store) - _RATE_LIMIT_MAX_IPS
            _evict_oldest_rate_limit_entries(entries_to_remove)
        return True


# In-memory cache for audit results (TTL 1 hour, max 500 entries)
_audit_cache: dict = {}
_CACHE_TTL = 3600
_MAX_CACHE_SIZE = 500
_audit_cache_lock = asyncio.Lock()  # race condition protection on _audit_cache (fix #209)
_stats_cache_lock = asyncio.Lock()  # race condition protection on stats cache (#456)


def _cache_key(url: str) -> str:
    """Generate cache key from URL.

    Fix #103: uses the first 32 hex characters (128 bits) instead of 16 (64 bits)
    to drastically reduce collision risk.
    """
    return hashlib.sha256(url.lower().strip().encode()).hexdigest()[:32]


async def _get_cached(url: str) -> dict | None:
    """Retrieve result from cache if valid.

    Fix race condition: uses asyncio.Lock to protect the atomic
    read/remove on _audit_cache (fix #209).
    """
    async with _audit_cache_lock:
        key = _cache_key(url)
        entry = _audit_cache.get(key)
        if entry and (time.time() - entry["cached_at"]) < _CACHE_TTL:
            return entry["data"]
        # Remove expired entry
        if entry:
            _audit_cache.pop(key, None)
        return None


def _evict_expired() -> None:
    """Remove expired entries from cache. Caller must hold _audit_cache_lock."""
    now = time.time()
    expired = [k for k, v in _audit_cache.items() if (now - v["cached_at"]) >= _CACHE_TTL]
    for k in expired:
        _audit_cache.pop(k, None)


async def _set_cached(url: str, data: dict) -> str:
    """Save result in cache with size limit. Returns the report ID.

    Fix race condition: uses asyncio.Lock to protect the
    check-size / evict / insert block on _audit_cache (fix #209).
    """
    async with _audit_cache_lock:
        key = _cache_key(url)
        # Avoid unbounded growth: evict expired entries, then remove oldest
        if len(_audit_cache) >= _MAX_CACHE_SIZE:
            _evict_expired()
        if len(_audit_cache) >= _MAX_CACHE_SIZE:
            oldest_key = min(_audit_cache, key=lambda k: _audit_cache[k]["cached_at"])
            _audit_cache.pop(oldest_key, None)
        _audit_cache[key] = {"data": data, "cached_at": time.time()}
        return key


@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """Homepage with form for GEO audit."""
    # Fix #75: retrieve the CSP nonce set by SecurityHeadersMiddleware
    nonce = getattr(request.state, "csp_nonce", "")
    return _render_homepage(nonce=nonce)


# ─── Pagine statiche informative ──────────────────────────────────────────────


@app.get("/roadmap", response_class=HTMLResponse)
async def roadmap_page(request: Request):
    """Public roadmap: Now / Next / Later — no dates, just direction."""
    # Fix #313: propaga nonce per coerenza CSP (template privo di script al momento)
    nonce = getattr(request.state, "csp_nonce", "")
    nonce_attr = f' nonce="{nonce}"' if nonce else ""
    template_path = Path(__file__).parent / "templates" / "roadmap.html"
    html = template_path.read_text(encoding="utf-8")
    return html.replace("__NONCE_ATTR__", nonce_attr)


@app.get("/research", response_class=HTMLResponse)
async def research_page(request: Request):
    """Research foundation: peer-reviewed papers behind the scoring."""
    # Fix #313: propaga nonce per coerenza CSP (template privo di script al momento)
    nonce = getattr(request.state, "csp_nonce", "")
    nonce_attr = f' nonce="{nonce}"' if nonce else ""
    template_path = Path(__file__).parent / "templates" / "research.html"
    html = template_path.read_text(encoding="utf-8")
    return html.replace("__NONCE_ATTR__", nonce_attr)


@app.get("/manifesto", response_class=HTMLResponse)
async def manifesto_page(request: Request):
    """The GEO Optimizer Manifesto — philosophy and principles."""
    nonce = getattr(request.state, "csp_nonce", "")
    nonce_attr = f' nonce="{nonce}"' if nonce else ""
    template_path = Path(__file__).parent / "templates" / "manifesto.html"
    html = template_path.read_text(encoding="utf-8")
    return HTMLResponse(html.replace("__NONCE_ATTR__", nonce_attr))


# ─── Documentazione online (Markdown → HTML) ─────────────────────────────────

# Mappa slug → titolo per la sidebar e i meta tag
_DOCS_PAGES = {
    "index": "Documentation",
    "getting-started": "Getting Started",
    "geo-audit": "GEO Audit Script",
    "geo-fix": "geo fix Command",
    "llms-txt": "Generating llms.txt",
    "schema-injector": "Schema Injector",
    "mcp-server": "MCP Server",
    "ai-context": "Using as AI Context",
    "geo-methods": "The 11 GEO Methods",
    "ai-bots-reference": "AI Bots Reference",
    "ci-cd": "CI/CD Integration",
    "scoring-rubric": "Scoring Rubric",
    "troubleshooting": "Troubleshooting",
}


@app.get("/docs/", response_class=HTMLResponse)
async def docs_index(request: Request):
    """Documentation index — redirect to the main docs page."""
    return await docs_page(request, "index")


@app.get("/docs/{slug}", response_class=HTMLResponse)
async def docs_page(request: Request, slug: str):
    """Render a documentation page from docs/*.md as styled HTML."""
    import re as _re

    # Slug validation: only alphanumerics and hyphens (prevents path traversal)
    if not _re.match(r"^[a-z0-9\-]+$", slug):
        raise HTTPException(status_code=404, detail="Page not found")

    # Look for the markdown file: first in the web/docs/ directory (installed package),
    # then in the project root docs/ directory (local development)
    docs_dir = Path(__file__).resolve().parent / "docs"
    md_path = docs_dir / f"{slug}.md"
    if not md_path.exists():
        # Fallback: docs/ directory in the project root (for local development)
        docs_dir = Path(__file__).resolve().parent.parent.parent.parent / "docs"
        md_path = docs_dir / f"{slug}.md"

    if not md_path.exists():
        raise HTTPException(status_code=404, detail="Page not found")

    # Convert Markdown to HTML
    md_content = md_path.read_text(encoding="utf-8")
    html_content = _markdown_to_html(md_content)

    # Build sidebar with links to all pages
    sidebar_links = []
    for page_slug, page_title in _DOCS_PAGES.items():
        if page_slug == "index":
            continue
        active = " active" if page_slug == slug else ""
        sidebar_links.append(f'<a href="/docs/{page_slug}" class="{active}">{page_title}</a>')
    sidebar_html = "\n".join(sidebar_links)

    # Title and description from the map
    title = _DOCS_PAGES.get(slug, slug.replace("-", " ").title())
    description = f"GEO Optimizer documentation: {title}"

    # Load template and replace placeholders
    # Fix #313: propaga nonce CSP per coerenza (template privo di script al momento)
    nonce = getattr(request.state, "csp_nonce", "")
    nonce_attr = f' nonce="{nonce}"' if nonce else ""
    template_path = Path(__file__).parent / "templates" / "docs.html"
    template = template_path.read_text(encoding="utf-8")
    html = (
        template.replace("__TITLE__", title)
        .replace("__DESCRIPTION__", description)
        .replace("__SLUG__", slug)
        .replace("__SIDEBAR__", sidebar_html)
        .replace("__CONTENT__", html_content)
        .replace("__NONCE_ATTR__", nonce_attr)
    )
    return html


def _markdown_to_html(md: str) -> str:
    """Convert Markdown to HTML. Uses the markdown library if available, otherwise basic regex."""
    try:
        import markdown

        html = markdown.markdown(
            md,
            extensions=["tables", "fenced_code", "toc"],
            output_format="html",
        )
        # Fix #404: sanitize markdown output to prevent XSS (javascript: links, raw HTML)
        import re as _re_md

        html = _re_md.sub(r'href\s*=\s*"javascript:[^"]*"', 'href="#"', html)
        html = _re_md.sub(r"<script[^>]*>.*?</script>", "", html, flags=_re_md.DOTALL | _re_md.IGNORECASE)
        html = _re_md.sub(r"\bon\w+\s*=\s*\"[^\"]*\"", "", html, flags=_re_md.IGNORECASE)
        return html
    except ImportError:
        # Fallback: basic conversion with regex
        import html as _html_mod
        import re

        # Fix #35: escape HTML before conversion to prevent XSS
        html = _html_mod.escape(md)
        # Headers
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
        # Code blocks
        html = re.sub(r"```(\w*)\n(.*?)```", r"<pre><code>\2</code></pre>", html, flags=re.DOTALL)
        # Inline code
        html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)
        # Bold
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)

        # Links — Fix #308: valida href per prevenire XSS (es. javascript:)
        def _safe_link(m: re.Match) -> str:
            text, href = m.group(1), m.group(2)
            if href.startswith(("https://", "http://", "/", "#")):
                return f'<a href="{href}">{text}</a>'
            return text

        html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _safe_link, html)
        # Paragraphs
        html = re.sub(r"\n\n", r"</p><p>", html)
        html = f"<p>{html}</p>"
        # Horizontal rules
        html = re.sub(r"<p>---</p>", "<hr>", html)
        return html


@app.get("/compare", response_class=HTMLResponse)
async def compare_page(request: Request):
    """Compare GEO scores of two websites side by side."""
    nonce = getattr(request.state, "csp_nonce", "")
    template_path = Path(__file__).parent / "templates" / "compare.html"
    html = template_path.read_text(encoding="utf-8")
    nonce_attr = f' nonce="{nonce}"' if nonce else ""
    return html.replace("__NONCE_ATTR__", nonce_attr)


# ─── Stats API esterna (AgencyPilot) ─────────────────────────────────────────
# Audit counter persisted on an external SQLite DB via REST API
_STATS_API_URL = os.environ.get("GEO_STATS_API_URL", "https://agencypilot.it/api/geo-stats")
_STATS_API_KEY = os.environ.get("GEO_STATS_API_KEY", "")

# Fix #307/#349: anti-SSRF validation on GEO_STATS_API_URL at startup
_STATS_API_URL_SAFE = True
if _STATS_API_URL:
    from urllib.parse import urlparse as _urlparse_stats

    _parsed_stats = _urlparse_stats(_STATS_API_URL)
    if not _parsed_stats.hostname or "." not in _parsed_stats.hostname:
        _STATS_API_URL_SAFE = False
    elif not _STATS_API_URL.startswith("https://"):
        _STATS_API_URL_SAFE = False
    else:
        # Fix #349: full anti-SSRF validation (blocks private IPs/metadata endpoints)
        try:
            from geo_optimizer.utils.validators import validate_public_url

            safe, _ = validate_public_url(_STATS_API_URL)
            if not safe:
                _STATS_API_URL_SAFE = False
        except Exception:
            pass  # if module not loadable, keep basic check


def _increment_remote_stat(key: str, amount: int = 1) -> None:
    """Increment a counter on the external API (best-effort, does not block on failure)."""

    if not _STATS_API_KEY:
        return
    if not _STATS_API_URL_SAFE:
        return
    if not _STATS_API_URL.startswith("https://"):
        return
    try:
        # Fix #406: use requests with DNS pinning instead of bare urllib.request.urlopen
        from geo_optimizer.utils.http import create_session_with_retry
        from geo_optimizer.utils.validators import resolve_and_validate_url

        target = f"{_STATS_API_URL}/increment"
        ok, _reason, pinned_ips = resolve_and_validate_url(target)
        if not ok:
            return
        session = create_session_with_retry(total_retries=1, pinned_ips=pinned_ips)
        try:
            session.post(
                target,
                json={"key": key, "amount": amount},
                headers={"X-API-Key": _STATS_API_KEY},
                timeout=3,
            )
        finally:
            session.close()
    except Exception:
        pass  # Best-effort: don't block the audit if the API is down


@app.get("/health")
async def health():
    """Health check for monitoring."""
    return {"status": "ok", "version": __version__}


@app.get("/api/stats")
async def stats():
    """Public stats: GitHub stars, PyPI downloads, audit count.

    Fetches GitHub and PyPI data with in-memory cache (1h TTL).
    Used by the homepage for social proof counters.
    Uses urllib (standard library) to avoid dependency on httpx.
    """
    import json as _json
    import time as _time
    import urllib.request

    cache_key = "_stats_cache"
    cache_ttl = 3600  # 1 hour

    # Fix #456 + thundering herd: hold lock for the entire check-fetch-write cycle
    # so only one coroutine fetches while others wait for the cached result
    async with _stats_cache_lock:
        cached = getattr(stats, cache_key, None)
        if cached and (_time.time() - cached["ts"]) < cache_ttl:
            return cached["data"]

        result = {"github_stars": 0, "pypi_downloads_month": 0, "audits_run": 0}

        def _fetch_json(url: str, headers: dict | None = None) -> dict | None:
            """Fetch JSON from URL with 5s timeout. Returns None on failure."""
            try:
                req = urllib.request.Request(url, headers=headers or {"User-Agent": "GEO-Optimizer"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status == 200:
                        return _json.loads(resp.read())
            except Exception:
                return None

        _stats_fetch_target = _STATS_API_URL if _STATS_API_URL_SAFE else None

        async def _maybe_fetch_stats() -> dict | None:
            if _stats_fetch_target is None:
                return None
            return await asyncio.to_thread(_fetch_json, _stats_fetch_target)

        # Run the 3 calls in parallel (GitHub, PyPI, AgencyPilot stats)
        github_data, pypi_data, geo_stats = await asyncio.gather(
            asyncio.to_thread(
                _fetch_json,
                "https://api.github.com/repos/Auriti-Labs/geo-optimizer-skill",
                {"User-Agent": "GEO-Optimizer", "Accept": "application/vnd.github.v3+json"},
            ),
            asyncio.to_thread(
                _fetch_json,
                "https://pypistats.org/api/packages/geo-optimizer-skill/system?mirrors=false",
            ),
            _maybe_fetch_stats(),
        )

        if github_data and github_data.get("stargazers_count"):
            result["github_stars"] = github_data["stargazers_count"]
        else:
            result["github_stars"] = 13  # Fallback: last known value

        if pypi_data:
            downloads = sum(
                item.get("downloads", 0)
                for item in pypi_data.get("data", [])
                if item.get("category") not in (None, "null")
            )
            result["pypi_downloads_month"] = downloads

        if geo_stats and "stats" in geo_stats:
            result["audits_run"] = geo_stats["stats"].get("audits", 0)

        setattr(stats, cache_key, {"data": result, "ts": _time.time()})
        return result


# ─── Pydantic model for POST body validation ─────────────────────────────────


class AuditRequest(BaseModel):
    """Schema for the POST /api/audit request body.

    Fix #149: Pydantic validation prevents 500 crashes with non-string input
    (e.g. {"url": 123} now returns 422 Unprocessable Entity instead of 500).
    """

    url: str


@app.get("/api/audit")
async def audit_get(
    request: Request,
    url: str = Query(..., description="URL del sito da analizzare"),
):
    """Run GEO audit via GET."""
    # Fix #42: verify token on GET too (same policy as POST)
    if not _verify_bearer_token(request):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Fix #95: use _get_client_ip to handle request.client None and trusted proxy
    if not await _check_rate_limit(_get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests. Try again soon.")
    return await _run_audit(url)


@app.post("/api/audit")
async def audit_post(request: Request, body: AuditRequest):
    """Run GEO audit via POST (JSON body with 'url' field).

    Fix #149: Pydantic validates the body — url must be a string.
    Fix #95: use _get_client_ip to handle request.client None and trusted proxy.
    Fix #93: optional Bearer token authentication via GEO_API_TOKEN.
    """
    # Verify token if GEO_API_TOKEN is set
    if not _verify_bearer_token(request):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not await _check_rate_limit(_get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests. Try again soon.")
    return await _run_audit(body.url)


@app.get("/report/{report_id}", response_class=HTMLResponse)
async def report(report_id: str):
    """Temporary report valid for 1 hour, kept in memory. Restarting the server clears all reports."""
    # Validate that report_id is exactly 32 lowercase hex characters
    # matching the output of _cache_key() — fix #210: isalnum() was
    # too permissive (accepted uppercase and other invalid charsets)
    if not _HEX_ID_RE.match(report_id):
        raise HTTPException(status_code=400, detail="Invalid report ID format")

    # Fix #286: cache access protected by lock to avoid race condition
    # Fix #343: check TTL — expired reports are no longer served
    # Fix #457: extract data inside lock to prevent concurrent mutation
    async with _audit_cache_lock:
        entry = _audit_cache.get(report_id)
        if entry and (time.time() - entry.get("cached_at", 0)) >= _CACHE_TTL:
            entry = None
        if not entry:
            raise HTTPException(status_code=404, detail="Report not found or expired")
        data = entry["data"]

    from geo_optimizer.cli.html_formatter import format_audit_html

    result = _dict_to_audit_result(data)
    return HTMLResponse(content=format_audit_html(result))


@app.get("/api/audit/pdf")
async def audit_pdf(
    request: Request,
    url: str = Query(..., description="URL del sito da analizzare — genera report PDF"),
):
    """Generate and download PDF report for a URL."""
    from fastapi.responses import Response

    from geo_optimizer.utils.validators import validate_public_url

    # Fix #403: verify Bearer token (same as /api/audit GET and POST)
    if not _verify_bearer_token(request):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Rate limit
    if not await _check_rate_limit(_get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests. Try again soon.")

    # URL format validation
    url, error = _normalize_url(url)
    if error:
        raise HTTPException(status_code=400, detail=error)

    # Anti-SSRF validation
    safe, reason = validate_public_url(url)
    if not safe:
        raise HTTPException(status_code=400, detail=f"Unsafe URL: {reason}")

    # Check weasyprint availability
    try:
        from geo_optimizer.cli.pdf_formatter import format_audit_pdf  # noqa: F401
    except Exception:
        pass

    try:
        from weasyprint import HTML  # noqa: F401
    except ImportError as exc:
        raise HTTPException(
            status_code=501,
            detail="PDF generation not available. Install weasyprint: pip install geo-optimizer-skill[pdf]",
        ) from exc

    # Cache o audit
    cached = await _get_cached(url)
    if cached:
        result = _dict_to_audit_result(cached)
    else:
        try:
            from geo_optimizer.core.audit import run_full_audit

            audit_result = await asyncio.wait_for(
                asyncio.to_thread(run_full_audit, url),
                timeout=60.0,
            )
            data = _audit_result_to_dict(audit_result)
            await _set_cached(url, data)
            result = audit_result
        except asyncio.TimeoutError as exc:
            raise HTTPException(
                status_code=504,
                detail="Audit timeout: site takes too long to respond.",
            ) from exc
        except Exception as e:
            logger.error("PDF audit error for %s: %s", url, e)
            raise HTTPException(
                status_code=500,
                detail="Internal error during audit. Try again later.",
            ) from e

    # Generate PDF
    from geo_optimizer.cli.pdf_formatter import format_audit_pdf

    try:
        pdf_bytes = await asyncio.to_thread(format_audit_pdf, result)
    except Exception as e:
        logger.error("PDF generation error for %s: %s", url, e)
        raise HTTPException(status_code=500, detail="Error generating PDF report.") from e

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=geo-report.pdf"},
    )


@app.get("/badge")
async def badge(
    request: Request,
    url: str = Query(..., description="URL del sito per il badge"),
    label: str = Query("GEO Score", max_length=50, description="Etichetta lato sinistro"),
):
    """Dynamic SVG badge with GEO Score (Shields.io style).

    Usage in Markdown:
        ![GEO Score](https://geo.example.com/badge?url=https://yoursite.com)
    """
    from fastapi.responses import Response

    from geo_optimizer.utils.validators import validate_public_url

    # Fix #95: use _get_client_ip to handle request.client None and trusted proxy
    if not await _check_rate_limit(_get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests. Try again soon.")

    # URL format validation
    url, error = _normalize_url(url)
    if error:
        raise HTTPException(status_code=400, detail=error)

    # Anti-SSRF validation
    safe, reason = validate_public_url(url)
    if not safe:
        raise HTTPException(status_code=400, detail=f"Unsafe URL: {reason}")

    # Check cache or run audit
    cached = await _get_cached(url)
    if cached:
        score = cached.get("score", 0)
        band = cached.get("band", "critical")
    else:
        try:
            from geo_optimizer.core.audit import run_full_audit

            # Run in separate thread to avoid blocking the event loop
            # Timeout 60s to avoid blocking the event loop (fix #82)
            result = await asyncio.wait_for(
                asyncio.to_thread(run_full_audit, url),
                timeout=60.0,
            )
            data = _audit_result_to_dict(result)
            await _set_cached(url, data)
            score = data["score"]
            band = data["band"]
        except asyncio.TimeoutError:
            # Timeout: show badge with "Error" text (fix #152)
            logger.warning("Badge audit timeout (60s) per URL: %s", url)
            from geo_optimizer.web.badge import generate_badge_svg

            svg = generate_badge_svg(0, "critical", label=label, error=True)
            return Response(
                content=svg,
                media_type="image/svg+xml",
                headers={"Cache-Control": "no-store"},
            )
        except Exception:
            # Generic error: show badge with "Error" text (fix #152)
            from geo_optimizer.web.badge import generate_badge_svg

            svg = generate_badge_svg(0, "critical", label=label, error=True)
            return Response(
                content=svg,
                media_type="image/svg+xml",
                headers={"Cache-Control": "no-store"},
            )

    from geo_optimizer.web.badge import generate_badge_svg

    svg = generate_badge_svg(score, band, label=label)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=3600",
            "ETag": f'"{_cache_key(url)}-{score}"',
        },
    )


@app.get("/badge/endpoint")
async def badge_endpoint(
    request: Request,
    url: str = Query(..., description="URL del sito da analizzare"),
):
    """Endpoint compatibile con shields.io per badge dinamico.

    Usage with shields.io:
        ![GEO Score](https://img.shields.io/endpoint?url=https://geo-optimizer-web.onrender.com/badge/endpoint?url=https://yoursite.com)

    Returns JSON in shields.io schema:
        {"schemaVersion": 1, "label": "GEO Score", "message": "77/100", "color": "green"}
    """
    from geo_optimizer.utils.validators import validate_public_url

    # Rate limit
    if not await _check_rate_limit(_get_client_ip(request)):
        return JSONResponse(
            {"schemaVersion": 1, "label": "GEO Score", "message": "rate limited", "color": "lightgrey"},
            status_code=429,
        )

    # URL format validation
    url, error = _normalize_url(url)
    if error:
        return JSONResponse(
            {"schemaVersion": 1, "label": "GEO Score", "message": "invalid url", "color": "lightgrey"},
            status_code=400,
        )

    # Anti-SSRF validation
    safe, reason = validate_public_url(url)
    if not safe:
        return JSONResponse(
            {"schemaVersion": 1, "label": "GEO Score", "message": "invalid url", "color": "lightgrey"},
            status_code=400,
        )

    # Cache o audit
    cached = await _get_cached(url)
    if cached:
        score = cached.get("score", 0)
        band = cached.get("band", "critical")
    else:
        try:
            from geo_optimizer.core.audit import run_full_audit

            result = await asyncio.wait_for(
                asyncio.to_thread(run_full_audit, url),
                timeout=60.0,
            )
            data = _audit_result_to_dict(result)
            await _set_cached(url, data)
            score = data["score"]
            band = data["band"]
        except (asyncio.TimeoutError, Exception):
            return JSONResponse(
                {"schemaVersion": 1, "label": "GEO Score", "message": "error", "color": "lightgrey"},
                status_code=503,
            )

    # Fix #459: use hex codes to match direct SVG badge colors (cyan for "good", not green)
    color_map = {"excellent": "22c55e", "good": "06b6d4", "foundation": "eab308", "critical": "ef4444"}
    color = color_map.get(band, "lightgrey")

    return JSONResponse(
        {"schemaVersion": 1, "label": "GEO Score", "message": f"{score}/100", "color": color},
        headers={"Cache-Control": "public, max-age=3600"},
    )


def _normalize_url(raw: str) -> tuple[str | None, str]:
    """Normalize and validate URL format.

    Returns (normalized_url, error). If error is non-empty, the URL is invalid.
    """
    from urllib.parse import urlparse

    url = raw.strip()

    # Empty or contains spaces — not a URL
    if not url or " " in url:
        return None, "Invalid input: please enter a URL (e.g. https://example.com)"

    # Add https:// if protocol is missing
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Must have a hostname with at least one dot (real domain)
    parsed = urlparse(url)
    if not parsed.hostname or "." not in parsed.hostname:
        return None, "Invalid URL: a valid domain is required (e.g. https://example.com)"

    return url, ""


async def _run_audit(url: str) -> JSONResponse:
    """Common logic for running an audit."""
    from geo_optimizer.utils.validators import validate_public_url

    url, error = _normalize_url(url)
    if error:
        raise HTTPException(status_code=400, detail=error)

    # Anti-SSRF validation
    safe, reason = validate_public_url(url)
    if not safe:
        raise HTTPException(status_code=400, detail=f"Unsafe URL: {reason}")

    # Check cache
    cached = await _get_cached(url)
    if cached:
        report_id = _cache_key(url)
        response_data = dict(cached)
        response_data["report_url"] = f"/report/{report_id}"
        history_summary = await asyncio.to_thread(_load_history_summary, url)
        if history_summary:
            response_data["history"] = history_summary
        return JSONResponse(content=response_data)

    # Run audit
    try:
        from geo_optimizer.core.audit import run_full_audit

        # Run in separate thread with 60s timeout to avoid blocking the event loop (fix #82)
        result = await asyncio.wait_for(
            asyncio.to_thread(run_full_audit, url),
            timeout=60.0,
        )
    except asyncio.TimeoutError as exc:
        logger.warning("Audit timeout (60s) for URL: %s", url)
        raise HTTPException(
            status_code=504,
            detail="Audit timeout: site takes too long to respond.",
        ) from exc
    except Exception as e:
        logger.error("Audit error for %s: %s", url, e)
        raise HTTPException(
            status_code=500,
            detail="Internal error during audit. Try again later.",
        ) from e

    # Serialize result
    data = _audit_result_to_dict(result)
    history_summary = await asyncio.to_thread(_save_and_load_history_summary, result)
    if history_summary:
        data["history"] = history_summary

    # Incrementa contatore audit sul DB persistente (AgencyPilot)
    await asyncio.to_thread(_increment_remote_stat, "audits")

    # Save to cache
    report_id = await _set_cached(url, data)
    data["report_url"] = f"/report/{report_id}"

    return JSONResponse(content=data)


def _load_history_summary(url: str) -> dict | None:
    """Recupera una summary trend dalla history locale per la web demo."""
    try:
        from geo_optimizer.core.history import HistoryStore, summarize_history

        store = HistoryStore()
        history = store.build_history_result(url)
        if history.total_snapshots == 0:
            return None
        return summarize_history(history)
    except Exception as exc:  # pragma: no cover - best effort non-blocking
        logger.warning("Unable to load local history for %s: %s", url, exc)
        return None


def _save_and_load_history_summary(result) -> dict | None:
    """Salva l'audit web nella history locale e restituisce il trend aggiornato."""
    try:
        from geo_optimizer.core.history import HistoryStore, summarize_history

        store = HistoryStore()
        store.save_audit_result(result)
        history = store.build_history_result(result.url)
        return summarize_history(history)
    except Exception as exc:  # pragma: no cover - best effort non-blocking
        logger.warning("Unable to save local history for %s: %s", getattr(result, "url", "unknown"), exc)
        return None


def _audit_result_to_dict(result) -> dict:
    """Convert AuditResult to serializable dictionary.

    Uses dataclasses.asdict() as the base to avoid losing fields,
    then adds the nested calculated "checks" fields for API compatibility.
    Fix #151: the previous version lost 10+ result fields.
    """
    # Full base via dataclasses.asdict (includes all fields)
    base = dataclasses.asdict(result)

    # Add the "checks" mapping (structure expected by the frontend)
    base["checks"] = {
        "robots_txt": {
            "found": result.robots.found,
            "citation_bots_ok": result.robots.citation_bots_ok,
            "citation_bots_explicit": result.robots.citation_bots_explicit,
            "bots_allowed": result.robots.bots_allowed,
            "bots_blocked": result.robots.bots_blocked,
            "bots_missing": result.robots.bots_missing,
            "bots_partial": result.robots.bots_partial,
        },
        "llms_txt": {
            "found": result.llms.found,
            "has_h1": result.llms.has_h1,
            "has_description": result.llms.has_description,
            "has_sections": result.llms.has_sections,
            "has_links": result.llms.has_links,
            "word_count": result.llms.word_count,
        },
        "schema_jsonld": {
            "found_types": result.schema.found_types,
            "has_website": result.schema.has_website,
            "has_faq": result.schema.has_faq,
            "has_webapp": result.schema.has_webapp,
            "has_article": result.schema.has_article,
            "has_organization": result.schema.has_organization,
            "has_sameas": result.schema.has_sameas,
            "any_schema_found": result.schema.any_schema_found,
            "schema_richness_score": result.schema.schema_richness_score,
            "raw_schemas": result.schema.raw_schemas[:5],  # fix #41: limita a 5 per evitare memory bloat
        },
        "meta_tags": {
            "has_title": result.meta.has_title,
            "has_description": result.meta.has_description,
            "has_canonical": result.meta.has_canonical,
            "has_og_title": result.meta.has_og_title,
            "has_og_description": result.meta.has_og_description,
            "has_og_image": result.meta.has_og_image,
            "title_text": result.meta.title_text,
            "description_text": result.meta.description_text,
            "description_length": result.meta.description_length,
            "title_length": result.meta.title_length,
            "canonical_url": result.meta.canonical_url,
        },
        "content": {
            "has_h1": result.content.has_h1,
            "heading_count": result.content.heading_count,
            "has_numbers": result.content.has_numbers,
            "has_links": result.content.has_links,
            "word_count": result.content.word_count,
            "h1_text": result.content.h1_text,
            "numbers_count": result.content.numbers_count,
            "external_links_count": result.content.external_links_count,
            # These 3 fields are worth 6pts in scoring — must be serialized for cache
            "has_heading_hierarchy": result.content.has_heading_hierarchy,
            "has_lists_or_tables": result.content.has_lists_or_tables,
            "has_front_loading": result.content.has_front_loading,
        },
    }

    return base


def _dict_to_audit_result(data: dict):
    """Reconstruct AuditResult from dictionary (for HTML report)."""
    from geo_optimizer.models.results import (
        AuditResult,
        ContentResult,
        LlmsTxtResult,
        MetaResult,
        RobotsResult,
        SchemaResult,
    )

    checks = data.get("checks", {})
    r = checks.get("robots_txt", {})
    ll = checks.get("llms_txt", {})
    s = checks.get("schema_jsonld", {})
    m = checks.get("meta_tags", {})
    c = checks.get("content", {})

    result = AuditResult(
        url=data.get("url", ""),
        score=data.get("score", 0),
        band=data.get("band", "critical"),
        robots=RobotsResult(
            found=r.get("found", False),
            citation_bots_ok=r.get("citation_bots_ok", False),
            citation_bots_explicit=r.get("citation_bots_explicit", False),
            bots_allowed=r.get("bots_allowed", []),
            bots_blocked=r.get("bots_blocked", []),
            bots_missing=r.get("bots_missing", []),
            bots_partial=r.get("bots_partial", []),
        ),
        llms=LlmsTxtResult(
            found=ll.get("found", False),
            has_h1=ll.get("has_h1", False),
            has_description=ll.get("has_description", False),
            has_sections=ll.get("has_sections", False),
            has_links=ll.get("has_links", False),
            word_count=ll.get("word_count", 0),
            # Fix #452: missing LlmsTxt fields
            has_full=ll.get("has_full", False),
            sections_count=ll.get("sections_count", 0),
            links_count=ll.get("links_count", 0),
            has_blockquote=ll.get("has_blockquote", False),
            has_optional_section=ll.get("has_optional_section", False),
            companion_files_hint=ll.get("companion_files_hint", False),
            validation_warnings=ll.get("validation_warnings", []),
        ),
        schema=SchemaResult(
            found_types=s.get("found_types", []),
            has_website=s.get("has_website", False),
            has_faq=s.get("has_faq", False),
            has_webapp=s.get("has_webapp", False),
            has_article=s.get("has_article", False),
            has_organization=s.get("has_organization", False),
            has_sameas=s.get("has_sameas", False),
            any_schema_found=s.get("any_schema_found", False),
            schema_richness_score=s.get("schema_richness_score", 0),
            raw_schemas=s.get("raw_schemas", []),
            # Fix #452: missing Schema fields
            has_howto=s.get("has_howto", False),
            has_person=s.get("has_person", False),
            has_product=s.get("has_product", False),
            sameas_urls=s.get("sameas_urls", []),
            has_date_modified=s.get("has_date_modified", False),
            avg_attributes_per_schema=s.get("avg_attributes_per_schema", 0.0),
            ecommerce_signals=s.get("ecommerce_signals", {}),
            json_parse_errors=s.get("json_parse_errors", 0),
        ),
        meta=MetaResult(
            has_title=m.get("has_title", False),
            has_description=m.get("has_description", False),
            has_canonical=m.get("has_canonical", False),
            has_og_title=m.get("has_og_title", False),
            has_og_description=m.get("has_og_description", False),
            has_og_image=m.get("has_og_image", False),
            title_text=m.get("title_text", ""),
            description_text=m.get("description_text", ""),
            description_length=m.get("description_length", 0),
            title_length=m.get("title_length", 0),
            canonical_url=m.get("canonical_url", ""),
        ),
        content=ContentResult(
            has_h1=c.get("has_h1", False),
            heading_count=c.get("heading_count", 0),
            has_numbers=c.get("has_numbers", False),
            has_links=c.get("has_links", False),
            word_count=c.get("word_count", 0),
            h1_text=c.get("h1_text", ""),
            numbers_count=c.get("numbers_count", 0),
            external_links_count=c.get("external_links_count", 0),
            # Fix #415: missing Content fields (affect score by up to 6pts)
            has_heading_hierarchy=c.get("has_heading_hierarchy", False),
            has_lists_or_tables=c.get("has_lists_or_tables", False),
            has_front_loading=c.get("has_front_loading", False),
        ),
        recommendations=data.get("recommendations", []),
        http_status=data.get("http_status", 0),
        page_size=data.get("page_size", 0),
        score_breakdown=data.get("score_breakdown", {}),
    )

    # Fix #34: reconstruct additional fields if present in cache
    if "signals" in data and isinstance(data["signals"], dict):
        from geo_optimizer.models.results import SignalsResult

        s = data["signals"]
        result.signals = SignalsResult(
            has_lang=s.get("has_lang", False),
            lang_value=s.get("lang_value", ""),
            has_rss=s.get("has_rss", False),
            rss_url=s.get("rss_url", ""),
            has_freshness=s.get("has_freshness", False),
            freshness_date=s.get("freshness_date", ""),
        )
    if "ai_discovery" in data and isinstance(data["ai_discovery"], dict):
        from geo_optimizer.models.results import AiDiscoveryResult

        ad = data["ai_discovery"]
        result.ai_discovery = AiDiscoveryResult(
            has_well_known_ai=ad.get("has_well_known_ai", False),
            has_summary=ad.get("has_summary", False),
            has_faq=ad.get("has_faq", False),
            has_service=ad.get("has_service", False),
            summary_valid=ad.get("summary_valid", False),
            faq_count=ad.get("faq_count", 0),
            endpoints_found=ad.get("endpoints_found", 0),
        )

    # Fix #309: rebuild cdn_check if present in cache
    if "cdn_check" in data and isinstance(data["cdn_check"], dict):
        from geo_optimizer.models.results import CdnAiCrawlerResult

        cdn = data["cdn_check"]
        result.cdn_check = CdnAiCrawlerResult(
            checked=cdn.get("checked", False),
            browser_status=cdn.get("browser_status", 0),
            browser_content_length=cdn.get("browser_content_length", 0),
            bot_results=cdn.get("bot_results", []),
            any_blocked=cdn.get("any_blocked", False),
            cdn_detected=cdn.get("cdn_detected", ""),
            cdn_headers=cdn.get("cdn_headers", {}),
            error=cdn.get("error", ""),
        )

    # Fix #309: rebuild js_rendering if present in cache
    if "js_rendering" in data and isinstance(data["js_rendering"], dict):
        from geo_optimizer.models.results import JsRenderingResult

        js = data["js_rendering"]
        result.js_rendering = JsRenderingResult(
            checked=js.get("checked", False),
            raw_word_count=js.get("raw_word_count", 0),
            raw_heading_count=js.get("raw_heading_count", 0),
            has_empty_root=js.get("has_empty_root", False),
            has_noscript_content=js.get("has_noscript_content", False),
            framework_detected=js.get("framework_detected", ""),
            js_dependent=js.get("js_dependent", False),
            details=js.get("details", ""),
        )

    # Rebuild brand_entity if present in cache
    if "brand_entity" in data and isinstance(data["brand_entity"], dict):
        from geo_optimizer.models.results import BrandEntityResult

        be = data["brand_entity"]
        result.brand_entity = BrandEntityResult(
            brand_name_consistent=be.get("brand_name_consistent", False),
            names_found=be.get("names_found", []),
            schema_desc_matches_meta=be.get("schema_desc_matches_meta", False),
            kg_pillar_count=be.get("kg_pillar_count", 0),
            kg_pillar_urls=be.get("kg_pillar_urls", []),
            has_wikipedia=be.get("has_wikipedia", False),
            has_wikidata=be.get("has_wikidata", False),
            has_linkedin=be.get("has_linkedin", False),
            has_crunchbase=be.get("has_crunchbase", False),
            has_about_link=be.get("has_about_link", False),
            has_contact_info=be.get("has_contact_info", False),
            has_geo_schema=be.get("has_geo_schema", False),
            has_hreflang=be.get("has_hreflang", False),
            hreflang_count=be.get("hreflang_count", 0),
            faq_depth=be.get("faq_depth", 0),
            has_recent_articles=be.get("has_recent_articles", False),
        )

    # Rebuild webmcp if present in cache (#233)
    if "webmcp" in data and isinstance(data["webmcp"], dict):
        from geo_optimizer.models.results import WebMcpResult

        wm = data["webmcp"]
        result.webmcp = WebMcpResult(
            checked=wm.get("checked", False),
            has_register_tool=wm.get("has_register_tool", False),
            has_tool_attributes=wm.get("has_tool_attributes", False),
            tool_count=wm.get("tool_count", 0),
            has_potential_action=wm.get("has_potential_action", False),
            potential_actions=wm.get("potential_actions", []),
            has_labeled_forms=wm.get("has_labeled_forms", False),
            labeled_forms_count=wm.get("labeled_forms_count", 0),
            has_openapi=wm.get("has_openapi", False),
            agent_ready=wm.get("agent_ready", False),
            readiness_level=wm.get("readiness_level", "none"),
        )

    # Rebuild negative_signals if present in cache (v4.3)
    if "negative_signals" in data and isinstance(data["negative_signals"], dict):
        from geo_optimizer.models.results import NegativeSignalsResult

        ns = data["negative_signals"]
        result.negative_signals = NegativeSignalsResult(
            checked=ns.get("checked", True),
            cta_density_high=ns.get("cta_density_high", False),
            cta_count=ns.get("cta_count", 0),
            has_popup_signals=ns.get("has_popup_signals", False),
            popup_indicators=ns.get("popup_indicators", []),
            is_thin_content=ns.get("is_thin_content", False),
            broken_links_count=ns.get("broken_links_count", 0),
            has_broken_links=ns.get("has_broken_links", False),
            has_keyword_stuffing=ns.get("has_keyword_stuffing", False),
            stuffed_word=ns.get("stuffed_word", ""),
            stuffed_density=ns.get("stuffed_density", 0.0),
            has_author_signal=ns.get("has_author_signal", False),
            boilerplate_ratio=ns.get("boilerplate_ratio", 0.0),
            boilerplate_high=ns.get("boilerplate_high", False),
            has_mixed_signals=ns.get("has_mixed_signals", False),
            mixed_signal_detail=ns.get("mixed_signal_detail", ""),
            signals_found=ns.get("signals_found", 0),
            severity=ns.get("severity", "clean"),
        )

    # Rebuild prompt_injection if present in cache (#276)
    if "prompt_injection" in data and isinstance(data["prompt_injection"], dict):
        from geo_optimizer.models.results import PromptInjectionResult

        pi = data["prompt_injection"]
        result.prompt_injection = PromptInjectionResult(
            checked=pi.get("checked", True),
            hidden_text_found=pi.get("hidden_text_found", False),
            hidden_text_count=pi.get("hidden_text_count", 0),
            hidden_text_samples=pi.get("hidden_text_samples", []),
            invisible_unicode_found=pi.get("invisible_unicode_found", False),
            invisible_unicode_count=pi.get("invisible_unicode_count", 0),
            llm_instruction_found=pi.get("llm_instruction_found", False),
            llm_instruction_count=pi.get("llm_instruction_count", 0),
            llm_instruction_samples=pi.get("llm_instruction_samples", []),
            html_comment_injection_found=pi.get("html_comment_injection_found", False),
            html_comment_injection_count=pi.get("html_comment_injection_count", 0),
            html_comment_samples=pi.get("html_comment_samples", []),
            monochrome_text_found=pi.get("monochrome_text_found", False),
            monochrome_text_count=pi.get("monochrome_text_count", 0),
            microfont_found=pi.get("microfont_found", False),
            microfont_count=pi.get("microfont_count", 0),
            data_attr_injection_found=pi.get("data_attr_injection_found", False),
            data_attr_injection_count=pi.get("data_attr_injection_count", 0),
            data_attr_samples=pi.get("data_attr_samples", []),
            aria_hidden_injection_found=pi.get("aria_hidden_injection_found", False),
            aria_hidden_injection_count=pi.get("aria_hidden_injection_count", 0),
            aria_hidden_samples=pi.get("aria_hidden_samples", []),
            patterns_found=pi.get("patterns_found", 0),
            severity=pi.get("severity", "clean"),
            risk_level=pi.get("risk_level", "none"),
        )

    # Rebuild trust_stack if present in cache (#273)
    if "trust_stack" in data and isinstance(data["trust_stack"], dict):
        from geo_optimizer.models.results import TrustLayerScore, TrustStackResult

        ts = data["trust_stack"]

        def _rebuild_layer(layer_data: dict) -> TrustLayerScore:
            return TrustLayerScore(
                name=layer_data.get("name", ""),
                label=layer_data.get("label", ""),
                score=layer_data.get("score", 0),
                max_score=layer_data.get("max_score", 5),
                signals_found=layer_data.get("signals_found", []),
                signals_missing=layer_data.get("signals_missing", []),
                details=layer_data.get("details", {}),
            )

        result.trust_stack = TrustStackResult(
            checked=ts.get("checked", True),
            technical=_rebuild_layer(ts.get("technical", {})),
            identity=_rebuild_layer(ts.get("identity", {})),
            social=_rebuild_layer(ts.get("social", {})),
            academic=_rebuild_layer(ts.get("academic", {})),
            consistency=_rebuild_layer(ts.get("consistency", {})),
            composite_score=ts.get("composite_score", 0),
            grade=ts.get("grade", "F"),
            trust_level=ts.get("trust_level", "low"),
        )

    return result


# ─── GEO Optimization endpoints ──────────────────────────────────────────────


@app.get("/robots.txt")
async def robots_txt():
    """Serve robots.txt ottimizzato per AI crawler."""
    from fastapi.responses import PlainTextResponse

    robots = (
        "# GEO Optimizer — robots.txt\n"
        "User-agent: *\nAllow: /\n\n"
        "User-agent: GPTBot\nAllow: /\n"
        "User-agent: OAI-SearchBot\nAllow: /\n"
        "User-agent: ChatGPT-User\nAllow: /\n"
        "User-agent: ClaudeBot\nAllow: /\n"
        "User-agent: Claude-SearchBot\nAllow: /\n"
        "User-agent: anthropic-ai\nAllow: /\n"
        "User-agent: claude-web\nAllow: /\n"
        "User-agent: PerplexityBot\nAllow: /\n"
        "User-agent: Perplexity-User\nAllow: /\n"
        "User-agent: Google-Extended\nAllow: /\n"
        "User-agent: Google-CloudVertexBot\nAllow: /\n"
        "User-agent: Bingbot\nAllow: /\n"
        "User-agent: Applebot-Extended\nAllow: /\n"
        "User-agent: Applebot\nAllow: /\n"
        "User-agent: DuckAssistBot\nAllow: /\n"
        "User-agent: cohere-ai\nAllow: /\n"
        "User-agent: Bytespider\nAllow: /\n"
        "User-agent: meta-externalagent\nAllow: /\n"
        "User-agent: Meta-ExternalFetcher\nAllow: /\n"
        "User-agent: facebookexternalhit\nAllow: /\n"
        "User-agent: Amazonbot\nAllow: /\n"
        "User-agent: AI2Bot\nAllow: /\n"
        "User-agent: AI2Bot-Dolma\nAllow: /\n"
        "User-agent: xAI-Bot\nAllow: /\n"
        "User-agent: PetalBot\nAllow: /\n"
        "User-agent: YouBot\nAllow: /\n"
        "User-agent: CCBot\nAllow: /\n"
    )
    return PlainTextResponse(content=robots, media_type="text/plain")


@app.get("/llms.txt")
async def llms_txt():
    """Serve llms.txt per AI content discovery."""
    from fastapi.responses import PlainTextResponse

    llms = (
        "# GEO Optimizer\n\n"
        "> Open-source toolkit to audit, fix, and optimize any website for AI search engine visibility.\n"
        "> Scores 0-100 across 8 categories and 47 research-backed methods.\n"
        "> Based on Princeton KDD 2024 and AutoGEO ICLR 2026 peer-reviewed research.\n"
        "> MIT License. Free for commercial and personal use.\n\n"
        "## What GEO Optimizer Does\n\n"
        "GEO Optimizer audits any publicly accessible URL — regardless of CMS, framework, or hosting — "
        "and measures how visible that site is to AI search engines like ChatGPT, Perplexity, Claude, and Gemini.\n\n"
        "The audit covers 8 categories:\n"
        "1. robots.txt (18pt) — AI bot access configuration for OAI-SearchBot, ClaudeBot, PerplexityBot\n"
        "2. llms.txt (18pt) — Machine-readable site index for AI agents, depth-graduated scoring\n"
        "3. Schema JSON-LD (16pt) — Structured data: FAQPage, Article, Organization, WebSite, sameAs\n"
        "4. Meta Tags (14pt) — Title, description, canonical, Open Graph\n"
        "5. Content Quality (12pt) — Statistics, citations, headings, word count, front-loading\n"
        "6. Technical Signals (6pt) — Language, RSS feed, freshness indicators\n"
        "7. AI Discovery (6pt) — well-known/ai.txt, /ai/summary.json, /ai/faq.json, /ai/service.json\n"
        "8. Brand & Entity Signals (10pt) — Knowledge graph, sameAs, About/Contact, geographic identity\n\n"
        "Score bands: 86-100 Excellent | 68-85 Good | 36-67 Foundation | 0-35 Critical\n\n"
        "## Tools\n\n"
        "- [GEO Audit Web](https://geo-optimizer-web.onrender.com/): Audit any URL — score 0-100 with breakdown\n"
        "- [Compare](https://geo-optimizer-web.onrender.com/compare): Side-by-side GEO score comparison of two URLs\n"
        "- [Badge](https://geo-optimizer-web.onrender.com/badge?url=https://example.com): Dynamic SVG GEO score badge\n"
        "- [Manifesto](https://geo-optimizer-web.onrender.com/manifesto): Why AI search visibility should be open\n"
        "- [Research](https://geo-optimizer-web.onrender.com/research): Scientific papers behind the scoring\n"
        "- [Roadmap](https://geo-optimizer-web.onrender.com/roadmap): Upcoming features and milestones\n\n"
        "## CLI Install\n\n"
        "```\n"
        "pip install geo-optimizer-skill\n"
        "geo audit --url https://example.com\n"
        "geo audit --url https://example.com --format rich\n"
        "geo audit --url https://example.com --format json\n"
        "geo fix --url https://example.com --only robots,llms,schema\n"
        "```\n\n"
        "## Integrations\n\n"
        "- CLI: `geo` command — 7 output formats (text, rich, json, html, pdf, github, ci)\n"
        "- GitHub Actions: `geo-action` — CI/CD integration with SARIF and JUnit output\n"
        "- MCP Server: `geo-mcp` — Tool server for Claude, Cursor, Windsurf, Continue\n"
        "- Python API: `from geo_optimizer import run_full_audit` — programmatic access\n"
        "- Plugin system: Custom checks via `CheckRegistry` — extend without forking\n\n"
        "## Documentation\n\n"
        "- [Getting Started](https://auriti-labs.github.io/geo-optimizer-skill/getting-started/): Install and first audit\n"
        "- [GEO Audit](https://auriti-labs.github.io/geo-optimizer-skill/geo-audit/): Full CLI reference\n"
        "- [Scoring Rubric](https://auriti-labs.github.io/geo-optimizer-skill/scoring-rubric/): All 8 categories explained\n"
        "- [MCP Server](https://auriti-labs.github.io/geo-optimizer-skill/mcp-server/): AI agent integration\n"
        "- [CI/CD](https://auriti-labs.github.io/geo-optimizer-skill/ci-cd/): GitHub Actions integration\n"
        "- [GEO Methods](https://auriti-labs.github.io/geo-optimizer-skill/geo-methods/): 47 research-backed methods\n\n"
        "## Reference\n\n"
        "- [AI Bots Reference](https://auriti-labs.github.io/geo-optimizer-skill/ai-bots-reference/): 27 AI crawlers documented\n"
        "- [Troubleshooting](https://auriti-labs.github.io/geo-optimizer-skill/troubleshooting/): Common issues\n"
        "- [Changelog](https://github.com/Auriti-Labs/geo-optimizer-skill/blob/main/CHANGELOG.md): Full release history\n"
        "- [PyPI](https://pypi.org/project/geo-optimizer-skill/): Package and version history\n\n"
        "## Research Foundation\n\n"
        "- GEO: Generative Engine Optimization — Princeton NLP, KDD 2024 — https://arxiv.org/abs/2311.09735\n"
        "- AutoGEO: Automatic GEO — Carnegie Mellon, ICLR 2026 — https://arxiv.org/abs/2510.11438\n"
        "- llms.txt specification — Answer.AI — https://llmstxt.org/\n"
        "- geo-checklist.dev standard — https://geo-checklist.dev/\n\n"
        "## Optional\n\n"
        "- [GitHub Issues](https://github.com/Auriti-Labs/geo-optimizer-skill/issues): Bug reports and feature requests\n"
        "- [Releases RSS](https://github.com/Auriti-Labs/geo-optimizer-skill/releases.atom): Subscribe to new releases\n"
    )
    return PlainTextResponse(content=llms, media_type="text/plain")


@app.get("/.well-known/ai.txt")
async def well_known_ai():
    """AI crawler permissions."""
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(
        content="User-Agent: *\nAllow: /\n",
        media_type="text/plain",
    )


@app.get("/ai/summary.json")
async def ai_summary():
    """Site summary for AI systems."""
    return {
        "name": "GEO Optimizer",
        "description": "Open-source toolkit to audit and optimize websites for AI search engine visibility. Scores 0-100 based on 47 research-backed methods.",
        "url": "https://geo-optimizer-web.onrender.com",
        "lastModified": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


@app.get("/ai/faq.json")
async def ai_faq():
    """FAQ for AI systems."""
    return {
        "faqs": [
            {
                "question": "What is GEO Optimizer?",
                "answer": "An open-source toolkit that audits websites for AI search visibility, scoring 0-100 based on 47 research-backed methods.",
            },
            {
                "question": "How is the score calculated?",
                "answer": "Across 8 categories: robots.txt (18pt), llms.txt (18pt), schema (16pt), meta (14pt), content (12pt), signals (6pt), AI discovery (6pt), brand & entity (10pt).",
            },
            {"question": "Is it free?", "answer": "Yes, MIT License. Install: pip install geo-optimizer-skill"},
        ]
    }


@app.get("/ai/service.json")
async def ai_service():
    """Service capabilities for AI systems."""
    return {
        "name": "GEO Optimizer",
        "capabilities": ["Audit GEO score", "Generate fixes", "Citability analysis", "MCP server", "CI/CD integration"],
    }


def _render_homepage(nonce: str = "") -> str:
    """Load and render the homepage HTML from the template file.

    Fix #89: HTML moved to templates/index.html instead of being inline.
    Fix #75: accepts the CSP nonce and replaces the __NONCE_ATTR__ placeholder.
    The template uses '__NONCE_ATTR__' as a placeholder in the <script> tag attribute.
    """
    template_path = Path(__file__).parent / "templates" / "index.html"
    html = template_path.read_text(encoding="utf-8")
    # Replace the nonce placeholder with the real value for the CSP
    # With nonce: "<script__NONCE_ATTR__>" → "<script nonce='xxx'>"
    # Without nonce: "<script__NONCE_ATTR__>" → "<script>"
    nonce_attr = f' nonce="{nonce}"' if nonce else ""
    return html.replace("__NONCE_ATTR__", nonce_attr)
