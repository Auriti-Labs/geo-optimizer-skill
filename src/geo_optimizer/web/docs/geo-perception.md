# GEO Perception

`geo perception` extracts a deterministic **AI perception snapshot** from a page: what an AI/retrieval system would likely pull out of it — brand identity, schema types, citability grade, trust score, supported and unsupported factual claims, and missing authority signals.

It runs a full audit under the hood and aggregates its signals. No LLM call is made and no extra network request beyond the audit itself — the output is always disclosed as **simulated perception**, not a real AI system's answer. For a real model's answer, use [`geo citations`](geo-citations.md) instead.

---

## Usage

```bash
# Deterministic perception snapshot for a page
geo perception --url https://example.com

# JSON output for CI or downstream tooling
geo perception --url https://example.com --format json
```

## Flags

| Flag | Required | Description |
|------|----------|-------------|
| `--url` | Yes | URL to extract a perception snapshot from |
| `--format` | No | Output format: `text` (default) or `json` |
| `--output` | No | Write the report to a file |
| `--cache` | No | Use local HTTP cache for the underlying audit |

## Output

`geo perception` reports:

- brand name and entity type
- citability grade and trust score
- schema types present on the page
- citation-worthy signals (methods that scored highly)
- supported vs. unsupported factual claims
- missing authority signals (no about page, no contact info, no Knowledge Graph pillars, missing FAQ/Article schema)

Use it to sanity-check what a page communicates about itself before an AI system reads it — the same signals `geo audit` scores, reframed as a perception summary rather than a checklist.
