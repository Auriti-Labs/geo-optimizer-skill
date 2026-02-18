# Changelog

All notable changes to GEO Optimizer are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/) · [SemVer](https://semver.org/)

---

## [Unreleased]

### Added

- `ai-context/kiro-steering.md` — Kiro steering file with `inclusion: fileMatch` + `fileMatchPattern` array; place in `.kiro/steering/`
- Kiro entry in `SKILL.md`, `README.md`, `docs/ai-context.md` (setup, frontmatter reference, platform comparison table, update commands)
- `meta-externalagent` (Meta AI — Facebook/Instagram AI) added to `AI_BOTS` in `geo_audit.py`

### Fixed

- `ai-context/windsurf.md` — added YAML frontmatter with `description` and `globs` fields (Windsurf supports the same format as Cursor; previous docs were incorrect)
- `docs/ai-context.md` — removed incorrect claim "Windsurf uses plain Markdown in rules files"; added frontmatter reference and glob activation explanation
- `SKILL.md` — Windsurf limit column updated from "No limit" to "Glob activation (same as Cursor)"
- `geo_audit.py` — schema scoring redistributed: `WebSite=10pt`, `FAQPage=10pt`, `WebApplication=5pt` (webapp is a bonus, not a core requirement; blogs can now reach 100)
- `geo_audit.py` — score thresholds corrected: `>=91 EXCELLENT`, `>=71 GOOD`, `>=41 FAIR`, `<41 CRITICAL`; score band note printed below result
- `docs/geo-audit.md` — score band table updated to match code (`91/71/41` breakpoints)
- `docs/getting-started.md` — score range line corrected to `0–40 Critical · 41–70 Fair · 71–90 Good · 91–100 Excellent`
- `install.sh` — added comment block explaining that `--dir` cannot be used with `curl | bash`; download-first procedure documented
- `README.md` / `docs/getting-started.md` — added custom install path note under the `curl | bash` command

### Planned

- PyPI package (`pip install geo-optimizer`)
- Weekly GEO score tracker with trend reporting
- Support for Hugo, Jekyll, Nuxt

---

## [1.0.0] — 2026-02-18

### Added

**Scripts**
- `scripts/geo_audit.py` — automated GEO audit, scores any website 0–100
  - Checks: robots.txt (AI bots), /llms.txt (structure + links), JSON-LD schema (WebSite/WebApp/FAQPage), meta tags (title/description/canonical/OG), content quality (headings/statistics/citations)
  - Lazy dependency import — `--help` always works even without dependencies installed
  - Inline comment stripping in robots.txt parser (e.g. `User-agent: GPTBot # note`)
  - Duplicate WebSite schema detection with warning

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

**AI Context Files** (`ai-context/`)
- `claude-project.md` — full GEO context for Claude Projects (no size limit)
- `chatgpt-custom-gpt.md` — compressed for ChatGPT GPT Builder (<8,000 chars)
- `chatgpt-instructions.md` — ultra-compressed for ChatGPT Custom Instructions (<1,500 chars)
- `cursor.mdc` — Cursor rules format with YAML frontmatter (`globs`, `alwaysApply`)
- `windsurf.md` — Windsurf rules format (plain Markdown, same content as Cursor)

**References** (`references/`)
- `princeton-geo-methods.md` — the 9 GEO methods with measured impact (Princeton KDD 2024)
- `ai-bots-list.md` — 25+ AI crawlers with purpose, vendor, and robots.txt snippets
- `schema-templates.md` — 8 ready-to-use JSON-LD templates

**Documentation** (`docs/`)
- `index.md`, `getting-started.md`, `geo-audit.md`, `llms-txt.md`, `schema-injector.md`
- `ai-context.md`, `geo-methods.md`, `ai-bots-reference.md`, `troubleshooting.md`

**Tooling**
- `install.sh` — one-line installer: clones repo, creates Python venv, installs deps, creates `./geo` wrapper
- `update.sh` — one-command updater via `bash update.sh`
- `requirements.txt` — pinned: requests>=2.28.0, beautifulsoup4>=4.11.0, lxml>=4.9.0
- `SKILL.md` — platform index with file table and quick-copy commands
- Professional README: ASCII banner, collapsible script docs, visual audit output sample, badges
