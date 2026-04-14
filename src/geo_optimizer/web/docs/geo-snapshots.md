# GEO Snapshots

`geo snapshots` archives complete AI answer snapshots in a local SQLite database.

This feature is designed for audit trail, regression analysis, and compliance-style record keeping when you want to preserve:

- the full answer text
- the original query and prompt
- the model/provider used
- extracted cited URLs with position order
- the timestamp of the answer

Snapshots are stored in `~/.geo-optimizer/snapshots.db`.

---

## Use cases

- prove that your site was cited on a given date
- compare how answers changed over time for the same query
- keep an internal archive of AI responses used for reporting

---

## Save a snapshot

```bash
geo snapshots \
  --query "best GEO tool" \
  --prompt "What is the best GEO tool?" \
  --model "gpt-5.4" \
  --provider "openai" \
  --answer-file ./answer.txt
```

You can also pass the answer inline:

```bash
geo snapshots \
  --query "best GEO tool" \
  --model "claude-4" \
  --answer-text "GEO Optimizer is referenced at https://example.com/report"
```

If URLs appear in the answer text, they are extracted automatically as citations. You can also add explicit citations with repeated `--citation-url`.

---

## Query the archive

```bash
geo snapshots --query "best GEO tool"
geo snapshots --query "best GEO tool" --from 2026-03-01 --to 2026-03-30
geo snapshots --model "gpt-5.4" --format json
```

## Citation quality scoring

Once a snapshot is archived, you can score the quality of each citation:

```bash
geo snapshots --quality --snapshot-id 12
geo snapshots --quality --snapshot-id 12 --target-domain example.com
```

The quality report assigns:

- a tier (`T1` recommended → `T5` mentioned)
- a position score (first citations rank higher)
- a context snippet around the citation
- an overall score combining tier + position

---

## Options

| Flag | Required | Description |
|------|----------|-------------|
| `--query` | No | Query text used for saving or filtering |
| `--prompt` | No | Full prompt used when saving |
| `--model` | Save mode: Yes | Model/version used to generate the answer |
| `--provider` | No | Provider label such as `openai`, `anthropic`, `google` |
| `--quality` | No | Analyze citation quality for a saved snapshot |
| `--snapshot-id` | Quality mode: Yes | Snapshot ID to analyze |
| `--target-domain` | No | Restrict quality analysis to one cited domain |
| `--answer-text` | Save mode: Yes* | Full answer text inline |
| `--answer-file` | Save mode: Yes* | File containing the full answer text |
| `--citation-url` | No | Extra cited URL to store explicitly |
| `--timestamp` | No | Override snapshot timestamp |
| `--from` | No | Filter archive from this date |
| `--to` | No | Filter archive until this date |
| `--limit` | No | Maximum number of returned snapshots |
| `--format` | No | `text` or `json` |

\* Use either `--answer-text` or `--answer-file`.

---

## Notes

- `geo snapshots` does not query AI APIs by itself
- it acts as the local persistence layer for answer archives
- it pairs well with [`geo monitor`](geo-monitor.md) and future active visibility checks
