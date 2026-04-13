# GEO Schema Readiness

## Mission

Evaluate whether a page or site is structurally ready from a schema / structured-data perspective for GEO-related discoverability, extractability, attribution clarity, and AI-facing interpretation.

## Required Inputs

- `target_url`
- `audit_evidence_input` — either a full `AuditResult` or a normalized audit summary that preserves the relevant schema evidence

## Execution Protocol

1. Start from the authoritative GEO audit surface so the assessment is grounded in real structured-data findings, not a generic schema checklist.
2. Interpret schema readiness in terms of coverage, type fit, richness, and attribution-supporting clarity using the existing scoring rubric and audit semantics.
3. Use the schema validation surface only to clarify whether concrete JSON-LD blocks are absent, malformed, or underspecified. Do not let validation status replace the broader readiness judgment.
4. Keep the interpretation focused on GEO value: explain whether the current schema layer helps AI systems understand the site, extract useful facts, and attribute entities or content clearly.
5. If the main need is implementation planning rather than readiness interpretation, route to the foundation-repair workflow instead of expanding this skill into a repair plan.

## Output Contract

- `schema_readiness_summary`: concise judgment of the current schema / structured-data posture as it relates to GEO goals.
- `prioritized_schema_gaps`: ordered list of the most meaningful schema-related weaknesses, each tied to the evidence surface it comes from.
- `schema_signal_strengths`: clear summary of the schema signals that already support machine-readable understanding well.
- `schema_improvement_priorities`: short list of the highest-leverage schema improvements to address first.
- `next_step_recommendation`: one explicit next workflow recommendation, typically foundation repair or a broader GEO audit follow-up.

## Guardrails

- Do not duplicate the full GEO audit output.
- Do not reduce the answer to raw validator output.
- Do not drift into a broad repair plan or generic SEO schema advice.
- Keep every claim tied to existing engine surfaces, MCP tools, or repository docs.
