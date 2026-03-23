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

import asyncio
import dataclasses
import hashlib
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from geo_optimizer import __version__

logger = logging.getLogger(__name__)

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
        # Use 'nonce-{value}' instead of 'unsafe-inline' for XSS protection (fix #75)
        response.headers["Content-Security-Policy"] = (
            f"default-src 'self'; script-src 'self' 'nonce-{nonce}'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "frame-ancestors 'none'"
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
    allow_headers=["Content-Type"],
    max_age=3600,
)

# ─── Optional Bearer token authentication (fix #93) ──────────────────────────
# If GEO_API_TOKEN is set, POST /api/audit requests require
# the "Authorization: Bearer <token>" header. If not set, no auth.
_API_TOKEN: Optional[str] = os.environ.get("GEO_API_TOKEN") or None


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
            if real_ip:
                return real_ip

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


def _check_rate_limit(client_ip: str) -> bool:
    """Verifica rate limit per IP. Ritorna True se consentito."""
    now = time.time()
    timestamps = _rate_limit_store.get(client_ip, [])
    # Rimuovi timestamp fuori finestra temporale
    timestamps = [t for t in timestamps if (now - t) < _RATE_LIMIT_WINDOW]
    if len(timestamps) >= _RATE_LIMIT_MAX_REQUESTS:
        _rate_limit_store[client_ip] = timestamps
        return False
    timestamps.append(now)
    _rate_limit_store[client_ip] = timestamps
    # Fix #70/#99: LRU eviction — rimuovi solo le entry più vecchie, non tutto
    if len(_rate_limit_store) > _RATE_LIMIT_MAX_IPS:
        entries_to_remove = len(_rate_limit_store) - _RATE_LIMIT_MAX_IPS
        _evict_oldest_rate_limit_entries(entries_to_remove)
    return True


# Cache in-memory per risultati audit (TTL 1 ora, max 500 entry)
_audit_cache: dict = {}
_CACHE_TTL = 3600
_MAX_CACHE_SIZE = 500


def _cache_key(url: str) -> str:
    """Genera chiave cache da URL.

    Fix #103: usa i primi 32 caratteri hex (128 bit) invece di 16 (64 bit)
    per ridurre drasticamente il rischio di collisione.
    """
    return hashlib.sha256(url.lower().strip().encode()).hexdigest()[:32]


def _get_cached(url: str) -> Optional[dict]:
    """Recupera risultato dalla cache se valido."""
    key = _cache_key(url)
    entry = _audit_cache.get(key)
    if entry and (time.time() - entry["cached_at"]) < _CACHE_TTL:
        return entry["data"]
    # Rimuovi entry scaduta
    if entry:
        _audit_cache.pop(key, None)
    return None


def _evict_expired() -> None:
    """Rimuovi entry scadute dalla cache."""
    now = time.time()
    expired = [k for k, v in _audit_cache.items() if (now - v["cached_at"]) >= _CACHE_TTL]
    for k in expired:
        _audit_cache.pop(k, None)


def _set_cached(url: str, data: dict) -> str:
    """Salva risultato nella cache con limite dimensione. Ritorna l'ID del report."""
    key = _cache_key(url)
    # Evita crescita illimitata: evict scadute, poi rimuovi le più vecchie
    if len(_audit_cache) >= _MAX_CACHE_SIZE:
        _evict_expired()
    if len(_audit_cache) >= _MAX_CACHE_SIZE:
        oldest_key = min(_audit_cache, key=lambda k: _audit_cache[k]["cached_at"])
        _audit_cache.pop(oldest_key, None)
    _audit_cache[key] = {"data": data, "cached_at": time.time()}
    return key


@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """Homepage con form per audit GEO."""
    # Fix #75: recupera il nonce CSP impostato dal SecurityHeadersMiddleware
    nonce = getattr(request.state, "csp_nonce", "")
    return _render_homepage(nonce=nonce)


@app.get("/health")
async def health():
    """Health check per monitoring."""
    return {"status": "ok", "version": __version__}


# ─── Modello Pydantic per validazione body POST ───────────────────────────────


class AuditRequest(BaseModel):
    """Schema per il body della richiesta POST /api/audit.

    Fix #149: validazione Pydantic previene crash 500 con input non-stringa
    (es. {"url": 123} ora ritorna 422 Unprocessable Entity invece di 500).
    """

    url: str


@app.get("/api/audit")
async def audit_get(
    request: Request,
    url: str = Query(..., description="URL del sito da analizzare"),
):
    """Esegui audit GEO via GET."""
    # Fix #95: usa _get_client_ip per gestire request.client None e proxy trusted
    if not _check_rate_limit(_get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests. Try again soon.")
    return await _run_audit(url)


@app.post("/api/audit")
async def audit_post(request: Request, body: AuditRequest):
    """Esegui audit GEO via POST (body JSON con campo 'url').

    Fix #149: Pydantic valida il body — url deve essere stringa.
    Fix #95: usa _get_client_ip per gestire request.client None e proxy trusted.
    Fix #93: autenticazione Bearer token opzionale tramite GEO_API_TOKEN.
    """
    # Verifica token se GEO_API_TOKEN è impostato
    if not _verify_bearer_token(request):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not _check_rate_limit(_get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests. Try again soon.")
    return await _run_audit(body.url)


@app.get("/report/{report_id}", response_class=HTMLResponse)
async def report(report_id: str):
    """Report temporaneo valido per 1 ora, conservato in memoria. Riavviare il server azzera tutti i report."""
    # Valida che report_id sia un hash esadecimale valido
    if not report_id.isalnum() or len(report_id) > 64:
        raise HTTPException(status_code=400, detail="Invalid report ID")

    entry = _audit_cache.get(report_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Report not found or expired")

    from geo_optimizer.cli.html_formatter import format_audit_html

    data = entry["data"]
    result = _dict_to_audit_result(data)
    return HTMLResponse(content=format_audit_html(result))


@app.get("/badge")
async def badge(
    request: Request,
    url: str = Query(..., description="URL del sito per il badge"),
    label: str = Query("GEO Score", max_length=50, description="Etichetta lato sinistro"),
):
    """Badge SVG dinamico con GEO Score (stile Shields.io).

    Uso in Markdown:
        ![GEO Score](https://geo.example.com/badge?url=https://yoursite.com)
    """
    from fastapi.responses import Response

    from geo_optimizer.utils.validators import validate_public_url

    # Fix #95: usa _get_client_ip per gestire request.client None e proxy trusted
    if not _check_rate_limit(_get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests. Try again soon.")

    # Normalizza URL
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Validazione anti-SSRF
    safe, reason = validate_public_url(url)
    if not safe:
        raise HTTPException(status_code=400, detail=f"Unsafe URL: {reason}")

    # Controlla cache o esegui audit
    cached = _get_cached(url)
    if cached:
        score = cached.get("score", 0)
        band = cached.get("band", "critical")
    else:
        try:
            from geo_optimizer.core.audit import run_full_audit

            # Esegui in thread separato per non bloccare l'event loop
            # Timeout 60s per non bloccare l'event loop (fix #82)
            result = await asyncio.wait_for(
                asyncio.to_thread(run_full_audit, url),
                timeout=60.0,
            )
            data = _audit_result_to_dict(result)
            _set_cached(url, data)
            score = data["score"]
            band = data["band"]
        except asyncio.TimeoutError:
            # Timeout: mostra badge con testo "Error" (fix #152)
            logger.warning("Badge audit timeout (60s) per URL: %s", url)
            from geo_optimizer.web.badge import generate_badge_svg

            svg = generate_badge_svg(0, "critical", label=label, error=True)
            return Response(
                content=svg,
                media_type="image/svg+xml",
                headers={"Cache-Control": "no-store"},
            )
        except Exception:
            # Errore generico: mostra badge con testo "Error" (fix #152)
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


async def _run_audit(url: str) -> JSONResponse:
    """Logica comune per eseguire un audit."""
    from geo_optimizer.utils.validators import validate_public_url

    # Normalizza URL
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Validazione anti-SSRF
    safe, reason = validate_public_url(url)
    if not safe:
        raise HTTPException(status_code=400, detail=f"Unsafe URL: {reason}")

    # Controlla cache
    cached = _get_cached(url)
    if cached:
        report_id = _cache_key(url)
        response_data = dict(cached)
        response_data["report_url"] = f"/report/{report_id}"
        return JSONResponse(content=response_data)

    # Esegui audit
    try:
        from geo_optimizer.core.audit import run_full_audit

        # Esegui in thread separato con timeout 60s per non bloccare l'event loop (fix #82)
        result = await asyncio.wait_for(
            asyncio.to_thread(run_full_audit, url),
            timeout=60.0,
        )
    except asyncio.TimeoutError as exc:
        logger.warning("Audit timeout (60s) per URL: %s", url)
        raise HTTPException(
            status_code=504,
            detail="Audit timeout: site takes too long to respond.",
        ) from exc
    except Exception as e:
        logger.error("Errore audit per %s: %s", url, e)
        raise HTTPException(
            status_code=500,
            detail="Internal error during audit. Try again later.",
        ) from e

    # Serializza risultato
    data = _audit_result_to_dict(result)

    # Salva in cache
    report_id = _set_cached(url, data)
    data["report_url"] = f"/report/{report_id}"

    return JSONResponse(content=data)


def _audit_result_to_dict(result) -> dict:
    """Converte AuditResult in dizionario serializzabile.

    Usa dataclasses.asdict() come base per non perdere campi,
    poi aggiunge i campi calcolati nidificati (checks) per compatibilità API.
    Fix #151: la versione precedente perdeva 10+ campi del risultato.
    """
    # Base completa tramite dataclasses.asdict (include tutti i campi)
    base = dataclasses.asdict(result)

    # Aggiungi il mapping "checks" (struttura attesa dal frontend)
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
            "raw_schemas": result.schema.raw_schemas,
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
        },
    }

    return base


def _dict_to_audit_result(data: dict):
    """Ricostruisce AuditResult da dizionario (per report HTML)."""
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

    return AuditResult(
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
        ),
        schema=SchemaResult(
            found_types=s.get("found_types", []),
            has_website=s.get("has_website", False),
            has_faq=s.get("has_faq", False),
            has_webapp=s.get("has_webapp", False),
            raw_schemas=s.get("raw_schemas", []),
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
        ),
        recommendations=data.get("recommendations", []),
        http_status=data.get("http_status", 0),
        page_size=data.get("page_size", 0),
    )


def _render_homepage(nonce: str = "") -> str:
    """Carica e renderizza l'HTML homepage dal template file.

    Fix #89: HTML spostato in templates/index.html invece di essere inline.
    Fix #75: accetta il nonce CSP e sostituisce il placeholder __NONCE_ATTR__.
    Il template usa '__NONCE_ATTR__' come placeholder nell'attributo del tag <script>.
    """
    template_path = Path(__file__).parent / "templates" / "index.html"
    html = template_path.read_text(encoding="utf-8")
    # Sostituisce il placeholder nonce con il valore reale per la CSP
    # Con nonce: "<script__NONCE_ATTR__>" → "<script nonce='xxx'>"
    # Senza nonce: "<script__NONCE_ATTR__>" → "<script>"
    nonce_attr = f' nonce="{nonce}"' if nonce else ""
    return html.replace("__NONCE_ATTR__", nonce_attr)
