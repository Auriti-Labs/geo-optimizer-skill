"""
Test per l'endpoint POST /api/llms/generate (Sprint 3) in geo_optimizer.web.app.

Tutte le funzioni core (discover_sitemap, fetch_sitemap, generate_llms_txt) sono
mockate ai nomi importati DENTRO app.py: zero chiamate di rete.

Naming: test_llms_generate_{scenario}_{aspettativa}.
Pattern AAA (Arrange-Act-Assert).
"""

import os
from unittest.mock import patch

import pytest

# Dipendenza opzionale: skip dei test se FastAPI o httpx non sono installati
pytest.importorskip("fastapi", reason="FastAPI non installato (pip install geo-optimizer-skill[web])")
pytest.importorskip("httpx", reason="httpx non installato (pip install httpx)")

# Isolamento test (vincolo: zero rete): app.py al momento dell'import valida
# GEO_STATS_API_URL con validate_public_url, che fa una DNS lookup reale
# (socket.getaddrinfo). In un ambiente senza DNS questa risoluzione blocca fino
# al timeout del resolver, facendo "appendere" anche la semplice raccolta dei
# test. Azzerando la variabile PRIMA dell'import, l'app salta quella lookup e
# il modulo si importa in modo deterministico e offline.
os.environ.setdefault("GEO_STATS_API_URL", "")

from starlette.testclient import TestClient

from geo_optimizer.models.results import SitemapUrl
from geo_optimizer.web.app import app

# raise_server_exceptions=False: vogliamo verificare i codici HTTP, non far
# propagare le eccezioni come errori del test runner (come in test_web_app.py).
client = TestClient(app, raise_server_exceptions=False)

# Endpoint sotto test
_ENDPOINT = "/api/llms/generate"


# ─── Helper ──────────────────────────────────────────────────────────────────


def _sample_sitemap_urls(count: int = 3) -> list[SitemapUrl]:
    """Costruisce una lista di SitemapUrl di esempio (no rete)."""
    return [SitemapUrl(url=f"https://example.com/page-{i}", priority=0.8, title=f"Page {i}") for i in range(count)]


# ─── 1. Sitemap scoperta correttamente ───────────────────────────────────────


def test_llms_generate_sitemap_found_returns_content():
    # Arrange
    generated = "# Site\n\n> Descrizione del sito\n\n## Pages\n- [Page 0](https://example.com/page-0)\n"
    with (
        patch("geo_optimizer.utils.validators.validate_public_url", return_value=(True, None)),
        patch("geo_optimizer.web.app.discover_sitemap", return_value="https://example.com/sitemap.xml"),
        patch("geo_optimizer.web.app.fetch_sitemap", return_value=_sample_sitemap_urls(3)),
        patch("geo_optimizer.web.app.generate_llms_txt", return_value=generated),
    ):
        # Act
        resp = client.post(_ENDPOINT, json={"base_url": "https://example.com"})

    # Assert
    assert resp.status_code == 200
    data = resp.json()
    assert data["found_sitemap"] is True
    assert data["url_count"] > 0
    assert data["content"]
    assert data["size_bytes"] > 0
    assert data["line_count"] > 0


# ─── 2. Sitemap mancante → fallback minimale homepage ─────────────────────────


def test_llms_generate_sitemap_missing_returns_minimal():
    # Arrange: discover_sitemap non trova nulla → fallback alla sola homepage
    generated = "# example.com\n\n- [Home](https://example.com)\n"
    with (
        patch("geo_optimizer.utils.validators.validate_public_url", return_value=(True, None)),
        patch("geo_optimizer.web.app.discover_sitemap", return_value=None),
        patch("geo_optimizer.web.app.fetch_sitemap") as mock_fetch,
        patch("geo_optimizer.web.app.generate_llms_txt", return_value=generated),
    ):
        # Act
        resp = client.post(_ENDPOINT, json={"base_url": "https://example.com"})

    # Assert: 200 (NON 500), fallback alla homepage
    assert resp.status_code == 200
    data = resp.json()
    assert data["found_sitemap"] is False
    assert data["url_count"] == 1
    assert "example.com" in data["content"]
    # Nessuna sitemap scoperta → fetch_sitemap non deve essere chiamato
    mock_fetch.assert_not_called()


# ─── 3. sitemap_url esplicito → discover_sitemap NON chiamato ─────────────────


def test_llms_generate_custom_sitemap_url_skips_discovery():
    # Arrange
    with (
        patch("geo_optimizer.utils.validators.validate_public_url", return_value=(True, None)),
        patch("geo_optimizer.web.app.discover_sitemap") as mock_discover,
        patch("geo_optimizer.web.app.fetch_sitemap", return_value=_sample_sitemap_urls(2)) as mock_fetch,
        patch("geo_optimizer.web.app.generate_llms_txt", return_value="# Site\n"),
    ):
        # Act
        resp = client.post(
            _ENDPOINT,
            json={
                "base_url": "https://example.com",
                "sitemap_url": "https://example.com/custom-sitemap.xml",
            },
        )

    # Assert
    assert resp.status_code == 200
    data = resp.json()
    assert data["found_sitemap"] is True
    # sitemap fornita esplicitamente → niente discovery
    mock_discover.assert_not_called()
    mock_fetch.assert_called_once()
    # fetch_sitemap deve ricevere l'URL fornito (normalizzato)
    assert mock_fetch.call_args.args[0] == "https://example.com/custom-sitemap.xml"


# ─── 4. base_url unsafe → 400 (anti-SSRF, difesa a strati) ────────────────────


def test_llms_generate_unsafe_base_url_returns_400():
    # Arrange: IP link-local (metadata cloud) bloccato da validate_public_url
    with patch("geo_optimizer.web.app.discover_sitemap") as mock_discover:
        # Act
        resp = client.post(_ENDPOINT, json={"base_url": "http://169.254.169.254/"})

    # Assert: 400 e nessun lavoro core eseguito (validazione PRIMA della pipeline)
    assert resp.status_code == 400
    assert "Unsafe URL" in resp.json()["detail"]
    mock_discover.assert_not_called()


# ─── 5. sitemap_url unsafe → 400 ──────────────────────────────────────────────


def test_llms_generate_unsafe_sitemap_url_returns_400():
    # Arrange: base_url valido, ma sitemap_url punta a un host bloccato.
    # Mock di validate_public_url (importata DENTRO l'endpoint) per gestire
    # in modo deterministico i due URL: base ok, sitemap unsafe.
    def _fake_validate(url):
        if "internal" in url:
            return (False, "blocked")
        return (True, None)

    with (
        patch("geo_optimizer.utils.validators.validate_public_url", side_effect=_fake_validate),
        patch("geo_optimizer.web.app.discover_sitemap") as mock_discover,
        patch("geo_optimizer.web.app.fetch_sitemap") as mock_fetch,
    ):
        # Act
        resp = client.post(
            _ENDPOINT,
            json={
                "base_url": "https://example.com",
                "sitemap_url": "http://internal.local/sitemap.xml",
            },
        )

    # Assert
    assert resp.status_code == 400
    assert "Unsafe URL" in resp.json()["detail"]
    # sitemap unsafe → nessuna pipeline core
    mock_discover.assert_not_called()
    mock_fetch.assert_not_called()


# ─── 6. max_per_section clampato a 20 ─────────────────────────────────────────


def test_llms_generate_max_per_section_clamped_to_20():
    # Arrange
    with (
        patch("geo_optimizer.utils.validators.validate_public_url", return_value=(True, None)),
        patch("geo_optimizer.web.app.discover_sitemap", return_value="https://example.com/sitemap.xml"),
        patch("geo_optimizer.web.app.fetch_sitemap", return_value=_sample_sitemap_urls(3)),
        patch("geo_optimizer.web.app.generate_llms_txt", return_value="# Site\n") as mock_generate,
    ):
        # Act
        resp = client.post(
            _ENDPOINT,
            json={"base_url": "https://example.com", "max_per_section": 999},
        )

    # Assert
    assert resp.status_code == 200
    # generate_llms_txt e chiamata posizionalmente:
    # (base_url, urls, site_name, description, fetch_titles, max_per_section)
    call = mock_generate.call_args
    passed_max = call.args[5] if len(call.args) > 5 else call.kwargs.get("max_urls_per_section")
    assert passed_max <= 20


# ─── 7. base_url invalido → 400 o 422 ─────────────────────────────────────────


@pytest.mark.parametrize("bad_url", ["", "not a url"])
def test_llms_generate_invalid_base_url_returns_error(bad_url):
    # Arrange: nessun core deve essere raggiunto su input non valido
    with patch("geo_optimizer.web.app.discover_sitemap") as mock_discover:
        # Act
        resp = client.post(_ENDPOINT, json={"base_url": bad_url})

    # Assert: 400 (normalize/validate) oppure 422 (validazione Pydantic)
    assert resp.status_code in (400, 422)
    mock_discover.assert_not_called()


# ─── 8. Sitemap vuota → fallback minimale homepage ───────────────────────────


def test_llms_generate_empty_sitemap_falls_back_to_homepage():
    # Arrange: sitemap scoperta ma fetch_sitemap ritorna lista vuota
    with (
        patch("geo_optimizer.utils.validators.validate_public_url", return_value=(True, None)),
        patch("geo_optimizer.web.app.discover_sitemap", return_value="https://example.com/sitemap.xml"),
        patch("geo_optimizer.web.app.fetch_sitemap", return_value=[]),
        patch("geo_optimizer.web.app.generate_llms_txt", return_value="# example.com\n- [Home](https://example.com)\n"),
    ):
        # Act
        resp = client.post(_ENDPOINT, json={"base_url": "https://example.com"})

    # Assert: 200, fallback alla homepage (NON 500)
    assert resp.status_code == 200
    data = resp.json()
    assert data["found_sitemap"] is False
    assert data["url_count"] == 1
    assert data["content"]
