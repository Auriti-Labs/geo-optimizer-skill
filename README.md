# 🤖 GEO Optimizer — Generative Engine Optimization

[![GEO Toolkit](https://img.shields.io/badge/GEO-Toolkit-blueviolet)](https://github.com/auriti-web-design/geo-optimizer-skill)
[![GEO](https://img.shields.io/badge/GEO-Optimization-green)](https://arxiv.org/abs/2311.09735)
[![Princeton Research](https://img.shields.io/badge/Based_on-Princeton_KDD_2024-orange)](https://arxiv.org/abs/2311.09735)
[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://python.org)
[![GitHub Stars](https://img.shields.io/github/stars/auriti-web-design/geo-optimizer-skill?style=social)](https://github.com/auriti-web-design/geo-optimizer-skill/stargazers)

> Optimize websites to be **cited** by AI search engines: ChatGPT, Perplexity, Claude, Gemini.  
> Based on Princeton research "GEO: Generative Engine Optimization" (KDD 2024, +40% AI visibility).

---

## ⭐ Why Star This Repo?

If you build websites, run a SaaS, or do SEO for clients — **this will matter to you in 2026**.

AI search engines (ChatGPT, Perplexity, Gemini) are changing how people find information. They don't show a list of links — they give a direct answer and **cite their sources**. If your site isn't optimized for this, you're invisible to a growing share of your audience.

This toolkit gives you everything to fix that in under 15 minutes:

| Without GEO Optimizer | With GEO Optimizer |
|------------------------|---------------------|
| Read a 40-page Princeton paper | Workflow distilled into 4 clear steps |
| Manually research which AI bots exist | Ready-to-use `robots.txt` block (15+ bots) |
| Write `llms.txt` from scratch | Auto-generate from your sitemap with one command |
| Build JSON-LD schema by hand | Templates + injection script included |
| Guess what improves AI visibility | 9 research-backed methods with measured impact |

**The timing advantage is real.** GEO is where SEO was in 2005. Sites that implement it now will have authority and history when everyone else catches up.

If this saves you time or lands you a client — a ⭐ on GitHub goes a long way. It helps others discover the project.

---

## 🎯 What is GEO?

**GEO (Generative Engine Optimization)** is the evolution of SEO for the AI era. Instead of optimizing to rank on Google, you optimize to be **cited and referenced** by AI search engines:

- 💬 **ChatGPT Search** (OAI-SearchBot)
- 🔍 **Perplexity AI** (PerplexityBot)
- 🤖 **Claude** (ClaudeBot)
- ✨ **Google AI Overviews / Gemini** (Google-Extended)
- 🔵 **Microsoft Copilot** (Bingbot)

**Proven results (Princeton KDD 2024):**
- +40% average visibility in AI engines with statistics and citations
- +115% for some rank positions with the Cite Sources method
- +37% on real Perplexity.ai in tests

---

## 🧠 Use SKILL.md as AI Context

`SKILL.md` is a universal context document that turns any AI assistant into a GEO specialist. Drop it into:

| Platform | How to use |
|----------|-----------|
| **Claude** | Create a Project → Add `SKILL.md` as Project Knowledge |
| **ChatGPT** | Custom Instructions → paste the content |
| **Gemini** | Gems → paste as context |
| **Cursor** | `.cursor/rules/geo-optimizer.md` → new rule file |
| **Windsurf** | `.windsurf/rules/geo-optimizer.md` → new rule file |

Once loaded, just describe your site and ask: *"run a GEO audit"*, *"generate my llms.txt"*, *"add FAQPage schema to this page"*.

---

## 📦 Structure

```
geo-optimizer/
├── SKILL.md                          # AI context document (Claude/ChatGPT/Gemini/Cursor/Windsurf)
├── README.md                         # This file
├── CHANGELOG.md                      # Version history
├── LICENSE                           # MIT License
├── requirements.txt                  # Python dependencies
├── install.sh                        # One-line installer
├── update.sh                         # Updater script
├── scripts/
│   ├── geo_audit.py                  # Full GEO audit — score 0–100
│   ├── generate_llms_txt.py          # Auto-generate llms.txt from sitemap
│   └── schema_injector.py            # Generate/inject JSON-LD schema
└── references/
    ├── princeton-geo-methods.md      # The 9 Princeton GEO methods
    ├── ai-bots-list.md               # 25+ AI crawlers with robots.txt snippets
    └── schema-templates.md           # Ready-to-use JSON-LD templates (8 types)
```

---

## ✅ Requirements

- **Python 3.8+** — [python.org](https://python.org)
- **git** — [git-scm.com](https://git-scm.com)
- A website with a publicly accessible URL

---

## 📥 Installation

**One-line install (recommended):**
```bash
curl -sSL https://raw.githubusercontent.com/auriti-web-design/geo-optimizer-skill/main/install.sh | bash
```

> **Prefer to inspect before running?** [View install.sh →](install.sh) — it clones this repo, creates a Python venv, and installs dependencies.

**Manual install:**
```bash
git clone https://github.com/auriti-web-design/geo-optimizer-skill.git
cd geo-optimizer-skill
pip install -r requirements.txt
```

---

## 🔄 Updating

When a new version is released, update with one command:

```bash
# From the install directory
bash update.sh
```

Or manually:
```bash
cd geo-optimizer-skill
git pull origin main
pip install -r requirements.txt -q
```

> **Watch this repo** (top-right → Watch → Releases only) to get notified when new features or bot list updates are released.

---

## 🚀 Quick Start

### 1. Install (see above)
```bash
curl -sSL https://raw.githubusercontent.com/auriti-web-design/geo-optimizer-skill/main/install.sh | bash
# Installs to ~/geo-optimizer-skill by default
```

### 2. Run your first audit
```bash
cd ~/geo-optimizer-skill
./geo scripts/geo_audit.py --url https://yoursite.com
```

> `./geo` is a wrapper that uses the bundled virtual environment automatically.  
> Alternatively: `source .venv/bin/activate` and then use `python3` directly.

**Output:**
```
🔍 GEO AUDIT — https://yoursite.com

1. ROBOTS.TXT — AI Bot Access
  ✅ robots.txt found (200)
  ❌ OAI-SearchBot NOT configured — CRITICAL for AI citations!
  ✅ ClaudeBot allowed ✓
  ✅ PerplexityBot allowed ✓
  ...

📊 FINAL GEO SCORE
  [███████████░░░░░░░░░] 55/100
  ⚠️  SUFFICIENT — Implement the missing optimizations
```

### 3. Generate llms.txt
```bash
./geo scripts/generate_llms_txt.py \
  --base-url https://yoursite.com \
  --output ./public/llms.txt
```

### 4. Generate JSON-LD schema
```bash
# Analyze existing HTML file
./geo scripts/schema_injector.py --file index.html --analyze

# Generate WebSite snippet
./geo scripts/schema_injector.py --type website --name "MySite" --url https://yoursite.com
```

---

## 📋 GEO Workflow in 4 Steps

> **Using an AI assistant?** Load `SKILL.md` as context for the full interactive workflow.

### Step 1 — Audit 🔍
Run `geo_audit.py` to discover what's missing.

### Step 2 — robots.txt 🤖
Add all AI search bots to robots.txt:
```
User-agent: OAI-SearchBot
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: Google-Extended
Allow: /
```
> Full list in [`references/ai-bots-list.md`](references/ai-bots-list.md)

### Step 3 — llms.txt 📋
Create `/llms.txt` at the site root (like robots.txt but for AI):
```markdown
# Site Name

> Brief description for LLMs

## Tools

- [Tool 1](https://yoursite.com/tool): Description

## Optional

- [About](https://yoursite.com/about)
```
> Spec: https://llmstxt.org

### Step 4 — Schema JSON-LD 🏗️
Add structured schema in the `<head>`:
- **WebSite** — globally on all pages
- **WebApplication** — on every tool/calculator
- **FAQPage** — with frequently asked questions → maximum probability of AI citation
> Templates in [`references/schema-templates.md`](references/schema-templates.md)

---

## 🔬 The 9 Princeton GEO Methods

> **Using an AI assistant?** Load `SKILL.md` as context for the full interactive workflow.

| # | Method | AI Impact | Priority |
|---|--------|-----------|----------|
| 1 | **Cite Sources** | +30-115% | 🔴 High |
| 2 | **Statistics** | +40% | 🔴 High |
| 3 | **Quotation Addition** | +30-40% | 🟠 Medium |
| 4 | **Authoritative** | +6-12% | 🟠 Medium |
| 5 | **Fluency Optimization** | +15-30% | 🟡 Medium |
| 6 | **Easy-to-Understand** | +8-15% | 🟡 Low |
| 7 | **Technical Terms** | +5-10% | 🟢 Low |
| 8 | **Unique Words** | +5-8% | 🟢 Low |
| 9 | **Keyword Stuffing** | ≈0% ⚠️ | ❌ Avoid |

> Full detail in [`references/princeton-geo-methods.md`](references/princeton-geo-methods.md) and [`SKILL.md`](SKILL.md)

---

## 🤖 Supported AI Bots

| Bot | Vendor | Purpose |
|-----|--------|---------|
| `OAI-SearchBot` | OpenAI | ChatGPT Search — citations |
| `GPTBot` | OpenAI | Model training |
| `ClaudeBot` | Anthropic | Claude — citations |
| `anthropic-ai` | Anthropic | Claude training |
| `PerplexityBot` | Perplexity | AI search index |
| `Google-Extended` | Google | Gemini + AI Overviews |
| `Bingbot` | Microsoft | Copilot |
| `Applebot-Extended` | Apple | Apple Intelligence |
| `cohere-ai` | Cohere | Cohere models |
| `DuckAssistBot` | DuckDuckGo | DuckAssist AI |
| + 15 more... | | |

> Full list in [`references/ai-bots-list.md`](references/ai-bots-list.md)

---

## 🛠️ Script Reference

### `geo_audit.py`
```
usage: geo_audit.py [--url URL] [--verbose]

Checks:
  - robots.txt: 13 AI bots
  - llms.txt: presence and quality
  - JSON-LD Schema: WebSite, WebApp, FAQPage
  - Meta tags: description, canonical, OG
  - Content: headings, numbers, external links

Output: Report with ✅/❌/⚠️ + GEO Score /100
```

### `generate_llms_txt.py`
```
usage: generate_llms_txt.py --base-url URL [--output FILE]
                             [--sitemap URL] [--site-name NAME]
                             [--description TEXT] [--max-per-section N]

Features:
  - Auto-detect sitemap from robots.txt
  - Supports sitemap index (multi-sitemap)
  - Automatically groups URLs by category
  - Generates structured markdown sections
  - Handles "Optional" section for secondary content
```

### `schema_injector.py`
```
usage: schema_injector.py [--file HTML] [--type TYPE]
                           [--name NAME] [--url URL]
                           [--description TEXT] [--astro]
                           [--inject] [--analyze]

Types: website, webapp, faq, article, organization, breadcrumb
```

---

## 📊 Sample Output

Running `./geo scripts/geo_audit.py --url https://example.com` on a real financial calculators site:

```
🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍
  GEO AUDIT — https://example.com
  github.com/auriti-web-design/geo-optimizer-skill
🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍

⏳ Fetching homepage...
   Status: 200 | Size: 50,251 bytes

============================================================
  1. ROBOTS.TXT — AI Bot Access
============================================================
  ✅ robots.txt found (200)
  ✅ GPTBot allowed ✓ (OpenAI - ChatGPT training)
  ✅ OAI-SearchBot allowed ✓ (OpenAI - ChatGPT search citations)
  ✅ ClaudeBot allowed ✓ (Anthropic - Claude citations)
  ✅ PerplexityBot allowed ✓ (Perplexity AI - index builder)
  ✅ Google-Extended allowed ✓ (Google - Gemini training)
  ✅ All critical CITATION bots are correctly configured

============================================================
  2. LLMS.TXT — AI Index File
============================================================
  ✅ llms.txt found (200, 6517 bytes, ~559 words)
  ✅ H1 present
  ✅ Blockquote description present
  ✅ H2 sections present: 6 sections
  ✅ Links found: 46 links to site pages

============================================================
  3. SCHEMA JSON-LD — Structured Data
============================================================
  ✅ Found 5 JSON-LD blocks
  ✅ WebSite schema ✓
  ✅ Organization schema ✓
  ✅ BreadcrumbList schema ✓
  ⚠️  FAQPage schema missing — very useful for AI citations

============================================================
  4. META TAGS — SEO & Open Graph
============================================================
  ✅ Title (56 chars) ✓
  ✅ Meta description (124 chars) ✓
  ✅ Canonical URL ✓
  ✅ og:title / og:description / og:image ✓

============================================================
  5. CONTENT QUALITY — GEO Best Practices
============================================================
  ✅ H1-H4 heading structure: 31 headings
  ✅ Numerical data: 15 statistics detected ✓
  ✅ External citations: 2 links to external sources ✓

============================================================
  📊 FINAL GEO SCORE
============================================================

  [█████████████████░░░] 85/100

  🏆 EXCELLENT — Site is optimized for AI search engines!

  📋 NEXT PRIORITY STEPS:
  4. Add FAQPage schema with frequently asked questions
```

---

## 📚 Resources

- **Princeton Paper**: https://arxiv.org/abs/2311.09735
- **GEO-bench**: https://generative-engines.com/GEO/
- **llms.txt spec**: https://llmstxt.org
- **Schema.org**: https://schema.org
- **Schema Validator**: https://validator.schema.org

---

## 👤 Author

**Juan Camilo Auriti**  
Web Developer | GEO Specialist  
📧 juancamilo.auriti@gmail.com  
🐙 [@auriti-web-design](https://github.com/auriti-web-design)

---

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Open an issue for bugs or feature requests
- Submit a pull request with improvements
- Share results from your own GEO audits

Please keep PRs focused and well-documented.

---

## 📄 License

MIT License — free to use, modify and distribute.

---

*Found this useful? A ⭐ on [GitHub](https://github.com/auriti-web-design/geo-optimizer-skill) takes 2 seconds and helps others find the project. Thank you.*
