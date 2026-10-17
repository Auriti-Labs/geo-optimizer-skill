# Pre-registration: GEO score and citation by Perplexity (written 2026-10-17, before the full run)

Fixed before any full-study data exist. Pilot data (40 pages, 2026-10-17) were seen and used only to check the pipeline, the base rate (about 40-55%) and phrasing robustness; they are NOT part of the full-study data.

Sample: the pages in audits.jsonl with a valid CLI audit (389 pages, engine 4.19.3, rubric v2), one page per site, drawn from the Tranco list in 10 log-rank strata (seed 20261017).

Outcome (primary): `domain_cited` for question template A ("What are the most reliable sources on: {H1}"), one run per page. Secondary: template B ("Explain this topic and cite your sources: {H1}"); exact-page citation; either-template citation. Pages whose H1 contains the brand token are excluded (as in the pilot).

Exposure: total readiness score (0-100, rubric v2). Secondary: each of the nine category scores.

Primary analysis: logistic regression of the primary outcome on score, controlling for log(Tranco rank) and log(word count); report the odds ratio per 10 score points with a 95% confidence interval and a bootstrap check (2,000 resamples), plus the partial Spearman correlation controlling for log rank. Significance level 0.05, two-sided. Secondary analyses: the nine categories one by one with Holm correction; the other outcomes; excluding pages on sites that block at least one AI bot in robots.txt.

Interpretation rules: observational data, no causal claim. A null or weak result is reported as such. Limits stated in any publication: one engine (Perplexity Sonar), one date, one model version; the question is built from the page's own H1, so the outcome measures whether the page is cited when the question names its own topic, not preference among all competing sources; sites that block our user agent or lack a sitemap or English text are under-represented.

Decision rule on weights: no change to the scoring rubric is made on the basis of this study alone; any such change is a product decision of the founder.
