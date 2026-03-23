# Findings — Audit Completo GEO Optimizer (9 Agenti, 2 Round)

## Inventario Totale: ~85 problemi unici

---

## ROUND 1 — 4 Agenti (Code Review, Security, Consistency, Performance)

### Sicurezza Critica (7)
1. SSRF DNS Rebinding TOCTOU — `validators.py:89` + `http.py:81`
2. SSRF via HTTP Redirect chain — `http.py:81` allow_redirects=True
3. Body scaricato intero prima del size check — `http.py:81-90`
4. Rate limiter `clear()` globale — `app.py:84`
5. Rate limiter bypass via proxy (X-Forwarded-For) — `app.py:151`
6. Cache key 64-bit (collisione) — `app.py:97`
7. XSS via `band` fallback non whitelist — `html_formatter.py`

### Architettura (5)
8. Scoring duplicato in 4 formatter (20 funzioni identiche)
9. CheckRegistry mai integrato (`run_all()` mai chiamato)
10. `_llms_score()` senza guardia `found` — `formatters.py:203`
11. `extra_bots` da config YAML mai usato — `audit_cmd.py:46`
12. `min_score` e `verbose` da config ignorati

### Bug Logici (5)
13. `classify_bot` ignora `Allow` specifici con `Disallow: /` — `robots_parser.py:119`
14. `except (JSONDecodeError, Exception): pass` silenzioso — `schema_injector.py:187`
15. `soup.get_text()` senza separator — `audit.py:214`
16. `url_to_label` isdigit() fallisce su segmenti numerici con separatori
17. URL invalido in geo_audit.py causa timeout — ✅ FIXATO

### Performance (4)
18. Nuova Session HTTP per ogni chiamata — `llms_generator.py:71,189,396`
19. `fetch_page_title()` seriale — `llms_generator.py:296`
20. Regex non precompilate — `llms_generator.py:139,159`
21. Sitemap bomb senza limite URL totali

### Codice Non Idiomatico (5)
22. Typing `List/Dict/Optional` obsoleto (Python 3.9+ usa builtin)
23. Ruff senza regole UP/B/C4/SIM
24. `httpx.AsyncClient` senza `async with`
25. `CachedResponse` classe locale ridefinita
26. `run_full_audit_async` duplica logica `audit_llms_txt`

---

## ROUND 2 — 5 Agenti (Test, Architettura, CI/CD, Marketing, Runtime)

### Test Coverage Gap (8)
27. `core/registry.py` — 0% copertura
28. `i18n/__init__.py` — 0% copertura
29. `web/cli.py` — 0% copertura
30. `cli/github_formatter.py` — 0% copertura
31. `run_full_audit_async` — 0% (feature performance principale)
32. `web/app.py` endpoint — nessun test HTTP via TestClient
33. Path cache-hit in `run_full_audit` — mai testato
34. Mock `test_http_utils.py` bypass HTTPAdapter/Retry — test triviale

### CI/CD (6)
35. `publish.yml` non dipende da CI — PyPI con test rotti
36. Nessun type checking (mypy/pyright)
37. Nessun lockfile + nessun Dependabot
38. Nessun cache pip in CI
39. Dockerfile.web CMD non propaga SIGTERM
40. Nessun concurrency group per PR

---

## ROUND 3 — 5 Agenti (Web App, Scoring, Mercato, Docs, CLI UX)

### Web App / API (12)
41. POST body non validato con Pydantic — 500 su url non-stringa
42. Report "permanente" = cache in-memory TTL 1h — docstring falsa
43. `_audit_result_to_dict` perde 10+ campi dei dataclass
44. Nessun `Retry-After` header nel 429
45. Badge silenzioso su errori (mostra "0/100 CRITICAL")
46. Badge larghezza calcolata approssimativamente per font proporzionale
47. `asyncio.to_thread` senza timeout esplicito
48. `X-XSS-Protection` deprecato nei browser moderni
49. Nessun SSE/WebSocket per progresso audit real-time
50. Homepage solo in inglese vs CLI in italiano
51. `redoc_url=None` disabilita ReDoc senza motivo
52. Endpoint `/health` senza metriche cache

### Scoring Accuracy (13)
53. **Content quality sottopesato** — 15/100 ma copre i metodi Princeton top 3
54. **Metodo 3 (citazioni/blockquote)** — completamente assente (+30-40% Princeton)
55. **Metodo 4 (linguaggio autorevole)** — assente
56. **Bingbot mancante** da AI_BOTS e CITATION_BOTS — Copilot ignorato
57. **Claude-SearchBot** mancante — nuovo bot Anthropic 2025
58. **Fallback wildcard** rende `citation_bots_ok` quasi sempre True
59. **`has_numbers` regex** con falsi positivi (anni, ID, codici postali)
60. **`word_count`** calcolato ma mai scorato
61. **`has_description` llms.txt** non contribuisce al punteggio (bug vs spec)
62. **Article/Organization** schema a 0 punti
63. **`/llms-full.txt`** non verificato
64. **robots.txt a 20/100** — peso eccessivo per configurazione default
65. **Qualità link** non valutata (dominio .gov/.edu vs Facebook)

### Documentazione (12)
66. **TUTTI i docs/ e ai-context/ usano sintassi legacy** `./geo scripts/`
67. `--verbose` documentato "coming soon" in v3.0 (implementato da v1.5)
68. Python 3.8+ in getting-started vs 3.9+ ovunque
69. Meta tags "5pt each" in docs — falso, sono 5/8/3/4
70. `pip install geo-optimizer` nel README — pacchetto è `geo-optimizer-skill`
71. README parla di "v2.0" come novità, siamo a v3.0
72. SCORING_RUBRIC fermo a v1.5.0
73. Nessuna docs per web demo, plugin system, Python API, optional deps
74. CODE_OF_CONDUCT.md mancante
75. SECURITY.md mancante
76. Issue/PR templates mancanti
77. GitHub Copilot context file mancante

### CLI UX (8)
78. `llms` scrive messaggi di stato su stdout — rompe `> llms.txt`
79. `--verbose` in audit non fa nulla
80. Exit code per score sotto soglia non implementato
81. `format_audit_rich` usa `export_text()` — colori persi
82. Nessuno spinner/progress durante audit (10-30s muti)
83. `schema_cmd.py` errori su stdout invece di stderr
84. `--lang` accetta valori arbitrari senza `click.Choice`
85. Nessun esempio negli help text

### Mercato / Posizionamento
- 55 repo nel topic GEO, pochi sono tool reali (la maggior parte sono liste/skill)
- Tool commerciali ($29-$989/mese) fanno monitoring, NON audit tecnico — nostro differenziatore
- Paper settembre 2025: earned media > brand-owned content per AI citation
- llms.txt adozione reale: ~0.3% top 1000 siti — segnale forward-looking
- `Claude-SearchBot` nuovo bot Anthropic 2025 — manca dal nostro config

---

## Distribuzione per Severità

| Severità | Round 1 | Round 2 | Round 3 | Totale |
|----------|---------|---------|---------|--------|
| Critico | 7 | 3 | 5 | **15** |
| Alto | 8 | 5 | 10 | **23** |
| Medio | 6 | 4 | 12 | **22** |
| Basso | 5 | 4 | 16 | **25** |
| **Totale** | **26** | **16** | **43** | **85** |
