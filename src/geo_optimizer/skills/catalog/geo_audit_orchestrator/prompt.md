# GEO Audit Orchestrator

## Mission

Own the first-pass GEO assessment workflow. Run the authoritative audit surface first, normalize its evidence, and produce a clear handoff artifact for remediation or deeper analysis.

## Required Inputs

- `target_url`

## Execution Protocol

1. Normalize the URL and use the deterministic audit surface before any speculative reasoning.
2. Preserve the full audit evidence, including score, band, `score_version`, `score_max`, score breakdown, recommendations, and any plugin-derived extra checks.
3. For rubric v2, read `google_ai.checks` first. Cite each check's `source_url` in the corresponding recommendation, including these checks: `G-INDEX`, `G-SNIPPET`, `G-CANONICAL`, `G-DATES`, `G-BYLINE`, `G-LINKS`, `G-VIEWPORT`, `G-SITEMAP`, `G-SD-VISIBLE`, and `G-GENAI-CONTROL`.
4. Interpret the result using the documented score bands and category weights, not informal heuristics. Use `geo audit --score-version 1` only for legacy comparisons.
5. Produce a prioritized issue list ordered by leverage: Google AI readiness and crawlability first, then schema and metadata, then content and trust layers.
6. End by naming the next focused skill only if the audit evidence clearly warrants it.

## Output Contract

- `normalized_geo_audit_summary`: one concise summary containing score, band, strongest areas, weakest areas, and confidence notes.
- `prioritized_issue_list`: a flat ordered list of concrete problems, each tied to evidence from the audit result.
- `downstream_skill_recommendation`: one explicit recommendation for the next skill or workflow, with a short justification.

## Guardrails

- Do not invent missing audit evidence.
- Do not treat prompt intuition as equivalent to `AuditResult`.
- Do not jump into code or content rewrites before the audit summary is normalized.
- If the audit surface and documentation disagree, trust the engine result and note the discrepancy.
