# 🤖 GEO Optimizer Skill — Generative Engine Optimization

[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-blue)](https://github.com/auriti-web-design)
[![GEO](https://img.shields.io/badge/GEO-Optimization-green)](https://arxiv.org/abs/2311.09735)
[![Princeton Research](https://img.shields.io/badge/Based_on-Princeton_KDD_2024-orange)](https://arxiv.org/abs/2311.09735)
[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://python.org)

> Optimize websites to be **cited** by AI search engines: ChatGPT, Perplexity, Claude, Gemini.  
> Based on Princeton research "GEO: Generative Engine Optimization" (KDD 2024, +40% AI visibility).

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

## 📦 Structure

```
geo-optimizer/
├── SKILL.md                          # Main OpenClaw skill
├── scripts/
│   ├── geo_audit.py                  # Full audit with ✅/❌/⚠️ report
│   ├── generate_llms_txt.py          # Generates llms.txt from XML sitemap
│   └── schema_injector.py            # Adds JSON-LD schema to HTML/Astro
└── references/
    ├── princeton-geo-methods.md      # The 9 Princeton methods with estimated impact
    ├── ai-bots-list.md               # 25+ AI bots with user-agent and robots.txt snippet
    └── schema-templates.md           # Ready-to-use JSON-LD templates (8 types)
```

---

## 🚀 Quick Start

### 1. Clone and install dependencies
```bash
git clone https://github.com/auriti-web-design/geo-optimizer-skill.git
cd geo-optimizer-skill
pip install requests beautifulsoup4
```

### 2. Audit your site
```bash
python scripts/geo_audit.py --url https://yoursite.com
```

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
python scripts/generate_llms_txt.py \
  --base-url https://yoursite.com \
  --output ./public/llms.txt
```

### 4. Generate JSON-LD schema
```bash
# Analyze existing HTML file
python scripts/schema_injector.py --file index.html --analyze

# Generate WebSite snippet
python scripts/schema_injector.py --type website --name "MySite" --url https://yoursite.com

# Generate Astro snippet
python scripts/schema_injector.py --type website --url https://yoursite.com --astro
```

---

## 📋 GEO Workflow in 4 Steps

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

> Full detail in [`references/princeton-geo-methods.md`](references/princeton-geo-methods.md)

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

## 📊 Real-World Result

Audit on a financial calculators website (Feb 2026):

```
GEO Score: 85/100 🏆 EXCELLENT

✅ robots.txt with GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot, Google-Extended, Applebot
✅ llms.txt present (46 links, 6 sections)
✅ WebSite + Organization + Person + BreadcrumbList schema
✅ Optimized meta description
✅ Complete OG tags
✅ H1-H4 heading structure: 31 headings
✅ Numerical data: 15 statistics detected
⚠️ FAQPage schema missing on homepage (next step)
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
