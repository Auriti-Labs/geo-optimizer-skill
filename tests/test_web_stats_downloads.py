"""Test per GET /api/stats — il contatore dei download PyPI.

Due regressioni reali, entrambe coperte qui:

1. Il campo `pypi_downloads_month` veniva riempito sommando l'endpoint `/system`
   di pypistats, che ripartisce i download per sistema operativo sull'INTERA
   storia del pacchetto. Il sito pubblicava un cumulativo storico (~74.000)
   sotto l'etichetta "downloads/mo", contro ~5.700 download reali al mese.

2. Il primo tentativo di correzione usava `/recent` (che riporta last_month
   già calcolato), ma pypistats **rate-limita quell'endpoint**: risponde 429
   mentre `/system` e `/overall` rispondono 200. In produzione il campo cadeva
   silenziosamente a 0, e uno zero in pagina è peggio di un numero vecchio.

Soluzione: sommare gli ultimi 30 giorni della serie giornaliera di `/overall`,
e in caso di fallimento riusare l'ultima lettura buona invece di pubblicare 0.

Nessuna chiamata di rete: `urllib.request.urlopen` è mockato.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip("fastapi", reason="FastAPI non installato (pip install geo-optimizer-skill[web])")
pytest.importorskip("httpx", reason="httpx non installato (pip install httpx)")

from starlette.testclient import TestClient

from geo_optimizer.web import app as app_module

GITHUB_PAYLOAD = {"stargazers_count": 831}


def _day(offset: int) -> str:
    """Data ISO di `offset` giorni fa (UTC)."""
    return (datetime.now(timezone.utc) - timedelta(days=offset)).strftime("%Y-%m-%d")


# Serie giornaliera come la restituisce /overall?mirrors=false: include righe
# dentro e fuori la finestra dei 30 giorni.
OVERALL_PAYLOAD = {
    "data": [
        {"category": "without_mirrors", "date": _day(400), "downloads": 50_000},  # fuori
        {"category": "without_mirrors", "date": _day(60), "downloads": 20_000},   # fuori
        {"category": "without_mirrors", "date": _day(20), "downloads": 3_000},    # dentro
        {"category": "without_mirrors", "date": _day(10), "downloads": 2_000},    # dentro
        {"category": "without_mirrors", "date": _day(1), "downloads": 690},       # dentro
    ]
}
EXPECTED_MONTH = 3_000 + 2_000 + 690


class _FakeResponse:
    def __init__(self, payload: dict, status: int = 200) -> None:
        self.status = status
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_exc) -> None:
        return None


def _clear_cache() -> None:
    if hasattr(app_module.stats, "_stats_cache"):
        delattr(app_module.stats, "_stats_cache")


@pytest.fixture
def stats_client(monkeypatch):
    """Client con la cache di /api/stats svuotata e le URL chiamate registrate."""
    _clear_cache()
    called: list[str] = []

    def fake_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        called.append(url)
        if "api.github.com" in url:
            return _FakeResponse(GITHUB_PAYLOAD)
        if "/overall" in url:
            return _FakeResponse(OVERALL_PAYLOAD)
        return _FakeResponse({})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with TestClient(app_module.app) as client:
        yield client, called
    _clear_cache()


def test_somma_solo_gli_ultimi_30_giorni(stats_client):
    client, _called = stats_client
    body = client.get("/api/stats").json()

    assert body["pypi_downloads_month"] == EXPECTED_MONTH
    # I controtest che contano: nessuno dei due bug storici deve poter riapparire.
    assert body["pypi_downloads_month"] != 75_690, "sommata tutta la serie: cumulativo"
    assert body["pypi_downloads_month"] != 0, "fetch fallito mascherato da zero"


def test_interroga_overall_non_recent_ne_system(stats_client):
    """`/recent` risponde 429 su pypistats, `/system` è il cumulativo storico."""
    client, called = stats_client
    client.get("/api/stats")

    pypi_urls = [u for u in called if "pypistats.org" in u]
    assert pypi_urls, "nessuna chiamata a pypistats"
    assert all("/overall" in u for u in pypi_urls), f"atteso /overall, chiamato: {pypi_urls}"
    assert not any("/recent" in u or "/system" in u for u in pypi_urls)


def test_fetch_fallito_riusa_lultima_lettura_buona(stats_client, monkeypatch):
    """Un 429 da pypistats non deve far comparire 0 sul sito."""
    client, _called = stats_client
    primo = client.get("/api/stats").json()
    assert primo["pypi_downloads_month"] == EXPECTED_MONTH

    # La cache resta popolata ma scaduta: il prossimo giro rifetcha e fallisce.
    app_module.stats._stats_cache["ts"] = 0

    def urlopen_429(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "api.github.com" in url:
            return _FakeResponse(GITHUB_PAYLOAD)
        raise OSError("HTTP Error 429: RATE LIMIT EXCEEDED")

    monkeypatch.setattr("urllib.request.urlopen", urlopen_429)
    secondo = client.get("/api/stats").json()

    assert secondo["pypi_downloads_month"] == EXPECTED_MONTH, (
        "con pypistats a 429 va riusata l'ultima lettura buona, non pubblicato 0"
    )


def test_senza_cache_e_senza_upstream_resta_zero_ma_non_rompe(stats_client, monkeypatch):
    """Primo avvio con pypistats giù: 0, ma la risposta è valida.

    È il caso in cui i consumer applicano la regola "tutto o niente"
    (StatsBar e utils/publicStats usano i loro valori di fallback).
    """
    _clear_cache()
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: _FakeResponse({}))
    client, _called = stats_client
    body = client.get("/api/stats").json()

    assert body["pypi_downloads_month"] == 0
    assert "github_stars" in body


@pytest.fixture
def app_senza_stats_url(monkeypatch):
    """Modulo ricaricato senza GEO_STATS_API_URL, per leggere il default reale."""
    import importlib

    monkeypatch.delenv("GEO_STATS_API_URL", raising=False)
    monkeypatch.setenv("GEO_STATS_API_KEY", "chiave-presente")
    modulo = importlib.reload(app_module)
    yield modulo
    monkeypatch.undo()
    importlib.reload(app_module)


def test_senza_stats_url_nessuna_chiamata_al_servizio_statistiche(app_senza_stats_url, monkeypatch):
    """Un geo-web self-hosted non configurato non contatta nessun servizio esterno di statistiche."""
    modulo = app_senza_stats_url
    called: list[str] = []

    def fake_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        called.append(url)
        if "api.github.com" in url:
            return _FakeResponse(GITHUB_PAYLOAD)
        return _FakeResponse(OVERALL_PAYLOAD)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr(
        "geo_optimizer.utils.http.create_session_with_retry",
        lambda *a, **k: pytest.fail("POST /increment senza GEO_STATS_API_URL"),
    )

    with TestClient(modulo.app) as client:
        body = client.get("/api/stats").json()
    modulo._increment_remote_stat("audits")

    assert modulo._STATS_API_URL == ""
    assert body["audits_run"] == 0
    # Restano solo GitHub e PyPI, fuori scope di questo test.
    assert all("api.github.com" in u or "pypistats.org" in u for u in called), called
