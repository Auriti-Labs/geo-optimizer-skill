# CLAUDE.md — GEO Optimizer

## Panoramica

**GEO Optimizer** (v4.0.0-beta.1) è un toolkit Python open-source per Generative Engine Optimization: rende i siti web visibili e citabili dai motori di ricerca AI (ChatGPT, Perplexity, Claude, Gemini).

Basato su Princeton KDD 2024, AutoGEO ICLR 2026, SE Ranking 2025, Growth Marshal 2026.

4 comandi CLI (`geo audit`, `geo fix`, `geo llms`, `geo schema`) + MCP server + web demo FastAPI. Licenza MIT.

## Comandi di sviluppo

```bash
pip install -e ".[dev]"              # Installazione editable
pytest tests/ -v                     # 1030+ test (tutti mockati, no rete)
pytest tests/ -v --cov=geo_optimizer # Con coverage
ruff check src/geo_optimizer/        # Lint
ruff format src/geo_optimizer/       # Format
geo audit --url https://example.com  # CLI audit
geo fix --url https://example.com    # Auto-fix
geo-web                              # Web demo FastAPI
```

## Architettura

```
cli/          → Click commands + 7 formatter (text, json, rich, html, sarif, junit, github)
core/         → Business logic (ritorna dataclasses, MAI stampa)
  audit.py    → run_full_audit() + run_full_audit_async() — 8 categorie scoring
  citability.py → 42 metodi citability (3200 righe)
  fixer.py    → Generazione fix (robots, llms, schema, meta, ai_discovery)
  scoring.py  → Engine scoring separato (pesi da config.py)
  injection_detector.py → Prompt Injection Detection (8 categorie, #276)
  registry.py → Plugin system via entry_points
models/       → config.py (costanti, pesi SCORING) + results.py (dataclass)
utils/        → http.py (anti-SSRF + DNS pinning), validators.py, cache.py, http_async.py
web/          → FastAPI app + templates + badge SVG
mcp/          → MCP server con 8 tool e 5 resource
i18n/         → Traduzioni it/en (parziale)
```

## Scoring (100 punti totali)

| Categoria | Punti | Chiavi SCORING |
|-----------|-------|---------------|
| Robots.txt | 18 | robots_found(5) + robots_citation_ok(13) |
| llms.txt | 18 | found(5) + h1(2) + blockquote(1) + sections(2) + links(2) + depth(2) + depth_high(2) + full(2) |
| Schema JSON-LD | 16 | any_valid(2) + richness(3) + faq(3) + article(3) + organization(3) + website(2) |
| Meta Tags | 14 | title(5) + description(2) + canonical(3) + og(4) |
| Content | 12 | h1(2) + numbers(1) + links(1) + word_count(2) + hierarchy(2) + lists(2) + front_loading(2) |
| Signals | 6 | lang(3) + rss(2) + freshness(1) |
| AI Discovery | 6 | well_known(2) + summary(2) + faq(1) + service(1) |
| Brand & Entity | 10 | coherence(3) + kg_readiness(3) + about_contact(2) + geo_identity(1) + topic_authority(1) |

**Bande:** 86-100 excellent · 68-85 good · 36-67 foundation · 0-35 critical

## Vincoli inderogabili

1. **core/ non stampa MAI** — ritorna dataclasses da `models/results.py`
2. **Anti-SSRF obbligatorio** — ogni URL utente passa per `validators.resolve_and_validate_url()` → `fetch_url()` con DNS pinning. MAI `requests.get()` diretto. MAI `allow_redirects=True`
3. **Streaming con size check** — `MAX_RESPONSE_SIZE` (10 MB), `_stream_response()` in chunks
4. **Costanti in config.py** — AI_BOTS, SCORING, SCHEMA_TEMPLATES. MAI hardcodare valori
5. **Python 3.9 compat** — `from __future__ import annotations` in tutti i file. `entry_points()` ha API diversa pre-3.10
6. **Test senza rete** — 1030+ test tutti con `unittest.mock.patch`, zero HTTP reali
7. **Plugin via CheckRegistry** — `entry_points("geo_optimizer.checks")`, Protocol `AuditCheck`, `run_all()` passa `deepcopy(soup)` ai plugin
8. **JSON-LD @graph** — il parser supporta sia `@type` diretto che `@graph: [{...}]` (Yoast/RankMath)
9. **Ruff** — line-length 120, target py39, regole E/F/W/I/UP/B/C4/SIM

## Deploy

- **PyPI**: tag `v*` → workflow `publish.yml` → pypa/gh-action-pypi-publish (trusted publisher)
- **Docker**: tag `v*` → workflow `docker.yml` → GHCR + Docker Hub
- **Web demo**: Render free tier da `Dockerfile.web`, auto-deploy su push main
- **Docs**: GitHub Pages da `site/` via Jekyll, workflow `pages.yml`
- **Wiki**: 14 pagine su github.com/Auriti-Labs/geo-optimizer-skill/wiki

## Endpoint web app

| Endpoint | Descrizione |
|----------|-------------|
| `GET /` | Homepage con audit form |
| `POST /api/audit` | Audit JSON (richiede Bearer se GEO_API_TOKEN) |
| `GET /api/audit` | Audit JSON via query param (stessa auth del POST) |
| `GET /report/{id}` | Report HTML temporaneo (TTL 1h, in-memory) |
| `GET /api/audit/pdf` | Report PDF |
| `GET /badge` | Badge SVG dinamico |
| `GET /badge/endpoint` | Shields.io compatible endpoint |
| `GET /compare` | Pagina confronto |
| `GET /robots.txt` | Robots.txt con 27 AI bot |
| `GET /llms.txt` | llms.txt per AI discovery |
| `GET /.well-known/ai.txt` | AI crawler permissions |
| `GET /ai/summary.json` | Site summary per AI |
| `GET /ai/faq.json` | FAQ strutturate per AI |
| `GET /ai/service.json` | Capabilities per AI |
| `GET /health` | Health check con versione |

## Variabili d'ambiente

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `PORT` | 8000 | Porta web server (solo Dockerfile.web, non geo-web CLI) |
| `GEO_API_TOKEN` | — | Bearer token per autenticazione API |
| `GEO_LANG` | it | Lingua output CLI (it/en) |
| `ALLOWED_ORIGINS` | * | CORS origins (CSV) |
| `TRUSTED_PROXIES` | — | IP proxy trusted per X-Forwarded-For |
| `GEO_STATS_API_URL` | agencypilot.it | URL stats API (solo HTTPS) |
| `GEO_STATS_API_KEY` | — | Key per stats API |

## Gotcha

1. **`from __future__ import annotations`** deve essere in OGNI file `.py` in `src/` — senza, Python 3.9 crasha su `str | None`, `list[str]`, ecc.
2. **Import circolari http ↔ validators** — `fetch_url()` importa `validators` dentro la funzione
3. **Mock HTTP nei test** — i mock legacy usano `r.content = b"..."`. `fetch_url()` gestisce sia `_content` che `content` per backward compat
4. **`audit_js_rendering` non deve mutare soup** — usa `copy.deepcopy(body)` prima di `.decompose()`
5. **`_CTA_RE` vs `_CTA_FUNNEL_RE`** in citability.py — sono due regex separate, non rinominarle
6. **`_compute_grade` citability** usa le stesse bande di `SCORE_BANDS` in config.py
7. **Max score nei formatter** — devono corrispondere ai pesi in SCORING (18/18/16/14/12/6/6/10)
