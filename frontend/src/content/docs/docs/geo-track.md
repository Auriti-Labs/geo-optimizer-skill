---
title: "GEO Track Command: Scheduled AI Audits"
description: "Run recurring, tracked AI-visibility audits with geo track and keep local history. CLI reference: schedule, history, and re-audit workflows."
order: 10
---

`geo track` is the monitoring-oriented CLI surface for recurring GEO audits with local history.

---

## What It Does

- Runs a fresh audit and stores the snapshot locally
- Reuses the same SQLite tracking database as `geo history`
- Can render the stored trend instead of auditing again
- Can generate a lightweight HTML report for scheduled monitoring

---

## Usage

```bash
# Run audit + save snapshot
geo track --url https://yoursite.com

# Show saved history
geo track --url https://yoursite.com --history

# Generate HTML monitoring report
geo track --url https://yoursite.com --report --output geo-track-report.html
```

---

## Flags

| Flag | Required | Description |
|------|----------|-------------|
| `--url` | Yes | URL to track |
| `--history` | No | Show saved history instead of running a new audit |
| `--report` | No | Generate an HTML trend report after saving the snapshot |
| `--format` | No | `text` (default) or `json` |
| `--cache` | No | Reuse local HTTP cache during the audit |
| `--limit` | No | Maximum snapshots to include in the trend (default: `12`) |
| `--retention-days` | No | Retention window for local snapshots (default: `90`) |
| `--output` | No | Output file path |

---

## Storage

- Local database: `~/.geo-optimizer/tracking.db`
- Saved fields include:
  - URL
  - timestamp
  - score and band
  - HTTP status
  - recommendation count
  - per-category score breakdown

This makes `geo track` suitable for cron jobs, scheduled GitHub Actions, and lightweight longitudinal monitoring without requiring any external service.

---

## Scheduled Monitoring Example

```bash
0 6 * * 1 /usr/local/bin/geo track --url https://yoursite.com --report --output /tmp/geo-report.html
```

That pattern gives you:

- a new saved snapshot every run
- an updated trend report
- a local history database that `geo history` and `geo audit --regression` can reuse
