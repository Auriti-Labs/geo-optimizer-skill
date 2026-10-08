---
title: "GEO Monitor Command: Passive Visibility Check"
description: "The geo monitor command measures a domain's AI-discoverability readiness without querying LLM APIs. Structural checks for crawling, fetching and citation."
order: 12
---

# GEO Monitor

`geo monitor` is the passive AI-visibility checker for a domain.

It does **not** query LLM APIs and does **not** verify direct brand mentions in model answers. Instead, it measures whether the domain is structurally ready to be discovered, fetched, and cited by AI systems.

---

## What it checks

- citation bot access in `robots.txt`
- on-demand fetch bot access
- `llms.txt` readiness
- AI discovery endpoints (`/.well-known/ai.txt`, `/ai/*.json`)
- brand/entity strength
- trust stack strength
- local trend momentum from saved snapshots

The command reuses the same local SQLite database as `geo history` and `geo track`: `~/.geo-optimizer/tracking.db`.

---

## Usage

```bash
# Passive visibility snapshot for a domain
geo monitor --domain example.com

# JSON output
geo monitor --domain example.com --format json

# Do not persist the snapshot in local history
geo monitor --domain example.com --no-save-history
```

---

## Options

| Flag | Required | Description |
|------|----------|-------------|
| `--domain` | Yes | Domain to monitor (homepage is normalized automatically) |
| `--format` | No | Output format: `text` or `json` |
| `--output` | No | Write output to a file |
| `--cache` | No | Reuse local HTTP cache for the homepage audit |
| `--save-history / --no-save-history` | No | Persist or skip the local snapshot |
| `--retention-days` | No | Retention window for local history snapshots |

---

## Output

Text output includes:

- visibility score (`0-100`) and band
- latest GEO score for the homepage
- local trend delta, if previous snapshots exist
- per-signal passive readiness summary
- next actions derived from the audit

Band meanings:

- `strong`: domain is broadly ready for passive AI discovery and citation fetches
- `visible`: good baseline with a few important gaps
- `emerging`: some useful signals exist, but readiness is incomplete
- `low`: the domain is still weak on key AI-visibility surfaces

---

## Relationship to other commands

- [`geo audit`](/docs/geo-audit/): full homepage GEO audit with detailed scoring and recommendations
- [`geo history`](/docs/geo-history/): saved GEO score trend only
- [`geo track`](/docs/geo-track/): recurring GEO audit snapshots and HTML trend reports

Use `geo monitor` when you want a quick passive answer to:

> “Is this domain structurally ready to be found and cited by AI systems?”
