# AGENTS.md

## Project Context

GEO Optimizer is an open-source Python toolkit for Generative Engine Optimization. It audits and improves websites so they are more discoverable and citable by AI search engines such as ChatGPT, Perplexity, Claude, and Gemini.

Current project shape:
- Python package with CLI commands, core audit/fix logic, FastAPI web demo, and MCP server support
- MIT licensed
- Python 3.9+ compatibility is required

Primary user-facing surfaces:
- `geo audit`
- `geo fix`
- `geo llms`
- `geo schema`
- `geo-web`

## Repository Map

Top-level structure:
- `src/geo_optimizer/cli/`: Click presentation layer and output formatters
- `src/geo_optimizer/core/`: business logic, scoring, audit execution, fix generation
- `src/geo_optimizer/models/`: dataclasses and centralized config/constants
- `src/geo_optimizer/utils/`: HTTP, validation, cache, parsers
- `src/geo_optimizer/web/`: FastAPI app, badge generation, web entrypoints
- `src/geo_optimizer/mcp/`: MCP server tools/resources
- `src/geo_optimizer/i18n/`: translations
- `tests/`: pytest suite, mostly mocked end-to-end and unit coverage

Important file roles:
- `models/config.py`: centralized constants, scoring weights, schema templates, bot lists
- `models/results.py`: result dataclasses
- `core/audit.py`: full audit orchestration
- `utils/http.py`: secure fetching, anti-SSRF, response size protections
- `utils/validators.py`: public URL and safe-path validation

## Architectural Rules

These are hard constraints:

1. `core/` must never print or directly format output.
   Return dataclasses from `models/results.py`.

2. Keep CLI and formatter logic in `cli/`.
   `cli/*` can call core and format results; core must not depend on CLI.

3. Keep constants centralized.
   Do not hardcode scoring weights, AI bot lists, or schema defaults outside `models/config.py`.

4. Preserve Python 3.9 compatibility.
   Every Python file under `src/` must include:
   ```python
   from __future__ import annotations
   ```
   Also avoid relying on Python 3.10+ only behavior, including newer `entry_points()` assumptions.

5. Respect dependency direction.
   - `core/*` may import from `models/*`
   - `cli/*` may import from `core/*` and `models/*`
   - `models/*` must not import from `core/*` or `cli/*`

6. Preserve plugin architecture.
   Plugin checks are loaded through `entry_points("geo_optimizer.checks")` and use the `AuditCheck` protocol.

## Security Rules

Security-sensitive behavior is non-negotiable:

1. Never bypass anti-SSRF protections.
   Any user URL must go through validation and secure fetch flow.

2. Do not introduce direct `requests.get()` or equivalent on unvalidated user input.

3. Do not enable unsafe redirect behavior.
   `allow_redirects=True` must not be introduced for user-controlled fetches.

4. Preserve DNS pinning and URL validation behavior in the HTTP stack.

5. Keep response streaming and size checks in place.
   Large responses must still honor the configured `MAX_RESPONSE_SIZE`.

6. Be careful with circular import boundaries.
   `utils/http.py` intentionally imports validators inside functions.

## Audit and Scoring Model

The GEO score totals 100 points across these categories:
- Robots.txt: 18
- llms.txt: 18
- Schema JSON-LD: 16
- Meta Tags: 14
- Content: 12
- Signals: 6
- AI Discovery: 6
- Brand & Entity: 10

Score bands:
- `86-100`: excellent
- `68-85`: good
- `36-67`: foundation
- `0-35`: critical

When modifying scoring or output:
- keep formatter totals aligned with config weights
- keep `_compute_grade` behavior aligned with score bands
- avoid silent drift between display code and scoring code

## Data Flow Expectations

Typical audit flow:

```text
URL -> validation -> fetch_url() -> BeautifulSoup -> sub-audits -> dataclasses -> score computation -> formatter/web/API output
```

Separation expectations:
- core functions return typed result objects
- formatters convert results to text, JSON, HTML, SARIF, JUnit, GitHub summaries, or rich terminal output
- web endpoints should reuse the same core logic, not fork business rules

## Testing Expectations

The test suite is heavily mocked and should remain that way.

Rules:
- use `pytest`
- prefer `unittest.mock.patch`, `Mock`, `MagicMock`
- use `click.testing.CliRunner` for CLI tests
- no real HTTP in normal tests
- preserve AAA style where practical

Naming convention:
- `test_{module}_{scenario}_{expectation}`

Common testing guidance:
- mock `fetch_url()` return values as tuples
- maintain compatibility with legacy mocks that use `.content` or `._content`
- keep tests compatible with `pythonpath = ["src", "scripts"]`

Markers currently in use:
- `@pytest.mark.legacy`
- `@pytest.mark.network`

## Project-Specific Gotchas

Watch for these before editing:

1. `from __future__ import annotations` is required in every `src/` Python file.
2. `audit_js_rendering` must not mutate the original soup; it should operate on a deep copy.
3. The JSON-LD parser must support both direct `@type` and `@graph`.
4. `_CTA_RE` and `_CTA_FUNNEL_RE` in `citability.py` are distinct and should not be collapsed.
5. Formatter max scores must match the scoring config exactly.
6. Some legacy tests rely on non-ideal import order and have Ruff exceptions by design.

## Style and Conventions

Code style:
- `snake_case.py` filenames
- snake_case functions
- PascalCase dataclasses
- constants in ALL_CAPS
- docstrings in Google style, in Italian
- inline comments in Italian when useful, often with issue references

Tooling:
- Ruff is the formatter/linter baseline
- line length: 120
- target: py39

Useful commands:

```bash
pip install -e ".[dev]"
pytest tests/ -v
pytest tests/ -v --cov=geo_optimizer
ruff check src/geo_optimizer/
ruff format src/geo_optimizer/
```

## Guidance for Future Agents

When making changes:
- prefer small, localized edits that preserve layer boundaries
- add or update tests with behavior changes
- do not move business logic into CLI or web handlers
- do not duplicate config values that already exist centrally
- treat HTTP, validation, and scoring code as security- and regression-sensitive
- preserve compatibility with both CLI and web/demo consumers

When adding features:
- wire new user-facing behavior through core result models first
- expose presentation details in formatters or web handlers second
- keep plugin compatibility and mocked testability in mind from the start
