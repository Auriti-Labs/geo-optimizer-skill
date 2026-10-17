# GEO Optimizer — Local Setup

## Stack tecnologico

| Livello | Tecnologia | Versione minima |
|---------|------------|-----------------|
| Language | Python | 3.10+ (produzione), 3.10.12 (WSL) |
| CLI | Click | 8.0+ |
| HTTP | Requests / HTTPX | 2.28+ / 0.27+ |
| HTML parsing | BeautifulSoup4 | 4.12+ |
| Markup | lxml | 4.9+ |
| Web (opt) | FastAPI | 0.110+ |
| Web server (opt) | Uvicorn | 0.27+ |
| Templates | Jinja2 (dist) | — |
| Packaging | Setuptools | 68+ |
| Testing | Pytest | 7+ |
| Type checking | Mypy | — |
| Linting | Ruff | 0.8+ |
| Embedding (opt) | sentence-transformers | 2.2+ |
| LLM (opt) | openai, anthropic | 1.0+ / 0.30+ |
| MCP (opt) | mcp | 1.0+ |

## Repository

- **Repository principale:** https://github.com/auriti-labs/geo-optimizer-skill
- **Package PyPI:** geo-optimizer-skill
- **Live demo:** https://geoready.dev
- **Versione corrente:** v4.10.2 (2026-05-05)

## Installazione locale

### 1. Clonare il repository

```bash
cd geo-optimizer-skill
```

### 2. Creare virtualenv (opzionale ma raccomandato)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Installare package con dipendenze opzionali

Tutte le dipendenze:
```bash
pip install -e ".[all]"
```

Minime (solo dipendenze obbligatorie per CLI):
```bash
pip install -e .
```

Solo dipendenze di sviluppo:
```bash
pip install -e ".[dev]"
```

### 4. Verificare installazione CLI

```bash
geo --version
geo --help
geo audit --help
```

## Comandi principali in locale

### Audit di un sito
```bash
geo audit --url https://yoursite.com
geo audit --url https://yoursite.com --format json
geo audit --sitemap https://yoursite.com/sitemap.xml --max-urls 25
```

### Generazione file GEO
```bash
geo fix --url https://yoursite.com --apply
geo llms --base-url https://yoursite.com --site-name "My Site" --description "Desc" --output ./public/llms.txt
geo schema --type faq --url https://yoursite.com
```

### Confronto e monitoring
```bash
geo diff --before URL1 --after URL2
geo history --url https://yoursite.com
geo track --url https://yoursite.com --report --output ./track.html
```

## Comandi MCP e Web

### MCP Server (per Claude, Cursor, Windsurf)
```bash
geo-mcp
```

### FastAPI Web Demo
```bash
geo-web
# Available at: http://localhost:8000
```

## Verifica installazione

Eseguire i test localmente:

```bash
pytest tests/ -v --cov=geo_optimizer
ruff check src/geo_optimizer/
ruff format src/geo_optimizer/
```

## Docker (opzionale)

```bash
docker build -t geo-optimizer .
docker run -it geo-optimizer geo --version
```

## Setup per contribuire

1. Forkare il repo
2. Creare una feature branch: `git checkout -b feat/my-feature`
3. Installare dev: `pip install -e ".[dev]"`
4. Scrivere test → eseguire con `pytest`
5. Verificare formatting: `ruff check . && ruff format .`
6. Fare commit con conventional commit in italiano
7. Creare PR su GitHub

## Env vars opzionali (per LLM)

- `OPENAI_API_KEY`: per analisi cognitiva avanzata
- `ANTHROPIC_API_KEY`: per analisi con Claude

---

*Local setup validato su WSL2 (Ubuntu) con Python 3.10.12 e venv.*
