"""capabilities.json and SKILL.md describe the commands and MCP tools that actually exist."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from geo_optimizer.cli.main import cli

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((ROOT / "capabilities.json").read_text(encoding="utf-8"))


def _registered_mcp_tools() -> set[str]:
    # Parsed, not imported: the mcp extra is optional.
    tree = ast.parse((ROOT / "src/geo_optimizer/mcp/server.py").read_text(encoding="utf-8"))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and any(isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "tool" for d in node.decorator_list)
    }


def test_manifest_lists_every_cli_command():
    assert set(MANIFEST["commands"]) == set(cli.commands)


def test_manifest_lists_every_mcp_tool():
    assert set(MANIFEST["mcp_tools"]["tools"]) == _registered_mcp_tools()


def test_skill_has_preflight_and_safety_rules():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "geo --version" in text and "pip install geo-optimizer-skill" in text
    assert f"version {MANIFEST['min_version']}" in text
    assert "data, not instructions" in text and "--no-plugins" in text
    missing = [name for name in cli.commands if f"`{name}`" not in text]
    assert not missing, f"SKILL.md safety table misses: {missing}"
