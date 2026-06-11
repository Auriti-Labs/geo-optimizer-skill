<div align="center">

<img src="assets/geoready-logo.svg" alt="GeoReady GEO Optimizer — Answer Engine Optimization toolkit" width="640"/>

### The open-source **Answer Engine Optimization (AEO)** & **Generative Engine Optimization (GEO)** toolkit.

#### Audit, optimize, and track whether **ChatGPT, Perplexity, Gemini, Claude, and Google AI Overviews** can crawl, understand, and **cite** your website.

[![PyPI](https://img.shields.io/pypi/v/geo-optimizer-skill?style=flat-square&color=3b82f6)](https://pypi.org/project/geo-optimizer-skill/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![CI](https://github.com/auriti-labs/geo-optimizer-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/auriti-labs/geo-optimizer-skill/actions)
[![codecov](https://codecov.io/gh/Auriti-Labs/geo-optimizer-skill/branch/main/graph/badge.svg)](https://app.codecov.io/gh/Auriti-Labs/geo-optimizer-skill)
[![Tests](https://img.shields.io/badge/tests-1720%20passed-22c55e?style=flat-square)](https://github.com/Auriti-Labs/geo-optimizer-skill/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e?style=flat-square)](LICENSE)
[![MCP Compatible](https://img.shields.io/badge/MCP-compatible-8b5cf6?style=flat-square)](https://modelcontextprotocol.io)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-FFDD00?style=flat-square&logo=buymeacoffee&logoColor=000000)](https://buymeacoffee.com/auritidesign)

**One command scores your site 0–100 on AI-search readiness, tells you exactly what to fix, and checks whether AI engines actually cite you.**

[Quick Start](#quick-start) · [Live Demo](https://geoready.dev) · [Pricing](https://geoready.dev/pricing) · [Sign Up](https://app.geoready.dev/signup) · [Documentation](https://auriti-labs.github.io/geo-optimizer-skill/) · [Changelog](CHANGELOG.md)

<img src="assets/demo.gif" alt="geo audit demo — AI visibility score 0-100 with prioritized fixes in one command" width="800"/>

**15 CLI commands** · **8 scoring categories** · **47 research-backed methods** · **7 output formats** · **1,720 tests** · academic foundation ([KDD 2024](https://arxiv.org/abs/2311.09735), [ICLR 2026](https://arxiv.org/abs/2510.11438)) · runs in CI/CD, as a [Python library](#python-api), an [MCP server](#mcp-server), or an [Astro integration](#astro-integration)

</div>

---

## What is GEO Optimizer?

**GEO Optimizer** is a free, open-source command-line tool (and Python library, MCP server, and [Astro integration](#astro-integration)) that measures how visible your website is to **AI answer engines** — ChatGPT, Perplexity, Google AI Overviews, Gemini, and Claude — and tells you how to get cited by them.

This discipline goes by several names; this tool covers all of them: **Answer Engine Optimization (AEO)**, **Generative Engine Optimization (GEO)**, **AI SEO**, **LLM SEO**, **AI Search Optimization**, and **AI visibility / LLM visibility** monitoring. If you're searching for an *"open-source AEO tool"*, a *"tool to check if ChatGPT cites my website"*, or an *"llms.txt checker"* — that's this.

```bash
# Zero install — score any site against 8 AI-readiness categories
uvx --from geo-optimizer-skill geo audit --url https://yoursite.com
```

It scores your site against **47 research-backed methods** ([Princeton KDD 2024](https://arxiv.org/abs/2311.09735), [AutoGEO ICLR 2026](https://arxiv.org/abs/2510.11438)) and generates the exact fixes — robots.txt bot rules, `llms.txt`, JSON-LD schema, and the content patterns models quote.

---

## Why AI visibility matters in 2026

AI search engines give one synthesized answer and **cite a handful of sources**. If your site isn't one of them, you're invisible — even if you rank #1 on Google.

```
User asks ChatGPT: "What's the best mortgage calculator?"

ChatGPT: "According to [Competitor.com], the formula is..."
          ↑ They get cited. You don't.
```

- ChatGPT alone serves [**900M weekly users**](https://llmrefs.com/generative-engine-optimization) — a growing share of sessions that used to be Google searches.
- [**28.3% of ChatGPT's most-cited pages have *zero* organic visibility on Google**](https://llmrefs.com/generative-engine-optimization) (Ahrefs) — AI engines reward different signals than classic SEO.
- Proper JSON-LD schema lifts LLM extraction accuracy [**from 16% to 54%**](https://dev.to/geobuddy/llmstxt-schema-markup-and-technical-geo-what-actually-works-in-2026-o63) (Semrush test on GPT-4).
- [**844,000+ sites**](https://webflow.com/blog/llms-txt) already ship an `llms.txt`. Yours?

### Does AI actually cite your brand? Ask it directly.

`geo citations` queries real answer engines with the questions your customers ask, then reports whether your brand is mentioned and your domain is cited as a source — and which competitors get cited instead of you.

<img src="assets/citations.gif" alt="geo citations demo — is your brand cited by ChatGPT and Perplexity?" width="800"/>

---

## AEO / GEO is not traditional SEO

SEO and AEO/GEO answer different questions:

- **SEO** optimizes for ranking and clicks in traditional search result pages — crawlability, backlinks, keyword signals.
- **AEO / GEO** measures whether an AI answer engine can read, parse, understand, and **cite** your content when generating a response.
- A site can rank well on Google and still be largely opaque to AI systems — missing structured data, no llms.txt, bot access blocked, thin factual density.

GEO Optimizer focuses on the technical and structural signals AI answer engines use: robots.txt bot permissions, `llms.txt` presence and depth, JSON-LD schema richness, brand entity coherence, multi-page topical authority, and content citability across 47 methods. These complement traditional SEO rather than replacing it.

---

## Try it online

| | |
|---|---|
| **Free audit** | [geoready.dev](https://geoready.dev) — single-URL GEO score, no account required |
| **Free tools** | [llms.txt generator](https://geoready.dev/tools/llms-txt-generator/) — build a starter llms.txt from your sitemap |
| **Pricing** | [geoready.dev/pricing](https://geoready.dev/pricing) — plans and feature comparison |
| **Sign up** | [app.geoready.dev/signup](https://app.geoready.dev/signup) — Pro/Studio/Agency available now |

---

## Open-source vs GeoReady Platform

| | GEO Optimizer CLI | GeoReady.dev Free | GeoReady Pro / Studio / Agency |
|---|---|---|---|
| **License / access** | MIT, open-source | Free, no account | Self-serve — [sign up](https://app.geoready.dev/signup) |
| **Core use** | Local audit engine, CI/CD integration, JSON output | Web audit, score preview, educational pages | Monitoring, score history, regression alerts, agency reporting |
| **Target** | Developers, automation | Developers, SEO specialists | Ongoing clients, multi-site portfolios |
| **Pricing** | Free forever | Free forever | From $19/month — see [geoready.dev/pricing](https://geoready.dev/pricing) |

The CLI and web audit remain MIT-licensed and free. The GeoReady platform adds server-side continuity — monitoring, history, and team features — that a local CLI cannot provide on its own.

---

## Quick Start

```bash
pip install geo-optimizer-skill
```

No install? One-shot audit with [uv](https://docs.astral.sh/uv/):

```bash
uvx --from geo-optimizer-skill geo audit --url https://yoursite.com
```

```bash
# Audit any site — get a score 0-100 with actionable recommendations
geo audit --url https://yoursite.com

# Audit a full sitemap and surface weakest pages first
geo audit --sitemap https://yoursite.com/sitemap.xml --max-urls 25

# Compare before/after versions of a page
geo diff --before https://yoursite.com/page-old --after https://yoursite.com/page-new

# Save history and detect regressions over time
geo audit --url https://yoursite.com --save-history --regression

# Show the saved trend for a site
geo history --url https://yoursite.com

# What changed since the last snapshot? (severity + category deltas; CI: --fail-on warning)
geo drift --url https://yoursite.com

# Passive AI visibility snapshot for a domain
geo monitor --domain yoursite.com

# Ask real AI engines: is my brand mentioned? Is my domain cited as a source?
# BYO API key — PERPLEXITY_API_KEY recommended (real web citations)
geo citations --brand "YourBrand" --domain yoursite.com --topic "your product category"

# Save or query archived AI answer snapshots
geo snapshots --query "best GEO tool" --from 2026-03-01 --to 2026-03-30

# Score citation quality inside an archived answer snapshot
geo snapshots --quality --snapshot-id 12 --target-domain yoursite.com

# Run recurring monitoring and generate an HTML trend report
geo track --url https://yoursite.com --report --output ./geo-track-report.html

# Auto-generate all missing files (robots.txt, llms.txt, schema, meta)
geo fix --url https://yoursite.com --apply

# Generate llms.txt from sitemap
geo llms --base-url https://yoursite.com --output ./public/llms.txt

# Generate JSON-LD schema
geo schema --type faq --url https://yoursite.com
```

---

## What it checks

| Area | Points | What GEO Optimizer looks for |
|------|--------|------------------------------|
| **Robots.txt** | /18 | 27 AI bots across 3 tiers (training, search, user). Citation bots explicitly allowed? |
| **llms.txt** | /18 | Present, has H1 + blockquote, sections, links, depth. Companion llms-full.txt? |
| **Schema JSON-LD** | /16 | WebSite, Organization, FAQPage, Article. Schema richness (5+ attributes)? |
| **Meta Tags** | /14 | Title, description, canonical, Open Graph complete? |
| **Content** | /12 | H1, statistics, external citations, heading hierarchy, lists/tables, front-loading? |
| **Brand & Entity** | /10 | Brand name coherence, Knowledge Graph links (Wikipedia/Wikidata/LinkedIn/Crunchbase), about page, geo signals, topic authority |
| **Signals** | /6 | `<html lang>`, RSS/Atom feed, dateModified freshness? |
| **AI Discovery** | /6 | `.well-known/ai.txt`, `/ai/summary.json`, `/ai/faq.json`, `/ai/service.json`? |

**Score bands:** 86-100 Excellent · 68-85 Good · 36-67 Foundation · 0-35 Critical

**Bonus checks** (informational, do not affect score):

| Check | What it detects |
|-------|-----------------|
| **CDN Crawler Access** | Does Cloudflare/Akamai/Vercel block GPTBot, ClaudeBot, PerplexityBot? |
| **JS Rendering** | Is content accessible without JavaScript? SPA framework detection |
| **WebMCP Readiness** | Chrome WebMCP support: `registerTool()`, `toolname` attributes, `potentialAction` schema |
| **Negative Signals** | 8 anti-citation signals: CTA overload, popups, thin content, keyword stuffing, missing author, boilerplate ratio |
| **Prompt Injection Detection** | 8 manipulation patterns: hidden text, invisible Unicode, LLM instructions, HTML comment injection, monochrome text, micro-font, data-attr injection, aria-hidden abuse |
| **Trust Stack Score** | 5-layer trust aggregation (Technical, Identity, Social, Academic, Consistency) — composite grade A-F |
| **RAG Chunk Readiness** | Content segmentation for RAG retrieval: section word counts, definition openings, heading boundaries, anchor sentences `🆕 v4.7` |
| **Content Decay Prediction** | Detects temporal, statistical, version, event, and price decay patterns — evergreen score 0-100 `🆕 v4.7` |
| **Platform Citation Profile** | Per-platform readiness scores for ChatGPT, Perplexity, Google AI `🆕 v4.7` |
| **Multimodal Readiness** | Image alt coverage, captions, VideoObject/AudioObject schema, subtitle tracks, transcripts — the text scaffolding multimodal engines (Gemini, GPT-4o) need `🆕` |

Plus a separate **Citability Score** (0-100) measuring content quality across 47 methods:
Quotation +41% · Statistics +33% · Fluency +29% · Cite Sources +27% · and 43 more.

### Additional tools

```bash
geo coherence --sitemap https://example.com/sitemap.xml  # Cross-page terminology consistency
geo logs --file access.log                                # AI Crawler Activity — crawler evidence from user-agent logs
geo access --url https://example.com                      # Agent Access Audit — browser vs AI bot access simulation
geo citations --brand "Acme" --domain acme.com            # AI Citation Check — are you cited by answer engines? (BYO key)
geo authority --sitemap https://example.com/sitemap.xml   # Topic Authority — multi-page entity coverage, clusters, pillars
geo drift --url https://example.com                        # Semantic Drift — what changed since the last snapshot
```

**Topic authority** — AI engines map entities and multi-page coverage, not single pages. `geo authority` clusters your site by topic and scores depth, interlinking, and pillar pages:

<img src="assets/authority.gif" alt="geo authority demo — site-level topical authority score and recommendations" width="800"/>

GEO Optimizer checks whether websites can be **crawled, understood, cited, and monitored** by AI answer engines:

- **Crawled** — robots.txt, CDN access, AI-bot reachability
- **Understood** — schema, llms.txt, content structure
- **Cited** — citability signals across 47 research-backed methods
- **Monitored** — `geo logs` (crawler evidence) and `geo access` (access simulation)

Note on wording: AI Crawler Activity reports crawler evidence from server-log user-agents. Agent Access Audit reports *citation readiness* (whether bots can reach and parse the page). For actual answer-engine checking — "does the AI mention my brand and cite my domain?" — use `geo citations` with your own API key (Perplexity Sonar returns the real source URLs; OpenAI/Anthropic/Groq reveal parametric brand knowledge).

Optional LLM-powered analysis (`pip install geo-optimizer-skill[llm]`):
brand sentiment, citation attribution, multi-turn persistence, cross-platform citation map, prompt library.

---

## Output formats

```bash
geo audit --url https://example.com --format text     # Human-readable (default)
geo audit --url https://example.com --format json      # Machine-readable
geo audit --sitemap https://example.com/sitemap.xml    # Batch sitemap audit (text)
geo audit --sitemap https://example.com/sitemap.xml --format json  # Batch sitemap audit (JSON)
geo audit --url https://example.com --format rich      # Colored terminal
geo audit --url https://example.com --format html      # Self-contained report
geo audit --url https://example.com --format sarif     # GitHub Code Scanning
geo audit --url https://example.com --format junit     # Jenkins, GitLab CI
geo audit --url https://example.com --format github    # GitHub Actions annotations
geo monitor --domain example.com                       # Passive AI visibility readiness
geo snapshots --query "best GEO tool"                 # Saved AI answer archive
geo snapshots --quality --snapshot-id 12              # Citation quality tiers for a saved answer
geo history --url https://example.com                  # Saved score trend
geo track --url https://example.com --report           # Monitoring HTML report
```

The JSON output format is intended to remain stable across minor versions and acts as the machine-readable integration contract for the GeoReady platform.

---

## CI/CD Integration — fail the build when AI-readiness drops

Treat AI visibility like test coverage: gate every deploy on it. The GitHub Action scores your site, fails the build below a threshold, and uploads results to the Security tab.

```yaml
# .github/workflows/geo.yml
- uses: Auriti-Labs/geo-optimizer-skill@v4.14.0
  with:
    url: https://yoursite.com
    min-score: 70        # Fail the build if the GEO score drops below 70
    format: sarif        # Upload findings to the GitHub Security tab
```

Works with GitHub Actions, GitLab CI, Jenkins, CircleCI, and any CI that runs Python. For longitudinal checks, persist snapshots and **fail on regression or semantic drift**:

```bash
geo audit --url https://yoursite.com --save-history --regression
geo drift --url https://yoursite.com --fail-on warning   # exit non-zero if signals degraded
```

---

## MCP Server

Use GEO Optimizer from Claude, Cursor, Windsurf, or any MCP client:

```bash
pip install geo-optimizer-skill[mcp]
claude mcp add geo-optimizer -- geo-mcp
```

Then ask: *"audit my site and fix what's missing"*

| Tool | Purpose |
|------|---------|
| `geo_audit` | Full audit with score + recommendations |
| `geo_fix` | Generate fix files |
| `geo_llms_generate` | Generate llms.txt |
| `geo_citability` | Content citability analysis (47 methods) |
| `geo_schema_validate` | Validate JSON-LD |
| `geo_compare` | Compare multiple sites |
| `geo_gap_analysis` | Explain the gap between two sites and prioritize fixes |
| `geo_ai_discovery` | Check AI discovery endpoints |
| `geo_check_bots` | Check bot access via robots.txt |
| `geo_trust_score` | 5-layer trust signal aggregation |
| `geo_negative_signals` | 8 anti-citation signal detection |
| `geo_factual_accuracy` | Audit unsourced claims, contradictions, and broken citations |

---

## Use as AI Context

Load the right file into your AI assistant for GEO expertise:

| Platform | File |
|----------|------|
| Claude Projects | [`ai-context/claude-project.md`](ai-context/claude-project.md) |
| ChatGPT Custom GPT | [`ai-context/chatgpt-custom-gpt.md`](ai-context/chatgpt-custom-gpt.md) |
| Cursor | [`ai-context/cursor.mdc`](ai-context/cursor.mdc) |
| Windsurf | [`ai-context/windsurf.md`](ai-context/windsurf.md) |
| Kiro | [`ai-context/kiro-steering.md`](ai-context/kiro-steering.md) |

---

## Internal Skill System

The repository now includes a structured internal skill catalog for maintainers at [`src/geo_optimizer/skills/catalog/`](src/geo_optimizer/skills/catalog/) plus validation rules and examples. See [`docs/skill-system.md`](docs/skill-system.md) for the v1 architecture.

---

## Python API

```python
from geo_optimizer import audit

result = audit("https://example.com")
print(result.score)                      # 85
print(result.band)                       # "good"
print(result.citability.total_score)     # 72
print(result.score_breakdown)            # {"robots": 18, "llms": 14, ...}
print(result.recommendations)            # ["Add FAQPage schema..."]
```

Async variant:

```python
from geo_optimizer import audit_async
result = await audit_async("https://example.com")
```

---

## Show your GEO score

Add a live GEO score badge to your README — like a coverage badge, but for AI visibility:

![GEO Score](https://geoready.dev/badge?url=https://geoready.dev)

```markdown
[![GEO Score](https://geoready.dev/badge?url=https://yoursite.com)](https://geoready.dev?utm_source=badge)
```

HTML variant for docs sites:

```html
<a href="https://geoready.dev?utm_source=badge"><img src="https://geoready.dev/badge?url=https://yoursite.com" alt="GEO Score"></a>
```

Colors: 86-100 green · 68-85 cyan · 36-67 yellow · 0-35 red. Re-audited and cached hourly — improve your site, watch the badge change. No account needed.

---

## Astro Integration

Make an Astro site GEO-ready at build time — generates `llms.txt`,
`/.well-known/ai.txt`, and `/ai/summary.json` from your built routes
(never overwrites hand-curated files):

```js
// astro.config.mjs
import geoReady from 'astro-geoready';
export default defineConfig({
  site: 'https://yoursite.com',
  integrations: [geoReady({ siteName: 'Your Site' })],
});
```

See [`integrations/astro-geoready/`](integrations/astro-geoready/) — geoready.dev itself builds with it.

---

## Plugin System

Extend the audit with custom checks via entry points:

```toml
[project.entry-points."geo_optimizer.checks"]
my_check = "mypackage:MyCheck"
```

See [`examples/example_plugin.py`](examples/example_plugin.py) for a working example.

---

## Research Foundation

| Paper | Venue | Key Finding |
|-------|-------|-------------|
| [GEO: Generative Engine Optimization](https://arxiv.org/abs/2311.09735) | **KDD 2024** | 9 methods tested on 10k queries. Cite Sources: +115%, Statistics: +40% |
| [AutoGEO](https://arxiv.org/abs/2510.11438) | **ICLR 2026** | Automatic rule extraction. +50.99% over Princeton baseline |
| [C-SEO Bench](https://arxiv.org/abs/2506.11097) | **2025** | Most content manipulation is ineffective. Infrastructure matters most |

We focus on **technical infrastructure** (robots.txt, llms.txt, schema, meta) over content rewriting. The research confirms: if crawlers can't find and parse your content, prose optimization doesn't matter.

GEO Optimizer translates these findings into technical and content-level signals that can be operationally audited and tracked over time.

---

## Roadmap

This project follows a deliberate release cadence — focused waves, not noisy patches.

| Version | Window | Codename | Status |
|---------|--------|----------|--------|
| v4.10.0 | Apr 2026 | Veil | Shipped |
| v4.11.0 | May 2026 | Static | Shipped |
| v4.12.0 | May 2026 | Ledger | Shipped |
| v4.13.0 | Jun 2026 | Echo | Shipped |
| v4.14.0 | Jun 2026 | Quiet Glass | Shipped |
| v4.15.0-rc1 | Jan 2027 | Threshold | Planned |
| v4.15.0-rc2 / v4.16.0 | Mar 2027 | Pale Signal | Planned |
| v5.0.0 | May 2027 | Black Archive | Exploring |

Next focus areas: signal architecture, retrieval surface analysis, scoring recalibration, and structural pattern recognition. The v5.0 cycle represents a broader architectural evolution.

Full release calendar, philosophy, and direction → [docs/ROADMAP.md](docs/ROADMAP.md)

---

## FAQ

**What is Answer Engine Optimization (AEO)?**
AEO is the practice of structuring your website so AI answer engines — ChatGPT, Perplexity, Google AI Overviews, Gemini, Claude — can find, understand, and cite it as the direct answer to a user's question. It is also called Generative Engine Optimization (GEO), AI SEO, LLM SEO, or AI Search Optimization. GEO Optimizer audits and scores your site for all of it.

**How do I check if ChatGPT or Perplexity cites my website?**
Run `geo citations --brand "Your Brand" --domain yoursite.com` with a Perplexity or OpenAI API key. It asks the engine customer-style questions and reports whether your brand is mentioned, whether your domain is cited as a source, and which competitors are cited instead. No account needed for the [free web version](https://geoready.dev/tools/ai-citation-checker/).

**Is this an llms.txt generator and checker?**
Yes. `geo llms` generates an `llms.txt` from your sitemap, the audit scores its presence and depth, and the [Astro integration](#astro-integration) creates one at build time. There's also a [free online llms.txt generator](https://geoready.dev/tools/llms-txt-generator/).

**Is it free and open source?**
Yes — MIT licensed, free forever via `pip install geo-optimizer-skill` or `uvx`. The hosted [GeoReady](https://geoready.dev) platform adds continuous monitoring, score history, citation tracking, and team features on top of the same engine.

**Which AI engines does it cover?**
ChatGPT (GPTBot, OAI-SearchBot), Perplexity (PerplexityBot), Claude (ClaudeBot, anthropic-ai), Google (Google-Extended, Gemini), plus 27 AI bots total and per-platform readiness profiles for ChatGPT, Perplexity, and Google AI Overviews.

**How is it different from a traditional SEO tool?**
Traditional SEO tools optimize for Google rankings and backlinks. GEO Optimizer measures AI *citation readiness* — whether answer engines can crawl, parse, and quote your content — using signals (llms.txt, AI-bot access, schema richness, citability, topical authority) that classic SEO ignores.

---

## Security

All URL inputs are validated against private IP ranges (RFC 1918, loopback, link-local, cloud metadata) with DNS pinning before any request. See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.

---

## Contributing

```bash
git clone https://github.com/YOUR_USERNAME/geo-optimizer-skill.git
cd geo-optimizer-skill && pip install -e ".[dev]"
pytest tests/ -v   # 1720 tests, all mocked
```

[Bug reports](https://github.com/Auriti-Labs/geo-optimizer-skill/issues/new?template=bug_report.yml) · [Feature requests](https://github.com/Auriti-Labs/geo-optimizer-skill/issues/new?template=feature_request.yml) · [CONTRIBUTING.md](CONTRIBUTING.md)

---

<div align="center">

Run the [CLI locally](#quick-start), try the [free audit online](https://geoready.dev), see [pricing](https://geoready.dev/pricing), or [sign up](https://app.geoready.dev/signup) for Pro monitoring.

---

**MIT License** · Built by [Auriti Labs](https://github.com/auriti-labs)

If this saved you time, a star helps others find it.

[![Star on GitHub](https://img.shields.io/github/stars/auriti-labs/geo-optimizer-skill?style=for-the-badge&color=facc15&logo=github&label=Star)](https://github.com/auriti-labs/geo-optimizer-skill/stargazers)

The open-source engine for **Answer Engine Optimization** — get your site cited by ChatGPT, Perplexity, and Gemini.

</sub>

</div>

## Star History

<a href="https://www.star-history.com/?repos=Auriti-Labs%2Fgeo-optimizer-skill&type=timeline&logscale=&legend=bottom-right">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/image?repos=Auriti-Labs/geo-optimizer-skill&type=timeline&theme=dark&logscale&legend=bottom-right" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/image?repos=Auriti-Labs/geo-optimizer-skill&type=timeline&logscale&legend=bottom-right" />
   <img alt="Star History Chart" src="https://api.star-history.com/image?repos=Auriti-Labs/geo-optimizer-skill&type=timeline&logscale&legend=bottom-right" />
 </picture>
</a>
