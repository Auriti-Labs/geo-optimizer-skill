# GEO Align

`geo align` measures how much of each prompt your page's own text covers. It answers one question: *for the questions I want to be found for, does this page say the words?*

It is deterministic. It fetches the page once (with the same anti-SSRF checks as the audit) and then works offline: no language model, no embedding, no other request. It is a lexical measure of your content against your own list. It is **not** what ChatGPT, Perplexity or Google would answer.

---

## Usage

```bash
# A list of prompts, one per line
geo align --url https://yoursite.com/roof-repair --prompts prompts.txt

# A Search Console or Bing export (the header names a query column)
geo align --url https://yoursite.com --prompts queries.csv

# A few prompts on the command line
geo align --url https://yoursite.com --prompt "roof repair leeds" --prompt "flat roof leak cost"

# JSON, or write to a file
geo align --url https://yoursite.com --prompts prompts.txt --format json --output align.json
```

Input rules: blank lines and lines starting with `#` are ignored; duplicates are skipped; a prompt over 300 characters is skipped; at most 200 prompts are read; a prompt file over 1 MB is refused. A CSV is read by its header (`Query`, `Top queries`, `Query principali`, `Prompt`, `Keyword` and a few others, with or without a byte-order mark); a file without such a header is read as lines. Prompts given with `--prompt` are added after the file.

---

## How a prompt is scored

The prompt is reduced to its terms: lower case, without stopwords (English and Italian function words) and one-letter tokens. Plain English plurals are matched (`repairs` and `repair`); other languages match on exact words.

For every surface of the page the report takes the share of the prompt's terms found in that surface, multiplied by the surface weight, and keeps the best one:

| Surface | Weight |
|---------|--------|
| `<title>`, `<h1>` | 1.0 |
| meta description, `<h2>` to `<h6>` | 0.9 |
| a passage (a paragraph, list item, cell or text block, in windows of up to 120 words) | 0.8 |

A score of 0.75 or more is **covered**, from 0.4 it is **partial**, below that **uncovered**. The status follows the score as shown (two decimals). Navigation, footer, aside and script text is not read. The weights and thresholds are judgments, not measurements; they are constants in `models/config.py`.

The report also lists, for each prompt, the terms that appear **nowhere on the page**. Those are the words to write, not the words to repeat.

---

## What it does not do

- It does not know whether the page answers the question, only whether it uses the words together.
- A one-term prompt is covered as soon as the term appears in a heading.
- Text in images, in scripts or loaded after the page is fetched is not read.
- It does not discover related questions (sub-intents); the list is yours.
