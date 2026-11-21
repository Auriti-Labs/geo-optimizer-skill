# GEO Lint

`geo lint` lists sentences on a page that claim more than the page supports. It is a set of text heuristics, English and Italian, with false positives: **a finding is a question to ask about the sentence, never a verdict**. Nothing here is scored, no language model is used, and the only network request is the page itself (with the same anti-SSRF checks as the audit).

## Usage

```bash
geo lint --url https://yoursite.com/pricing
geo lint --url https://yoursite.com --format json --output lint.json
```

## What it checks

| Rule | Family | Fires when |
|------|--------|-----------|
| `unsourced_statistic` | authority without evidence | an outcome figure (a percentage, "3x", "N times faster", "increased by N%") appears and neither the block, a link in it, nor the blocks before and after mention a source, a study, a survey, a sample, a year. Prices, fees, rates, discounts and VAT are not outcome claims and are skipped |
| `unsupported_authority` | authority without evidence | "award-winning", "#1", "market leader", "trusted by N", "certified" and similar, with no link in the block |
| `duplicate_block` | repetition | the same paragraph (six words or more) appears five times or more. Cards, table cells and list items are not counted: they repeat by design |
| `keyword_list` | repetition | a block is only a list of 20 or more short items |
| `caveat_omitted` | promise without caveat | an asserted absolute promise ("guaranteed", "risk-free", "never fails", "always works") with no qualifier in the block ("up to", "unless", "depends", "conditions") |

A sentence that asks (`?`), denies ("does not guarantee") or softens ("almost always") the promise is not counted. Navigation, footer, aside, script and code (`pre`, `code`, `kbd`, `samp`) text is not read. The thresholds and patterns are judgments, in `models/config.py`.

## What it does not do

- It does not check facts: a figure with a source nearby passes whether or not it is true.
- A testimonial quoted with a figure is flagged like any other statistic. So is a product limit written as "up to 500% higher limits".
- A technical guarantee ("evaluation order is guaranteed") counts as an absolute promise.
- Evidence behind a link is not followed.
- Other languages than English and Italian are not covered.
- The listing is capped at 50 findings; the counts are complete.
