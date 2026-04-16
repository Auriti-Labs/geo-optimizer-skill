<div align="center">

<img src="assets/logo.svg" alt="GEO Optimizer" width="480"/>

### Make websites visible to AI search engines

[![PyPI](https://img.shields.io/pypi/v/geo-optimizer-skill?style=flat-square&color=3b82f6)](https://pypi.org/project/geo-optimizer-skill/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![CI](https://github.com/auriti-labs/geo-optimizer-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/auriti-labs/geo-optimizer-skill/actions)
[![codecov](https://codecov.io/gh/auriti-labs/geo-optimizer-skill/branch/main/graph/badge.svg)](https://codecov.io/gh/auriti-labs/geo-optimizer-skill)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e?style=flat-square)](LICENSE)
[![MCP Compatible](https://img.shields.io/badge/MCP-compatible-8b5cf6?style=flat-square)](https://modelcontextprotocol.io)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-FFDD00?style=flat-square&logo=buymeacoffee&logoColor=000000)](https://buymeacoffee.com/auritidesign)

**Audit, fix, and optimize any website to be cited by ChatGPT, Perplexity, Claude, and Gemini.**

[Quick Start](#quick-start) · [Live Demo](https://geo-optimizer-web.onrender.com) · [Documentation](https://auriti-labs.github.io/geo-optimizer-skill/) · [Changelog](CHANGELOG.md)

</div>

---

## Why this exists

AI search engines give direct answers and **cite their sources**. If your site isn't optimized, you're invisible — even if you rank #1 on Google.

```
User: "What's the best mortgage calculator?"

Perplexity: "According to [Competitor.com], the formula is..."
             ↑ They appear. You don't.
```

GEO Optimizer audits your site against **47 research-backed methods** ([Princeton KDD 2024](https://arxiv.org/abs/2311.09735), [AutoGEO ICLR 2026](https://arxiv.org/abs/2510.11438)) and generates the fixes.

---

## Quick Start

```bash
pip install geo-optimizer-skill
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

# Passive AI visibility snapshot for a domain
geo monitor --domain yoursite.com

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

Plus a separate **Citability Score** (0-100) measuring content quality across 47 methods:
Quotation +41% · Statistics +33% · Fluency +29% · Cite Sources +27% · and 43 more.

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

---

## CI/CD Integration

```yaml
# .github/workflows/geo.yml
- uses: Auriti-Labs/geo-optimizer-skill@v1
  with:
    url: https://yoursite.com
    min-score: 70        # Fail if score drops below 70
    format: sarif        # Upload to GitHub Security tab
```

Works with GitHub Actions, GitLab CI, Jenkins, CircleCI, and any CI that runs Python.

For longitudinal checks, persist snapshots and fail on regressions:

```bash
geo audit --url https://yoursite.com --save-history --regression
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

## Dynamic Badge

Show your GEO score in your README:

```markdown
![GEO Score](https://geo-optimizer-web.onrender.com/badge?url=https://yoursite.com)
```

Colors: 86-100 green · 68-85 cyan · 36-67 yellow · 0-35 red. Cached 1h.

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

---

## Security

All URL inputs are validated against private IP ranges (RFC 1918, loopback, link-local, cloud metadata) with DNS pinning before any request. See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.

---

## Contributing

```bash
git clone https://github.com/YOUR_USERNAME/geo-optimizer-skill.git
cd geo-optimizer-skill && pip install -e ".[dev]"
pytest tests/ -v   # 1189 tests, all mocked
```

[Bug reports](https://github.com/Auriti-Labs/geo-optimizer-skill/issues/new?template=bug_report.yml) · [Feature requests](https://github.com/Auriti-Labs/geo-optimizer-skill/issues/new?template=feature_request.yml) · [CONTRIBUTING.md](CONTRIBUTING.md)

---

<div align="center">

**MIT License** · Built by [Auriti Labs](https://github.com/auriti-labs)

If this saved you time, a star helps others find it.

[![Star on GitHub](https://img.shields.io/github/stars/auriti-labs/geo-optimizer-skill?style=for-the-badge&color=facc15&logo=github&label=Star)](https://github.com/auriti-labs/geo-optimizer-skill/stargazers)

</div>

## Star History

<a href="https://www.star-history.com/?repos=Auriti-Labs%2Fgeo-optimizer-skill&type=timeline&logscale=&legend=bottom-right">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/image?repos=Auriti-Labs/geo-optimizer-skill&type=timeline&theme=dark&logscale&legend=bottom-right" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/image?repos=Auriti-Labs/geo-optimizer-skill&type=timeline&logscale&legend=bottom-right" />
   <img alt="Star History Chart" src="https://api.star-history.com/image?repos=Auriti-Labs/geo-optimizer-skill&type=timeline&logscale&legend=bottom-right" />
 </picture>
</a>
