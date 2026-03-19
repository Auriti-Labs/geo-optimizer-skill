# CLAUDE.md — AI Assistant Context for geo-optimizer-skill

## Project Overview

GEO Optimizer Skill is a Generative Engine Optimization (GEO) toolkit that makes websites visible and citable by AI search engines (ChatGPT, Perplexity, Claude, Gemini). It audits sites, auto-generates `/llms.txt`, and generates/injects JSON-LD structured data. Research-backed by Princeton KDD 2024 paper.

**Version:** 3.0.1 | **License:** MIT | **Python:** 3.9–3.13

## Repository Structure

```
src/geo_optimizer/          # Main package
├── cli/                    # Click-based CLI (display layer, formatting)
│   ├── main.py             # CLI entry point with subcommands
│   ├── audit_cmd.py        # `geo audit` command
│   ├── llms_cmd.py         # `geo llms` command
│   ├── schema_cmd.py       # `geo schema` command
│   └── formatters.py       # Text/JSON/HTML/GitHub output formatters
├── core/                   # Business logic (returns dataclasses, NO printing)
│   ├── audit.py            # run_full_audit(), run_full_audit_async()
│   ├── llms_generator.py   # /llms.txt generation from sitemaps
│   ├── schema_injector.py  # JSON-LD schema generation & injection
│   ├── schema_validator.py # Manual schema validation (no jsonschema dep)
│   └── registry.py         # Plugin system: CheckRegistry, AuditCheck protocol
├── models/                 # Data structures
│   ├── config.py           # Centralized constants (AI_BOTS, SCORING, SCHEMA_TEMPLATES)
│   ├── results.py          # Result dataclasses (AuditResult, RobotsResult, etc.)
│   └── project_config.py   # YAML project config loading
├── utils/                  # Utilities
│   ├── http.py             # HTTP session with retry logic + SSRF prevention
│   ├── http_async.py       # Async HTTP client (httpx)
│   ├── validators.py       # SSRF/path traversal prevention
│   ├── robots_parser.py    # RFC 9309 compliant robots.txt parser
│   └── cache.py            # FileCache with TTL (disk-based)
├── web/                    # FastAPI micro-service (optional)
│   ├── app.py              # Endpoints: /, /api/audit, /badge, /report
│   ├── badge.py            # SVG badge generator
│   └── cli.py              # geo-web CLI entry point
└── i18n/                   # Internationalization (IT/EN)

tests/                      # 814 tests, 88% coverage, 18 test files
scripts/                    # Legacy scripts (geo_audit.py, generate_llms_txt.py)
docs/                       # 10 markdown documentation guides
ai-context/                 # Platform-specific AI context files
references/                 # Research references and templates
.github/workflows/          # CI/CD (ci.yml, docker.yml, publish.yml)
```

## Key Commands

```bash
# Install
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
pytest tests/ -v --cov=geo_optimizer --cov-report=term-missing
pytest tests/ -v -m "not network"    # Skip network-dependent tests

# Lint & format
ruff check src/ tests/               # Check lint
ruff format src/ tests/              # Auto-format
ruff check --fix src/ tests/         # Auto-fix lint issues

# CLI usage
geo audit --url <URL>                # Full GEO audit
geo llms --base-url <URL>            # Generate /llms.txt
geo schema --file <HTML> --analyze   # Analyze/generate JSON-LD
geo --version                        # Verify install
```

## Architecture Principles

1. **Separation of concerns:** `core/` contains business logic returning typed dataclasses (no side effects or I/O). `cli/` handles all display, formatting, and user interaction.
2. **Configuration centralization:** All constants live in `models/config.py` — AI_BOTS, SCORING weights, SCHEMA_TEMPLATES, CATEGORY_PATTERNS.
3. **Plugin architecture:** `CheckRegistry` singleton with `AuditCheck` protocol (PEP 544). Checks registered via entry points.
4. **Dataclass results:** All audit functions return typed dataclasses for programmatic API + CLI flexibility.
5. **Security-first:** SSRF prevention (20+ blocked IP ranges, DNS pinning), XSS protection, DoS limits, rate limiting.

## Code Style & Conventions

- **Linter/formatter:** Ruff (`ruff check` and `ruff format`)
- **Line length:** 120 characters max
- **Target Python:** 3.9 (minimum — use compatible syntax)
- **Import order:** Standard lib → third-party → local (sorted by ruff)
- **Docstrings:** Required for all public functions
- **Type hints:** Encouraged, using Python 3.9+ syntax
- **Commit convention:** Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`)
- **Ruff rules enabled:** E, F, W, I, UP, B, C4, SIM (see `pyproject.toml` for ignored rules)

## Testing Conventions

- Framework: pytest with `unittest.mock`
- Test markers: `@pytest.mark.legacy` (scripts/ imports), `@pytest.mark.network` (requires internet)
- Test paths configured in `pyproject.toml`: `testpaths = ["tests"]`, `pythonpath = ["src", "scripts"]`
- All HTTP calls must be mocked in unit tests
- Security tests are critical: `test_security_critical.py`, `test_ssrf_hardening.py`, `test_p0_security_fixes.py`

## CI/CD Pipeline

- **ci.yml:** Tests on Python 3.9, 3.11, 3.12, 3.13. Runs pytest with coverage, verifies CLI entry points, checks ruff formatting, runs pip-audit.
- **docker.yml:** Builds and publishes to GHCR
- **publish.yml:** Publishes to PyPI via OIDC trusted publisher
- Coverage uploaded to Codecov (Python 3.12 run)

## Dependencies

**Core:** click, requests, beautifulsoup4, lxml, urllib3
**Optional groups:** `[rich]` for colored tables, `[web]` for FastAPI service, `[dev]` for testing/linting

## Security Considerations

- SSRF prevention blocks all private/reserved IP ranges (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, etc.)
- SVG badge output is sanitized with `html.escape()`
- Response size capped at 10 MB, sitemap URLs capped at 10,000
- Rate limiting: 30 req/min per IP on audit endpoints
- HTTP 500 errors return generic messages; details logged server-side only
- Do not weaken any security validations without explicit justification

## Important Notes

- The `scripts/` directory contains legacy scripts — prefer using the `src/geo_optimizer/` package
- The `ai-context/` directory has platform-specific AI prompts (Claude, ChatGPT, Cursor, Windsurf, Kiro) — update these if core features change
- Web service is optional: `pip install geo-optimizer-skill[web]`
- Score bands: 0–40 critical, 41–70 foundation, 71–90 good, 91–100 excellent
