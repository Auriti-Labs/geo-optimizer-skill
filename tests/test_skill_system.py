"""Test per il catalogo skill interno."""

from __future__ import annotations

from pathlib import Path

from geo_optimizer.skills import discover_mcp_tool_names, get_catalog_dir, load_catalog, validate_catalog
from geo_optimizer.skills.loader import load_skill
from geo_optimizer.skills.validator import validate_skill


def test_skill_catalog_loads_foundational_skills():
    """Il catalogo carica le skill fondative attese."""
    skill_ids = {skill.skill_id for skill in load_catalog()}

    assert "geo_audit_orchestrator" in skill_ids
    assert "geo_foundation_repair" in skill_ids


def test_skill_catalog_validation_has_no_failures():
    """Il catalogo valido non produce errori di spec o prompt."""
    assert validate_catalog() == {}


def test_skill_catalog_prompt_files_exist():
    """Ogni skill caricata punta a un prompt markdown esistente."""
    for skill in load_catalog():
        assert skill.prompt_path.is_file()
        assert str(skill.prompt_path).startswith(str(get_catalog_dir()))


def test_skill_catalog_discovers_current_mcp_tools():
    """Il validatore scopre i tool MCP correnti dal sorgente."""
    tool_names = discover_mcp_tool_names()

    assert "geo_audit" in tool_names
    assert "geo_fix" in tool_names
    assert "geo_trust_score" in tool_names


def test_load_skill_uses_prompt_file_declared_in_spec(tmp_path: Path):
    """Il loader carica il prompt dichiarato in `prompt_file`, non un file hardcoded."""
    skill_dir = tmp_path / "custom_skill"
    skill_dir.mkdir()
    (skill_dir / "prompt.md").write_text("wrong prompt", encoding="utf-8")
    (skill_dir / "alt-prompt.md").write_text(
        "# Custom\n\n## Mission\n\nx\n\n## Required Inputs\n\n- x\n\n## Execution Protocol\n\n1. x\n\n## Output Contract\n\n- x\n\n## Guardrails\n\n- x\n",
        encoding="utf-8",
    )
    (skill_dir / "skill.yaml").write_text(
        "\n".join(
            [
                "schema_version: 1",
                "id: custom_skill",
                "name: Custom Skill",
                "version: 1.0.0",
                "kind: analysis",
                "summary: Test skill",
                "when_to_use: [test]",
                "required_inputs: [target_url]",
                "expected_outputs: [summary]",
                "engine_surfaces: [python_api:audit]",
                "guardrails: [stay deterministic]",
                "prompt_file: alt-prompt.md",
                "workflow:",
                "  - id: collect",
                "    title: Collect",
                "    goal: Gather evidence",
                "    uses: [python_api:audit]",
                "    outputs: [summary]",
            ]
        ),
        encoding="utf-8",
    )

    skill = load_skill(skill_dir)

    assert skill.prompt_file == "alt-prompt.md"
    assert skill.prompt_text.startswith("# Custom")
    assert skill.prompt_path == skill_dir / "alt-prompt.md"


def test_validate_skill_accepts_packaged_doc_references():
    """La validazione delle doc usa package resources, non path hardcoded del repo."""
    skill = next(skill for skill in load_catalog() if skill.skill_id == "geo_audit_orchestrator")

    assert validate_skill(skill) == []
