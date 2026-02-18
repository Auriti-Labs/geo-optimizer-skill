# Changelog — geo-optimizer

All notable changes to this skill will be documented here.

Format: [SemVer](https://semver.org/) — `MAJOR.MINOR.PATCH`

---

## [1.2.0] — 2026-02-18

### 🌍 Internationalization
- Full English translation of SKILL.md, README.md, CHANGELOG.md
- Documentation now follows open-source English standards

---

## [1.1.0] — 2026-02-18

### 🔧 Fixes & Improvements

- **Critical fix**: removed all hardcoded absolute paths from SKILL.md — all commands now use relative paths (`python scripts/...`)
- **Fix**: removed `source /home/openclaw/...` from Quick Start — now only `pip install requests beautifulsoup4` is needed
- **Fix**: removed duplicate `PerplexityBot` entry in the robots.txt block
- **Fix**: "Astro Implementation" section generalized — removed site-specific references, added generic `siteUrl`/`siteName`/`isTool` props
- **Fix**: GEO Score in README updated with real data from script (85/100, not 78)
- **Improvement**: Quick Start in README includes `git clone` step
- **Version bump**: `1.0.0` → `1.1.0`

---

## [1.0.0] — 2026-02-18

### 🎉 First Release

Initial complete implementation of the GEO Optimizer skill for OpenClaw.

#### Included
- **SKILL.md** — Full workflow based on Princeton GEO research (9 methods)
- **`scripts/geo_audit.py`** — Automated GEO audit: robots.txt, llms.txt, schema, meta tags
- **`scripts/generate_llms_txt.py`** — Auto-generates `llms.txt` from sitemap or manual URL list
- **`scripts/schema_injector.py`** — Injects WebApplication + FAQPage JSON-LD schema into HTML
- **`references/princeton-geo-methods.md`** — Summary of the 9 Princeton GEO optimization methods
- **`references/ai-bots-list.md`** — Complete list of AI crawler User-Agents (GPTBot, PerplexityBot, etc.)
- **`references/schema-templates.md`** — Ready-to-use JSON-LD schema templates

#### Proven results (tested on a financial calculators website)
- `robots.txt` updated with 8 AI crawlers
- `llms.txt` generated with 60+ pages and structured content
- FAQPage + WebApplication schema on top pages
- Google Indexing API integration (150 URL/day quota-safe)

---

## [Unreleased]

- ClawHub marketplace listing
- Automated weekly GEO score tracker cron
- End-to-end tests on additional site types
