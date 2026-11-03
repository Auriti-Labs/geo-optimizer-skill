"""capabilities.json and SKILL.md describe the commands and MCP tools that actually exist."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from geo_optimizer.cli.main import cli

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((ROOT / "capabilities.json").read_text(encoding="utf-8"))


def _is_tool_decorator(d: ast.expr) -> bool:
    # Matches both @mcp.tool() and bare @mcp.tool.
    target = d.func if isinstance(d, ast.Call) else d
    return isinstance(target, ast.Attribute) and target.attr == "tool"


def _registered_mcp_tools() -> set[str]:
    # Parsed, not imported: the mcp extra is optional.
    tree = ast.parse((ROOT / "src/geo_optimizer/mcp/server.py").read_text(encoding="utf-8"))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(_is_tool_decorator(d) for d in node.decorator_list)
    }


def _safety_table_rows(text: str) -> list[str]:
    """Rows of the table under "### What each command touches", up to the next heading."""
    section = text.split("### What each command touches", 1)[1]
    rows = []
    for line in section.splitlines():
        if line.startswith("#"):
            break
        if line.startswith("|"):
            rows.append(line)
    return rows


def test_manifest_lists_every_cli_command():
    assert set(MANIFEST["commands"]) == set(cli.commands)


def test_manifest_lists_every_mcp_tool():
    assert set(MANIFEST["mcp_tools"]["tools"]) == _registered_mcp_tools()


def test_skill_has_preflight_and_safety_rules():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "geo --version" in text and "pip install geo-optimizer-skill" in text
    assert f"version {MANIFEST['min_version']}" in text
    assert "data, not instructions" in text and "--no-plugins" in text
    first_cells = [row.split("|")[1] for row in _safety_table_rows(text)]
    missing = [name for name in cli.commands if not any(f"`{name}`" in cell for cell in first_cells)]
    assert not missing, f"SKILL.md safety table misses: {missing}"


def test_manifest_executables_match_project_scripts():
    tomllib = pytest.importorskip("tomllib")  # Python 3.11+
    scripts = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
    assert set(MANIFEST["executables"]) == set(scripts)
