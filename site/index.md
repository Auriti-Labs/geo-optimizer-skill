---
layout: default
title: Documentation
description: "Complete documentation for GEO Optimizer — the open-source toolkit to audit, fix, and optimize websites for AI search engines."
---

# GEO Optimizer Documentation

<p class="page-desc">Everything you need to make your website visible to ChatGPT, Perplexity, Claude, and Gemini. From first audit to production CI/CD pipeline.</p>

---

## Get started in 30 seconds

```bash
pip install geo-optimizer-skill
geo audit --url https://yoursite.com
```

Get a score 0-100 with actionable recommendations. Then auto-fix everything:

```bash
geo fix --url https://yoursite.com --apply
```

> **New to GEO?** Start with [Getting Started](getting-started/) — install, first audit, first fix in 5 minutes.

---

## CLI Commands

| Command | What it does |
|---------|-------------|
| [`geo audit`](geo-audit/) | Full audit — score 0-100, 8 categories, 7 output formats |
| [`geo fix`](geo-fix/) | Auto-generate robots.txt, llms.txt, schema, meta tags |
| [`geo llms`](llms-txt/) | Generate `/llms.txt` from your sitemap |
| [`geo schema`](schema-injector/) | Generate and inject JSON-LD structured data |

---

## Integrations

| Platform | Guide |
|----------|-------|
| [MCP Server](mcp-server/) | Use from Claude Code, Cursor, Windsurf — 12 tools, 5 resources |
| [CI/CD](ci-cd/) | GitHub Actions, GitLab CI, Jenkins — fail builds on low score |
| [AI Context](ai-context/) | Load GEO expertise into Claude, ChatGPT, Cursor, Windsurf, Kiro |

---

## Reference

| Page | Description |
|------|-------------|
| [AI Bots](ai-bots-reference/) | 27 AI crawlers across 3 tiers — training, search, user |
| [47 GEO Methods](geo-methods/) | Research-backed citability methods with measured impact |
| [Scoring Rubric](scoring-rubric/) | How the score is calculated: 8 categories, 100 points total |
| [Troubleshooting](troubleshooting/) | Solutions to common issues |

---

## Python API

```python
from geo_optimizer import audit

result = audit("https://example.com")
print(result.score)                   # 85
print(result.band)                    # "good"
print(result.citability.total_score)  # 72
print(result.score_breakdown)         # {"robots": 18, "llms": 14, ...}
```

Async: `result = await audit_async("https://example.com")`

---

## Links

- [Live Demo](https://geo-optimizer-web.onrender.com) — audit any site online
- [GitHub](https://github.com/Auriti-Labs/geo-optimizer-skill) — source, issues, discussions
- [PyPI](https://pypi.org/project/geo-optimizer-skill/) — latest release
- [Changelog](https://github.com/Auriti-Labs/geo-optimizer-skill/blob/main/CHANGELOG.md)
