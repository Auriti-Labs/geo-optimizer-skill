# Skill System

GEO Optimizer now includes a minimal internal skill framework for maintainers.

This layer does **not** replace the existing audit engine, MCP server, or plugin system. It standardizes how AI-facing workflows should consume them.

## Design Goals

- Keep skills explicit, small, and reviewable
- Reuse existing deterministic engine surfaces
- Avoid prompt blobs with hidden assumptions
- Make future skill additions testable

## Canonical Format

Each skill lives in `src/geo_optimizer/skills/catalog/<skill_id>/` and contains:

- `skill.yaml` — structured metadata and workflow contract
- `prompt.md` — operational prompt contract with required sections

Required metadata includes:

- `id`, `name`, `version`, `kind`, `summary`
- `when_to_use`
- `required_inputs`
- `expected_outputs`
- `engine_surfaces`
- `workflow`
- `guardrails`

## Relationship to Existing Systems

### Audit engine

The audit engine remains the authoritative evidence layer. Skills should call or reference it first when they need site-state truth.

### MCP surface

MCP tools remain the remote-control interface for agent workflows. Skills can depend on `mcp:` surfaces, but they should still preserve deterministic evidence and validation.

### Plugin/check system

`CheckRegistry` remains the extensibility point for additional audit checks. Skills can reference the plugin hook, but they do not replace per-check execution or scoring.

### Documentation

Skills can reference `doc:` surfaces so prompt behavior stays tied to versioned repository documentation instead of folklore.

## Validation

`geo_optimizer.skills.validator` checks:

- required fields
- legal `kind` values
- folder name matches skill `id`
- engine surface references resolve
- workflow step ids are unique
- `prompt.md` contains the required contract sections

The repository test suite validates the whole catalog.

## Catalog v1

Initial foundational skills:

- `geo_audit_orchestrator`
- `geo_foundation_repair`

These are intentionally narrow. They define the contract for future skills without introducing a runtime agent engine.

## Adding a New Skill

1. Copy `src/geo_optimizer/skills/catalog/_template/` into a new folder named after the new skill `id`.
2. Fill in `skill.yaml` with real `engine_surfaces`, explicit `workflow` steps, and concrete `guardrails`.
3. Write `prompt.md` so it includes all required sections:
   `Mission`, `Required Inputs`, `Execution Protocol`, `Output Contract`, `Guardrails`.
4. Keep the skill narrow. If it overlaps an existing skill, tighten the scope before adding it.
5. Validate the catalog before opening a PR:

```bash
pytest tests/test_skill_system.py -q
```

Use `geo_audit_orchestrator` and `geo_foundation_repair` as the canonical examples for tone and structure.

## What This Layer Intentionally Does Not Do Yet

- no dynamic agent runtime
- no prompt rendering engine
- no skill chaining executor
- no new CLI surface
- no replacement for MCP tools or plugin checks

That work should only happen after the catalog grows enough to justify execution infrastructure.
