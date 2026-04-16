"""Loader per il catalogo skill interno."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from geo_optimizer.skills.models import SkillSpec, SkillStepSpec


def get_catalog_dir() -> Path:
    """Restituisce la directory canonica del catalogo skill."""
    return Path(__file__).resolve().parent / "catalog"


def _require_yaml():
    """Importa PyYAML solo al momento del parsing.

    Raises:
        RuntimeError: Se PyYAML non e' disponibile.
    """
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - coperto indirettamente dai test ambiente
        raise RuntimeError(
            "Skill loading requires PyYAML. Install geo-optimizer-skill[config] or geo-optimizer-skill[dev]."
        ) from exc

    return yaml


def _ensure_list(value: Any, field_name: str) -> list[str]:
    """Normalizza un campo lista in lista di stringhe."""
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"Field '{field_name}' must be a list")
    return [str(item) for item in value]


def load_skill(skill_dir: Path) -> SkillSpec:
    """Carica una skill dal suo folder canonico.

    Args:
        skill_dir: Directory contenente almeno `skill.yaml` e il prompt dichiarato nella spec.

    Returns:
        SkillSpec tipizzata con prompt caricato.
    """
    yaml = _require_yaml()

    spec_path = skill_dir / "skill.yaml"
    if not spec_path.is_file():
        raise FileNotFoundError(f"Missing skill spec: {spec_path}")

    raw = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Skill spec must be a mapping: {spec_path}")

    prompt_file = str(raw.get("prompt_file", "prompt.md"))
    prompt_path = (skill_dir / prompt_file).resolve()
    if not str(prompt_path).startswith(str(skill_dir.resolve()) + os.sep):
        raise ValueError(f"prompt_file escapes skill directory: {prompt_file}")
    if not prompt_path.is_file():
        raise FileNotFoundError(f"Missing prompt file: {prompt_path}")

    workflow_raw = raw.get("workflow", [])
    if not isinstance(workflow_raw, list):
        raise ValueError(f"Field 'workflow' must be a list in {spec_path}")

    workflow = []
    for step in workflow_raw:
        if not isinstance(step, dict):
            raise ValueError(f"Each workflow step must be a mapping in {spec_path}")
        workflow.append(
            SkillStepSpec(
                step_id=str(step.get("id", "")),
                title=str(step.get("title", "")),
                goal=str(step.get("goal", "")),
                uses=_ensure_list(step.get("uses", []), "workflow[].uses"),
                outputs=_ensure_list(step.get("outputs", []), "workflow[].outputs"),
            )
        )

    return SkillSpec(
        schema_version=int(raw.get("schema_version", 0)),
        skill_id=str(raw.get("id", "")),
        name=str(raw.get("name", "")),
        version=str(raw.get("version", "")),
        kind=str(raw.get("kind", "")),
        summary=str(raw.get("summary", "")),
        when_to_use=_ensure_list(raw.get("when_to_use", []), "when_to_use"),
        required_inputs=_ensure_list(raw.get("required_inputs", []), "required_inputs"),
        expected_outputs=_ensure_list(raw.get("expected_outputs", []), "expected_outputs"),
        engine_surfaces=_ensure_list(raw.get("engine_surfaces", []), "engine_surfaces"),
        workflow=workflow,
        guardrails=_ensure_list(raw.get("guardrails", []), "guardrails"),
        prompt_file=prompt_file,
        prompt_text=prompt_path.read_text(encoding="utf-8"),
        source_dir=skill_dir,
    )


def load_catalog(include_templates: bool = False) -> list[SkillSpec]:
    """Carica l'intero catalogo skill.

    Args:
        include_templates: Se True include anche folder template o underscore-prefixed.
    """
    catalog_dir = get_catalog_dir()
    skills = []
    for entry in sorted(catalog_dir.iterdir()):
        if not entry.is_dir():
            continue
        if not include_templates and entry.name.startswith("_"):
            continue
        if (entry / "skill.yaml").is_file():
            skills.append(load_skill(entry))
    return skills
