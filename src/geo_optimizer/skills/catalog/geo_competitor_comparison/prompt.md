# GEO Competitor Comparison

## Mission

Compare the GEO posture of two or more sites using existing audit, scoring, trust, and citability evidence, then explain which differences matter most and what the weaker site should prioritize to close the gap.

## Required Inputs

- `target_site_list`

## Execution Protocol

1. Start from the existing comparison and audit surfaces so the comparison is anchored to real score, band, and category evidence.
2. Normalize the comparison into meaningful deltas instead of restating each audit independently.
3. Use the scoring rubric to explain why a difference matters and whether it is foundational, trust-related, or content/citability-related.
4. Use trust and citability evidence only when they sharpen the comparative explanation of why one site is easier to trust, quote, or surface.
5. End with priorities for the weaker site, not just an observation that another site is ahead.

## Output Contract

- `comparison_summary`: concise statement of which site is stronger overall and why.
- `strongest_advantages_by_site`: flat summary of the clearest GEO advantages each site holds.
- `prioritized_gap_list`: ordered deltas that best explain the weaker site's disadvantage.
- `closing_gap_priorities`: short list of the highest-leverage actions the weaker site should take first.
- `next_step_recommendation`: one explicit next workflow recommendation for the weaker site.

## Guardrails

- Do not produce a generic competitor analysis.
- Do not just paste multiple audit summaries with no synthesis.
- Do not invent unsupported scoring or market-positioning criteria.
- Keep every comparative claim tied to existing GEO surfaces and docs.
