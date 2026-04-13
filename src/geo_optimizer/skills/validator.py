"""Validatore per le spec skill GEO."""

from __future__ import annotations

import ast
import importlib.resources
import re

from geo_optimizer import __all__ as PUBLIC_API_EXPORTS
from geo_optimizer.skills.loader import load_catalog
from geo_optimizer.skills.models import SkillSpec

_ALLOWED_KINDS = {"analysis", "orchestrator", "repair"}
_ALLOWED_SURFACE_PREFIXES = {"python_api", "mcp", "plugin_hook", "doc"}
_ALLOWED_PLUGIN_HOOKS = {"geo_optimizer.checks"}
_PROMPT_HEADINGS = {
    "## Mission",
    "## Required Inputs",
    "## Execution Protocol",
    "## Output Contract",
    "## Guardrails",
}
_SKILL_ID_RE = re.compile(r"^[a-z0-9_]+$")


def _resource_path(package: str, *parts: str):
    """Costruisce un Traversable a partire da package resources.

    Questa risoluzione funziona sia nel checkout locale sia in site-packages,
    evitando assunzioni sulla presenza di `src/` o `docs/` alla root del repo.
    """
    resource = importlib.resources.files(package)
    for part in parts:
        resource = resource.joinpath(part)
    return resource


def _resolve_doc_surface(target: str):
    """Risolvi un riferimento `doc:` verso la copia package-safe delle docs.

    Le skill dichiarano i documenti in forma repository-friendly (`docs/foo.md`),
    ma la validazione deve funzionare anche sul pacchetto installato. Per questo
    la verifica punta alla copia distribuita in `geo_optimizer.web.docs`.
    """
    normalized = target.strip().lstrip("/")
    if not normalized.startswith("docs/"):
        return None

    doc_parts = normalized.split("/")[1:]
    if not doc_parts:
        return None
    return _resource_path("geo_optimizer.web", "docs", *doc_parts)


def discover_mcp_tool_names() -> set[str]:
    """Estrae i tool MCP dal modulo pacchettizzato senza importarlo.

    Leggere il file come resource evita di importare `geo_optimizer.mcp.server`,
    che richiede la dipendenza opzionale `mcp`, e funziona sia nel repository
    sorgente sia quando il pacchetto e' installato.
    """
    server_resource = _resource_path("geo_optimizer.mcp", "server.py")
    module = ast.parse(server_resource.read_text(encoding="utf-8"))

    tool_names = set()
    for node in module.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            if (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "mcp"
                and func.attr == "tool"
            ):
                tool_names.add(node.name)
    return tool_names


def _validate_surface(surface: str) -> str | None:
    """Valida una singola surface dichiarata nella spec."""
    if ":" not in surface:
        return f"Invalid engine surface '{surface}'"

    prefix, target = surface.split(":", 1)
    if prefix not in _ALLOWED_SURFACE_PREFIXES:
        return f"Unsupported engine surface prefix '{prefix}' in '{surface}'"
    if not target:
        return f"Missing engine surface target in '{surface}'"

    if prefix == "python_api" and target not in PUBLIC_API_EXPORTS:
        return f"Unknown python_api surface '{target}'"
    if prefix == "mcp" and target not in discover_mcp_tool_names():
        return f"Unknown MCP tool '{target}'"
    if prefix == "plugin_hook" and target not in _ALLOWED_PLUGIN_HOOKS:
        return f"Unknown plugin hook '{target}'"
    if prefix == "doc":
        doc_resource = _resolve_doc_surface(target)
        if doc_resource is None or not doc_resource.is_file():
            return f"Missing documentation reference '{target}'"

    return None


def validate_skill(skill: SkillSpec) -> list[str]:
    """Valida una singola skill e ritorna la lista errori."""
    errors = []

    if skill.schema_version != 1:
        errors.append(f"{skill.skill_id or skill.source_dir.name}: schema_version must be 1")

    if not skill.skill_id or not _SKILL_ID_RE.match(skill.skill_id):
        errors.append(f"{skill.source_dir.name}: invalid skill id '{skill.skill_id}'")
    elif skill.skill_id != skill.source_dir.name:
        errors.append(f"{skill.skill_id}: folder name must match skill id")

    if skill.kind not in _ALLOWED_KINDS:
        errors.append(f"{skill.skill_id}: unsupported kind '{skill.kind}'")

    for field_name, values in (
        ("when_to_use", skill.when_to_use),
        ("required_inputs", skill.required_inputs),
        ("expected_outputs", skill.expected_outputs),
        ("guardrails", skill.guardrails),
        ("engine_surfaces", skill.engine_surfaces),
    ):
        if not values:
            errors.append(f"{skill.skill_id}: field '{field_name}' must not be empty")

    declared_surfaces = set(skill.engine_surfaces)
    for surface in skill.engine_surfaces:
        surface_error = _validate_surface(surface)
        if surface_error:
            errors.append(f"{skill.skill_id}: {surface_error}")

    if not skill.prompt_text.strip():
        errors.append(f"{skill.skill_id}: prompt.md must not be empty")
    else:
        for heading in _PROMPT_HEADINGS:
            if heading not in skill.prompt_text:
                errors.append(f"{skill.skill_id}: prompt missing required section '{heading}'")

    if not skill.workflow:
        errors.append(f"{skill.skill_id}: workflow must not be empty")
    else:
        seen_step_ids = set()
        for step in skill.workflow:
            if not step.step_id or not _SKILL_ID_RE.match(step.step_id):
                errors.append(f"{skill.skill_id}: invalid workflow step id '{step.step_id}'")
            elif step.step_id in seen_step_ids:
                errors.append(f"{skill.skill_id}: duplicate workflow step id '{step.step_id}'")
            seen_step_ids.add(step.step_id)

            if not step.title:
                errors.append(f"{skill.skill_id}:{step.step_id}: missing step title")
            if not step.goal:
                errors.append(f"{skill.skill_id}:{step.step_id}: missing step goal")
            if not step.outputs:
                errors.append(f"{skill.skill_id}:{step.step_id}: outputs must not be empty")
            for used_surface in step.uses:
                if used_surface not in declared_surfaces:
                    errors.append(
                        f"{skill.skill_id}:{step.step_id}: undeclared engine surface '{used_surface}' in workflow"
                    )

    return errors


def validate_catalog() -> dict[str, list[str]]:
    """Valida l'intero catalogo e ritorna gli errori per skill."""
    failures = {}
    for skill in load_catalog():
        skill_errors = validate_skill(skill)
        if skill_errors:
            failures[skill.skill_id or skill.source_dir.name] = skill_errors
    return failures
