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
pip install -r requirements.txt
pip install pytest pytest-cov flake8

# 5. Make your changes
# 6. Run tests and linting
pytest tests/ -v
flake8 scripts/ --max-line-length=120

# 7. Commit (use Conventional Commits)
git commit -m "feat(audit): add timeout handling for network requests"

# 8. Push and open a Pull Request
git push origin feature/your-feature-name
```

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat(scope): add new feature` — new functionality
- `fix(scope): fix bug` — bug fixes
- `docs(scope): update docs` — documentation only
- `refactor(scope): refactor code` — code changes with no behavior change
- `test(scope): add tests` — adding missing tests
- `chore(scope): update build` — build process, dependencies, tooling

**Scopes:** `audit`, `llms`, `schema`, `install`, `docs`, `ci`

Examples:
```
feat(audit): add JSON output format with --format json
fix(llms): handle malformed XML sitemap gracefully
docs(readme): update installation instructions for Windows
test(audit): add unit tests for robots.txt parser
```

## Code Style

- **Python:** PEP 8 compliant (checked by flake8)
- **Line length:** 120 characters max
- **Imports:** Standard library → third-party → local, alphabetically sorted
- **Docstrings:** Required for all public functions
- **Type hints:** Encouraged but not mandatory

## Testing

**Required:** All new features and bug fixes must include tests.

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=scripts --cov-report=term-missing

# Run specific test file
pytest tests/test_audit.py -v
```

### Test Structure

```
tests/
├── test_audit.py       # geo_audit.py tests
├── test_llms.py        # generate_llms_txt.py tests
├── test_schema.py      # schema_injector.py tests
└── fixtures/           # Test data (HTML, XML, JSON)
```

### Writing Good Tests

```python
import pytest
from scripts.geo_audit import check_robots_txt

def test_robots_allows_gptbot():
    """Test that GPTBot is correctly identified as allowed."""
    content = "User-agent: GPTBot\nAllow: /"
    result = check_robots_txt(content)
    assert result['gptbot'] is True

def test_robots_blocks_gptbot():
    """Test that GPTBot is correctly identified as blocked."""
    content = "User-agent: GPTBot\nDisallow: /"
    result = check_robots_txt(content)
    assert result['gptbot'] is False
```

## Documentation

- **README.md:** User-facing installation and usage
- **docs/*.md:** In-depth guides and references
- **SKILL.md:** AI context files (update when adding features)
- **CHANGELOG.md:** Keep a Changelog format, update with every PR

When adding new features:
1. Update README.md with usage examples
2. Add relevant documentation in docs/
3. Update CHANGELOG.md under `[Unreleased]`
4. Update ai-context files if it changes tool behavior

## Pull Request Process

1. **One feature per PR** — keeps reviews focused and fast
2. **Update tests** — all tests must pass (CI checks this)
3. **Update CHANGELOG.md** — add your change under `[Unreleased]`
4. **Describe the problem** — what issue does this solve?
5. **Show the impact** — example output, before/after screenshots if applicable
6. **Be patient** — maintainers will review within 3-5 days

### PR Checklist

Before submitting:

- [ ] Code follows PEP 8 (checked with `flake8 scripts/`)
- [ ] Tests added and passing (`pytest tests/ -v`)
- [ ] CHANGELOG.md updated under `[Unreleased]`
- [ ] Documentation updated (if adding features)
- [ ] Commit messages follow Conventional Commits
- [ ] No merge conflicts with `main`

## Reporting Bugs

Use [GitHub Issues](https://github.com/auriti-labs/geo-optimizer-skill/issues) with this template:

**Expected behavior:**  
What should happen?

**Actual behavior:**  
What actually happens?

**Steps to reproduce:**
```bash
./geo scripts/geo_audit.py --url https://example.com
```

**Environment:**
- OS: Ubuntu 22.04 / macOS 14 / Windows 11
- Python version: `python --version`
- Installed via: `install.sh` / `pip install` / manual

**Error output:**
```
Paste full error traceback here
```

## Suggesting Features

Open a GitHub Issue with:

- **Problem statement:** What GEO challenge does this address?
- **Proposed solution:** How would the feature work?
- **Impact:** Who benefits? (developers, marketers, agencies)
- **Princeton KDD reference:** Does the feature implement a specific GEO method?

## Development Tips

### Running Scripts Without Install

```bash
# Activate venv first
source .venv/bin/activate

# Run directly
python scripts/geo_audit.py --url https://example.com

# Or use the wrapper (creates venv if missing)
./geo scripts/geo_audit.py --url https://example.com
```

### Testing Against Real Sites

```bash
# Test against your own site
./geo scripts/geo_audit.py --url https://yoursite.com

# Test schema injection (creates backup automatically)
./geo scripts/schema_injector.py --file test.html --type website --name "Test" --url https://test.com --inject
```

### Debugging

```python
# Add breakpoints
import pdb; pdb.set_trace()

# Or use ipdb for better experience
import ipdb; ipdb.set_trace()

# Print JSON structures nicely
import json
print(json.dumps(data, indent=2))
```

## Release Process (Maintainers Only)

1. Update `CHANGELOG.md` — move `[Unreleased]` to `[X.Y.Z] - YYYY-MM-DD`
2. Tag release: `git tag vX.Y.Z && git push origin vX.Y.Z`
3. GitHub Actions will run CI on the tag
4. Create GitHub Release with changelog excerpt
5. (Future) Publish to PyPI: `python -m build && twine upload dist/*`

## Questions?

- Open a [GitHub Discussion](https://github.com/auriti-labs/geo-optimizer-skill/discussions)
- Check existing [Issues](https://github.com/auriti-labs/geo-optimizer-skill/issues)
- Read the [docs](docs/)

---

**Thank you for contributing to making the web more AI-discoverable! 🚀**
