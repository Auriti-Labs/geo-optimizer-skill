---
title: "GEO Coherence Command: Semantic Consistency"
description: "Detect cross-page terminology inconsistencies across a sitemap with geo coherence. Usage, flags and how coherence feeds your GEO score."
order: 15
---

Cross-page semantic coherence analysis. Detects terminology inconsistencies across site pages.

## Usage

```bash
geo coherence --sitemap https://example.com/sitemap.xml
geo coherence --sitemap https://example.com/sitemap.xml --max-pages 10
geo coherence --sitemap https://example.com/sitemap.xml --format json
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--sitemap` | required | Sitemap URL to analyze |
| `--max-pages` | 20 | Maximum pages to analyze |
| `--format` | text | Output format: `text` or `json` |

## Checks

- **Conflicting definitions** (high) — same term defined differently across pages
- **Duplicate titles** (medium) — pages with near-identical titles (>85% similarity)
- **Mixed language** (medium) — inconsistent `lang` attributes

## Scoring

Coherence score starts at 100, minus 10 per high-severity issue, minus 5 per medium.

## Python API

```python
from geo_optimizer.core.site_coherence import run_site_coherence

result = run_site_coherence("https://example.com/sitemap.xml", max_pages=20)
```
