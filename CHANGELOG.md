# Changelog

All notable changes to GEO Optimizer are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/) · [SemVer](https://semver.org/)

---

## [1.0.0] — 2026-02-18

### Added

**Scripts**
- `scripts/geo_audit.py` — automated GEO audit, scores any website 0–100
  - Checks: robots.txt (13 AI bots), /llms.txt (structure + links), JSON-LD schema (WebSite/WebApp/FAQPage), meta tags (title/description/canonical/OG), content quality (headings/statistics/citations)
  - Lazy dependency import — `--help` always works even without dependencies installed
  - Inline comment stripping in robots.txt parser (e.g. `User-agent: GPTBot # note`)
  - Duplicate WebSite schema detection with warning

- `scripts/generate_llms_txt.py` — auto-generates `/llms.txt` from XML sitemap
  - Auto-detects sitemap from robots.txt Sitemap directive
  - Supports sitemap index files (multi-sitemap)
  - Groups URLs by category (Tools, Finance, Blog, etc.)
  - Generates structured markdown with H1, blockquote, sections, links
  - Lazy dependency import — `--help` always works

- `scripts/schema_injector.py` — generates and injects JSON-LD schema
  - Schema types: website, webapp, faq, article, organization, breadcrumb
  - `--analyze`: checks existing HTML file for missing schemas (requires `--file`)
  - `--astro`: generates complete Astro BaseLayout snippet
  - `--inject`: injects directly into HTML file with automatic backup
  - `--faq-file`: generates FAQPage from JSON file
  - FAQ placeholder mode with `REPLACE:` markers and warning

**AI Context Files** (`ai-context/`)
- `claude-project.md` — full GEO context for Claude Projects (no size limit)
- `chatgpt-custom-gpt.md` — compressed for ChatGPT GPT Builder (<8,000 chars)
- `chatgpt-instructions.md` — ultra-compressed for ChatGPT Custom Instructions (<1,500 chars)
- `cursor.mdc` — Cursor rules format with YAML frontmatter (`globs`, `alwaysApply`)
- `windsurf.md` — Windsurf rules format (same content, plain markdown)
- `kiro-steering.md` — Kiro steering file format (`inclusion: fileMatch`, `fileMatchPattern` array)

**References** (`references/`)
- `princeton-geo-methods.md` — the 9 GEO methods with measured impact (Princeton KDD 2024)
- `ai-bots-list.md` — 25+ AI crawlers with purpose, vendor, and robots.txt snippets
- `schema-templates.md` — 8 ready-to-use JSON-LD templates with `YOUR_LANGUAGE_CODE` placeholder

**Documentation** (`docs/`)
- `index.md` — navigation overview
- `getting-started.md` — install, first audit, reading output, update
- `geo-audit.md` — full script reference, score breakdown, fix guide
- `llms-txt.md` — generation guide, per-framework examples
- `schema-injector.md` — all flags, framework examples (Astro/Next.js/WordPress/HTML)
- `ai-context.md` — per-platform setup with accurate character limits
- `geo-methods.md` — all 9 Princeton methods with diff examples and 3-phase strategy
- `ai-bots-reference.md` — citation vs training bots, full table, monitoring guide
- `troubleshooting.md` — 10 common issues with solutions

**Tooling**
- `install.sh` — one-line installer: clones repo, creates Python venv, installs deps, creates `./geo` wrapper
- `update.sh` — one-command updater via `bash update.sh`
- `requirements.txt` — pinned: requests>=2.28.0, beautifulsoup4>=4.11.0, lxml>=4.9.0

---

## [Unreleased]

- PyPI package (`pip install geo-optimizer`)
- Weekly GEO score tracker with trend reporting
- Support for Hugo, Jekyll, Nuxt
