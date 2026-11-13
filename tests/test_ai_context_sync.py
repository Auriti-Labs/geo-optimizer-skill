"""The generated ai-context blocks and the Claude Code plugin match SKILL.md, capabilities.json and pyproject."""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# scripts/ is not a package: load the generator from its path
_spec = importlib.util.spec_from_file_location("build_ai_context", ROOT / "scripts" / "build_ai_context.py")
build_ai_context = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_ai_context)


def test_ai_context_blocks_are_current():
    stale = build_ai_context.check(ROOT)
    assert not stale, f"stale ai-context files, run python scripts/build_ai_context.py: {stale}"


def _copy_sources(tmp_path: Path) -> None:
    for name in ("SKILL.md", "capabilities.json", "pyproject.toml"):
        shutil.copy(ROOT / name, tmp_path / name)
    for name in ("ai-context", "plugins"):
        shutil.copytree(ROOT / name, tmp_path / name)


def test_stale_block_is_detected(tmp_path):
    _copy_sources(tmp_path)
    target = tmp_path / "ai-context" / "cursor.mdc"
    # Age the block by rewriting the current minimum version: no hardcoded number to bump at each release
    version = json.loads((ROOT / "capabilities.json").read_text(encoding="utf-8"))["min_version"]
    target.write_text(target.read_text(encoding="utf-8").replace(version, "0.0.1", 1), encoding="utf-8")
    assert build_ai_context.check(tmp_path) == ["ai-context/cursor.mdc"]


def test_plugin_drift_is_detected(tmp_path):
    _copy_sources(tmp_path)
    skill = tmp_path / "SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8") + "\nedited\n", encoding="utf-8")
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace('version = "', 'version = "9', 1), encoding="utf-8"
    )
    stale = build_ai_context.check(tmp_path)
    assert "plugins/geo-optimizer/skills/geo-optimizer/SKILL.md" in stale
    assert "plugins/geo-optimizer/.claude-plugin/plugin.json" in stale


def test_marketplace_lists_the_plugin():
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    [entry] = market["plugins"]
    plugin_root = ROOT / entry["source"]
    manifest = json.loads((plugin_root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    # The install id uses the entry name, skill prefixes use the manifest name: keep them equal
    assert entry["name"] == manifest["name"] == "geo-optimizer"
    assert ".." not in entry["source"] and (plugin_root / "skills" / "geo-optimizer" / "SKILL.md").is_file()
    assert (
        "geo-mcp"
        in json.loads((plugin_root / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["geo-optimizer"]["args"]
    )
