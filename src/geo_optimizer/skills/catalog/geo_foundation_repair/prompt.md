# GEO Foundation Repair

## Mission

Turn a GEO audit into a practical repair plan for the foundational surfaces that most directly affect discoverability and citation readiness.

## Required Inputs

- `target_url`
- `audit_result_or_gap_list`

## Execution Protocol

1. Start from authoritative audit evidence and confirm the exact missing foundations.
2. Use the existing fix-generation surface to derive concrete artifacts before offering generic guidance.
3. Treat robots.txt, llms.txt, schema, metadata, and AI discovery as the primary repair order unless the audit proves a different blocker.
4. Validate machine-readable artifacts when possible, especially JSON-LD.
5. End with a verification checklist that can be executed after implementation.

## Output Contract

- `remediation_plan`: ordered list of foundation repairs with rationale tied to audit evidence.
- `generated_artifact_list`: explicit files, snippets, or endpoint payloads to create or update.
- `verification_checklist`: concrete follow-up checks covering bots, AI discovery, schema validation, and a re-run audit.

## Guardrails

- Do not skip directly to content rewriting when technical foundations are still missing.
- Do not recommend bot directives or schema fields that conflict with repository docs or validators.
- Do not mark a repair complete without a verification step.
- Keep the plan deterministic, evidence-based, and implementation-oriented.
