"""Le due composite Action rifiutano un audit non valido, anche con soglia disattivata.

Gli script vengono estratti dagli YAML reali ed eseguiti con bash; il comando `geo` della legacy è uno stub.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent
ROOT_ACTION = "action.yml"
LEGACY_ACTION = ".github/actions/geo-audit/action.yml"


def _step_script(action: str, name: str) -> str:
    steps = yaml.safe_load((REPO / action).read_text(encoding="utf-8"))["runs"]["steps"]
    return next(step for step in steps if step.get("name") == name)["run"]


def _body(payload) -> str:
    return payload[4:] if isinstance(payload, str) else json.dumps(payload)


def _bash(script, cwd, extra):
    env = {**os.environ, **extra}
    return subprocess.run(["bash", "-eo", "pipefail", "-c", script], cwd=cwd, env=env, capture_output=True, text=True)


def _run_root(tmp_path, payload):
    if payload is not None:
        (tmp_path / "geo-score-tmp.json").write_text(_body(payload))
    out = tmp_path / "out"
    out.write_text("")
    result = _bash(_step_script(ROOT_ACTION, "Extract score and band"), tmp_path, {"GITHUB_OUTPUT": str(out)})
    return result.returncode, out.read_text()


def _run_legacy(tmp_path, payload, audit_rc=0):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    write = "" if payload is None else f"cat > \"$7\" <<'EOF'\n{_body(payload)}\nEOF\n"
    stub = bindir / "geo"
    stub.write_text(f"#!/bin/bash\n{write}exit {audit_rc}\n")
    stub.chmod(0o755)
    out = tmp_path / "out"
    out.write_text("")
    extra = {"GITHUB_OUTPUT": str(out), "GEO_URL": "https://example.com", "PATH": f"{bindir}:{os.environ['PATH']}"}
    result = _bash(_step_script(LEGACY_ACTION, "Run GEO Audit"), tmp_path, extra)
    return result.returncode, out.read_text()


VALID = [{"score": 70, "band": "good"}, {"score": 0, "band": "critical"}, {"score": 69.5, "band": "foundation"}]
INVALID = [
    {},
    {"error": "boom"},
    {"score": None},
    {"score": True},
    {"score": "70"},
    {"score": 101},
    {"score": -1},
    {"score": float("nan")},
    {"score": float("inf")},
    {"score": 50, "error": "x"},
    "raw:{bad",
    "raw:[1]",
    None,
]
RUNNERS = [pytest.param(_run_root, id="root"), pytest.param(_run_legacy, id="legacy")]


@pytest.mark.parametrize("runner", RUNNERS)
@pytest.mark.parametrize("payload", VALID, ids=str)
def test_a_valid_audit_passes_and_exports_score_and_band(runner, payload, tmp_path):
    code, out = runner(tmp_path, payload)
    assert code == 0
    assert f"score={payload['score']}\n" in out
    assert f"band={payload['band']}\n" in out


@pytest.mark.parametrize("runner", RUNNERS)
@pytest.mark.parametrize("payload", INVALID, ids=str)
def test_an_invalid_audit_fails_without_any_threshold(runner, payload, tmp_path):
    code, _ = runner(tmp_path, payload)
    assert code != 0


def test_the_legacy_action_distrusts_a_report_written_by_a_failed_cli(tmp_path):
    code, out = _run_legacy(tmp_path, {"score": 80, "band": "good"}, audit_rc=1)
    assert code != 0
    assert "score=0\n" in out and "band=error\n" in out


@pytest.mark.parametrize("runner", RUNNERS)
def test_a_band_with_a_newline_cannot_inject_another_output(runner, tmp_path):
    code, out = runner(tmp_path, {"score": 50, "band": "a\nscore=99"})
    assert code == 0
    assert "score=99" not in out
    assert "band=unknown\n" in out
