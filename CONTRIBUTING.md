# Contributing to GEO Optimizer

Thank you for considering contributing! GEO Optimizer aims to make websites more visible to AI search engines, and every improvement helps thousands of site owners.

## Quick Start

```bash
# 1. Fork the repo on GitHub
# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/geo-optimizer-skill.git
cd geo-optimizer-skill

# 3. Create a branch
git checkout -b feature/your-feature-name

# 4. Set up development environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 5. Make your changes
# 6. Run tests and linting
pytest tests/ -v
ruff check src/ tests/
ruff format --check src/ tests/

# 7. Commit (use Conventional Commits)
git commit -m "feat(audit): add timeout handling for network requests"

# 8. Push and open a Pull Request
git push origin feature/your-feature-name
```

## Project Architecture

```
src/geo_optimizer/
├── cli/             # Click commands — handles display, I/O
│   ├── main.py      # CLI group: geo audit, geo fix, geo llms, geo schema
│   ├── audit_cmd.py # Audit command with 7 output formats
│   ├── fix_cmd.py   # Auto-fix (robots, llms, schema, meta, ai_discovery)
│   ├── formatters.py        # text + json formatters
│   ├── rich_formatter.py    # Colored terminal (ASCII art dashboard)
│   ├── html_formatter.py    # Self-contained HTML report
│   ├── github_formatter.py  # GitHub Actions annotations
│   └── scoring_helpers.py   # Score display helpers
├── core/            # Business logic — returns dataclasses, NEVER prints
│   ├── audit.py             # Orchestrator: run_full_audit() + async variant
│   ├── audit_meta.py        # Meta tags audit
│   ├── audit_signals.py     # Signals (lang, RSS, freshness)
│   ├── audit_content.py     # Content quality checks
│   ├── audit_js.py          # JS rendering detection
│   ├── audit_schema.py      # JSON-LD schema analysis
│   ├── audit_brand.py       # Brand & Entity signals
│   ├── audit_cdn.py         # CDN crawler access
│   ├── audit_webmcp.py      # WebMCP readiness
│   ├── audit_negative.py    # Negative signals detection
│   ├── audit_robots.py      # robots.txt analysis (fetch_url)
│   ├── audit_llms.py        # llms.txt analysis (fetch_url)
│   ├── audit_ai_discovery.py # AI discovery endpoints (fetch_url)
│   ├── citability.py        # 47 citability methods (~3500 lines)
│   ├── scoring.py           # Engine scoring (weights from config.py)
│   ├── injection_detector.py # Prompt Injection Detection (8 categories)
│   ├── fixer.py             # Fix generation (robots, llms, schema, meta)
│   ├── llms_generator.py    # Sitemap → llms.txt
│   ├── schema_injector.py   # HTML analysis + JSON-LD injection
│   ├── schema_validator.py  # JSON-LD validation
│   └── registry.py          # Plugin system (CheckRegistry + AuditCheck Protocol)
├── models/
│   ├── config.py        # ALL constants: AI_BOTS (27), SCORING, SCHEMA_TEMPLATES
│   ├── results.py       # Result dataclasses (AuditResult, RobotsResult, etc.)
│   └── project_config.py # YAML project configuration
├── utils/
│   ├── http.py          # fetch_url() with anti-SSRF + DNS pinning + retry
│   ├── http_async.py    # httpx async client
│   ├── cache.py         # FileCache with TTL
│   ├── validators.py    # Anti-SSRF, path validation
│   └── robots_parser.py # RFC 9309 compliant parser
├── web/             # FastAPI web demo
│   ├── app.py       # Endpoints: /, /api/audit, /badge, /report, /compare
│   ├── badge.py     # SVG badge generator
│   └── cli.py       # geo-web CLI entry point
├── mcp/             # MCP server (12 tools, 5 resources)
└── i18n/            # Internationalization (gettext IT/EN)
```

**Key design pattern**: core modules return dataclasses (`models/results.py`), CLI layer formats output. All constants are centralized in `models/config.py`.

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat(scope): add new feature` — new functionality
- `fix(scope): fix bug` — bug fixes
- `docs(scope): update docs` — documentation only
- `refactor(scope): refactor code` — code changes with no behavior change
- `test(scope): add tests` — adding missing tests
- `chore(scope): update build` — build process, dependencies, tooling

**Scopes:** `audit`, `llms`, `schema`, `web`, `i18n`, `cli`, `docs`, `ci`

Examples:
```
feat(audit): add JSON output format with --format json
fix(llms): handle malformed XML sitemap gracefully
feat(web): add badge SVG endpoint
test(audit): add unit tests for robots.txt parser
```

## Code Style

- **Linter/Formatter:** ruff (replaces flake8)
- **Line length:** 120 characters max
- **Imports:** Standard library → third-party → local, sorted by ruff
- **Docstrings:** Required for all public functions
- **Type hints:** Encouraged but not mandatory (Python 3.9+ syntax)

```bash
# Check lint
ruff check src/ tests/

# Auto-fix lint issues
ruff check --fix src/ tests/

# Check formatting
ruff format --check src/ tests/

# Auto-format
ruff format src/ tests/
```

## Testing

**Required:** All new features and bug fixes must include tests.

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=geo_optimizer --cov-report=term-missing

# Run specific test file
pytest tests/test_audit.py -v

# Run single test
pytest tests/test_audit.py::test_name -v

# Skip network-dependent tests
pytest tests/ -v -m "not network"
```

### Writing Good Tests

```python
from unittest.mock import patch, MagicMock
from geo_optimizer.core.audit import run_full_audit
from geo_optimizer.models.results import AuditResult

def test_audit_returns_result():
    """Test that audit returns a valid AuditResult."""
    with patch("geo_optimizer.core.audit.fetch_url") as mock_fetch:
        mock_fetch.return_value = MagicMock(status_code=200, text="<html>...</html>")
        result = run_full_audit("https://example.com")
        assert isinstance(result, AuditResult)
        assert 0 <= result.score <= 100
```

## Writing Plugins

GEO Optimizer supports custom audit checks via the plugin system:

```python
# In your package's pyproject.toml:
# [project.entry-points."geo_optimizer.checks"]
# my_check = "my_package:MyCheck"

from geo_optimizer import AuditCheck, CheckResult

class MyCheck:
    name = "my_custom_check"
    description = "Checks for something custom"
    max_score = 10

    def run(self, url: str, html: str, **kwargs) -> CheckResult:
        passed = "my-element" in html
        return CheckResult(
            name=self.name,
            score=10 if passed else 0,
            max_score=self.max_score,
            passed=passed,
            details={"found": passed},
            message="Custom check passed" if passed else "Custom check failed",
        )
```

## Pull Request Process

1. **One feature per PR** — keeps reviews focused and fast
2. **Update tests** — all tests must pass (CI checks this)
3. **Update CHANGELOG.md** — add your change under `[Unreleased]`
4. **Describe the problem** — what issue does this solve?
5. **Show the impact** — example output, before/after screenshots if applicable

### What We Don't Accept

The following types of PRs will be declined without review:

- **Vendor integrations:** PRs that add third-party commercial tools, GitHub Actions, or services to our CI/CD pipeline. We build and choose our own tooling.
- **Promotional rewrites:** PRs that restructure project files to conform to a specific vendor's format or ecosystem, even if presented as improvements.
- **Undiscussed rewrites:** Large-scale rewrites of existing files without a prior issue discussion. Open an issue first to align on scope and direction.

If you work for a company and want to contribute, that's welcome — just contribute code or fixes that stand on their own merit, independent of your employer's products.

### PR Checklist

Before submitting:

- [ ] Code passes lint (`ruff check src/ tests/`)
- [ ] Code is formatted (`ruff format --check src/ tests/`)
- [ ] Tests added and passing (`pytest tests/ -v`)
- [ ] CHANGELOG.md updated under `[Unreleased]`
- [ ] Documentation updated (if adding features)
- [ ] Commit messages follow Conventional Commits
- [ ] No merge conflicts with `main`

## Reporting Bugs

Use [GitHub Issues](https://github.com/auriti-labs/geo-optimizer-skill/issues) with:

**Expected behavior:** What should happen?

**Actual behavior:** What actually happens?

**Steps to reproduce:**
```bash
geo audit --url https://example.com
```

**Environment:**
- OS: Ubuntu 22.04 / macOS 14 / Windows 11
- Python version: `python --version`
- geo-optimizer version: `geo --version`

## Suggesting Features

Open a GitHub Issue with:

- **Problem statement:** What GEO challenge does this address?
- **Proposed solution:** How would the feature work?
- **Impact:** Who benefits? (developers, marketers, agencies)
- **Princeton KDD reference:** Does the feature implement a specific GEO method?

## Release Process (Maintainers Only)

1. Update `CHANGELOG.md` — move `[Unreleased]` to `[X.Y.Z] - YYYY-MM-DD`
2. Update version in `pyproject.toml` and `src/geo_optimizer/__init__.py`
3. Tag release: `git tag vX.Y.Z && git push origin vX.Y.Z`
4. GitHub Actions publishes to PyPI (OIDC trusted publisher)
5. Create GitHub Release with changelog excerpt

## Optional Dependencies

```bash
pip install geo-optimizer-skill[rich]    # Colored CLI tables
pip install geo-optimizer-skill[config]  # YAML project config
pip install geo-optimizer-skill[async]   # Parallel HTTP fetch
pip install geo-optimizer-skill[web]     # Web demo (FastAPI)
pip install geo-optimizer-skill[dev]     # pytest + ruff
```

---

**Thank you for contributing to making the web more AI-discoverable!**
