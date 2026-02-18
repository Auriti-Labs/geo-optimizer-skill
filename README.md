<div align="center">

```
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ██████╗ ███████╗ ██████╗                                ║
║  ██╔════╝ ██╔════╝██╔═══██╗                               ║
║  ██║  ███╗█████╗  ██║   ██║                               ║
║  ██║   ██║██╔══╝  ██║   ██║                               ║
║  ╚██████╔╝███████╗╚██████╔╝  Optimizer                    ║
║   ╚═════╝ ╚══════╝ ╚═════╝                                ║
║                                                           ║
║   Make AI cite your website — not your competitor's.      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
```

[![Python](https://img.shields.io/badge/Python-3.8+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![Based on Princeton KDD 2024](https://img.shields.io/badge/Based_on-Princeton_KDD_2024-f97316?style=flat-square)](https://arxiv.org/abs/2311.09735)
[![GitHub Stars](https://img.shields.io/github/stars/auriti-web-design/geo-optimizer-skill?style=flat-square&color=facc15&logo=github)](https://github.com/auriti-web-design/geo-optimizer-skill/stargazers)

**Optimize any website to be cited by ChatGPT, Perplexity, Claude, and Gemini.**  
Research-backed. Script-powered. Works in 15 minutes.

[**Quick Start**](#-quick-start) · [**How it works**](#-what-is-geo) · [**Use with AI**](#-use-skillmd-as-ai-context) · [**Changelog**](CHANGELOG.md)

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
├── 📄 SKILL.md                     ← AI context: paste into Claude / ChatGPT / Gemini / Cursor
│
├── 🐍 scripts/
│   ├── geo_audit.py                ← Score your site 0–100, find what's missing
│   ├── generate_llms_txt.py        ← Auto-generate /llms.txt from your sitemap
│   └── schema_injector.py          ← Generate & inject JSON-LD schema
│
├── 📚 references/
│   ├── princeton-geo-methods.md    ← The 9 research-backed methods (+40% AI visibility)
│   ├── ai-bots-list.md             ← 25+ AI crawlers — ready-to-use robots.txt block
│   └── schema-templates.md         ← 8 JSON-LD templates (WebSite, FAQPage, WebApp...)
│
├── ⚙️  install.sh / update.sh      ← One-line install, one-command update
└── 📋 requirements.txt             ← requests, beautifulsoup4, lxml
```

---

## ✅ Requirements

| | |
|---|---|
| **Python** | 3.8 or higher → [python.org](https://python.org) |
| **git** | any version → [git-scm.com](https://git-scm.com) |
| **Website** | publicly accessible URL |

---

## ⚡ Quick Start

**1. Install**

```bash
curl -sSL https://raw.githubusercontent.com/auriti-web-design/geo-optimizer-skill/main/install.sh | bash
```

> Installs to `~/geo-optimizer-skill`. Creates a Python venv automatically.  
> Prefer to inspect first? [View install.sh →](install.sh)

**2. Audit your site**

```bash
cd ~/geo-optimizer-skill
./geo scripts/geo_audit.py --url https://yoursite.com
```

**3. Fix what's missing**

```bash
# Generate llms.txt from your sitemap
./geo scripts/generate_llms_txt.py --base-url https://yoursite.com --output ./public/llms.txt

# Generate JSON-LD schema
./geo scripts/schema_injector.py --type website --name "MySite" --url https://yoursite.com

# Analyze an existing HTML file
./geo scripts/schema_injector.py --file index.html --analyze
```

**4. Update anytime**

```bash
bash ~/geo-optimizer-skill/update.sh
```

---

## 📊 Sample Output

```
╔══════════════════════════════════════════════════════════╗
  GEO AUDIT — https://yoursite.com
╚══════════════════════════════════════════════════════════╝

⏳ Fetching homepage...  200 OK | 50,251 bytes

▸ ROBOTS.TXT ─────────────────────────────────────────────
  ✅ GPTBot          allowed  (OpenAI — ChatGPT training)
  ✅ OAI-SearchBot   allowed  (OpenAI — ChatGPT citations)  ← critical
  ✅ ClaudeBot        allowed  (Anthropic — Claude)          ← critical
  ✅ PerplexityBot    allowed  (Perplexity AI)               ← critical
  ✅ Google-Extended  allowed  (Gemini + AI Overviews)
  ✅ All critical citation bots configured

▸ LLMS.TXT ───────────────────────────────────────────────
  ✅ Found  (6,517 bytes · 46 links · 6 sections)

▸ SCHEMA JSON-LD ─────────────────────────────────────────
  ✅ WebSite schema
  ✅ Organization schema
  ⚠️  FAQPage schema missing  ← next step

▸ META TAGS ──────────────────────────────────────────────
  ✅ Title · Meta description · Canonical · OG tags

▸ CONTENT QUALITY ────────────────────────────────────────
  ✅ 31 headings  ·  15 statistics  ·  2 external citations

──────────────────────────────────────────────────────────
  GEO SCORE   [█████████████████░░░]   85 / 100   🏆 EXCELLENT
──────────────────────────────────────────────────────────
```

---

## 🎯 What is GEO?

**GEO (Generative Engine Optimization)** is the practice of optimizing web content to be **cited** by AI search engines — not just ranked by Google.

| Engine | Bot | What it does |
|--------|-----|-------------|
| ChatGPT Search | `OAI-SearchBot` | Retrieves and cites sources in answers |
| Perplexity AI | `PerplexityBot` | Builds an index of trusted sources |
| Claude | `ClaudeBot` | Web citations in real-time answers |
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

## 🧠 Use SKILL.md as AI Context

`SKILL.md` is a universal context document. Drop it into any AI assistant and it becomes a GEO specialist that can run audits, generate files, and write schema for you.

| Platform | How |
|----------|-----|
| **Claude** | Project → Add as Project Knowledge |
| **ChatGPT** | Custom Instructions → paste content |
| **Gemini** | Gems → paste as context |
| **Cursor** | `.cursor/rules/geo-optimizer.md` |
| **Windsurf** | `.windsurf/rules/geo-optimizer.md` |

Then just ask:  
*"audit my site"* · *"generate llms.txt"* · *"add FAQPage schema to this page"*

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

## 🛠️ Script Reference

<details>
<summary><strong>geo_audit.py</strong> — Full GEO audit, score 0–100</summary>

```bash
./geo scripts/geo_audit.py --url https://yoursite.com
./geo scripts/geo_audit.py --url https://yoursite.com --verbose
```

**Checks:**
- robots.txt — 13 AI bots configured?
- /llms.txt — present, structured, has links?
- JSON-LD — WebSite, WebApplication, FAQPage?
- Meta tags — description, canonical, Open Graph?
- Content — headings, statistics, external citations?

</details>

<details>
<summary><strong>generate_llms_txt.py</strong> — Auto-generate /llms.txt from sitemap</summary>

```bash
./geo scripts/generate_llms_txt.py \
  --base-url https://yoursite.com \
  --site-name "MySite" \
  --description "Free calculators for finance and math" \
  --output ./public/llms.txt
```

**Features:** auto-detects sitemap · supports sitemap index · groups URLs by category · generates structured markdown

</details>

<details>
<summary><strong>schema_injector.py</strong> — Generate & inject JSON-LD schema</summary>

```bash
# Analyze HTML file — see what's missing
./geo scripts/schema_injector.py --file index.html --analyze

# Generate WebSite schema
./geo scripts/schema_injector.py --type website --name "MySite" --url https://yoursite.com

# Inject FAQPage schema into a file
./geo scripts/schema_injector.py --file page.html --type faq --inject

# Generate Astro BaseLayout snippet
./geo scripts/schema_injector.py --astro --name "MySite" --url https://yoursite.com
```

**Schema types:** `website` · `webapp` · `faq` · `article` · `organization` · `breadcrumb`

</details>

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

## 📚 Resources

| | |
|---|---|
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
🐙 [github.com/auriti-web-design](https://github.com/auriti-web-design)

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

[![Star on GitHub](https://img.shields.io/github/stars/auriti-web-design/geo-optimizer-skill?style=for-the-badge&color=facc15&logo=github&label=Star%20this%20repo)](https://github.com/auriti-web-design/geo-optimizer-skill/stargazers)

</div>
