---
title: "GEO Audit Command: Score Your Site 0–100"
description: "Run the geo audit CLI to score any website 0-100 across 9 GEO categories and get a fix list for ChatGPT, Perplexity, Claude and Gemini citation readiness."
order: 2
---
# GEO Audit

`geo audit` scores your website from 0 to 100 across **9 GEO categories** and tells you exactly what to fix.

---

## What It Checks

### Scored categories (100 points total)

| Area | Max Points | What is audited |
|------|-----------|-----------------|
| **Google AI readiness** | 20 | Indexing, snippets, canonical, dates, byline, links, viewport, sitemap, and manual generative-AI control check |
| **Robots.txt** | 14 | 27 AI bots across 3 tiers (training, search, user). Citation bots explicitly allowed? |
| **llms.txt** | 6 | Present, sections, links, and companion llms-full.txt; useful to other AI agents, ignored by Google Search |
| **Schema JSON-LD** | 14 | WebSite, Organization, FAQPage, Article, schema richness, and visible name match |
| **Meta Tags** | 11 | Title, description, Open Graph complete? Canonical is scored in Google AI readiness |
| **Content** | 14 | H1, statistics, external citations, heading hierarchy, lists/tables, front-loading, image alt coverage |
| **Brand & Entity** | 12 | Brand coherence, Knowledge Graph links (Wikipedia/Wikidata/LinkedIn), about page, geo signals, topic authority |
| **Signals** | 6 | `<html lang>`, RSS/Atom feed, dateModified freshness? |
| **AI Discovery** | 3 | `.well-known/ai.txt`, `/ai/summary.json`, and markdown negotiation? |

### Bonus checks (informational, no score impact)

| Check | What it detects |
|-------|-----------------|
| **CDN Crawler Access** | Does Cloudflare/Akamai/Vercel block GPTBot, ClaudeBot, PerplexityBot? |
| **JS Rendering** | Is content accessible without JavaScript? SPA framework detection |
| **WebMCP Readiness** | Chrome WebMCP support: `registerTool()`, `toolname` attributes, `potentialAction` schema |
| **Negative Signals** | 8 anti-citation signals: CTA overload, popups, thin content, keyword stuffing, missing author, boilerplate ratio |
| **Prompt Injection Detection** | 8 manipulation patterns: hidden text, invisible Unicode, LLM instructions, HTML comment injection |
| **Trust Stack Score** | 5-layer trust aggregation (Technical, Identity, Social, Academic, Consistency) — grade A-F |

### Google AI readiness - max 20 pts (v2)

| Check | Points | One-line check | Source |
|-------|--------|----------------|--------|
| `G-INDEX` | 5 | Final status 200, no noindex directives, and Googlebot is not blocked by robots.txt. | https://developers.google.com/search/docs/essentials/technical |
| `G-SNIPPET` | 5 | No restrictive snippet directives; data-nosnippet over 50% fails and over 10% warns. | https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag |
| `G-CANONICAL` | 3 | Exactly one absolute canonical in `<head>` matches the final URL. | https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls |
| `G-DATES` | 2 | Visible date agrees with datePublished/dateModified and is not in the future. | https://developers.google.com/search/docs/appearance/publication-dates |
| `G-BYLINE` | 2 | Visible author or JSON-LD author is present, ideally linked to an author page. | https://developers.google.com/search/docs/fundamentals/creating-helpful-content |
| `G-LINKS` | 1 | Internal links use crawlable `<a href>` elements, with no `#/` routes. | https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics |
| `G-VIEWPORT` | 1 | Meta viewport is present. | https://developers.google.com/search/docs/appearance/page-experience |
| `G-SITEMAP` | 1 | `Sitemap:` is declared in robots.txt. | https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap |
| `G-SD-VISIBLE` | 2 | JSON-LD `name` or `headline` appears in visible text; scored in Schema JSON-LD. | https://developers.google.com/search/docs/appearance/structured-data/sd-policies |
| `G-GENAI-CONTROL` | 0 | Search Console generative-AI opt-out; manual check. | https://developers.google.com/search/docs/fundamentals/ai-optimization-guide |

Plus a separate **Citability Score** (0-100) measuring content quality across 47 methods.

---

## Usage

```bash
# Standard audit
geo audit --url https://yoursite.com

# Save the snapshot in local history
geo audit --url https://yoursite.com --save-history

# Fail CI if the score regressed vs the previous saved snapshot
geo audit --url https://yoursite.com --regression

# Choose output format
geo audit --url https://yoursite.com --format rich

# Batch audit from sitemap
geo audit --sitemap https://yoursite.com/sitemap.xml --max-urls 25

# Batch audit as JSON
geo audit --sitemap https://yoursite.com/sitemap.xml --format json

# Compare with the legacy v1 rubric
geo audit --url https://yoursite.com --score-version 1
```

### Flags

| Flag | Required | Description |
|------|----------|-------------|
| `--url` | Yes* | Full URL of the site to audit (must include `https://`) |
| `--sitemap` | Yes* | XML sitemap URL to audit multiple pages in one run |
| `--format` | No | Output format: `text` (default), `json`, `rich`, `html`, `sarif`, `junit`, `github` |
| `--max-urls` | No | Maximum number of sitemap URLs to audit in batch mode (default: `50`) |
| `--concurrency` | No | Concurrent page audits in batch mode (default: `5`) |
| `--save-history` | No | Save the URL audit in local history (`~/.geo-optimizer/tracking.db`) |
| `--regression` | No | Exit with code `1` if the score dropped vs the previous saved snapshot |
| `--retention-days` | No | Retention window for local snapshots (default: `90`) |
| `--score-version` | No | Scoring rubric version: `2` (default) or `1` (legacy) |

\* Use either `--url` or `--sitemap`.

### Output Formats

| Format | Use case |
|--------|----------|
| `text` | Human-readable terminal output (default) |
| `json` | Machine-readable, pipe to jq or downstream tools |
| `rich` | Colored terminal with ASCII art dashboard |
| `html` | Self-contained HTML report (shareable) |
| `sarif` | GitHub Code Scanning (upload to Security tab) |
| `junit` | Jenkins, GitLab CI test reports |
| `github` | GitHub Actions step summary annotations |

When using `--sitemap`, only `text` and `json` are supported.
`--save-history` and `--regression` currently apply only to `--url` mode.

---

## Output Explained

Each section in the output maps to one of the 9 scoring categories:

```diff
▸ ROBOTS.TXT
+ ✅ GPTBot          allowed  (OpenAI — ChatGPT training)
+ ✅ OAI-SearchBot   allowed  (OpenAI — ChatGPT citations)  ← critical
- ❌ ClaudeBot        MISSING                               ← critical
- ❌ PerplexityBot    MISSING                               ← critical
```

```diff
▸ LLMS.TXT
- ❌ Not found at https://yoursite.com/llms.txt
```

```diff
▸ SCHEMA JSON-LD
+ ✅ WebSite schema
+ ✅ Organization schema
- ❌ FAQPage schema missing
- ❌ Article schema missing
```

```diff
▸ META TAGS
+ ✅ Title (62 chars)
+ ✅ Meta description (142 chars)
+ ✅ Canonical URL
- ❌ Open Graph tags missing (og:title, og:image)
```

```diff
▸ CONTENT QUALITY
+ ✅ 18 headings · H2+H3 hierarchy
- ❌ 1 statistic  (target: 5+)
- ❌ 0 external citations  (target: 3+)
+ ✅ Lists/tables present
```

```diff
▸ BRAND & ENTITY
+ ✅ Brand name coherent across title/schema/OG
- ❌ No sameAs Knowledge Graph links
+ ✅ About page found
```

```diff
▸ SIGNALS
+ ✅ <html lang="en">
- ❌ No RSS/Atom feed
- ❌ No dateModified freshness signal
```

```diff
▸ AI DISCOVERY
- ❌ /.well-known/ai.txt missing
- ❌ /ai/summary.json missing
```

---

## GEO Score Breakdown

The score is the sum of all points earned across **9 categories**, capped at 100. Rubric v2 is the default; use `--score-version 1` for legacy comparisons.

| Category | Max Points | How it's scored |
|----------|-----------|-----------------|
| Google AI readiness | 20 | G-INDEX 5 + G-SNIPPET 5 + G-CANONICAL 3 + G-DATES 2 + G-BYLINE 2 + G-LINKS 1 + G-VIEWPORT 1 + G-SITEMAP 1; G-GENAI-CONTROL is manual (0pt) |
| Robots.txt | 14 | 3pt found + 11pt all 4 citation bots allowed. 8pt partial credit if some bots allowed |
| llms.txt | 6 | 3pt found + 1pt sections + 1pt links + 1pt llms-full.txt; ignored by Google Search |
| Schema JSON-LD | 14 | 2pt any valid + 2pt richness + 2pt FAQPage + 2pt Article + 3pt Organization + 1pt WebSite + 2pt visible name match |
| Meta Tags | 11 | 5pt title + 2pt description + 4pt Open Graph; canonical moved to G-CANONICAL |
| Content | 14 | 2pt H1 + 1pt numbers + 1pt links + 1pt word count + 3pt hierarchy + 2pt lists/tables + 2pt front-loading + 2pt image alt coverage |
| Brand & Entity | 12 | 3pt coherence + 4pt KG readiness + 3pt about/contact + 1pt geo identity + 1pt topic authority |
| Signals | 6 | 3pt lang + 1pt RSS + 2pt freshness; valid, not future date |
| AI Discovery | 3 | 1pt ai.txt + 1pt summary.json + 1pt markdown negotiation (`Accept: text/markdown` → `Content-Type: text/markdown`) |

**Score bands:**

| Score | Label | Meaning |
|-------|-------|---------|
| 86-100 | Excellent | Fully optimized for AI citation engines |
| 68-85 | Good | Well-optimized, minor gaps remain |
| 36-67 | Foundation | Partially visible — key signals missing |
| 0-35 | Critical | AI engines cannot reliably discover or cite you |

---

## What Each Problem Means and How to Fix It

| Problem | Fix | Docs |
|---------|-----|------|
| AI bot MISSING in robots.txt | Add the bot's `User-agent` block with `Allow: /` | [AI Bots Reference](ai-bots-reference.md) |
| llms.txt not found | Generate with `geo llms`, place at site root | [Generating llms.txt](llms-txt.md) |
| FAQPage schema missing | Generate with `geo schema --type faq` | [Schema Injector](schema-injector.md) |
| Organization schema missing | Generate with `geo schema --type organization` | [Schema Injector](schema-injector.md) |
| Meta description missing | Add `<meta name="description" content="...">` to `<head>` | — |
| Open Graph tags missing | Add `og:title`, `og:description`, `og:image` to `<head>` | — |
| No KG sameAs links | Add `sameAs` to Organization schema (Wikipedia, LinkedIn, etc.) | [Scoring Rubric](scoring-rubric.md#8-brand--entity-signals--max-10-pts-new-in-v3182) |
| AI Discovery endpoints missing | Use `geo fix` to generate `.well-known/ai.txt` and `/ai/*.json` | — |
| Low statistics count | Add specific numbers, %, dates to page content | [GEO Methods](geo-methods.md#method-2--statistics) |
| 0 external citations | Link to authoritative sources (papers, .gov, .edu) | [GEO Methods](geo-methods.md#method-1--cite-sources) |

---

## Example Outputs

### Score 52/100 — Unoptimized Site

```
╔══════════════════════════════════════════════════════════╗
  GEO AUDIT — https://example.com
╚══════════════════════════════════════════════════════════╝

▸ ROBOTS.TXT ─────────────────────────── 5 / 14
  ✅ robots.txt found
  ❌ OAI-SearchBot   MISSING   ← critical
  ❌ ClaudeBot        MISSING   ← critical
  ❌ PerplexityBot    MISSING   ← critical

▸ LLMS.TXT ───────────────────────────── 0 / 6
  ❌ Not found at https://example.com/llms.txt

▸ SCHEMA JSON-LD ─────────────────────── 4 / 14
  ✅ WebSite schema (3 attributes)
  ❌ FAQPage schema missing
  ❌ Article schema missing
  ❌ Organization schema missing

▸ META TAGS ──────────────────────────── 10 / 11
  ✅ Title · Meta description · Canonical
  ❌ Open Graph tags missing

▸ CONTENT QUALITY ────────────────────── 5 / 14
  ✅ H1 present · 9 headings
  ❌ 1 statistic  (target: 5+)
  ❌ 0 external citations  (target: 3+)

▸ BRAND & ENTITY ─────────────────────── 3 / 12
  ✅ Brand name coherent
  ❌ No sameAs Knowledge Graph links
  ❌ No about/contact pages

▸ SIGNALS ────────────────────────────── 3 / 6
  ✅ <html lang="en">
  ❌ No RSS/Atom feed

▸ AI DISCOVERY ───────────────────────── 0 / 3
  ❌ No AI discovery endpoints found

──────────────────────────────────────────────────────────
  GEO SCORE   [██████████░░░░░░░░░░]   52 / 100   ⚠️  FOUNDATION
──────────────────────────────────────────────────────────
```

### Score 87/100 — Optimized Site

```
╔══════════════════════════════════════════════════════════╗
  GEO AUDIT — https://optimized-site.com
╚══════════════════════════════════════════════════════════╝

▸ ROBOTS.TXT ─────────────────────────── 14 / 14
  ✅ All 4 citation bots configured
  ✅ 27 AI bots explicitly allowed

▸ LLMS.TXT ───────────────────────────── 6 / 6
  ✅ Found  (6,517 bytes · 46 links · 6 sections)
  ❌ llms-full.txt missing (−2pt)

▸ SCHEMA JSON-LD ─────────────────────── 14 / 14
  ✅ WebSite · Organization · Article (8 attributes)
  ❌ FAQPage schema missing (−3pt)

▸ META TAGS ──────────────────────────── 11 / 11
  ✅ Title · Meta description · Canonical · OG tags

▸ CONTENT QUALITY ────────────────────── 12 / 14
  ✅ 31 headings · H2+H3 hierarchy · 15 statistics · 4 citations
  ✅ Lists/tables · Front-loading

▸ BRAND & ENTITY ─────────────────────── 9 / 12
  ✅ Brand coherent · KG links (Wikipedia, LinkedIn)
  ✅ About + Contact pages
  ❌ No geo identity signal (−1pt)

▸ SIGNALS ────────────────────────────── 4 / 6
  ✅ <html lang="en"> · RSS feed
  ❌ No dateModified freshness (−1pt)

▸ AI DISCOVERY ───────────────────────── 0 / 3
  ❌ No AI discovery endpoints

──────────────────────────────────────────────────────────
  GEO SCORE   [█████████████████░░░]   87 / 100   🏆 EXCELLENT
──────────────────────────────────────────────────────────
```
