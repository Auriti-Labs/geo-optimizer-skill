"""Regressione: la CSP deve consentire i fetch cross-origin dei form del frontend verso la SaaS."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="FastAPI non installato (pip install geo-optimizer-skill[web])")
pytest.importorskip("httpx", reason="httpx non installato (pip install httpx)")

from starlette.testclient import TestClient

from geo_optimizer.web.app import app

_COMPONENTS = Path(__file__).resolve().parent.parent / "frontend" / "src" / "components"
_FETCH_COMPONENTS = ("WaitlistForm.tsx", "NewsletterSignup.tsx", "SurveyForm.tsx")
# Origine di un endpoint API assoluto dichiarato come stringa letterale nel componente.
_API_ORIGIN_RE = re.compile(r"""["'](https://[a-z0-9.-]+)/api/""")


def _connect_src() -> list[str]:
    csp = TestClient(app).get("/health").headers["content-security-policy"]
    directive = next(d.strip() for d in csp.split(";") if d.strip().startswith("connect-src "))
    return directive.split()[1:]


def test_connect_src_allows_saas_origin():
    sources = _connect_src()
    assert "https://app.geoready.dev" in sources
    assert "https://*.geoready.dev" not in sources


def test_connect_src_covers_frontend_api_origins():
    files = [_COMPONENTS / name for name in _FETCH_COMPONENTS]
    if not all(f.is_file() for f in files):
        pytest.skip("sorgenti frontend non disponibili")
    origins = {o for f in files for o in _API_ORIGIN_RE.findall(f.read_text(encoding="utf-8"))}
    assert origins, "nessun endpoint cross-origin trovato: regex da aggiornare"
    missing = origins - set(_connect_src())
    assert not missing, f"origini mancanti in connect-src: {sorted(missing)}"
