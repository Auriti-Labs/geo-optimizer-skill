# Scripts of the calibration study (October 2026)

These are the scripts that produced the data behind the note and `../results.csv`. They are the originals of
2026-10-17 with four changes: paths and the API key are no longer hard-coded (the study read the key from a server
file; it now comes from `PERPLEXITY_API_KEY`), the CLI path comes from `GEO_CLI`, the working folder is a
command-line argument, and `export_results.py` was written afterwards (see below). The sampling, audit and API-call
logic is unchanged.

They have not been run again as a package: the study itself ran once, on 2026-10-17, and spent about 3.58 USD.
Running them again will give a different sample if the Tranco list is a different one, and different citations,
because the answers of an AI engine change from day to day.

## Order

1. `stage1_sample.py WORKDIR`: draws domains from the Tranco top million in 10 rank strata (seed 20261017), keeps
   reachable English-language sites and picks one informational page per site from its sitemap. Needs
   `WORKDIR/tranco-top1m.csv` (`rank,domain`, from tranco-list.eu; the list is third-party data and is not republished).
   One request per second per site; identifies itself with a user agent that names this repository.
2. `stage2_audit.py WORKDIR`: audits each chosen page with `geo audit --format json`. The study used the PyPI release
   `geo-optimizer-skill` 4.19.3 with its default rubric (v2), in a clean virtualenv (`GEO_CLI` points at its `geo`).
3. `study_perplexity.py WORKDIR CAP_USD`: asks Perplexity Sonar two fixed questions per page, built from the page's own
   headline, and records whether the page's domain and the exact page were among the cited sources. Needs
   `PERPLEXITY_API_KEY`; stops at the spending cap. Pages whose headline contains the site's own name are excluded.
4. `export_results.py WORKDIR OUTPUT.csv`: builds the published table (no domain, address or headline).
5. `analysis.py WORKDIR`: the pre-registered analysis (`../PREREGISTRATION.md`). Needs numpy, pandas, scipy and
   statsmodels.
6. `make_charts.py`: the two charts of the note, run in the folder that holds `results.csv`.

## What is not published

`sample.jsonl`, `audits.jsonl` and `study.jsonl` contain domains, page addresses, headlines and the questions built
from them, so they stay private. Only the aggregate table `results.csv` is published.

## One thing to know about `export_results.py`

The published `results.csv` came from an export step that was not saved. `export_results.py` was written later from
the column description in `../README.md` and checked against the published file: it produces the same 341 rows
(identical after sorting both). The row order of the published file was shuffled with an unknown seed, so the order
differs; the order does not matter for the analysis.
