---
title: "GEO Diff Command: A/B Audit Comparison"
description: "Compare two URLs with geo diff: what improved, what regressed and by how much. Ideal for before/after testing of your AI-citation optimizations."
order: 9
---

`geo diff` confronta due URL con un audit GEO A/B e mostra cosa è migliorato, cosa è peggiorato e di quanto.

---

## Usage

```bash
# Compare before/after versions of a page
geo diff --before https://site.com/page-old --after https://site.com/page-new

# JSON output for CI or downstream tooling
geo diff --before https://site.com/page-old --after https://site.com/page-new --format json
```

## Flags

| Flag | Required | Description |
|------|----------|-------------|
| `--before` | Yes | Baseline URL before optimization |
| `--after` | Yes | Candidate URL after optimization |
| `--format` | No | Output format: `text` (default) or `json` |
| `--output` | No | Write the diff report to a file |
| `--cache` | No | Use local HTTP cache for repeated comparisons |

## Output

`geo diff` reports:

- total GEO score delta
- score band change
- recommendation count delta
- per-category score deltas
- top improvements
- regressions to inspect before deploy

Use it when validating a rewrite, redesign, template refactor, or structured-data change before shipping.
