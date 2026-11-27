"""The version and the headline counts agree everywhere they are stated.

Version: pyproject.toml is the source of truth; the fallback in ``geo_optimizer/__init__.py``,
the installed metadata (when it belongs to this checkout), the newest released CHANGELOG
heading and ``capabilities.json`` ``min_version`` must agree with it.

Counts: a number claimed in README/SKILL/docs is checked only where one authoritative source
exists in code (CLI command group, MCP tool decorators, AI_BOTS, the default rubric's
categories, the ``--format`` choices of ``geo audit``).
"""

from __future__ import annotations

import ast
import json
import re
from importlib import metadata
from pathlib import Path

import click
import pytest

ROOT = Path(__file__).resolve().parent.parent


def _pyproject_version() -> str:
    # Regex, not tomllib: tomllib is 3.11+ and the suite also runs on 3.10.
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project = text.split("[project]", 1)[1].split("\n[", 1)[0]
    match = re.search(r'^version\s*=\s*"([^"]+)"', project, re.MULTILINE)
    assert match, "no version in the [project] table of pyproject.toml"
    return match.group(1)


def _as_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", version)[:3])


def test_init_fallback_version_matches_pyproject():
    tree = ast.parse((ROOT / "src/geo_optimizer/__init__.py").read_text(encoding="utf-8"))
    fallbacks = [
        node.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    ]
    assert fallbacks == [_pyproject_version()]


def test_installed_version_matches_pyproject():
    # __version__ is read from the installed metadata. Only a pip install of this checkout
    # (CI: pip install -e) says something about it; a src/*.egg-info left by an older install
    # can shadow it on sys.path, so the metadata is selected by its direct_url.json.
    ours = [
        dist
        for dist in metadata.distributions()
        if (dist.metadata["Name"] or "").lower() == "geo-optimizer-skill"
        and json.loads(dist.read_text("direct_url.json") or "{}").get("url") == ROOT.as_uri()
    ]
    if not ours:
        pytest.skip("geo-optimizer-skill is not pip-installed from this checkout")
    assert {dist.version for dist in ours} == {_pyproject_version()}


def test_changelog_latest_release_matches_pyproject():
    headings = re.findall(r"^## \[([^\]]+)\]", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), re.MULTILINE)
    released = [h for h in headings if h.lower() != "unreleased"]
    assert released, "CHANGELOG.md has no released heading"
    assert released[0] == _pyproject_version()


def test_capabilities_min_version_not_ahead_of_current():
    manifest = json.loads((ROOT / "capabilities.json").read_text(encoding="utf-8"))
    assert _as_tuple(manifest["min_version"]) <= _as_tuple(_pyproject_version())


# ─── Headline counts ─────────────────────────────────────────────────────────


def _cli_commands() -> int:
    from geo_optimizer.cli.main import cli

    return len(cli.commands)


def _mcp_tools() -> int:
    # Parsed, not imported: the mcp extra is optional.
    tree = ast.parse((ROOT / "src/geo_optimizer/mcp/server.py").read_text(encoding="utf-8"))

    def is_tool(d: ast.expr) -> bool:
        target = d.func if isinstance(d, ast.Call) else d
        return isinstance(target, ast.Attribute) and target.attr == "tool"

    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(is_tool(d) for d in node.decorator_list)
    )


def _ai_bots() -> int:
    from geo_optimizer.models.config import AI_BOTS

    return len(AI_BOTS)


def _default_categories() -> int:
    from geo_optimizer.models.config import CATEGORY_MAX_BY_VERSION, DEFAULT_SCORE_VERSION

    return len(CATEGORY_MAX_BY_VERSION[DEFAULT_SCORE_VERSION])


def _audit_formats() -> int:
    from geo_optimizer.cli.audit_cmd import audit

    (option,) = [p for p in audit.params if p.name == "output_format"]
    assert isinstance(option.type, click.Choice)
    return len(option.type.choices)


# Files whose headline numbers describe the current release. docs/discussions-launch.md is a
# dated launch post and is deliberately not scanned.
_SCANNED = [
    "README.md",
    "SKILL.md",
    "site/index.md",
    *sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "docs").glob("*.md")),
]
_SCANNED = [f for f in _SCANNED if f != "docs/discussions-launch.md"]

_CLAIMS = [
    ("CLI commands", re.compile(r"\b(\d+) CLI commands\b"), _cli_commands),
    ("MCP tools", re.compile(r"\b(\d+) MCP tools\b"), _mcp_tools),
    ("AI crawlers/bots", re.compile(r"\b(\d+) AI (?:crawlers|bots)\b"), _ai_bots),
    ("scoring categories", re.compile(r"\b(\d+) scoring categories\b"), _default_categories),
    ("output formats", re.compile(r"\b(\d+) output formats\b"), _audit_formats),
]


@pytest.mark.parametrize(("label", "pattern", "source"), _CLAIMS, ids=[c[0] for c in _CLAIMS])
def test_documented_counts_match_code(label, pattern, source):
    expected = source()
    found = []
    for name in _SCANNED:
        path = ROOT / name
        if not path.is_file():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            found += [(f"{name}:{lineno}", int(m.group(1))) for m in pattern.finditer(line)]
    assert found, f"no '{label}' claim found in {_SCANNED}"
    wrong = [(where, n) for where, n in found if n != expected]
    assert not wrong, f"{label}: code has {expected}, docs say {wrong}"
