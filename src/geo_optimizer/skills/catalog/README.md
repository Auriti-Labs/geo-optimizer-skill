# GEO Internal Skill Catalog

This catalog is the canonical v1 skill layer for GEO Optimizer maintainers.

Each skill folder contains:

- `skill.yaml`: structured metadata and workflow contract
- `prompt.md`: executable prompt contract for agents or maintainers

The format is intentionally small:

- deterministic references to existing engine surfaces
- explicit required inputs and expected outputs
- explicit workflow steps
- explicit guardrails

Supported engine surface prefixes:

- `python_api:` for exported package symbols such as `audit` or `AuditResult`
- `mcp:` for tools declared in `src/geo_optimizer/mcp/server.py`
- `plugin_hook:` for extensibility hooks such as `geo_optimizer.checks`
- `doc:` for repository documentation paths

Review checklist for every new skill:

1. The folder name matches the skill `id`.
2. Every workflow step is explicit and output-oriented.
3. Every engine surface reference resolves to a real implementation or doc.
4. `prompt.md` includes the required contract sections:
   `Mission`, `Required Inputs`, `Execution Protocol`, `Output Contract`, `Guardrails`.
5. The skill adds leverage without duplicating another skill under a different name.

Use `_template/` as the starting point for new skills.
