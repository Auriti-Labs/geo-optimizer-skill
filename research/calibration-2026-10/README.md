# Calibration study, October 2026: does the GEO score predict whether Perplexity cites a page?

Draft published with the note on geoready.dev. These files let a reader check the figures in the note.

## Files

- `PREREGISTRATION.md`: the analysis plan, written before the full run. Its SHA-256 is `441fcbb422964fdf2bf2b63eb02181ccbea9e7c5590d3e770399d567cd373ff8` (check with `sha256sum PREREGISTRATION.md`).
- `results.csv`: one row per page (341 pages), in shuffled order. No domain, address or headline.
- `analysis-results.txt`: the output of the pre-registered analysis (run on 2026-10-17 on the exact rank).

## Columns of `results.csv`

| Column | Meaning |
|---|---|
| `rank_band` | Band of the site's Tranco rank |
| `ln_rank_1dp` | Natural log of the exact rank, rounded to one decimal (used as the popularity control) |
| `score` | GEO score of the page, 0 to 100 (rubric v2, GEO Optimizer 4.19.3) |
| `google_ai` ... `negative_penalty` | Category scores and the negative-signal penalty of the same audit |
| `words` | Words on the page |
| `blocks_ai_bot` | 1 if the site's robots.txt blocks at least one AI bot named in `AI_BOTS` |
| `domain_cited_A`, `domain_cited_B` | 1 if the page's domain appeared among the sources Perplexity Sonar returned for question template A or B |
| `page_cited_A`, `page_cited_B` | The same, for the exact page |

Question template A: "What are the most reliable sources on: [headline]". Template B: "Explain this topic and cite your sources: [headline]".

## Reproducing the primary result

Logistic regression of `domain_cited_A` on `score / 10`, `ln_rank_1dp` and `log(words)`. On this table: odds ratio per 10 score points 0.962 (95% confidence interval 0.783 to 1.184), p = 0.717. The note reports 0.963 (0.783 to 1.184), p = 0.717, computed with the unrounded rank.

## Limits

One engine (Perplexity Sonar), one date (17 October 2026), one model version. The question is built from each page's own headline, so the outcome measures whether a page is cited when the question names its own topic. The sample favours reachable, English-language sites that publish a sitemap. Observational data: no causal claim. The sampling, audit and API-call scripts are not published.
