# GEO Fidelity

`geo fidelity` checks an AI answer against the pages it cites. An answer engine puts a link next to a sentence; this command reads each cited page and shows whether the page carries the words (and the figures) of that sentence.

It is deterministic: the answer is cut into sentences, each sentence is scored against every cited page with the same lexical measure as `geo align`, and there is no language model and no request beyond the cited pages (same anti-SSRF checks as the audit). It **does not decide whether a claim is true**, or whether a page endorses it.

## Usage

```bash
geo fidelity --answer answer.txt --source https://example.com/pricing --source https://example.org/review
geo fidelity --answer answer.txt --source https://example.com/pricing --format json --output fidelity.json
```

`--answer` is a text file with the answer as the engine gave it (footnote markers such as `[1]` and list bullets are ignored). `--source` is repeatable, up to 10 pages.

## What it does

Sentences of at least five words are claims, up to 40. Each claim is scored on every cited page; the best page wins and is named. A claim is *supported* at 0.75 or more, *partial* at 0.4 or more, *unsupported* below that. A figure in the claim (a price, a percentage, a year) must appear in the best page's text: if it does not, a supported claim is held at *partial* and the figure is listed. Words found on none of the cited pages are listed too.

The report gives the counts and the share of supported claims. An unsupported claim is the first one to read by hand.

## What it does not do

- A sentence can share every word with a page and still contradict it; a paraphrase can share few words and be right.
- It does not follow links, read PDFs, or run scripts: text inside images and scripts is not seen.
- Plurals are matched for English words only.
- It does not know which source the engine really used for a sentence; every cited page is tried.
- Pages that cannot be fetched are listed as not readable and left out of the match.
