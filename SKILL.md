---
name: geo-optimizer
description: "Optimize websites for AI search engine visibility and citation. Audits robots.txt, llms.txt, JSON-LD schema, and content quality using the Princeton GEO framework (KDD 2024). Use when auditing a site for AI discoverability, generating llms.txt, injecting JSON-LD schema, fixing AI crawler access, or improving content citability for ChatGPT, Perplexity, Claude, and Gemini."
---

# GEO Optimizer

Make websites visible and citable by AI search engines (ChatGPT Search, Perplexity, Claude, Gemini AI Overviews). Implements the GEO audit framework plus a 47-method citability engine based on Princeton KDD 2024 research.

## Workflow

### Step 1 — Audit the site

Run `geo audit` first. It scores the site 0–100 and generates a prioritized action list.

```bash
geo audit --url https://yoursite.com
```

Score interpretation: 0–40 = critical gaps, 41–70 = foundation exists, 71–90 = good, 91–100 = excellent.

For batch auditing: `geo audit --sitemap https://yoursite.com/sitemap.xml --max-urls 25`

### Step 2 — Fix AI crawler access (robots.txt)

Ensure all AI citation bots can access the site. Add these user-agents with `Allow: /`:

- **Critical citation bots**: `OAI-SearchBot`, `PerplexityBot`, `ClaudeBot`, `Google-Extended`
- **Additional bots**: `GPTBot`, `ChatGPT-User`, `anthropic-ai`, `claude-web`, `Googlebot`, `Bingbot`, `Applebot`, `Applebot-Extended`, `meta-externalagent`, `Bytespider`, `cohere-ai`, `DuckAssistBot`

To block training while keeping citations: `Disallow: /` for `GPTBot` and `anthropic-ai`, but always keep `OAI-SearchBot`, `ClaudeBot`, `PerplexityBot` at `Allow: /`.

### Step 3 — Generate llms.txt

Create `/llms.txt` so AI engines discover site content:

```bash
geo llms --base-url https://yoursite.com --site-name "Site Name" --description "One-sentence description." --output ./public/llms.txt
```

Required structure: H1 (site name) → blockquote (description) → sections with descriptive links (`- [Title](URL): Description`). Keep under 200 lines.

### Step 4 — Inject JSON-LD schema

Add structured data so AI engines understand page types:

```bash
geo schema --type website --url https://yoursite.com
geo schema --type faq --url https://yoursite.com/faq
geo schema --type webapp --url https://yoursite.com/tool
```

Schema types: `website` (all pages), `webapp` (tools/calculators), `faq` (Q&A content), `article` (blog/guides), `organization`, `breadcrumb`.

### Step 5 — Optimize content (Princeton GEO methods)

Apply evidence-based content improvements, ordered by measured impact:

1. **Cite sources** (+30–115% AI visibility) — add authoritative external links
2. **Add statistics** (+40%) — include concrete numbers, percentages, dates
3. **Add quotations** (+30–40%) — use expert quotes with attribution: `"Text" — Name, Role, Organization, Year`
4. **Fluency optimization** (+15–30%) — clear, direct language
5. **Authoritative tone** (+6–12%) — confident, expert framing

Never keyword-stuff — Princeton research shows ~0% impact with possible negative effect.

### Step 6 — Auto-fix all gaps

Generate all missing files at once:

```bash
geo fix --url https://yoursite.com --apply
```

This creates robots.txt entries, llms.txt, JSON-LD schema, and meta tags based on audit results.

## Additional Commands

```bash
# Compare before/after versions of a page
geo diff --before https://yoursite.com/old --after https://yoursite.com/new

# Track score history and detect regressions
geo audit --url https://yoursite.com --save-history --regression
geo history --url https://yoursite.com

# Passive AI visibility monitoring
geo monitor --domain yoursite.com

# Recurring monitoring with HTML trend report
geo track --url https://yoursite.com --report --output ./geo-track-report.html
```

## Platform-Specific Context Files

For platform-optimized versions of this skill, see `ai-context/`:

| Platform | File | Limit |
|----------|------|-------|
| Claude Projects | `ai-context/claude-project.md` | No limit — full context |
| Cursor | `ai-context/cursor.mdc` | Glob-activated |
| Windsurf | `ai-context/windsurf.md` | 12,000 chars |
| Kiro | `ai-context/kiro-steering.md` | fileMatch inclusion |
| ChatGPT Custom GPT | `ai-context/chatgpt-custom-gpt.md` | 8,000 chars |
| ChatGPT Instructions | `ai-context/chatgpt-instructions.md` | 1,500 chars/field |
