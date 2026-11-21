# GEO Fanout

`geo fanout` checks which of the usual commercial follow-up questions a page speaks to, for one topic. An answer engine often turns a buying question into narrower searches (price, alternatives, reviews, how to choose). This command lists those families and shows which ones your page has words for.

It is deterministic: fixed templates, a lexical match, no language model, and no request beyond the page (same anti-SSRF checks as the audit). The families are a **hand-written checklist**, not the searches any engine really issues, and not mined from data.

## Usage

```bash
geo fanout --url https://yoursite.com/crm --topic "CRM software"
geo fanout --url https://yoursite.com/crm --topic "CRM software" --format json --output fanout.json
```

## What it does

The topic is expanded into seven families, three queries each: `price`, `comparison`, `reviews`, `how_to`, `fit`, `trust`, `free_options` (for example "CRM software price", "best alternatives to CRM software", "is CRM software safe"). Each query is scored on the words the template adds to the topic ("price", "alternatives", "safe"), **not** on the topic's own words, which every query shares and which would make every family look covered. Those words only count in a surface that also speaks of the topic (at least half of its terms): a heading about something else that contains "price" does not help.

The surfaces and weights are those of `geo align` (title and h1 1.0, meta description and headings 0.9, passages 0.8). A family is as covered as the mean of its queries: 0.75 or more covered, 0.4 or more partial, below that uncovered. Words that appear nowhere on the page are listed per query: those are the words to write.

## What it does not do

- It does not know whether the page answers the follow-up, only whether it uses the words near the topic.
- The templates are English; other languages are not covered.
- A topic with no searchable words (empty, or only words such as "the" and "how to") is refused: nothing would tie a query to the topic.
- A topic that is itself a template word ("price", "free") loses that word from its family, which then has fewer queries.
- Plurals are matched for English words only.
- It does not discover sub-intents for your market; use `geo align` with your own list for that.
