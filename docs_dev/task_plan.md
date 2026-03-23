# Task: Superare geo-seo-claude — Piano d'Azione v4.0

## Obiettivo
Rendere geo-optimizer-skill il miglior tool GEO open-source, colmando i gap funzionali rispetto a geo-seo-claude mantenendo la superiorità ingegneristica.

## Strategia
**Non copiare, superare.** Ogni feature nuova deve essere implementata meglio: testata, sicura, estensibile.

---

## Fase 0: Fix Critici (Sprint 0 — 2 giorni) ⚠️ BLOCKERS
> Problemi trovati dall'audit multi-agente. Da risolvere PRIMA di qualsiasi feature.

### Sprint 0A — Sicurezza Critica
- [ ] **0A.1 SSRF DNS Rebinding (TOCTOU)** — `validators.py:89` + `http.py:81`
  - `validate_public_url` risolve DNS, poi `fetch_url` fa seconda risoluzione
  - Fix: pin IP risolto e passarlo a fetch, oppure hook requests per bloccare post-validazione
- [ ] **0A.2 SSRF via HTTP Redirect** — `http.py:81`
  - `allow_redirects=True` segue redirect verso rete interna senza ri-validare
  - Fix: `allow_redirects=False` + loop manuale con validazione su ogni redirect
- [ ] **0A.3 Body scaricato intero prima del size check** — `http.py:81-90`
  - Senza `stream=True`, server malevolo può caricare 500MB in RAM
  - Fix: usare `stream=True` + `iter_content()` con contatore

### Sprint 0B — Debito Architetturale Critico
- [ ] **0B.1 Scoring duplicato in 4 formatter** — 20 funzioni identiche
  - `formatters.py`, `rich_formatter.py`, `html_formatter.py`, `github_formatter.py`
  - Fix: creare `core/scoring.py` con `CategoryDescriptor`, importare ovunque
- [ ] **0B.2 CheckRegistry mai integrato** — `registry.py` + `audit.py`
  - `run_all()` mai chiamato da `run_full_audit()`
  - Fix: integrare nel flusso audit, aggiungere `extra_checks` ad AuditResult

### Sprint 0C — Hardening
- [ ] **0C.1 Rate limiter `clear()` globale** — `app.py:84`
  - Fix: LRU eviction parziale invece di clear totale
- [ ] **0C.2 Rate limiter bypass via proxy** — `app.py:151`
  - Fix: `ProxyHeadersMiddleware` con trusted hosts
- [ ] **0C.3 Cache key 64-bit** — `app.py:97`
  - Fix: usare almeno 32 char hex (128 bit)
- [ ] **0C.4 XSS via `band` fallback** — `html_formatter.py`
  - Fix: whitelist-only per `band_label`
- [ ] **0C.5 POST body size illimitato** — `app.py:161`
  - Fix: check `content-length` header, max 4KB
- [ ] **0C.6 CSP `unsafe-inline`** — `app.py:47`
  - Fix: nonce o hash per script inline

### Sprint 0D — Bug e Inconsistenze
- [ ] **0D.1 `_llms_score()` senza guardia `found`** — `formatters.py:203`
  - Inconsistente con `audit.py`. Fix: `if not found: return 0`
- [ ] **0D.2 `classify_bot` ignora `Allow` specifici con `Disallow: /`** — `robots_parser.py:119`
  - Fix: se `has_any_allow`, classificare come "allowed" parziale
- [ ] **0D.3 `except (JSONDecodeError, Exception): pass`** — `schema_injector.py:187`
  - Fix: catch specifico + logging debug
- [ ] **0D.4 `soup.get_text()` senza separator** — `audit.py:214`
  - Fix: `soup.get_text(separator=" ", strip=True)`
- [ ] **0D.5 URL invalido in geo_audit.py causa timeout** — `scripts/geo_audit.py`
  - ✅ FIXATO dall'agente debugger

### Sprint 0E — Performance
- [ ] **0E.1 Nuova `requests.Session` ad ogni chiamata** — `llms_generator.py:71,189,396`
  - Fix: passare sessione come parametro
- [ ] **0E.2 `fetch_page_title()` seriale** — `llms_generator.py:296`
  - Fix: `ThreadPoolExecutor(max_workers=10)`
- [ ] **0E.3 Regex non precompilate** — `llms_generator.py:139,159`
  - Fix: precompilare a livello modulo
- [ ] **0E.4 Sitemap bomb senza limite URL totali** — `llms_generator.py:88`
  - Fix: `MAX_TOTAL_URLS = 10_000`

### Sprint 0F — Test Coverage
- [ ] **0F.1 `core/registry.py`** — 0% copertura
- [ ] **0F.2 `i18n/__init__.py`** — 0% copertura
- [ ] **0F.3 `web/cli.py`** — 0% copertura
- [ ] **0F.4 `cli/github_formatter.py`** — 0% copertura
- [ ] **0F.5 `run_full_audit_async`** — 0% copertura (feature performance principale)
- [ ] **0F.6 `web/app.py` endpoint** — nessun test HTTP via TestClient
- [ ] **0F.7 Path cache-hit in `run_full_audit`** — mai testato

### Sprint 0G — CI/CD
- [ ] **0G.1 `publish.yml` non dipende da CI** — può pubblicare con test rotti
- [ ] **0G.2 Aggiungere mypy/pyright** — type checking
- [ ] **0G.3 Aggiungere Dependabot** — `.github/dependabot.yml`
- [ ] **0G.4 Cache pip in CI** — `actions/cache`
- [ ] **0G.5 Concurrency group** — cancella run obsolete su PR
- [ ] **0G.6 Exec form in Dockerfile.web** — SIGTERM non propagato a uvicorn

### Sprint 0H — Config YAML Dead Code
- [ ] **0H.1 `extra_bots`** — caricato da config ma mai usato
- [ ] **0H.2 `min_score`** — campo config ignorato
- [ ] **0H.3 `verbose`** — campo config ignorato
- [ ] **0H.4 `run_full_audit_async` duplica `audit_llms_txt`** — estrarre logica condivisa

### Sprint 0I — Codice Non Idiomatico
- [ ] **0I.1 Typing obsoleto** — `List`, `Dict`, `Optional` → builtin 3.9+
- [ ] **0I.2 Ruff senza regole UP/B/C4/SIM** — `pyproject.toml:101`
- [ ] **0I.3 `httpx.AsyncClient` senza `async with`** — `http_async.py:49`
- [ ] **0I.4 `CachedResponse` classe locale** — usare SimpleNamespace/dataclass

---

## Fase 1: Fondamenta Architetturali (Sprint 1 — 3-4 giorni)
> Prerequisito per le nuove feature. Dipende da Sprint 0B completato.

- [ ] **1.1 Creare `core/scoring.py` con CategoryDescriptor**
  - Unica fonte di verità per scoring per categoria
  - `BUILTIN_CATEGORIES` con 5 descrittori (robots, llms, schema, meta, content)
  - `compute_categories_score(result)` rimpiazza `compute_geo_score()`
  - Tutti i 4 formatter importano da qui — zero duplicazione

- [ ] **1.2 Spostare `CheckResult` in `models/results.py`**
  - Evita import circolari `core/` ↔ `models/`
  - `AuditResult.extra_checks: Dict[str, CheckResult]` + `plugin_score: int`

- [ ] **1.3 Ristrutturare SCORING con 8 categorie**
  - Nuova distribuzione pesi (vedi Fase 0 per tabella)
  - Flag `--scoring-version v3|v4` per backward compat

---

## Fase 2: Colmare il Gap di Dominio (Sprint 2 — 5-6 giorni)
> Le feature che geo-seo-claude ha e noi no.

- [ ] **2.1 E-E-A-T Scoring** (peso: 15%) — `core/checks/eeat_check.py`
- [ ] **2.2 Brand Mention Scanner** (peso: 12%) — `core/checks/brand_check.py`
- [ ] **2.3 AI Platform Readiness** (peso: 10%) — `core/checks/platform_check.py`

---

## Fase 3: Superare geo-seo-claude (Sprint 3 — 4-5 giorni)
> Feature killer che nessuno ha.

- [ ] **3.1 Citability Scorer** con mappatura 9 metodi Princeton
- [ ] **3.2 Competitor Comparison** (`--compare`)
- [ ] **3.3 CI/CD Integration** (SARIF, JUnit, `--threshold --exit-code`)
- [ ] **3.4 Trend Tracking** (SQLite locale)

---

## Fase 4: UX e Distribuzione (Sprint 4 — 3-4 giorni)

- [ ] **4.1 PDF Report** professionale — dipendenza `[pdf]`
- [ ] **4.2 Claude Code Skill** di prima classe
- [ ] **4.3 One-liner install** + GIF demo
- [ ] **4.4 Web Demo migliorata** con compare mode

---

## Fase 5: Marketing e Growth (Sprint 5 — 2 settimane)

### Settimana 1 — Base (0 budget, 4-6 ore)
- [ ] **5.1 Topics GitHub + About section** (30 min)
- [ ] **5.2 Keywords PyPI ampliate** + description update (30 min)
- [ ] **5.3 Rewrite hook README** per urgenza emotiva (1 ora)
- [ ] **5.4 Deploy demo web + badge SVG pubblico** (2-3 ore)

### Settimana 2 — Distribuzione
- [ ] **5.5 GIF demo** nel README (1 ora)
- [ ] **5.6 Post HackerNews** "Show HN" (timing: lunedì/martedì EST)
- [ ] **5.7 Post Reddit** r/Python + r/SEO
- [ ] **5.8 GitHub Action sul Marketplace** (primi nel segmento GEO)

### Settimana 3-4 — Conversione
- [ ] **5.9 Sezione "Results with real sites"** nel README
- [ ] **5.10 Product Hunt launch**

---

## Fase 6: Community (ongoing)

- [ ] **6.1 Docs MkDocs** — Getting Started, CLI Ref, API Ref, Plugin Dev
- [ ] **6.2 Plugin ecosystem** — template cookiecutter + plugin esempio WP
- [ ] **6.3 Contributing guide** + Code of Conduct
- [ ] **6.4 `.env.example`** per variabili Railway

---

## Decisioni Architetturali

| Decisione | Rationale | Data |
|-----------|-----------|------|
| 8 categorie scoring vs 5 | Copertura superiore a geo-seo-claude (6 cat.) | 2026-03-09 |
| CategoryDescriptor pattern | Elimina 20 funzioni duplicate, OCP per nuove categorie | 2026-03-09 |
| Nuove categorie come AuditCheck nel registry | Integra plugin system esistente, estensibile a terze parti | 2026-03-09 |
| 5 campi typed + extra_checks dict | Backward compat API pubblica + estensibilità | 2026-03-09 |
| PDF come dipendenza opzionale [pdf] | Non appesantire l'installazione base | 2026-03-09 |
| Scoring v3/v4 flag | Backward compat per utenti esistenti | 2026-03-09 |
| SSRF fix con redirect validation loop | Più sicuro di `allow_redirects=True` | 2026-03-09 |

## Inventario Problemi (52 totali)

| Severità | Conteggio | Sprint target |
|----------|-----------|---------------|
| Critici | 7 | Sprint 0A-0B |
| Alti | 15 | Sprint 0C-0D |
| Medi | 16 | Sprint 0E-0G |
| Bassi | 14 | Sprint 0H-0I |

## Metriche di Successo

- [ ] 0 vulnerabilità critiche (SSRF, XSS)
- [ ] Scoring deduplicato (1 source of truth vs 4 copie)
- [ ] CheckRegistry integrato e funzionante
- [ ] Score 0-100 con 8 categorie
- [ ] 100% test coverage su nuove feature
- [ ] CI/CD con type checking + dependency management
- [ ] Competitor comparison (unici nel mercato)
- [ ] < 5 secondi per audit completo (async)
- [ ] 100+ stelle GitHub entro 3 mesi dal launch
