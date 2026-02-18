# GEO Audit Script

`geo_audit.py` scores your website from 0 to 100 across five GEO dimensions and tells you exactly what to fix.

---

## What It Checks

| Area | What is audited |
|------|----------------|
| **robots.txt** | 13 AI bots — are they allowed or missing? |
| **llms.txt** | Present at site root? Has content and links? |
| **Schema JSON-LD** | WebSite, WebApplication, FAQPage, Article detected? |
| **Meta tags** | Title, description, canonical, Open Graph |
| **Content quality** | Headings count, statistics, external citations |

---

## Usage

```bash
# Standard audit
./geo scripts/geo_audit.py --url https://yoursite.com

# Verbose: shows raw bot detection and full schema dump
./geo scripts/geo_audit.py --url https://yoursite.com --verbose
```

### Flags

| Flag | Required | Description |
|------|----------|-------------|
| `--url` | ✅ Yes | Full URL of the site to audit (must include `https://`) |
| `--verbose` | No | Print extra debug info: bot UA strings, raw schema JSON, HTTP headers |

---

## Output Explained

Each line in the output maps to a specific check. Here's how to read it:

```diff
▸ ROBOTS.TXT
+ ✅ GPTBot          allowed  (OpenAI — ChatGPT training)
+ ✅ OAI-SearchBot   allowed  (OpenAI — ChatGPT citations)  ← critical
- ❌ ClaudeBot        MISSING                               ← critical
- ❌ PerplexityBot    MISSING                               ← critical
+ ✅ Google-Extended  allowed  (Gemini + AI Overviews)
- ❌ anthropic-ai     MISSING
- ❌ ChatGPT-User     MISSING
```

```diff
▸ LLMS.TXT
- ❌ Not found at https://yoursite.com/llms.txt
```

```diff
▸ SCHEMA JSON-LD
+ ✅ WebSite schema
- ❌ FAQPage schema missing     ← next step
- ❌ WebApplication schema missing
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
+ ✅ 18 headings
- ❌ 1 statistic  (target: 5+)
- ❌ 0 external citations  (target: 3+)
```

---

## GEO Score Breakdown

The score is calculated from five weighted categories:

| Category | Max Points | How it's scored |
|----------|-----------|-----------------|
| robots.txt | 20 | Full points if all 3 citation bots (OAI-SearchBot, ClaudeBot, PerplexityBot) are allowed; partial for other bots |
| llms.txt | 20 | 10pt for presence, 10pt for having H1, sections, and links |
| Schema JSON-LD | 25 | 10pt WebSite (essential), 10pt FAQPage (high value), 5pt WebApplication (bonus for tools) |
| Meta tags | 20 | 5pt each: title, description, canonical, OG tags |
| Content quality | 15 | 4pt for H1, 6pt for numerical statistics, 5pt for external citations |

**Score bands:**

| Score | Label | Meaning |
|-------|-------|---------|
| 91–100 | 🏆 Excellent | Fully optimized for AI citations |
| 71–90 | ✅ Good | Strong foundation, apply Princeton content methods |
| 41–70 | ⚠️ Fair | Core elements present, schema/content gaps remain |
| 0–40 | ❌ Critical | Missing essential elements — start with robots.txt and llms.txt |

---

## What Each ❌ Means and How to Fix It

| Problem | Fix | Docs |
|---------|-----|------|
| AI bot MISSING in robots.txt | Add the bot's `User-agent` block with `Allow: /` | [AI Bots Reference](ai-bots-reference.md) |
| llms.txt not found | Generate with `generate_llms_txt.py`, place at site root | [Generating llms.txt](llms-txt.md) |
| FAQPage schema missing | Generate with `schema_injector.py --type faq` | [Schema Injector](schema-injector.md) |
| WebSite schema missing | Generate with `schema_injector.py --type website` | [Schema Injector](schema-injector.md) |
| Meta description missing | Add `<meta name="description" content="...">` to `<head>` | — |
| Open Graph tags missing | Add `og:title`, `og:description`, `og:image` to `<head>` | — |
| Low statistics count | Add specific numbers, %, dates to page content | [GEO Methods](geo-methods.md#method-2--statistics) |
| 0 external citations | Link to authoritative sources (papers, .gov, .edu) | [GEO Methods](geo-methods.md#method-1--cite-sources) |

---

## Example Outputs

### Score 55/100 — Unoptimized Site

```
╔══════════════════════════════════════════════════════════╗
  GEO AUDIT — https://example.com
╚══════════════════════════════════════════════════════════╝

⏳ Fetching homepage...  200 OK | 22,418 bytes

▸ ROBOTS.TXT ─────────────────────────────────────────────
  ✅ GPTBot          allowed
  ❌ OAI-SearchBot   MISSING   ← critical
  ❌ ClaudeBot        MISSING   ← critical
  ❌ PerplexityBot    MISSING   ← critical
  ✅ Googlebot        allowed

▸ LLMS.TXT ───────────────────────────────────────────────
  ❌ Not found at https://example.com/llms.txt

▸ SCHEMA JSON-LD ─────────────────────────────────────────
  ✅ WebSite schema
  ❌ FAQPage schema missing
  ❌ WebApplication schema missing

▸ META TAGS ──────────────────────────────────────────────
  ✅ Title
  ✅ Meta description
  ❌ Canonical URL missing
  ❌ Open Graph tags missing

▸ CONTENT QUALITY ────────────────────────────────────────
  ✅ 9 headings
  ❌ 1 statistic  (target: 5+)
  ❌ 0 external citations  (target: 3+)

──────────────────────────────────────────────────────────
  GEO SCORE   [███████████░░░░░░░░░]   55 / 100   ⚠️  NEEDS WORK
──────────────────────────────────────────────────────────
```

### Score 85/100 — Optimized Site

```
╔══════════════════════════════════════════════════════════╗
  GEO AUDIT — https://example.com
╚══════════════════════════════════════════════════════════╝

⏳ Fetching homepage...  200 OK | 50,251 bytes

▸ ROBOTS.TXT ─────────────────────────────────────────────
  ✅ GPTBot          allowed  (OpenAI — ChatGPT training)
  ✅ OAI-SearchBot   allowed  (OpenAI — ChatGPT citations)  ← critical
  ✅ ClaudeBot        allowed  (Anthropic — Claude)          ← critical
  ✅ PerplexityBot    allowed  (Perplexity AI)               ← critical
  ✅ Google-Extended  allowed  (Gemini + AI Overviews)
  ✅ anthropic-ai     allowed
  ✅ ChatGPT-User     allowed
  ✅ All critical citation bots configured

▸ LLMS.TXT ───────────────────────────────────────────────
  ✅ Found  (6,517 bytes · 46 links · 6 sections)

▸ SCHEMA JSON-LD ─────────────────────────────────────────
  ✅ WebSite schema
  ✅ WebApplication schema
  ⚠️  FAQPage schema missing  ← next step

▸ META TAGS ──────────────────────────────────────────────
  ✅ Title · Meta description · Canonical · OG tags

▸ CONTENT QUALITY ────────────────────────────────────────
  ✅ 31 headings  ·  15 statistics  ·  2 external citations

──────────────────────────────────────────────────────────
  GEO SCORE   [█████████████████░░░]   85 / 100   🏆 EXCELLENT
──────────────────────────────────────────────────────────
```

The missing FAQPage schema (−8pt) and one external citation (−2pt) are the gap between 85 and 100.
