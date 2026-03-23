<div align="center">

<img src="assets/logo.svg" alt="Geo Optimizer" width="540"/>

[![PyPI](https://img.shields.io/pypi/v/geo-optimizer-skill?style=flat-square&color=blue&include_prereleases)](https://pypi.org/project/geo-optimizer-skill/)
[![Python](https://img.shields.io/badge/Python-3.9+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![CI](https://github.com/auriti-labs/geo-optimizer-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/auriti-labs/geo-optimizer-skill/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/auriti-labs/geo-optimizer-skill/branch/main/graph/badge.svg)](https://codecov.io/gh/auriti-labs/geo-optimizer-skill)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![Based on Princeton KDD 2024](https://img.shields.io/badge/Based_on-Princeton_KDD_2024-f97316?style=flat-square)](https://arxiv.org/abs/2311.09735)
[![GitHub Stars](https://img.shields.io/github/stars/auriti-labs/geo-optimizer-skill?style=flat-square&color=facc15&logo=github)](https://github.com/auriti-labs/geo-optimizer-skill/stargazers)
[![MCP](https://img.shields.io/badge/MCP-Compatible-8b5cf6?style=flat-square&logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjE2IiBoZWlnaHQ9IjE2IiByeD0iMyIgZmlsbD0iIzhiNWNmNiIvPjx0ZXh0IHg9IjgiIHk9IjEyIiBmb250LXNpemU9IjEwIiBmaWxsPSJ3aGl0ZSIgdGV4dC1hbmNob3I9Im1pZGRsZSI+TTwvdGV4dD48L3N2Zz4=)](https://modelcontextprotocol.io)
[![Docs](https://img.shields.io/badge/docs-auritidesign.it-00b4d8?style=flat-square)](https://auritidesign.it/docs/geo-optimizer/)

**Optimize any website to be cited by ChatGPT, Perplexity, Claude, and Gemini.**
Research-backed. Script-powered. Works in 15 minutes.

[**Docs**](https://auritidesign.it/docs/geo-optimizer/) · [**Quick Start**](#quick-start) · [**How it works**](#what-is-geo) · [**Use with AI**](#use-as-ai-context) · [**Changelog**](CHANGELOG.md)

</div>

---

## The problem nobody is talking about

AI search engines don't show a list of links. They give a direct answer and **cite their sources**.

If your site isn't optimized for this, you don't appear — even if you rank #1 on Google.

```
User: "What's the best mortgage calculator?"

Perplexity: "According to [Competitor.com], the standard formula is..."
             ↑ They appear. You don't.
```

This toolkit fixes that.

---

## What's inside

```
geo-optimizer/
├── 📄 SKILL.md                     ← Choose your platform — index of ai-context/ files
│
├── 🧠 ai-context/
│   ├── claude-project.md           ← Full context for Claude Projects
│   ├── chatgpt-custom-gpt.md       ← GPT Builder system prompt (<8k chars)
│   ├── chatgpt-instructions.md     ← Custom Instructions (<1.5k chars)
│   ├── cursor.mdc                  ← Cursor rules (YAML frontmatter)
│   ├── windsurf.md                 ← Windsurf rules
│   └── kiro-steering.md            ← Kiro steering file (inclusion: fileMatch)
│
├── 📚 references/
│   ├── princeton-geo-methods.md    ← The 9 research-backed methods (+40% AI visibility)
│   ├── ai-bots-list.md             ← 16 AI crawlers (3-tier) — ready-to-use robots.txt block
│   └── schema-templates.md         ← 8 JSON-LD templates (WebSite, FAQPage, WebApp...)
│
├── 📁 docs/                        ← Full documentation (9 pages)
├── 📁 examples/                    ← Plugin examples
├── ⚙️  install.sh / update.sh      ← One-line install, one-command update
└── 📦 pyproject.toml               ← Package config, dependencies, CLI entry point
```

The package ships four CLI commands — `geo audit`, `geo fix`, `geo llms`, `geo schema` — plus an MCP server (`geo-mcp`) and a web demo (`geo-web`). Everything is a proper installable Python package.

---

## ✅ Requirements

| | |
|---|---|
| **Python** | 3.9 or higher → [python.org](https://python.org) |
| **git** | any version → [git-scm.com](https://git-scm.com) |
| **Website** | publicly accessible URL |

---

## ⚡ Quick Start

**1. Install**

```bash
# From PyPI (recommended)
pip install geo-optimizer-skill

# Or from source
git clone https://github.com/auriti-labs/geo-optimizer-skill.git
cd geo-optimizer-skill
pip install -e ".[dev]"
```

**2. Audit your site**

```bash
geo audit --url https://yoursite.com

# JSON output for CI/CD integration
geo audit --url https://yoursite.com --format json --output report.json
```

**3. Fix what's missing**

```bash
# Preview all recommended fixes (dry-run, nothing written)
geo fix --url https://yoursite.com

# Write the fix files to disk
geo fix --url https://yoursite.com --apply

# Fix only specific categories
geo fix --url https://yoursite.com --only robots,llms

# Generate llms.txt from your sitemap
geo llms --base-url https://yoursite.com --output ./public/llms.txt

# Generate JSON-LD schema
geo schema --type website --name "MySite" --url https://yoursite.com
```

---

## What's New in v3.x

**`geo fix` — one command to generate all missing files.** Point it at any URL and it audits the site, then generates a robots.txt patch, llms.txt, JSON-LD schemas, and meta tag recommendations in one shot. Add `--apply` to write everything to disk, or `--only robots,llms` to target specific categories.

**MCP Server** — use all audit capabilities directly from Claude, Cursor, or any MCP-compatible client. Five tools and two resources, no API keys required. See [MCP Server](#mcp-server) below.

**Citability Score** — a separate 0–100 score based on the nine Princeton KDD 2024 methods, measuring how citable your content is (not just whether you have the right technical setup). Returned as `result.citability.total_score` in the library API.

**16 AI bots with 3-tier classification** — training, search, and user tiers. Bingbot (Microsoft Copilot) and Claude-SearchBot added in v3.4–3.5.

**7 output formats** — text, json, rich, html, github, sarif, junit. SARIF and JUnit are useful for CI pipelines that aggregate security/quality findings.

**Plugin system** — register custom audit checks via entry points. See `examples/example_plugin.py`.

See [CHANGELOG.md](CHANGELOG.md) for full details.

---

## 📊 Sample Output

```
🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍
  GEO AUDIT — https://yoursite.com
  github.com/auriti-labs/geo-optimizer-skill
🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍

⏳ Fetching homepage...
   Status: 200 | Size: 50,251 bytes

============================================================
  1. ROBOTS.TXT — AI Bot Access
============================================================
  ✅ GPTBot allowed ✓ (OpenAI (ChatGPT training))
  ✅ OAI-SearchBot allowed ✓ (OpenAI (ChatGPT search citations))
  ✅ ClaudeBot allowed ✓ (Anthropic (Claude citations))
  ✅ PerplexityBot allowed ✓ (Perplexity AI (index builder))
  ✅ Google-Extended allowed ✓ (Google (Gemini training))
  ✅ anthropic-ai allowed ✓ (Anthropic (Claude training))
  ✅ ChatGPT-User allowed ✓ (OpenAI (ChatGPT on-demand fetch))
  ⚠️  meta-externalagent not configured (Meta AI (Facebook/Instagram AI))
  ✅ All critical CITATION bots are correctly configured

============================================================
  2. LLMS.TXT — AI Index File
============================================================
  ✅ llms.txt found (200, 6517 bytes, ~46 words)
  ✅ H1 present: # Your Site Name
  ✅ Blockquote description present
  ✅ H2 sections present: 6 (Tools, Articles, Docs...)
  ✅ Links found: 46 links to site pages

============================================================
  3. SCHEMA JSON-LD — Structured Data
============================================================
  ✅ Found 2 JSON-LD blocks
  ✅ WebSite schema ✓ (url: https://yoursite.com)
  ✅ WebApplication schema ✓ (name: Your Tool)
  ⚠️  FAQPage schema missing — very useful for AI citations on questions

============================================================
  4. META TAGS — SEO & Open Graph
============================================================
  ✅ Title: Your Site — Best Tool for X
  ✅ Meta description (142 chars) ✓
  ✅ Canonical: https://yoursite.com
  ✅ og:title ✓
  ✅ og:description ✓
  ✅ og:image ✓

============================================================
  5. CONTENT QUALITY — GEO Best Practices
============================================================
  ✅ H1: Make AI cite your website
  ✅ Good heading structure: 31 headings (H1–H4)
  ✅ Numerical data present: 15 numbers/statistics found ✓
  ✅ Sufficient content: ~1,250 words
  ⚠️  No external source links — cite authoritative sources for +40% AI visibility

============================================================
  📊 FINAL GEO SCORE
============================================================

  [█████████████████░░░] 85/100
  ✅ GOOD — Core optimizations in place, fine-tune content and schema

  Score bands: 0–40 = critical | 41–70 = foundation | 71–90 = good | 91–100 = excellent

  📋 NEXT PRIORITY STEPS:
  4. Add FAQPage schema with frequently asked questions
  7. Cite authoritative sources with external links
```

---

## 🎯 What is GEO?

**GEO (Generative Engine Optimization)** is the practice of optimizing web content to be **cited** by AI search engines — not just ranked by Google.

| Engine | Bot | What it does |
|--------|-----|-------------|
| ChatGPT Search | `OAI-SearchBot` | Retrieves and cites sources in answers |
| Perplexity AI | `PerplexityBot` | Builds an index of trusted sources |
| Claude | `ClaudeBot`, `Claude-SearchBot` | Web citations in real-time answers |
| Gemini / AI Overviews | `Google-Extended` | Powers Google's AI answers |
| Microsoft Copilot | `Bingbot` | AI-assisted search |

**Proven results — Princeton KDD 2024 (10,000 real queries on Perplexity.ai):**

```
Cite Sources method    →  up to +115% visibility
Statistics method      →  +40% average
Fluency optimization   →  +15–30%
```

> Full paper: https://arxiv.org/abs/2311.09735

---

## CLI Reference

<details>
<summary><strong>geo audit</strong> — Full GEO audit, score 0–100</summary>

```bash
# Text output (default)
geo audit --url https://yoursite.com

# Rich colored output
geo audit --url https://yoursite.com --format rich

# JSON output for CI/CD pipelines
geo audit --url https://yoursite.com --format json --output report.json

# HTML report (self-contained, shareable)
geo audit --url https://yoursite.com --format html --output report.html

# GitHub Actions annotations
geo audit --url https://yoursite.com --format github

# SARIF (for GitHub Code Scanning, SonarQube, etc.)
geo audit --url https://yoursite.com --format sarif --output report.sarif

# JUnit XML (for Jenkins, GitLab CI, etc.)
geo audit --url https://yoursite.com --format junit --output report.xml
```

**Checks:**
- robots.txt — 16 AI bots across 3 tiers (training/search/user)?
- /llms.txt — present, structured, has links?
- JSON-LD — WebSite, WebApplication, FAQPage?
- Meta tags — description, canonical, Open Graph?
- Content — headings, statistics, external citations?

**CI/CD integration example:**

```bash
# Fail the build if GEO score drops below 70
geo audit --url https://yoursite.com --format sarif --output report.sarif
geo audit --url https://yoursite.com --format json --output report.json
SCORE=$(jq '.score' report.json)
if [ "$SCORE" -lt 70 ]; then
  echo "GEO score too low: $SCORE/100"
  exit 1
fi
```

**JSON Output Structure:**
```json
{
  "url": "https://example.com",
  "timestamp": "2026-02-21T12:52:18.983151Z",
  "score": 85,
  "band": "good",
  "checks": {
    "robots_txt": {
      "score": 20,
      "max": 20,
      "passed": true,
      "details": {
        "found": true,
        "citation_bots_ok": true,
        "bots_allowed": ["GPTBot", "ClaudeBot", "PerplexityBot"],
        "bots_blocked": [],
        "bots_missing": ["Applebot-Extended"]
      }
    },
    "llms_txt": {
      "score": 20,
      "max": 20,
      "passed": true,
      "details": {
        "found": true,
        "has_h1": true,
        "has_sections": true,
        "has_links": true,
        "word_count": 559
      }
    },
    "schema_jsonld": {
      "score": 10,
      "max": 25,
      "passed": true,
      "details": {
        "has_website": true,
        "has_webapp": false,
        "has_faq": false,
        "found_types": ["WebSite", "Organization"]
      }
    },
    "meta_tags": {
      "score": 20,
      "max": 20,
      "passed": true,
      "details": {
        "has_title": true,
        "has_description": true,
        "has_canonical": true,
        "has_og_title": true,
        "has_og_description": true,
        "has_og_image": true
      }
    },
    "content": {
      "score": 15,
      "max": 15,
      "passed": true,
      "details": {
        "has_h1": true,
        "heading_count": 31,
        "has_numbers": true,
        "has_links": true,
        "word_count": 538
      }
    }
  },
  "recommendations": [
    "Add FAQPage schema with frequently asked questions"
  ]
}
```

</details>

<details>
<summary><strong>geo fix</strong> — Generate all missing fix files in one shot</summary>

`geo fix` audits the target URL, then generates everything that's missing: a robots.txt patch, a ready-to-deploy llms.txt, JSON-LD schema blocks, and meta tag recommendations. By default it's a dry-run so you can review before writing anything.

```bash
# Preview what would be generated (dry-run)
geo fix --url https://yoursite.com

# Write fix files to disk
geo fix --url https://yoursite.com --apply

# Target only specific categories
geo fix --url https://yoursite.com --only robots,llms
geo fix --url https://yoursite.com --only schema,meta
```

**Generates:**
- `robots.txt` patch — adds missing AI bot entries
- `llms.txt` — structured AI index file for your site root
- JSON-LD schema blocks — WebSite, WebApplication, FAQPage as needed
- Meta tag recommendations — description, canonical, Open Graph

</details>

<details>
<summary><strong>geo llms</strong> — Auto-generate /llms.txt from sitemap</summary>

```bash
geo llms \
  --base-url https://yoursite.com \
  --site-name "MySite" \
  --description "Free calculators for finance and math" \
  --output ./public/llms.txt
```

**Features:** auto-detects sitemap · supports sitemap index · groups URLs by category · generates structured markdown

</details>

<details>
<summary><strong>geo schema</strong> — Generate & inject JSON-LD schema</summary>

```bash
# Analyze HTML file — see what's missing
geo schema --file index.html --analyze

# Generate WebSite schema
geo schema --type website --name "MySite" --url https://yoursite.com

# Inject FAQPage schema into a file
geo schema --file page.html --type faq --inject

# Generate Astro BaseLayout snippet
geo schema --astro --name "MySite" --url https://yoursite.com
```

**Schema types:** `website` · `webapp` · `faq` · `article` · `organization` · `breadcrumb`

</details>

---

## MCP Server

Use GEO Optimizer directly from Claude, Cursor, or any MCP-compatible client.

```bash
pip install geo-optimizer-skill[mcp]
claude mcp add geo-optimizer -- geo-mcp
```

Five tools are available:

| Tool | What it does |
|------|-------------|
| `geo_audit` | Full audit, returns score + recommendations |
| `geo_fix` | Generate fix files for a URL |
| `geo_llms_generate` | Generate llms.txt content |
| `geo_citability` | Citability score (Princeton methods) |
| `geo_schema_validate` | Validate JSON-LD schema |

Two resources are exposed:

| Resource | Content |
|----------|---------|
| `geo://ai-bots` | Full list of 16 tracked AI bots with tier classification |
| `geo://score-bands` | Score band definitions and their meaning |

Once connected, you can ask your AI assistant things like: *"audit my site and fix what's missing"* or *"what's my citability score and how do I improve it?"*

---

## Citability Score

Separate from the main GEO audit score, the citability score measures how well your **content** is written to be cited by AI — not just whether the technical plumbing is in place.

It's based on the nine Princeton KDD 2024 methods, each with a measured impact:

| Method | Impact |
|--------|--------|
| Quotation Addition | +41% |
| Statistics | +33% |
| Fluency Optimization | +29% |
| Cite Sources | +27% |
| Authoritative Tone | +15% |
| Easy-to-Understand | +12% |
| Technical Terms | +9% |
| Unique Words | +7% |
| Keyword Stuffing | ~0% |

You get back a score from 0–100 and per-method recommendations. Available via `geo audit`, the MCP `geo_citability` tool, and the Python API.

---

## Use as a Library

```python
from geo_optimizer import audit, CitabilityResult

result = audit("https://example.com")
print(result.score)                      # 85
print(result.citability.total_score)     # 72
print(result.recommendations)            # ["Add FAQPage schema..."]
```

The core `audit()` function returns a typed `AuditResult` dataclass. No side effects, no printing — compose it however you want. All result types are exported from the top-level package.

For async use:

```python
from geo_optimizer import audit_async

result = await audit_async("https://example.com")
```

---

## 🔬 The 9 Princeton GEO Methods

Apply in this order:

| Priority | Method | Impact |
|----------|--------|--------|
| 🔴 **1** | **Cite Sources** — link to authoritative external sources | +30–115% |
| 🔴 **2** | **Statistics** — add specific numbers, %, dates, measurements | +40% |
| 🟠 **3** | **Quotation Addition** — quote experts with attribution | +30–40% |
| 🟠 **4** | **Authoritative Tone** — expert language, precise terminology | +6–12% |
| 🟡 **5** | **Fluency Optimization** — clear sentences, logical flow | +15–30% |
| 🟡 **6** | **Easy-to-Understand** — define terms, use analogies | +8–15% |
| 🟢 **7** | **Technical Terms** — correct industry terminology | +5–10% |
| 🟢 **8** | **Unique Words** — vary vocabulary, avoid repetition | +5–8% |
| ❌ **9** | **Keyword Stuffing** — proven ineffective for GEO | ~0% |

> Full detail + domain-specific data: [`references/princeton-geo-methods.md`](references/princeton-geo-methods.md)

---

## 🧠 Use as AI Context

`SKILL.md` is the index. Pick the right file for your platform from `ai-context/`:

| Platform | File | Limit |
|----------|------|-------|
| **Claude Projects** | `ai-context/claude-project.md` | No limit |
| **ChatGPT Custom GPT** | `ai-context/chatgpt-custom-gpt.md` | 8,000 chars (paid) |
| **ChatGPT Custom Instructions** | `ai-context/chatgpt-instructions.md` | 1,500 chars |
| **Cursor** | `ai-context/cursor.mdc` → `.cursor/rules/` | No limit |
| **Windsurf** | `ai-context/windsurf.md` → `.windsurf/rules/` | Plain MD + activate via UI (Always On) |
| **Kiro** | `ai-context/kiro-steering.md` → `.kiro/steering/` | No limit |

Once loaded, just ask: *"audit my site"* · *"generate llms.txt"* · *"add FAQPage schema"*

> Full setup guide: [`docs/ai-context.md`](docs/ai-context.md)

---

## Plugin System

Custom audit checks can be registered via Python entry points. This lets you add domain-specific checks without modifying the package.

```toml
# pyproject.toml
[project.entry-points."geo_optimizer.checks"]
my_check = "mypackage.checks:MyAuditCheck"
```

See `examples/example_plugin.py` for a complete working example. Use `--no-plugins` when running `geo audit` to skip all registered plugins.

---

## 🤖 GEO Checklist

Before publishing any page:

- [ ] `robots.txt` — all AI bots with `Allow: /` → [`references/ai-bots-list.md`](references/ai-bots-list.md)
- [ ] `/llms.txt` — present at site root, structured, updated
- [ ] **WebSite** schema — in global `<head>` on all pages
- [ ] **WebApplication** schema — on every tool or calculator
- [ ] **FAQPage** schema — on every page with Q&A content
- [ ] At least **3 external citations** (links to authoritative sources)
- [ ] At least **5 concrete numerical data points**
- [ ] Meta description — accurate, 120–160 chars
- [ ] Canonical URL — on every page
- [ ] Open Graph tags — og:title, og:description, og:image

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=geo_optimizer --cov-report=term-missing

# Single test file
pytest tests/test_core.py -v

# Single test
pytest tests/test_core.py::TestAudit::test_name -v
```

800+ tests covering core audit, CLI, security, citability, MCP, and edge cases. All use `unittest.mock` — no real network calls.

See [Codecov](https://codecov.io/gh/auriti-labs/geo-optimizer-skill) for live coverage analysis.

---

## Security

Security issues should be reported via [SECURITY.md](SECURITY.md). The package includes anti-SSRF protection with DNS pinning, thread-safe caching, path traversal validation, and XSS-safe output rendering. All URL inputs are validated against private IP ranges (RFC 1918, loopback, link-local, cloud metadata) before any network request is made.

---

## 📚 Resources

| | |
|---|---|
| 📖 Full Documentation | [docs/index.md](docs/index.md) |
| 📄 Princeton Paper | https://arxiv.org/abs/2311.09735 |
| 🧪 GEO-bench dataset | https://generative-engines.com/GEO/ |
| 📋 llms.txt spec | https://llmstxt.org |
| 🏗️ Schema.org | https://schema.org |
| ✅ Schema Validator | https://validator.schema.org |

---

## 👤 Author

<table>
<tr>
<td>

**Juan Camilo Auriti**
Web Developer · GEO Researcher
📧 juancamilo.auriti@gmail.com
🐙 [github.com/auriti-labs](https://github.com/auriti-labs)

</td>
</tr>
</table>

---

## 🤝 Contributing

Issues, PRs, and shared audit results are all welcome.
Keep contributions focused and documented.

---

## 📄 License

[MIT](LICENSE) — free to use, modify, and distribute.

---

<div align="center">

**If this saved you time — a ⭐ helps others find it.**

[![Star on GitHub](https://img.shields.io/github/stars/auriti-labs/geo-optimizer-skill?style=for-the-badge&color=facc15&logo=github&label=Star%20this%20repo)](https://github.com/auriti-labs/geo-optimizer-skill/stargazers)

</div>

---

<p align="center">
  <a href="https://buymeacoffee.com/auritidesign">
    <img src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black" alt="Buy Me a Coffee" />
  </a>
</p>
