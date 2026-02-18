# Changelog

All notable changes to GEO Optimizer are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/) · [SemVer](https://semver.org/)

---

## [Unreleased]

- PyPI package (`pip install geo-optimizer`)
- Weekly GEO score tracker with trend reporting
- Support for Hugo, Jekyll, Nuxt

---

## [1.3.0] — 2026-02-18

### Added

- `ai-context/kiro-steering.md` — Kiro steering file with `inclusion: fileMatch` + `fileMatchPattern` array; file goes in `.kiro/steering/`
- `ai-context/cursor.mdc` — Cursor rules format with YAML frontmatter (`globs`, `alwaysApply`)
- `ai-context/windsurf.md` — Windsurf rules format with YAML frontmatter + glob activation
- `ai-context/claude-project.md` — full GEO context for Claude Projects (no size limit)
- `ai-context/chatgpt-custom-gpt.md` — compressed for ChatGPT GPT Builder (<8,000 chars)
- `ai-context/chatgpt-instructions.md` — ultra-compressed for ChatGPT Custom Instructions (<1,500 chars)
- Complete documentation suite (`docs/`) — 8 pages covering all scripts, methods, and platform setup
- `SKILL.md` — universal platform index with file table and quick-copy commands
- Professional README redesign: collapsible script docs, visual audit output sample, badges

### Fixed

- Lazy dependency imports — `--help` always works even without dependencies installed
- Inline comment stripping in robots.txt parser (e.g. `User-agent: GPTBot # note`)
- Duplicate WebSite schema detection now emits a warning instead of silently ignoring
- `install.sh` `--dir` flag bug (was incorrectly parsed in some shells)
- `./geo` wrapper path resolution — now always resolves to absolute path
- FAQ placeholder mode with clear `REPLACE:` markers and user warning
- Removed all hardcoded site-specific references — fully generic examples throughout
- Removed all OpenClaw internal references — fully standalone tool

### Changed

- README rewritten as public-facing documentation (professional layout, no internal refs)
- `SKILL.md` rewritten as universal AI context index (Claude/ChatGPT/Gemini/Cursor/Windsurf/Kiro)
- GEO score thresholds aligned to documentation: `>=91=EXCELLENT, >=71=GOOD, >=41=FAIR, <41=CRITICAL`
- Schema scoring redistributed: `has_website=10`, `has_faq=10`, `has_webapp=5` (webapp is bonus, not core)
- All user-visible messages and script docstrings use `./geo` prefix consistently
- `update.sh` is now venv-aware

---

## [1.2.0] — 2026-02-18

### Changed

- Full English translation of all files (README, SKILL.md, inline comments, docstrings)
- README rewritten with cleaner structure, Quick Start path clarified

### Fixed

- Italian comments removed from scripts
- CHANGELOG rewritten for public audience (removed internal notes)
- `ai-bots-list.md` dates updated to 2026

---

## [1.1.0] — 2026-02-18

### Fixed

- Relative paths throughout — no more hardcoded absolute paths
- Duplicate `PerplexityBot` entry removed from `AI_BOTS` dict
- Astro examples made fully generic (no site-specific names)
- GEO score calculation now reflects actual achievable scores

### Changed

- SKILL.md updated with corrected paths and examples
- README sections improved for clarity

---

## [1.0.0] — 2026-02-18

### Added

**Scripts**
- `scripts/geo_audit.py` — automated GEO audit, scores any website 0–100
  - Checks: robots.txt (13 AI bots), /llms.txt (structure + links), JSON-LD schema (WebSite/WebApp/FAQPage), meta tags (title/description/canonical/OG), content quality (headings/statistics/citations)

- `scripts/generate_llms_txt.py` — auto-generates `/llms.txt` from XML sitemap
  - Auto-detects sitemap from robots.txt Sitemap directive
  - Supports sitemap index files (multi-sitemap)
  - Groups URLs by category (Tools, Finance, Blog, etc.)
  - Generates structured markdown with H1, blockquote, sections, links

- `scripts/schema_injector.py` — generates and injects JSON-LD schema
  - Schema types: website, webapp, faq, article, organization, breadcrumb
  - `--analyze`: checks existing HTML file for missing schemas
  - `--astro`: generates complete Astro BaseLayout snippet
  - `--inject`: injects directly into HTML file with automatic backup
  - `--faq-file`: generates FAQPage from JSON file

**References** (`references/`)
- `princeton-geo-methods.md` — the 9 GEO methods with measured impact (Princeton KDD 2024)
- `ai-bots-list.md` — 25+ AI crawlers with purpose, vendor, and robots.txt snippets
- `schema-templates.md` — 8 ready-to-use JSON-LD templates

**Tooling**
- `install.sh` — one-line installer: clones repo, creates Python venv, installs deps, creates `./geo` wrapper
- `update.sh` — one-command updater
- `requirements.txt` — pinned: requests>=2.28.0, beautifulsoup4>=4.11.0, lxml>=4.9.0
