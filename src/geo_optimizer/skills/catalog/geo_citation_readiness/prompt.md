# GEO Citation Readiness

## Mission

Evaluate whether a page or site is realistically ready to be cited, reused, or surfaced by AI systems by interpreting the existing GEO audit, citability, trust, and citation-risk evidence.

## Required Inputs

- `target_url`
- `audit_evidence_input` — either a full `AuditResult` or a normalized audit summary that preserves the relevant evidence

## Execution Protocol

1. Start from the authoritative GEO audit surface so the assessment is grounded in real crawlability, structure, trust, and content evidence.
2. Use the citability surface to interpret extractability and content reuse readiness rather than inventing an ad hoc scoring model.
3. Use trust and negative-signal surfaces to identify whether the content looks reliable enough to quote and safe enough to surface.
4. Keep the interpretation focused on citation readiness: explain whether the content is easy to quote, easy to trust, and unlikely to be suppressed by citation-related blockers.
5. If the primary blockers are still foundational, say so explicitly and route to the foundation-repair workflow instead of over-prescribing editorial changes.

## Output Contract

- `citation_readiness_summary`: concise judgment of current citation readiness, tied to existing audit and citability evidence.
- `prioritized_citation_risks`: ordered list of the strongest citation-specific risks, each with the evidence surface it comes from.
- `remediation_focus_list`: short list of the highest-leverage follow-up actions that would most improve citation readiness.
- `next_step_recommendation`: one explicit next workflow recommendation, such as foundation repair or a deeper content/citation pass.

## Guardrails

- Do not duplicate the full GEO audit output.
- Do not invent unsupported notions of “AI visibility.”
- Do not drift into a generic writing-quality review.
- Keep every claim tied to existing engine surfaces, MCP tools, or repository docs.
