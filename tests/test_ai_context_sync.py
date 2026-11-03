"""The generated preflight block of every ai-context file matches SKILL.md and capabilities.json."""

from __future__ import annotations

import importlib.util
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


def test_stale_block_is_detected(tmp_path):
    for name in ("SKILL.md", "capabilities.json"):
        shutil.copy(ROOT / name, tmp_path / name)
    shutil.copytree(ROOT / "ai-context", tmp_path / "ai-context")
    target = tmp_path / "ai-context" / "cursor.mdc"
    target.write_text(target.read_text(encoding="utf-8").replace("4.19", "4.18", 1), encoding="utf-8")
    assert build_ai_context.check(tmp_path) == ["cursor.mdc"]
