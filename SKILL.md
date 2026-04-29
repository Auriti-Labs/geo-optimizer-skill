# GEO Optimizer

> Make websites visible and citable by AI search engines (ChatGPT Search, Perplexity, Claude, Gemini AI Overviews). Implements the GEO audit framework plus a 47-method citability engine based on Princeton KDD 2024 research.

## Workflow

### Step 1 — Audit the site

Run `geo audit` first. It scores the site 0–100 across 8 categories and generates a prioritized action list.

```bash
geo audit --url https://yoursite.com
geo audit --url https://yoursite.com --format json
geo audit --sitemap https://yoursite.com/sitemap.xml --max-urls 25
```

Score bands: 0–35 critical · 36–67 foundation · 68–85 good · 86–100 excellent.

### Step 2 — Fix AI crawler access (robots.txt)

Ensure AI citation bots can reach the site. Critical bots that must never be blocked:

- `OAI-SearchBot` — ChatGPT Search citations
- `PerplexityBot` — Perplexity answer citations
- `ClaudeBot` — Claude web citations
- `Google-Extended` — Gemini AI Overviews

To allow citations while blocking training: `Disallow: /` for `GPTBot` and `anthropic-ai`, but keep `Allow: /` for `OAI-SearchBot`, `ClaudeBot`, `PerplexityBot`.

### Step 3 — Generate llms.txt

`/llms.txt` tells AI crawlers what the site is about and which pages matter.

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

Types: `website`, `webapp`, `faq`, `article`, `organization`, `breadcrumb`.

### Step 5 — Optimize content (Princeton GEO methods)

Apply evidence-based improvements ordered by measured impact:

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

Source: Princeton KDD 2024 (10,000 queries on Perplexity.ai). Extended by AutoGEO ICLR 2026, SE Ranking 2025, Growth Marshal 2026 to 47 total methods.

### Step 6 — Auto-fix all gaps

Generate all missing files at once:

```bash
geo fix --url https://yoursite.com --apply
geo fix --url https://yoursite.com --only robots,llms,schema
```

Creates robots.txt entries, llms.txt, JSON-LD schema, meta tags, and AI discovery endpoints based on audit results.

## Scoring

8 categories, 100 points total:

| Category | What it measures |
|----------|-----------------|
| `robots` | AI bot access via robots.txt |
| `llms` | llms.txt presence, structure, depth |
| `schema` | JSON-LD types, richness, sameAs |
| `meta` | title, description, canonical, Open Graph |
| `content` | H1, word count, numbers, links, structure |
| `signals` | lang attribute, RSS feed, freshness |
| `ai_discovery` | .well-known/ai.txt, /ai/summary.json, /ai/faq.json |
| `brand_entity` | Name consistency, Knowledge Graph, about/contact |

## CLI Commands

**11 commands** covering audit, remediation, analysis, and monitoring:

```bash
# ── Primary ──
geo audit    --url URL [--format text|json|rich|html|github|ci|pdf] [--sitemap URL]
geo fix      --url URL [--apply] [--only robots,llms,schema,meta,ai_discovery,content]
geo llms     --base-url URL --site-name NAME --description DESC --output FILE
geo schema   --type TYPE --url URL [--inject FILE]

# ── Analysis ──
geo diff       --before URL --after URL
geo history    --url URL
geo coherence  --url URL

# ── Monitoring ──
geo monitor  --domain DOMAIN
geo track    --url URL [--report] [--output FILE]

# ── Utility ──
geo logs       --path LOGFILE
geo snapshots  --url URL [--save | --compare SNAPSHOT_ID]
```

## Output Formats

7 formats for different workflows:

| Format | Flag | Use case |
|--------|------|----------|
| text | `--format text` | Terminal (default) |
| json | `--format json` | Programmatic consumption, CI pipelines |
| rich | `--format rich` | Colored terminal with ASCII dashboard |
| html | `--format html` | Self-contained HTML report |
| github | `--format github` | GitHub Actions annotations |
| ci | `--format ci` | CI/CD systems (structured annotations) |
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
| `geo_citability` | Citability score (47 methods) |
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

---

*GEO Optimizer by Juan Camilo Auriti — https://github.com/auriti-labs/geo-optimizer-skill*
