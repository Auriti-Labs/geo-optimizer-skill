---
name: geo-optimizer
description: Audit and fix a website for AI search visibility (Generative Engine Optimization). Use when asked to check whether a site or page can be found and cited by ChatGPT Search, Perplexity, Claude or Google AI Overviews, to score it 0-100 with `geo audit`, or to fix robots.txt AI crawler rules, llms.txt, JSON-LD schema, meta tags and citability of the content before publishing.
---

# GEO Optimizer

> Make websites visible and citable by AI search engines (ChatGPT Search, Perplexity, Claude, Google AI Overviews). Implements the GEO audit framework plus a citability engine of 47 content checks, 9 of them taken directly from the methods tested in Princeton KDD 2024 research.

## Workflow

### Step 1 — Audit the site

Run `geo audit` first. It scores the site 0–100 across 9 categories and generates a prioritized action list.

```bash
geo audit --url https://yoursite.com
geo audit --url https://yoursite.com --format json
geo audit --sitemap https://yoursite.com/sitemap.xml --max-urls 25
```

Score bands: 0–35 critical · 36–67 foundation · 68–85 good · 86–100 excellent.

### Step 2 — Fix AI crawler access (robots.txt)

AI crawlers fall into three tiers: training, search, and user-triggered fetch. To stay eligible to appear in AI search answers, do not block the search-tier bots (this makes the site eligible; it does not guarantee placement or citation):

- `OAI-SearchBot` — ChatGPT search
- `PerplexityBot` — Perplexity search index
- `Claude-SearchBot` — Claude search
- `Googlebot` — Google Search, which also feeds AI Overviews and AI Mode. These are governed by Googlebot access and snippet controls (`nosnippet`, `max-snippet`), not by `Google-Extended`

`Google-Extended` is a robots.txt token, not a separate crawler. It controls whether Google may use content for Gemini/Vertex training and grounding. It does not affect Search or AI Overviews.

To opt out of training while staying open to AI search: `Disallow: /` for the training bots (`GPTBot`, `ClaudeBot`, `Google-Extended`), and keep `Allow: /` for `OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`, and `Googlebot`. Whether to block training is a policy choice; vendors treat these settings as independent.

### Step 3 — Generate llms.txt

`/llms.txt` is a proposed convention that gives AI agents a short, machine-readable map of the site. Support varies by system and it does not guarantee AI visibility or citation.

```bash
geo llms --base-url https://yoursite.com --site-name "Site Name" --description "One-sentence description." --output ./public/llms.txt
```

Required structure: H1 (site name) → blockquote (description) → H2 sections with descriptive links. Keep under 200 lines. Full spec: https://llmstxt.org

### Step 4 — Inject JSON-LD schema

Add structured data so AI engines understand page types:

```bash
geo schema --type website --url https://yoursite.com
geo schema --type faq --url https://yoursite.com/faq
geo schema --type webapp --url https://yoursite.com/tool
```

Types: `website`, `webapp`, `faq`, `article`, `organization`, `breadcrumb`, `howto`, `review`, `product`.

Structured data helps machines parse the page; it does not guarantee citation.

### Step 5 — Optimize content (Princeton GEO methods)

Apply content improvements ordered by the effect reported in the paper's benchmark:

| Priority | Method | Impact | Action |
|----------|--------|--------|--------|
| 🔴 1 | Cite Sources | +30–115% | Add authoritative external links |
| 🔴 2 | Add Statistics | +40% | Include concrete numbers, percentages, dates |
| 🟠 3 | Quotation Addition | +30–40% | Expert quotes: `"Text" — Name, Role, Org, Year` |
| 🟠 4 | Authoritative Tone | +6–12% | Confident, expert framing |
| 🟡 5 | Fluency Optimization | +15–30% | Clear, direct language |
| 🟡 6 | Easy-to-Understand | +8–15% | Define terms, use analogies |
| 🟢 7 | Technical Terms | +5–10% | Correct industry terminology |
| 🟢 8 | Unique Words | +5–8% | Vary vocabulary deliberately |
| ❌ 9 | Keyword Stuffing | ~0% ⚠️ | Do NOT apply — neutral to negative |

Source: Princeton KDD 2024 (GEO-bench, 10,000 queries; the authors also report tests on Perplexity.ai). The table lists the nine methods tested in the paper. Impact figures are relative changes in the paper's visibility metrics, not citation rates; effects varied by domain and engines have changed since. GEO Optimizer's citability score uses 47 content checks, 9 of which come from these methods. Related research: AutoGEO (arXiv preprint 2510.11438, 2025; no publication venue listed).

### Step 6 — Auto-fix all gaps

Generate all missing files at once:

```bash
geo fix --url https://yoursite.com --apply
geo fix --url https://yoursite.com --only robots,llms,schema
```

Creates robots.txt entries, llms.txt, JSON-LD schema, meta tags, and AI discovery endpoints based on audit results.

## Scoring

9 categories, 100 points total in rubric v2:

| Category | What it measures | Points (v2) |
|----------|------------------|-------------|
| `google_ai` | Google AI readiness checks | 20 |
| `robots` | Robots.txt availability and citation-bot access | 14 |
| `schema` | JSON-LD validity, richness, types, and visible-name match | 14 |
| `content` | Headings, evidence, links, structure, and image alt coverage | 14 |
| `brand_entity` | Brand coherence, Knowledge Graph, about/contact, identity, authority | 12 |
| `meta` | Title, description, and Open Graph | 11 |
| `llms` | llms.txt presence, sections, links, and llms-full.txt | 6 |
| `signals` | Language, RSS, and freshness | 6 |
| `ai_discovery` | ai.txt, summary.json, and markdown negotiation | 3 |

### Google AI readiness checks

Each check includes its Google source URL in audit JSON and recommendations:

- `G-INDEX` (5): final status 200; no meta robots, googlebot, or X-Robots-Tag noindex; Googlebot is not blocked by robots.txt. Source: https://developers.google.com/search/docs/essentials/technical
- `G-SNIPPET` (5): no nosnippet, max-snippet:0, or max-snippet below 50; max-image-preview:none warns; data-nosnippet over 50% fails and over 10% warns. Source: https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag
- `G-CANONICAL` (3): exactly one absolute canonical in `<head>`, matching the final URL. Source: https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls
- `G-DATES` (2): visible date agrees with datePublished/dateModified and no date is in the future. Source: https://developers.google.com/search/docs/appearance/publication-dates
- `G-BYLINE` (2): visible author or JSON-LD author, ideally linked to an author page. Source: https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- `G-LINKS` (1): internal links use crawlable `<a href>` elements and no `#/` routes. Source: https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics
- `G-VIEWPORT` (1): a meta viewport is present. Source: https://developers.google.com/search/docs/appearance/page-experience
- `G-SITEMAP` (1): a Sitemap directive is declared in robots.txt. Source: https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap
- `G-SD-VISIBLE` (2 in `schema`): JSON-LD `name` or `headline` appears in visible text. Source: https://developers.google.com/search/docs/appearance/structured-data/sd-policies
- `G-GENAI-CONTROL` (0, manual): check Search Console generative-AI opt-out. Source: https://developers.google.com/search/docs/fundamentals/ai-optimization-guide

`llms.txt` is useful to other AI agents but is ignored by Google Search. The score is versioned: JSON exposes `score_version` and per-category `score_max`; use `geo audit --score-version 1` for legacy v1 comparisons. History deltas and regressions compare snapshots only when their `score_version` matches.

## CLI Commands

**Main commands** covering audit, remediation, analysis, and monitoring (run `geo --help` for all 16, including `access`, `authority`, `citations`, `drift`, and `perception`):

```bash
# ── Primary ──
geo audit    --url URL [--format text|json|rich|html|pdf|github|sarif|junit] [--sitemap URL]
geo fix      --url URL [--apply] [--only robots,llms,schema,meta,ai_discovery,content]
geo llms     --base-url URL --site-name NAME --description DESC --output FILE
geo schema   --type TYPE --url URL [--file FILE --inject]

# ── Analysis ──
geo diff       --before URL --after URL
geo history    --url URL
geo coherence  --sitemap URL

# ── Monitoring ──
geo monitor  --domain DOMAIN
geo track    --url URL [--report | --history] [--output FILE]

# ── Utility ──
geo logs       --file LOGFILE
geo snapshots  [--query TEXT --answer-file FILE] [--quality --snapshot-id ID]
```

## Output Formats

8 formats for different workflows:

| Format | Flag | Use case |
|--------|------|----------|
| text | `--format text` | Terminal (default) |
| json | `--format json` | Programmatic consumption, CI pipelines |
| rich | `--format rich` | Colored terminal with ASCII dashboard |
| html | `--format html` | Self-contained HTML report |
| github | `--format github` | GitHub Actions annotations |
| sarif | `--format sarif` | Code-scanning tools (SARIF) |
| junit | `--format junit` | CI test reports (JUnit XML) |
| pdf | `--format pdf` | Client-facing reports |

## Informational Checks

10 non-scoring checks that provide deeper analysis beyond the 0–100 score:

| Check | What it detects |
|-------|-----------------|
| WebMCP Readiness | SearchAction, labeled forms, tool attributes for AI agents |
| Negative Signals | CTA overload, thin content, keyword stuffing, boilerplate |
| Prompt Injection | LLM instructions in content, HTML comment injection, hidden text |
| Trust Stack | 5-layer trust score (technical, identity, social, academic, consistency) |
| RAG Chunk Readiness | Content structure optimized for retrieval-augmented generation |
| Embedding Proximity | Semantic alignment between title, headings, and body content |
| Content Decay | Temporal signals indicating stale or outdated content |
| Platform Citation | Per-platform citation profile (ChatGPT vs Perplexity vs Gemini) |
| Context Window | Content length optimization for LLM context windows |
| Instruction Readiness | Content structure that helps LLMs follow extraction patterns |

## MCP Integration

12 tools and 5 resources for Claude Code, Cursor, Windsurf, and any MCP client:

**Tools:**

| Tool | Description |
|------|-------------|
| `geo_audit` | Full GEO audit (score 0–100) |
| `geo_fix` | Generate automatic fixes |
| `geo_llms_generate` | Generate llms.txt from sitemap |
| `geo_citability` | Citability score (47 content checks) |
| `geo_schema_validate` | Validate JSON-LD schema |
| `geo_compare` | Compare GEO scores across sites (max 5) |
| `geo_gap_analysis` | Competitive gap analysis with priorities |
| `geo_ai_discovery` | Check AI discovery endpoints |
| `geo_check_bots` | Check AI bot access via robots.txt |
| `geo_trust_score` | Trust Stack Score (5-layer, grade A–F) |
| `geo_negative_signals` | Negative signals detection |
| `geo_factual_accuracy` | Factual claims and sourcing audit |

**Resources:** `geo://ai-bots` · `geo://score-bands` · `geo://methods` · `geo://changelog` · `geo://ai-discovery-spec`

## Plugin System

Extend the audit with custom checks via entry points:

```python
# pyproject.toml
[project.entry-points."geo_optimizer.checks"]
my_check = "my_package:MyCheck"
```

Plugins implement the `AuditCheck` protocol (`name`, `description`, `max_score`, `run()`). Plugin results appear in the audit output but do not affect the base score.

## Platform Context Files

Platform-optimized versions of this skill for different AI tools:

| Platform | File | Size | Limit | How to use |
|----------|------|------|-------|------------|
| Claude Projects | `ai-context/claude-project.md` | ~11,700 chars | No limit | Project → Add as Knowledge |
| ChatGPT Custom GPT | `ai-context/chatgpt-custom-gpt.md` | ~4,500 chars | 8,000 chars | GPT Builder → System prompt |
| ChatGPT Instructions | `ai-context/chatgpt-instructions.md` | ~800 chars | 1,500 chars/field | Settings → Custom Instructions |
| Cursor | `ai-context/cursor.mdc` | ~4,200 chars | No limit | Copy to `.cursor/rules/geo-optimizer.mdc` |
| Windsurf | `ai-context/windsurf.md` | ~4,500 chars | 12,000 chars | Copy to `.windsurf/rules/geo-optimizer.md` |
| Kiro | `ai-context/kiro-steering.md` | ~3,300 chars | No limit | Copy to `.kiro/steering/geo-optimizer.md` |

```bash
# Quick copy commands
mkdir -p .cursor/rules && cp ai-context/cursor.mdc .cursor/rules/geo-optimizer.mdc
mkdir -p .windsurf/rules && cp ai-context/windsurf.md .windsurf/rules/geo-optimizer.md
mkdir -p .kiro/steering && cp ai-context/kiro-steering.md .kiro/steering/geo-optimizer.md
```

## Hosted monitoring (optional)

`geo audit` is a snapshot. [GeoReady](https://geoready.dev/?utm_source=skill&utm_medium=skill_md&utm_campaign=hosted) runs this same engine on a schedule: score history, regression alerts on drops of 5+ points, automated Perplexity answer checks, and an Agency plan for multi-client portfolios. The free web audit needs no account; paid plans are on [geoready.dev/pricing](https://geoready.dev/pricing/?utm_source=skill&utm_medium=skill_md&utm_campaign=hosted). Everything in this skill works without it.

---

*GEO Optimizer by Juan Camilo Auriti — https://github.com/auriti-labs/geo-optimizer-skill*
