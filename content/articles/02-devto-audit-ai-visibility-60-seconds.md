---
title: "Audit Your Site's AI Visibility in 60 Seconds with Python"
published: false
description: "A hands-on tutorial for using GEO Optimizer — an open-source Python tool — to audit, score, and fix your site's visibility in AI search engines like ChatGPT, Perplexity, and Claude."
tags: python, webdev, tutorial, opensource
cover_image: https://raw.githubusercontent.com/Auriti-Labs/geo-optimizer-skill/main/site/assets/og-banner.png
canonical_url:
series: Generative Engine Optimization
---

Your site might rank perfectly on Google and still be invisible to ChatGPT, Perplexity, and Claude. That is Generative Engine Optimization (GEO) in a nutshell: a new layer of discoverability that traditional SEO tools do not measure.

This tutorial walks you through [GEO Optimizer](https://github.com/Auriti-Labs/geo-optimizer-skill), a free, open-source Python tool that audits your site's AI visibility in under a minute, explains what is wrong, and generates the files needed to fix it — all from the command line.

By the end you will have: a scored audit of your site, auto-generated `llms.txt` and JSON-LD schema files, a GitHub Actions workflow for continuous AI-visibility monitoring, and a Python snippet for embedding audits in your own code.

---

## Step 1 — Install

GEO Optimizer requires Python 3.9+. Install it from PyPI:

```bash
pip install geo-optimizer-skill
```

Verify the install:

```bash
geo --version
# geo-optimizer-skill 3.19.2
```

That is it. No API keys, no sign-up.

---

## Step 2 — Run Your First Audit

Point `geo audit` at any public URL:

```bash
geo audit --url https://example.com
```

Default output is a clean text report. For a richer experience use the `--format rich` flag:

```bash
geo audit --url https://example.com --format rich
```

Sample output:

```
GEO Optimizer — AI Visibility Audit
URL: https://example.com
Date: 2026-04-01 09:14:32

┌─────────────────────────┬────────┬───────┬──────────────────────────────────────────┐
│ Category                │ Score  │ Max   │ Status                                   │
├─────────────────────────┼────────┼───────┼──────────────────────────────────────────┤
│ robots.txt              │  5/18  │  18   │ ⚠  No AI bot directives found            │
│ llms.txt                │  0/18  │  18   │ ✗  File not found                        │
│ Schema JSON-LD          │  4/16  │  16   │ ⚠  Missing FAQ and Article schema        │
│ Meta Tags               │ 11/14  │  14   │ ✓  Title and description present         │
│ Content Quality         │  7/12  │  12   │ ⚠  Low word count, no numbered lists     │
│ Signals                 │  3/6   │   6   │ ✓  Language declared                     │
│ AI Discovery            │  0/6   │   6   │ ✗  No .well-known/ai.txt or summary.json │
│ Brand & Entity          │  4/10  │  10   │ ⚠  No Knowledge Graph signals found      │
├─────────────────────────┼────────┼───────┼──────────────────────────────────────────┤
│ TOTAL                   │ 34/100 │ 100   │ CRITICAL — AI engines cannot cite you    │
└─────────────────────────┴────────┴───────┴──────────────────────────────────────────┘

Grade: CRITICAL (0–35)
```

Need machine-readable output? Seven formats are available:

```bash
geo audit --url https://example.com --format json   # CI pipelines
geo audit --url https://example.com --format sarif  # GitHub Code Scanning
geo audit --url https://example.com --format html   # shareable report
geo audit --url https://example.com --format junit  # test suite integration
```

---

## Step 3 — Understand the Score

The audit evaluates 100 points across eight categories. Here is what each one means for AI engines:

| Category | Points | What AI engines care about |
|---|---|---|
| **robots.txt** | 18 | Must explicitly allow known AI bots (GPTBot, ClaudeBot, PerplexityBot, etc.) |
| **llms.txt** | 18 | A structured plain-text file at `/llms.txt` that summarizes your site for LLMs |
| **Schema JSON-LD** | 16 | Structured data (Article, FAQ, Organization) that AI can parse without guessing |
| **Meta Tags** | 14 | Title, description, canonical, Open Graph — basic but still required |
| **Content Quality** | 12 | Word count, heading hierarchy, numbered lists, front-loaded answers |
| **Signals** | 6 | Language declaration, RSS feed, freshness indicators |
| **AI Discovery** | 6 | `.well-known/ai.txt`, `/ai/summary.json`, `/ai/faq.json` |
| **Brand & Entity** | 10 | Coherent name/domain/social signals, Knowledge Graph readiness |

Score bands:

- **86–100** — Excellent. AI engines can confidently cite and summarize your content.
- **68–85** — Good. Minor gaps but broadly discoverable.
- **36–67** — Foundation. Significant structural issues limiting citation frequency.
- **0–35** — Critical. AI engines will skip or misrepresent your site.

Most production sites land in the 30–50 range on first audit.

---

## Step 4 — Auto-Fix Issues

`geo fix` reads the audit results and generates corrected files locally. It does not touch your server — it outputs files for you to deploy.

```bash
geo fix --url https://example.com --output ./geo-fixes/
```

Sample output:

```
GEO Fixer — Generating fixes for https://example.com
──────────────────────────────────────────────────────
✓  robots.txt        → geo-fixes/robots.txt         (added 24 AI bot directives)
✓  llms.txt          → geo-fixes/llms.txt            (generated from page content)
✓  schema.jsonld     → geo-fixes/schema.jsonld       (Article + FAQ + Organization)
✓  meta-tags.html    → geo-fixes/meta-tags.html      (canonical + OG tags snippet)
✓  ai-summary.json   → geo-fixes/ai/summary.json
✓  ai-faq.json       → geo-fixes/ai/faq.json
✓  ai-service.json   → geo-fixes/ai/service.json
✓  ai.txt            → geo-fixes/.well-known/ai.txt

8 fixes generated. Deploy these files to your server root.
Estimated score after fix: 74/100 (Good)
```

Review each file before deploying — the tool generates sensible defaults but you will want to customize the descriptive fields.

---

## Step 5 — Generate llms.txt

`llms.txt` is the single highest-value file for AI visibility. It gives language models a structured, human-readable overview of your site — what it does, who it serves, and where the authoritative content lives.

Generate it standalone with:

```bash
geo llms --url https://example.com --output ./llms.txt
```

Sample generated file:

```markdown
# Example Domain

> A placeholder domain used in documentation examples by IANA.

## About

Example.com is maintained by IANA as a reference domain.
It is not affiliated with any commercial product or service.

## Key Pages

- [Home](https://example.com): Main landing page
- [More information](https://www.iana.org/domains/reserved): IANA reserved domains

## Contact

- Organization: IANA
- Website: https://www.iana.org
```

Upload this file to your server root so it is reachable at `https://yourdomain.com/llms.txt`. AI crawlers will pick it up on their next pass.

You can also validate an existing `llms.txt`:

```bash
geo llms --url https://yourdomain.com --validate
```

---

## Step 6 — Add to CI/CD (GitHub Actions)

The real value of a python SEO tool like this is running it on every deployment so regressions are caught before they ship. Here is a ready-to-use GitHub Actions workflow:

```yaml
# .github/workflows/geo-audit.yml
name: AI Visibility Audit

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: "0 9 * * 1"   # Every Monday at 09:00 UTC

jobs:
  geo-audit:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install GEO Optimizer
        run: pip install geo-optimizer-skill

      - name: Run AI visibility audit
        run: |
          geo audit \
            --url ${{ vars.SITE_URL }} \
            --format sarif \
            --output geo-results.sarif

      - name: Upload SARIF to GitHub Code Scanning
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: geo-results.sarif

      - name: Fail if score is critical
        run: |
          SCORE=$(geo audit --url ${{ vars.SITE_URL }} --format json | python -c "import sys,json; d=json.load(sys.stdin); print(d['score']['total'])")
          echo "GEO score: $SCORE"
          if [ "$SCORE" -lt 36 ]; then
            echo "Score is CRITICAL ($SCORE/100). Failing build."
            exit 1
          fi
```

Set `SITE_URL` in your repository variables (`Settings > Variables > Actions`). The workflow uploads SARIF results to GitHub's Security tab so issues appear inline in pull request diffs.

---

## Step 7 — Use the Python API Programmatically

The CLI is a wrapper around a clean Python API. You can embed generative engine optimization audits directly in your scripts, dashboards, or monitoring tools.

### Basic audit

```python
from geo_optimizer import audit

result = audit("https://example.com")

print(result.score.total)          # 34
print(result.score.grade)          # "critical"
print(result.score.robots)         # 5
print(result.score.llms)           # 0
print(result.score.schema)         # 4

for issue in result.issues:
    print(f"[{issue.severity}] {issue.category}: {issue.message}")
```

### Batch audit across multiple URLs

```python
from geo_optimizer import audit
import json

sites = [
    "https://site-a.com",
    "https://site-b.com",
    "https://site-c.com",
]

report = []
for url in sites:
    result = audit(url)
    report.append({
        "url": url,
        "score": result.score.total,
        "grade": result.score.grade,
        "top_issue": result.issues[0].message if result.issues else None,
    })

print(json.dumps(report, indent=2))
```

### Async audit for high-throughput pipelines

```python
import asyncio
from geo_optimizer import audit_async

async def audit_all(urls: list[str]):
    tasks = [audit_async(url) for url in urls]
    return await asyncio.gather(*tasks)

urls = ["https://site-a.com", "https://site-b.com"]
results = asyncio.run(audit_all(urls))

for result in results:
    print(f"{result.url}: {result.score.total}/100 ({result.score.grade})")
```

### Generate llms.txt from code

```python
from geo_optimizer import generate_llms_txt

content = generate_llms_txt("https://example.com")
with open("llms.txt", "w") as f:
    f.write(content)
```

---

## Bonus — MCP Server for AI IDEs

If you use Claude, Cursor, or any MCP-compatible AI IDE, you can give your assistant direct access to GEO audit tools — no CLI switching required.

Add this to your MCP configuration:

```json
{
  "mcpServers": {
    "geo-optimizer": {
      "command": "python",
      "args": ["-m", "geo_optimizer.mcp"],
      "env": {}
    }
  }
}
```

For Claude Desktop (`~/.config/claude/claude_desktop_config.json`) or Cursor (`.cursor/mcp.json`), the block is the same.

Once connected, your AI assistant can call eight MCP tools directly:

- `geo_audit` — full scored audit
- `geo_fix` — generate fix files
- `geo_llms_generate` — create or validate llms.txt
- `geo_schema_validate` — check JSON-LD structured data
- `geo_citability` — 42-point citability check
- `geo_ai_discovery` — check `.well-known/ai.txt` and related endpoints
- `geo_check_bots` — verify robots.txt bot permissions
- `geo_trust_score` — E-E-A-T and trust signal analysis

Example: in Claude Desktop, you can now type "Audit https://mysite.com for AI visibility" and get a live scored report inline.

---

## What to Do After Your Audit

A typical remediation sequence for a site scoring below 50:

1. **Deploy the generated `robots.txt`** — immediate unblocking of AI crawlers (+ up to 18 points).
2. **Publish `llms.txt`** — the highest-leverage single file for AI citation frequency (+ up to 18 points).
3. **Add JSON-LD schema** — `Article`, `FAQPage`, and `Organization` cover most of the schema gap (+ up to 12 points).
4. **Add AI discovery files** — drop the three JSON files under `/ai/` and the `.well-known/ai.txt` (+ 6 points).
5. **Re-run the audit** — confirm your score crossed into the Good band (68+).

Most sites move from Critical to Good in a single afternoon of work.

---

## Key Takeaways

- AI engines (ChatGPT, Perplexity, Claude) have their own discoverability requirements that standard SEO tools do not cover.
- `pip install geo-optimizer-skill` gives you a full AI visibility audit in one command, with no API keys needed.
- The eight-category, 100-point scoring system pinpoints exactly which files and signals are missing.
- `geo fix` generates all corrected files locally — you review and deploy, the tool never touches your server.
- The Python API and async support make it straightforward to embed continuous GEO monitoring into any pipeline.
- The MCP server integration lets AI IDEs audit sites on your behalf without leaving the chat interface.

---

## Resources

- GitHub: [Auriti-Labs/geo-optimizer-skill](https://github.com/Auriti-Labs/geo-optimizer-skill)
- Web demo (no install): [geo-optimizer-web.onrender.com](https://geo-optimizer-web.onrender.com)
- PyPI: [pypi.org/project/geo-optimizer-skill](https://pypi.org/project/geo-optimizer-skill)
- Docker: `docker pull ghcr.io/auriti-labs/geo-optimizer-skill:latest`

If this tutorial helped, drop a star on the repo and share your before/after score in the comments below. Questions about a specific audit result? Post the output and I will help interpret it.
