# GEO Audit

`geo audit` scores your website from 0 to 100 across **8 GEO categories** and tells you exactly what to fix.

---

## What It Checks

### Scored categories (100 points total)

| Area | Max Points | What is audited |
|------|-----------|-----------------|
| **Robots.txt** | 18 | 27 AI bots across 3 tiers (training, search, user). Citation bots explicitly allowed? |
| **llms.txt** | 18 | Present, has H1 + blockquote, sections, links, depth. Companion llms-full.txt? |
| **Schema JSON-LD** | 16 | WebSite, Organization, FAQPage, Article. Schema richness (5+ attributes)? |
| **Meta Tags** | 14 | Title, description, canonical, Open Graph complete? |
| **Content** | 12 | H1, statistics, external citations, heading hierarchy, lists/tables, front-loading? |
| **Brand & Entity** | 10 | Brand coherence, Knowledge Graph links (Wikipedia/Wikidata/LinkedIn), about page, geo signals, topic authority |
| **Signals** | 6 | `<html lang>`, RSS/Atom feed, dateModified freshness? |
| **AI Discovery** | 6 | `.well-known/ai.txt`, `/ai/summary.json`, `/ai/faq.json`, `/ai/service.json`? |

### Bonus checks (informational, no score impact)

| Check | What it detects |
|-------|-----------------|
| **CDN Crawler Access** | Does Cloudflare/Akamai/Vercel block GPTBot, ClaudeBot, PerplexityBot? |
| **JS Rendering** | Is content accessible without JavaScript? SPA framework detection |
| **WebMCP Readiness** | Chrome WebMCP support: `registerTool()`, `toolname` attributes, `potentialAction` schema |
| **Negative Signals** | 8 anti-citation signals: CTA overload, popups, thin content, keyword stuffing, missing author, boilerplate ratio |
| **Prompt Injection Detection** | 8 manipulation patterns: hidden text, invisible Unicode, LLM instructions, HTML comment injection |
| **Trust Stack Score** | 5-layer trust aggregation (Technical, Identity, Social, Academic, Consistency) — grade A-F |

Plus a separate **Citability Score** (0-100) measuring content quality across 47 methods.

---

## Usage

```bash
# Standard audit
geo audit --url https://yoursite.com

# Choose output format
geo audit --url https://yoursite.com --format rich

# Batch audit from sitemap
geo audit --sitemap https://yoursite.com/sitemap.xml --max-urls 25

# Batch audit as JSON
geo audit --sitemap https://yoursite.com/sitemap.xml --format json
```

### Flags

| Flag | Required | Description |
|------|----------|-------------|
| `--url` | Yes* | Full URL of the site to audit (must include `https://`) |
| `--sitemap` | Yes* | XML sitemap URL to audit multiple pages in one run |
| `--format` | No | Output format: `text` (default), `json`, `rich`, `html`, `sarif`, `junit`, `github` |
| `--max-urls` | No | Maximum number of sitemap URLs to audit in batch mode (default: `50`) |
| `--concurrency` | No | Concurrent page audits in batch mode (default: `5`) |

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

---

## Output Explained

Each section in the output maps to one of the 8 scoring categories:

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

The score is the sum of all points earned across **8 categories**, capped at 100.

| Category | Max Points | How it's scored |
|----------|-----------|-----------------|
| Robots.txt | 18 | 5pt found + 13pt all 4 citation bots allowed (OAI-SearchBot, ClaudeBot, Claude-SearchBot, PerplexityBot). 10pt partial credit if some bots allowed |
| llms.txt | 18 | 5pt found + 2pt H1 + 1pt blockquote + 2pt sections + 2pt links + 2pt depth (1k words) + 2pt high depth (5k) + 2pt llms-full.txt |
| Schema JSON-LD | 16 | 2pt any valid + 3pt richness (5+ attrs) + 3pt FAQPage + 3pt Article + 3pt Organization + 2pt WebSite |
| Meta Tags | 14 | 5pt title + 2pt description + 3pt canonical + 4pt Open Graph |
| Content | 12 | 2pt H1 + 1pt numbers + 1pt links + 2pt word count + 2pt hierarchy + 2pt lists/tables + 2pt front-loading |
| Brand & Entity | 10 | 3pt coherence + 3pt KG readiness + 2pt about/contact + 1pt geo identity + 1pt topic authority |
| Signals | 6 | 3pt lang + 2pt RSS + 1pt freshness |
| AI Discovery | 6 | 2pt ai.txt + 2pt summary.json + 1pt faq.json + 1pt service.json |

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

▸ ROBOTS.TXT ─────────────────────────── 5 / 18
  ✅ robots.txt found
  ❌ OAI-SearchBot   MISSING   ← critical
  ❌ ClaudeBot        MISSING   ← critical
  ❌ PerplexityBot    MISSING   ← critical

▸ LLMS.TXT ───────────────────────────── 0 / 18
  ❌ Not found at https://example.com/llms.txt

▸ SCHEMA JSON-LD ─────────────────────── 4 / 16
  ✅ WebSite schema (3 attributes)
  ❌ FAQPage schema missing
  ❌ Article schema missing
  ❌ Organization schema missing

▸ META TAGS ──────────────────────────── 10 / 14
  ✅ Title · Meta description · Canonical
  ❌ Open Graph tags missing

▸ CONTENT QUALITY ────────────────────── 5 / 12
  ✅ H1 present · 9 headings
  ❌ 1 statistic  (target: 5+)
  ❌ 0 external citations  (target: 3+)

▸ BRAND & ENTITY ─────────────────────── 3 / 10
  ✅ Brand name coherent
  ❌ No sameAs Knowledge Graph links
  ❌ No about/contact pages

▸ SIGNALS ────────────────────────────── 3 / 6
  ✅ <html lang="en">
  ❌ No RSS/Atom feed

▸ AI DISCOVERY ───────────────────────── 0 / 6
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

▸ ROBOTS.TXT ─────────────────────────── 18 / 18
  ✅ All 4 citation bots configured
  ✅ 27 AI bots explicitly allowed

▸ LLMS.TXT ───────────────────────────── 16 / 18
  ✅ Found  (6,517 bytes · 46 links · 6 sections)
  ❌ llms-full.txt missing (−2pt)

▸ SCHEMA JSON-LD ─────────────────────── 14 / 16
  ✅ WebSite · Organization · Article (8 attributes)
  ❌ FAQPage schema missing (−3pt)

▸ META TAGS ──────────────────────────── 14 / 14
  ✅ Title · Meta description · Canonical · OG tags

▸ CONTENT QUALITY ────────────────────── 12 / 12
  ✅ 31 headings · H2+H3 hierarchy · 15 statistics · 4 citations
  ✅ Lists/tables · Front-loading

▸ BRAND & ENTITY ─────────────────────── 9 / 10
  ✅ Brand coherent · KG links (Wikipedia, LinkedIn)
  ✅ About + Contact pages
  ❌ No geo identity signal (−1pt)

▸ SIGNALS ────────────────────────────── 4 / 6
  ✅ <html lang="en"> · RSS feed
  ❌ No dateModified freshness (−1pt)

▸ AI DISCOVERY ───────────────────────── 0 / 6
  ❌ No AI discovery endpoints

──────────────────────────────────────────────────────────
  GEO SCORE   [█████████████████░░░]   87 / 100   🏆 EXCELLENT
──────────────────────────────────────────────────────────
```
