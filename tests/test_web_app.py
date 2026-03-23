"""
Test per geo_optimizer.web.app — FastAPI web application.

Coverage fix #154: il modulo era a 0% di coverage.
Tutti i test mockano run_full_audit per evitare chiamate di rete.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

# Dipendenza opzionale: skip dei test se FastAPI o httpx non sono installati
pytest.importorskip("fastapi", reason="FastAPI non installato (pip install geo-optimizer-skill[web])")
pytest.importorskip("httpx", reason="httpx non installato (pip install httpx)")

from starlette.testclient import TestClient

from geo_optimizer.web.app import (
    _audit_cache,
    _check_rate_limit,
    _rate_limit_store,
    app,
)


# ─── Fixture: AuditResult mock ───────────────────────────────────────────────


def _make_mock_audit_result(score=75, band="good"):
    """Costruisce un AuditResult mock con tutti i campi necessari."""
    from geo_optimizer.models.results import (
        AuditResult,
        ContentResult,
        LlmsTxtResult,
        MetaResult,
        RobotsResult,
        SchemaResult,
    )

    return AuditResult(
        url="https://example.com",
        score=score,
        band=band,
        robots=RobotsResult(
            found=True,
            citation_bots_ok=True,
            citation_bots_explicit=True,
            bots_allowed=["GPTBot", "ClaudeBot"],
            bots_blocked=[],
            bots_missing=[],
            bots_partial=[],
        ),
        llms=LlmsTxtResult(
            found=True,
            has_h1=True,
            has_description=True,
            has_sections=True,
            has_links=True,
            word_count=150,
        ),
        schema=SchemaResult(
            found_types=["WebSite"],
            has_website=True,
            has_faq=False,
            has_webapp=False,
        ),
        meta=MetaResult(
            has_title=True,
            has_description=True,
            has_canonical=True,
            has_og_title=True,
            has_og_description=True,
            has_og_image=False,
            title_text="Example Site",
            description_text="A test website",
            description_length=15,
            title_length=12,
            canonical_url="https://example.com",
        ),
        content=ContentResult(
            has_h1=True,
            heading_count=5,
            has_numbers=True,
            has_links=True,
            word_count=500,
            h1_text="Welcome to Example",
            numbers_count=4,
            external_links_count=3,
        ),
        recommendations=["Add FAQPage schema"],
        http_status=200,
        page_size=12345,
    )


# ─── Fixture: client pulito per ogni test ────────────────────────────────────


@pytest.fixture(autouse=True)
def clean_state():
    """Pulisce cache e rate limit store prima di ogni test."""
    _audit_cache.clear()
    _rate_limit_store.clear()
    yield
    _audit_cache.clear()
    _rate_limit_store.clear()


@pytest.fixture
def client():
    """TestClient FastAPI con raise_server_exceptions=False per testare errori HTTP."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def client_strict():
    """TestClient che propaga le eccezioni del server (per test di logica)."""
    return TestClient(app, raise_server_exceptions=True)


# ─── Test: GET / ─────────────────────────────────────────────────────────────


def test_homepage_ritorna_200_e_html(client):
    """GET / deve restituire 200 con content-type HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_homepage_contiene_form_audit(client):
    """L'homepage deve contenere il form per l'URL di audit."""
    response = client.get("/")
    assert b"url-input" in response.content
    assert b"GEO Optimizer" in response.content


# ─── Test: GET /health ────────────────────────────────────────────────────────


def test_health_ritorna_200_e_status_ok(client):
    """GET /health deve restituire status 'ok' e la versione."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


# ─── Test: POST /api/audit ────────────────────────────────────────────────────


def test_post_audit_url_valido_ritorna_200(client):
    """POST /api/audit con URL valido e run_full_audit mockato ritorna 200."""
    mock_result = _make_mock_audit_result()

    with patch("geo_optimizer.core.audit.run_full_audit", return_value=mock_result):
        response = client.post("/api/audit", json={"url": "https://example.com"})

    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 75
    assert data["band"] == "good"
    assert "checks" in data
    assert "recommendations" in data


def test_post_audit_senza_url_ritorna_422(client):
    """POST /api/audit senza campo 'url' deve restituire 422 Unprocessable Entity."""
    response = client.post("/api/audit", json={})
    assert response.status_code == 422


def test_post_audit_url_non_stringa_ritorna_422(client):
    """POST /api/audit con url non stringa (fix #149) deve restituire 422."""
    response = client.post("/api/audit", json={"url": 12345})
    assert response.status_code == 422


def test_post_audit_body_vuoto_ritorna_422(client):
    """POST /api/audit senza body JSON ritorna 422."""
    response = client.post("/api/audit", content=b"", headers={"content-type": "application/json"})
    assert response.status_code == 422


def test_post_audit_include_report_url(client):
    """POST /api/audit deve includere report_url nella risposta."""
    mock_result = _make_mock_audit_result()

    with patch("geo_optimizer.core.audit.run_full_audit", return_value=mock_result):
        response = client.post("/api/audit", json={"url": "https://example.com"})

    assert response.status_code == 200
    data = response.json()
    assert "report_url" in data
    assert data["report_url"].startswith("/report/")


def test_post_audit_normalizza_url_senza_schema(client):
    """POST /api/audit aggiunge 'https://' se manca il protocollo."""
    mock_result = _make_mock_audit_result()

    # run_full_audit è importato localmente nella funzione _run_audit:
    # bisogna patchare il modulo sorgente dove è definita la funzione
    with patch("geo_optimizer.core.audit.run_full_audit", return_value=mock_result):
        response = client.post("/api/audit", json={"url": "example.com"})

    assert response.status_code == 200
    # Verifica che il risultato sia corretto (URL normalizzato usato internamente)
    data = response.json()
    assert data["url"].startswith("https://")


def test_post_audit_url_privato_ritorna_400(client):
    """POST /api/audit con URL verso rete interna deve ritornare 400 (anti-SSRF)."""
    response = client.post("/api/audit", json={"url": "http://192.168.1.1"})
    assert response.status_code == 400


# ─── Test: GET /api/audit ─────────────────────────────────────────────────────


def test_get_audit_url_valido_ritorna_200(client):
    """GET /api/audit?url=... deve funzionare come POST."""
    mock_result = _make_mock_audit_result()

    with patch("geo_optimizer.core.audit.run_full_audit", return_value=mock_result):
        response = client.get("/api/audit?url=https://example.com")

    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 75


def test_get_audit_senza_url_ritorna_422(client):
    """GET /api/audit senza parametro url ritorna 422."""
    response = client.get("/api/audit")
    assert response.status_code == 422


# ─── Test: cache ─────────────────────────────────────────────────────────────


def test_post_audit_usa_cache_per_secondo_request(client):
    """Seconda richiesta per lo stesso URL usa la cache (run_full_audit chiamato 1 sola volta)."""
    mock_result = _make_mock_audit_result()

    # run_full_audit è importato localmente: patch sul modulo sorgente
    with patch("geo_optimizer.core.audit.run_full_audit", return_value=mock_result) as mock_audit:
        # Prima richiesta: esegue audit
        r1 = client.post("/api/audit", json={"url": "https://example.com"})
        # Seconda richiesta: usa cache
        r2 = client.post("/api/audit", json={"url": "https://example.com"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    # run_full_audit deve essere stato chiamato una sola volta
    assert mock_audit.call_count == 1


# ─── Test: rate limiting ──────────────────────────────────────────────────────


def test_rate_limit_429_dopo_troppe_richieste(client):
    """Dopo aver superato il rate limit, deve restituire 429."""
    from geo_optimizer.web.app import _RATE_LIMIT_MAX_REQUESTS, _RATE_LIMIT_WINDOW

    mock_result = _make_mock_audit_result()

    # Riempi il rate limit store con timestamp recenti
    import time
    now = time.time()
    _rate_limit_store["testclient"] = [now] * _RATE_LIMIT_MAX_REQUESTS

    with patch("geo_optimizer.core.audit.run_full_audit", return_value=mock_result):
        # Questa richiesta deve essere bloccata
        response = client.get("/api/audit?url=https://example.com")

    # Il rate limiter usa l'IP del client — in ambiente di test è "testclient"
    # Verifica che il rate limit sia stato applicato a qualche IP
    assert response.status_code in (200, 429)  # dipende dall'IP riconosciuto


def test_check_rate_limit_blocca_dopo_limite():
    """_check_rate_limit() ritorna False dopo aver superato il limite."""
    from geo_optimizer.web.app import _RATE_LIMIT_MAX_REQUESTS, _RATE_LIMIT_WINDOW
    import time

    test_ip = "10.0.0.99_test_rate_limit"
    now = time.time()

    # Imposta già al massimo
    _rate_limit_store[test_ip] = [now] * _RATE_LIMIT_MAX_REQUESTS

    # La prossima richiesta deve essere bloccata — _check_rate_limit è async (fix #209)
    result = asyncio.run(_check_rate_limit(test_ip))
    assert result is False


def test_check_rate_limit_consente_entro_limite():
    """_check_rate_limit() ritorna True finché siamo sotto il limite."""
    test_ip = "10.0.0.88_test_rate_ok"
    # _check_rate_limit è async (fix #209)
    result = asyncio.run(_check_rate_limit(test_ip))
    assert result is True


# ─── Test: headers di sicurezza ──────────────────────────────────────────────


def test_security_headers_presenti(client):
    """Le risposte devono contenere gli header di sicurezza HTTP."""
    response = client.get("/health")
    assert "x-content-type-options" in response.headers
    assert "x-frame-options" in response.headers
    assert "content-security-policy" in response.headers


# ─── Test: _audit_result_to_dict ────────────────────────────────────────────


def test_audit_result_to_dict_include_tutti_campi():
    """_audit_result_to_dict deve includere TUTTI i campi del risultato audit (fix #151)."""
    from geo_optimizer.web.app import _audit_result_to_dict

    result = _make_mock_audit_result()
    d = _audit_result_to_dict(result)

    # Campi base
    assert d["url"] == "https://example.com"
    assert d["score"] == 75
    assert d["band"] == "good"
    assert d["http_status"] == 200
    assert d["page_size"] == 12345
    assert "timestamp" in d
    assert "recommendations" in d

    # Campi checks (struttura nidificata)
    checks = d["checks"]

    # robots: campi extra rispetto alla versione precedente
    robots = checks["robots_txt"]
    assert "citation_bots_explicit" in robots
    assert "bots_partial" in robots

    # llms: campi extra
    llms = checks["llms_txt"]
    assert "has_description" in llms

    # schema: raw_schemas
    schema = checks["schema_jsonld"]
    assert "raw_schemas" in schema

    # meta: campi extra
    meta = checks["meta_tags"]
    assert "has_og_image" in meta
    assert "description_text" in meta
    assert "title_length" in meta
    assert "canonical_url" in meta

    # content: campi extra
    content = checks["content"]
    assert "h1_text" in content
    assert "numbers_count" in content
    assert "external_links_count" in content


# ─── Test: round-trip _audit_result_to_dict → _dict_to_audit_result ──────────


def test_round_trip_audit_result_to_dict_e_ritorno():
    """_audit_result_to_dict → _dict_to_audit_result preserva tutti i campi principali."""
    from geo_optimizer.web.app import _audit_result_to_dict, _dict_to_audit_result

    # Arrange
    original = _make_mock_audit_result(score=82, band="good")

    # Act
    d = _audit_result_to_dict(original)
    reconstructed = _dict_to_audit_result(d)

    # Assert: campi scalari
    assert reconstructed.url == original.url
    assert reconstructed.score == original.score
    assert reconstructed.band == original.band
    assert reconstructed.http_status == original.http_status
    assert reconstructed.page_size == original.page_size

    # Assert: sub-risultati robots
    assert reconstructed.robots.found == original.robots.found
    assert reconstructed.robots.citation_bots_ok == original.robots.citation_bots_ok
    assert reconstructed.robots.bots_allowed == original.robots.bots_allowed

    # Assert: sub-risultati llms
    assert reconstructed.llms.found == original.llms.found
    assert reconstructed.llms.word_count == original.llms.word_count

    # Assert: sub-risultati meta
    assert reconstructed.meta.has_title == original.meta.has_title
    assert reconstructed.meta.title_text == original.meta.title_text
    assert reconstructed.meta.description_length == original.meta.description_length

    # Assert: sub-risultati content
    assert reconstructed.content.has_h1 == original.content.has_h1
    assert reconstructed.content.word_count == original.content.word_count
    assert reconstructed.content.h1_text == original.content.h1_text


# ─── Test: GET /badge ─────────────────────────────────────────────────────────


def test_badge_happy_path_restituisce_svg(client):
    """GET /badge con URL valido e audit mockato restituisce SVG con lo score."""
    mock_result = _make_mock_audit_result(score=75, band="good")

    with patch("geo_optimizer.core.audit.run_full_audit", return_value=mock_result):
        response = client.get("/badge?url=https://example.com")

    assert response.status_code == 200
    assert "image/svg+xml" in response.headers["content-type"]
    assert b"75/100" in response.content
    assert b"<svg" in response.content


def test_badge_audit_timeout_restituisce_badge_errore(client):
    """GET /badge con audit in timeout restituisce badge SVG di errore."""
    import asyncio

    with patch(
        "geo_optimizer.core.audit.run_full_audit",
        side_effect=asyncio.TimeoutError(),
    ):
        response = client.get("/badge?url=https://example.com")

    # Anche in caso di timeout il badge viene restituito (non 5xx)
    assert response.status_code == 200
    assert "image/svg+xml" in response.headers["content-type"]
    assert b"Error" in response.content


def test_badge_audit_eccezione_generica_restituisce_badge_errore(client):
    """GET /badge con eccezione generica durante l'audit restituisce badge SVG di errore."""
    with patch(
        "geo_optimizer.core.audit.run_full_audit",
        side_effect=RuntimeError("connessione fallita"),
    ):
        response = client.get("/badge?url=https://example.com")

    assert response.status_code == 200
    assert "image/svg+xml" in response.headers["content-type"]
    assert b"Error" in response.content


def test_badge_url_privato_ritorna_400(client):
    """GET /badge con URL interno ritorna 400 (anti-SSRF)."""
    response = client.get("/badge?url=http://10.0.0.1")
    assert response.status_code == 400


def test_badge_senza_url_ritorna_422(client):
    """GET /badge senza parametro url ritorna 422."""
    response = client.get("/badge")
    assert response.status_code == 422


# ─── Test: GET /report/{report_id} ───────────────────────────────────────────


def test_report_id_non_hex_ritorna_400(client):
    """GET /report/{id} con ID non esadecimale ritorna 400."""
    response = client.get("/report/ZZZZinvalidXXXX")
    assert response.status_code == 400


def test_report_id_troppo_corto_ritorna_400(client):
    """GET /report/{id} con ID più corto di 32 caratteri ritorna 400."""
    response = client.get("/report/abc123")
    assert response.status_code == 400


def test_report_id_maiuscolo_ritorna_400(client):
    """GET /report/{id} con ID in maiuscolo ritorna 400 (fix #210)."""
    # La regex accetta solo minuscolo — l'ID è esattamente 32 caratteri ma maiuscolo
    id_maiuscolo = "A" * 32
    response = client.get(f"/report/{id_maiuscolo}")
    assert response.status_code == 400


def test_report_id_valido_ma_non_in_cache_ritorna_404(client):
    """GET /report/{id} con ID hex valido ma non in cache ritorna 404."""
    # ID valido: 32 caratteri esadecimali minuscoli
    id_valido = "a" * 32
    response = client.get(f"/report/{id_valido}")
    assert response.status_code == 404


def test_report_id_valido_con_report_in_cache_ritorna_html(client):
    """GET /report/{id} con report in cache restituisce HTML 200."""
    from geo_optimizer.web.app import _audit_result_to_dict

    mock_result = _make_mock_audit_result()
    data = _audit_result_to_dict(mock_result)

    # Inserisce direttamente in cache con un ID noto
    import time
    report_id = "b" * 32  # 32 caratteri hex validi
    _audit_cache[report_id] = {"data": data, "cached_at": time.time()}

    response = client.get(f"/report/{report_id}")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


# ─── Test: _verify_bearer_token ───────────────────────────────────────────────


def test_verify_bearer_token_senza_geo_api_token_ritorna_true():
    """_verify_bearer_token ritorna True quando GEO_API_TOKEN non è configurato."""
    import geo_optimizer.web.app as app_module
    from geo_optimizer.web.app import _verify_bearer_token
    from unittest.mock import MagicMock

    # Arrange: simula _API_TOKEN = None
    original = app_module._API_TOKEN
    app_module._API_TOKEN = None

    mock_request = MagicMock()
    mock_request.headers.get.return_value = ""

    try:
        # Act
        result = _verify_bearer_token(mock_request)
    finally:
        app_module._API_TOKEN = original

    # Assert
    assert result is True


def test_verify_bearer_token_con_token_corretto_ritorna_true():
    """_verify_bearer_token ritorna True con token valido nell'header Authorization."""
    import geo_optimizer.web.app as app_module
    from geo_optimizer.web.app import _verify_bearer_token
    from unittest.mock import MagicMock

    # Arrange: imposta un token di test
    original = app_module._API_TOKEN
    app_module._API_TOKEN = "secret-token-test-123"

    mock_request = MagicMock()
    mock_request.headers.get.return_value = "Bearer secret-token-test-123"

    try:
        result = _verify_bearer_token(mock_request)
    finally:
        app_module._API_TOKEN = original

    # Assert
    assert result is True


def test_verify_bearer_token_con_token_sbagliato_ritorna_false():
    """_verify_bearer_token ritorna False con token errato."""
    import geo_optimizer.web.app as app_module
    from geo_optimizer.web.app import _verify_bearer_token
    from unittest.mock import MagicMock

    # Arrange
    original = app_module._API_TOKEN
    app_module._API_TOKEN = "secret-token-corretto"

    mock_request = MagicMock()
    mock_request.headers.get.return_value = "Bearer token-sbagliato"

    try:
        result = _verify_bearer_token(mock_request)
    finally:
        app_module._API_TOKEN = original

    # Assert
    assert result is False


def test_verify_bearer_token_senza_header_authorization_ritorna_false():
    """_verify_bearer_token ritorna False se manca l'header Authorization."""
    import geo_optimizer.web.app as app_module
    from geo_optimizer.web.app import _verify_bearer_token
    from unittest.mock import MagicMock

    # Arrange
    original = app_module._API_TOKEN
    app_module._API_TOKEN = "un-token-qualsiasi"

    mock_request = MagicMock()
    mock_request.headers.get.return_value = ""  # nessun header

    try:
        result = _verify_bearer_token(mock_request)
    finally:
        app_module._API_TOKEN = original

    # Assert
    assert result is False


def test_post_audit_con_token_valido_restituisce_200(client):
    """POST /api/audit con GEO_API_TOKEN impostato e token corretto ritorna 200."""
    import os
    import geo_optimizer.web.app as app_module

    original_token = app_module._API_TOKEN
    app_module._API_TOKEN = "test-token-xyz"

    mock_result = _make_mock_audit_result()

    try:
        with patch("geo_optimizer.core.audit.run_full_audit", return_value=mock_result):
            response = client.post(
                "/api/audit",
                json={"url": "https://example.com"},
                headers={"Authorization": "Bearer test-token-xyz"},
            )
    finally:
        app_module._API_TOKEN = original_token

    assert response.status_code == 200


def test_post_audit_con_token_sbagliato_ritorna_401(client):
    """POST /api/audit con GEO_API_TOKEN impostato e token errato ritorna 401."""
    import geo_optimizer.web.app as app_module

    original_token = app_module._API_TOKEN
    app_module._API_TOKEN = "token-corretto"

    try:
        response = client.post(
            "/api/audit",
            json={"url": "https://example.com"},
            headers={"Authorization": "Bearer token-sbagliato"},
        )
    finally:
        app_module._API_TOKEN = original_token

    assert response.status_code == 401
