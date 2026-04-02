---
title: "I Built a Python Tool to Check If AI Search Engines Can Find Your Website"
published: false
description: "You optimized for Google. But what about the AI replacing Google? Learn what Generative Engine Optimization (GEO) is and how to audit and fix your site's AI search visibility with an open-source Python tool."
tags: webdev, python, ai, seo
cover_image: https://placeholder.example.com/geo-optimizer-cover.png
canonical_url:
series:
---

You spent months tuning your `<title>` tags, chasing backlinks, submitting sitemaps to Google Search Console. Your rankings are solid. Then you ask ChatGPT about your industry — and it cites three of your competitors but not you.

You are not invisible to Google. You are invisible to the AI that is increasingly *replacing* Google.

This is the problem that **Generative Engine Optimization (GEO)** solves. And in this post, you will learn what GEO is, why it matters right now, and how to measure and fix your site's AI visibility using an open-source Python tool — in under 10 minutes.

---

## SEO vs GEO: What's the Difference?

Traditional SEO optimizes for *ranking*: getting your blue link to appear on page one of Google's results. The signals are well understood — crawlability, backlinks, Core Web Vitals, structured data.

**Generative Engine Optimization** optimizes for *citation*: getting an AI model (ChatGPT, Perplexity, Claude, Gemini) to mention, quote, or link to your content when a user asks a relevant question. These models do not return a list of ten blue links. They synthesize an answer — and if your site is not part of that synthesis, you simply do not exist in that response.

The signals are fundamentally different:

| Signal | SEO | GEO |
|--------|-----|-----|
| Primary goal | Rank high in SERPs | Be cited in AI answers |
| Crawler | Googlebot | GPTBot, ClaudeBot, PerplexityBot... |
| Key file | `sitemap.xml` | `llms.txt` |
| Schema priority | Breadcrumbs, Products | FAQPage, Article, Organization |
| Content style | Keyword density | Factual claims, statistics, citations |
| Trust signal | Backlinks | Authorship, dates, authoritative quotes |

The research backing this comes from Princeton KDD 2024 and AutoGEO ICLR 2026 — peer-reviewed work showing that specific content and technical signals consistently increase a site's citation rate in large language model responses.

---

## Meet GEO Optimizer

[**GEO Optimizer**](https://github.com/Auriti-Labs/geo-optimizer-skill) is an open-source Python toolkit (MIT license) that audits your website across all eight GEO signal categories, gives you a 0–100 score, and generates the files you need to fix the gaps.

- **1030 tests**, zero external HTTP calls in the test suite
- Based on Princeton KDD 2024 + AutoGEO ICLR 2026 research
- Four CLI commands: `geo audit`, `geo fix`, `geo llms`, `geo schema`
- MCP server for AI-powered IDE integration (Claude Code, Cursor, Windsurf)
- Web demo at [geo-optimizer-web.onrender.com](https://geo-optimizer-web.onrender.com)
- Current version: v4.0.0-beta.1

---

## Installation

Requires Python 3.9+.

```bash
pip install geo-optimizer-skill
```

That is the entire installation. Verify it worked:

```bash
geo --version
# geo-optimizer-skill 4.0.0b1
```

---

## Your First Audit

```bash
geo audit --url https://yoursite.com
```

The tool fetches your homepage, `robots.txt`, `llms.txt`, checks for JSON-LD schema blocks, meta tags, content quality signals, and AI discovery endpoints. The whole thing runs in a few seconds.

A typical output looks like this:

```
 GEO Optimizer — AI Citability Audit
 https://yoursite.com

 ROBOTS.TXT ─────────────────────────────────────────────────
   GPTBot           MISSING  (OpenAI — ChatGPT training)   critical
   OAI-SearchBot    MISSING  (OpenAI — ChatGPT citations)  critical
   ClaudeBot        allowed
   PerplexityBot    MISSING                                 critical

 LLMS.TXT ────────────────────────────────────────────────────
   Not found at https://yoursite.com/llms.txt

 SCHEMA JSON-LD ──────────────────────────────────────────────
   WebSite schema   found
   FAQPage schema   missing
   Article schema   missing
   Organization     missing

 META TAGS ───────────────────────────────────────────────────
   Title            yoursite.com - Home
   Description      missing
   Canonical        found
   OG tags          found

 CONTENT QUALITY ─────────────────────────────────────────────
   Headings         8
   Statistics       0        add numbers + data
   External links   0        add authoritative citations

 AI DISCOVERY ────────────────────────────────────────────────
   /.well-known/ai.txt        missing
   /ai/summary.json           missing

──────────────────────────────────────────────────────────────
 GEO SCORE   [████████░░░░░░░░░░░░]   41 / 100   FOUNDATION
──────────────────────────────────────────────────────────────

 Top recommendations:
   1. Add all 24 AI bots to robots.txt (currently blocking ChatGPT)
   2. Create llms.txt — biggest single GEO win available
   3. Add FAQPage schema for AI answer extraction
   4. Add statistics and data references to content
```

**Score bands:**

| Score | Band | What it means |
|-------|------|---------------|
| 86–100 | Excellent | Optimized for AI citation |
| 68–85 | Good | Solid foundation, tune for specifics |
| 36–67 | Foundation | Gaps exist, AI crawlers partially blocked |
| 0–35 | Critical | Invisible or blocked from most AI engines |

---

## The 8 Audit Categories Explained

GEO Optimizer evaluates eight signal areas, each weighted based on their empirical impact on AI citation rates.

### 1. Robots.txt (18 points)

**What it checks:** Whether the 24 known AI crawlers are explicitly allowed in your `robots.txt`. Many sites have a blanket `User-agent: *` rule that technically allows everything — but missing explicit entries for bots like `GPTBot`, `OAI-SearchBot`, `PerplexityBot`, and `ClaudeBot` can mean those bots apply conservative defaults.

**Why it matters:** If a bot cannot crawl your site, it cannot index or cite it. This is the single fastest fix available — it takes five minutes and affects everything downstream.

### 2. llms.txt (18 points)

**What it checks:** Whether your site has an `/llms.txt` file, and whether that file includes a proper H1, blockquote description, structured sections, links to key pages, and a full-text variant (`/llms-full.txt`).

**Why it matters:** `llms.txt` is an emerging standard (proposed 2024) that gives AI models a curated, machine-readable summary of your site. It is the `sitemap.xml` of the GEO era. Sites with a well-formed `llms.txt` see measurably higher citation rates in Perplexity and other retrieval-augmented systems.

### 3. JSON-LD Schema (16 points)

**What it checks:** Presence and quality of structured data — specifically `WebSite`, `Organization`, `FAQPage`, and `Article` schema types.

**Why it matters:** FAQPage schema is directly extracted by AI systems to populate answer snippets. Article schema provides authorship and date signals that LLMs use to assess freshness and trustworthiness.

### 4. Meta Tags (14 points)

**What it checks:** Title tag quality, meta description, canonical URL, and Open Graph tags.

**Why it matters:** Meta descriptions and OG descriptions are often used verbatim by AI systems when summarizing a page. A missing description means the AI has to guess — and it usually gets it wrong or omits your site.

### 5. Content Quality (12 points)

**What it checks:** Heading hierarchy (`h1` through `h3`), presence of statistics and numeric claims, front-loaded key information, use of lists, word count, and external citation links.

**Why it matters:** Princeton GEO research found that content with verifiable statistics and authoritative citations is cited 2–3x more frequently than equivalent content without them. "Cite your sources" turns out to be good advice for getting cited yourself.

### 6. Signals (6 points)

**What it checks:** `lang` attribute on `<html>`, RSS/Atom feed presence, and content freshness indicators (structured date data or visible publication dates).

**Why it matters:** AI systems use language declarations to route queries correctly. RSS feeds allow AI-integrated news systems to track your content. Date signals affect how AI systems rank freshness for time-sensitive queries.

### 7. AI Discovery Endpoints (6 points)

**What it checks:** Whether your site exposes `/.well-known/ai.txt`, `/ai/summary.json`, `/ai/faq.json`, and `/ai/service.json`.

**Why it matters:** These endpoints let AI crawlers self-serve a structured overview of your site without parsing full HTML. They are the API layer for AI discovery.

### 8. Brand and Entity (10 points)

**What it checks:** Coherence of brand name across pages, knowledge graph readiness, presence of About and Contact pages, geographic identity signals, and topic authority clustering.

**Why it matters:** LLMs build entity graphs. A site with a clear, consistent entity identity (one brand name, one headquarters, one topical focus) is significantly more likely to be cited as an authoritative source than a site with scattered signals.

---

## Auto-Fix: Generate the Missing Files

Auditing is the diagnosis. `geo fix` is the treatment:

```bash
geo fix --url https://yoursite.com
```

This generates ready-to-deploy files:

- A `robots.txt` patch with all 24 AI bots explicitly allowed
- A complete `llms.txt` built from your sitemap
- Missing JSON-LD schema blocks as `<script>` snippets
- Meta tag HTML for any missing tags

You can also target a specific category:

```bash
geo fix --url https://yoursite.com --only llms
geo fix --url https://yoursite.com --only schema
```

And generate just the `llms.txt` separately:

```bash
geo llms --url https://yoursite.com
```

---

## Python API Usage

If you need to integrate GEO auditing into your own tooling, the Python API is clean and returns typed dataclasses — it never prints to stdout.

```python
from geo_optimizer.core.audit import run_full_audit

result = run_full_audit("https://yoursite.com")

print(result.score)          # 41
print(result.band)           # "foundation"
print(result.robots.score)   # 8
print(result.llms.score)     # 0

for rec in result.recommendations:
    print(f"- {rec}")
# - Add all 24 AI bots to robots.txt
# - Create llms.txt
# - Add FAQPage schema
```

For async contexts (FastAPI, async scripts):

```python
import asyncio
from geo_optimizer.core.audit import run_full_audit_async

async def check_site(url: str) -> dict:
    result = await run_full_audit_async(url)
    return {
        "score": result.score,
        "band": result.band,
        "top_issues": result.recommendations[:3],
    }

asyncio.run(check_site("https://yoursite.com"))
```

The JSON output format works well for dashboards and monitoring pipelines:

```bash
geo audit --url https://yoursite.com --format json | jq '.score'
```

---

## CI/CD Integration: Catch Regressions Before They Ship

One of the most practical use cases is automated GEO regression testing. A CMS update can silently break your schema. A `robots.txt` change can accidentally block AI bots. Catching this in CI costs nothing.

The easiest path is the official GitHub Action:

```yaml
# .github/workflows/geo-audit.yml
name: GEO Audit

on:
  push:
    branches: [main]
  pull_request:

jobs:
  geo:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: Auriti-Labs/geo-optimizer-skill@v1
        with:
          url: https://yoursite.com
          threshold: 68        # Fail if score drops below "good" band
          format: sarif        # Appears in GitHub Security tab
```

With `format: sarif`, findings automatically populate the **Security** tab of your repository as Code Scanning alerts — no extra configuration needed.

For PR comments that show the score on every pull request:

```yaml
- uses: Auriti-Labs/geo-optimizer-skill@v1
  id: geo
  with:
    url: https://yoursite.com

- uses: actions/github-script@v7
  if: github.event_name == 'pull_request'
  with:
    script: |
      const score = '${{ steps.geo.outputs.score }}';
      const band  = '${{ steps.geo.outputs.band }}';
      await github.rest.issues.createComment({
        owner: context.repo.owner,
        repo:  context.repo.repo,
        issue_number: context.issue.number,
        body: `## GEO Audit\n\n**Score:** ${score}/100  **Band:** \`${band}\``
      });
```

For teams using JUnit-compatible CI dashboards (Jenkins, CircleCI, etc.):

```yaml
- uses: Auriti-Labs/geo-optimizer-skill@v1
  with:
    url: https://yoursite.com
    format: junit
    output-file: geo-results

- uses: dorny/test-reporter@v1
  with:
    name: GEO Audit
    path: geo-results.xml
    reporter: java-junit
```

---

## MCP Server: GEO Audits Inside Your AI IDE

If you use Claude Code, Cursor, or Windsurf, you can install the GEO Optimizer MCP server and audit sites directly from your AI assistant without leaving the editor.

```bash
pip install geo-optimizer-skill[mcp]
```

**Claude Code setup:**

```bash
claude mcp add geo-optimizer -- geo-mcp
```

**Cursor setup** — add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "geo-optimizer": {
      "command": "geo-mcp",
      "args": []
    }
  }
}
```

Once connected, you can ask your AI assistant things like:

> "Run a GEO audit on my-client-site.com and list the top three issues."

> "Generate an llms.txt for https://docs.myproduct.com"

> "Validate the JSON-LD schema on the homepage"

The MCP server exposes eight tools: `geo_audit`, `geo_fix`, `geo_llms_generate`, `geo_schema_validate`, `geo_citability`, `geo_ai_discovery`, `geo_trust_score`, and `geo_compare`. The last one is particularly useful for competitive analysis — you can compare your GEO score against a competitor's in a single call.

---

## Try It Now

The fastest way to see where you stand is the web demo — no installation required:

**[geo-optimizer-web.onrender.com](https://geo-optimizer-web.onrender.com)**

Paste your URL, get a full breakdown in seconds.

If you want the CLI:

```bash
pip install geo-optimizer-skill
geo audit --url https://yoursite.com
```

---

## Key Takeaways

- **GEO is not SEO.** Ranking on Google and being cited by ChatGPT require different signals. Both matter in 2026.
- **The biggest wins are quick.** Fixing `robots.txt` to allow AI bots and adding `llms.txt` can be done in under an hour and covers 36 of the 100 available points.
- **Automate the regression check.** One GitHub Actions step catches GEO regressions the same way ESLint catches code quality issues — before they reach production.
- **The MCP server brings auditing into your editor.** If you are already using an AI IDE, you can add GEO checks to your development workflow with a single command.

---

## Resources

- **GitHub:** [github.com/Auriti-Labs/geo-optimizer-skill](https://github.com/Auriti-Labs/geo-optimizer-skill) — star the repo to follow updates
- **Web demo:** [geo-optimizer-web.onrender.com](https://geo-optimizer-web.onrender.com) — free, no account required
- **Documentation:** [auriti-labs.github.io/geo-optimizer-skill](https://auriti-labs.github.io/geo-optimizer-skill)
- **Princeton KDD 2024 paper:** [GEO: Generative Engine Optimization](https://arxiv.org/abs/2311.09735)
- **llms.txt standard:** [llmstxt.org](https://llmstxt.org)

If the tool helps you, a GitHub star helps more developers find it. If you find a bug or want to contribute a new audit check, pull requests are open and the contributing guide is in the repo.

---

*What AI search visibility issues have you run into? Drop them in the comments — I read everything.*
