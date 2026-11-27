"""Le due composite Action rifiutano un audit non valido, anche con soglia disattivata.

La validazione vive in un solo script condiviso, ``scripts/action_audit.py``. I test lo eseguono
direttamente (contratto) e poi eseguono con bash gli step estratti dagli YAML reali, con
``GEO_ACTION_PATH`` impostato alla cartella dell'Action come farebbe il runner: così si prova
anche che entrambe le Action trovano e invocano lo script. Il comando ``geo`` della legacy è uno stub.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "action_audit.py"
ROOT_ACTION = "action.yml"
LEGACY_ACTION = ".github/actions/geo-audit/action.yml"


def _action_path(action: str) -> pathlib.Path:
    """Valore di ``github.action_path``: la cartella che contiene l'action.yml."""
    return (REPO / action).parent


def _step(action: str, name: str) -> dict:
    steps = yaml.safe_load((REPO / action).read_text(encoding="utf-8"))["runs"]["steps"]
    return next(step for step in steps if step.get("name") == name)


def _step_script(action: str, name: str) -> str:
    return _step(action, name)["run"]


def _body(payload) -> str:
    return payload[4:] if isinstance(payload, str) else json.dumps(payload)


def _bash(script, cwd, extra):
    env = {**os.environ, **extra}
    return subprocess.run(["bash", "-eo", "pipefail", "-c", script], cwd=cwd, env=env, capture_output=True, text=True)


def _script(*args, cwd=None):
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True)


def _run_script(tmp_path, payload):
    report = tmp_path / "report.json"
    if payload is not None:
        report.write_text(_body(payload))
    out = tmp_path / "out"
    out.write_text("")
    result = _script("extract", "--", str(report), str(out))
    return result.returncode, out.read_text()


def _run_root(tmp_path, payload):
    if payload is not None:
        (tmp_path / "geo-score-tmp.json").write_text(_body(payload))
    out = tmp_path / "out"
    out.write_text("")
    extra = {"GITHUB_OUTPUT": str(out), "GEO_ACTION_PATH": str(_action_path(ROOT_ACTION))}
    result = _bash(_step_script(ROOT_ACTION, "Extract score and band"), tmp_path, extra)
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
    extra = {
        "GITHUB_OUTPUT": str(out),
        "GEO_URL": "https://example.com",
        "GEO_ACTION_PATH": str(_action_path(LEGACY_ACTION)),
        "PATH": f"{bindir}:{os.environ['PATH']}",
    }
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
RUNNERS = [
    pytest.param(_run_script, id="script"),
    pytest.param(_run_root, id="root"),
    pytest.param(_run_legacy, id="legacy"),
]


# --- percorso dello script ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("action", "prefix"),
    [(ROOT_ACTION, "$GEO_ACTION_PATH/"), (LEGACY_ACTION, "$GEO_ACTION_PATH/../../../")],
    ids=["root", "legacy"],
)
def test_every_step_that_calls_the_script_resolves_it_from_the_action_path(action, prefix):
    steps = yaml.safe_load((REPO / action).read_text(encoding="utf-8"))["runs"]["steps"]
    callers = [step for step in steps if "action_audit.py" in step.get("run", "")]
    assert len(callers) == 2, "extract and threshold both go through the shared script"
    for step in callers:
        # Il percorso arriva dal runner via env, mai interpolato nello script
        assert step["env"]["GEO_ACTION_PATH"] == "${{ github.action_path }}"
        assert "${{" not in step["run"]
        paths = re.findall(r'"([^"]*action_audit\.py)"', step["run"])
        assert paths == [f"{prefix}scripts/action_audit.py"]
        resolved = pathlib.Path(paths[0].replace("$GEO_ACTION_PATH", str(_action_path(action)))).resolve()
        assert resolved == SCRIPT.resolve()
        assert resolved.is_file()


@pytest.mark.parametrize("action", [ROOT_ACTION, LEGACY_ACTION])
def test_no_action_keeps_an_inline_copy_of_the_validation(action):
    text = (REPO / action).read_text(encoding="utf-8")
    assert "<<'PY'" not in text
    assert "math.isfinite" not in text


# --- estrazione di score e band -----------------------------------------------------------


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


@pytest.mark.parametrize("payload", INVALID, ids=str)
def test_the_script_writes_nothing_and_explains_why_on_an_invalid_report(payload, tmp_path):
    report = tmp_path / "report.json"
    if payload is not None:
        report.write_text(_body(payload))
    out = tmp_path / "out"
    out.write_text("")
    result = _script("extract", "--", str(report), str(out))
    assert result.returncode == 2
    assert out.read_text() == ""
    assert "invalid audit result" in result.stderr


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


@pytest.mark.parametrize("band", ["a=b", "", None, "x" * 33, "good bad"])
def test_an_unsafe_or_missing_band_is_exported_as_unknown(band, tmp_path):
    code, out = _run_script(tmp_path, {"score": 50, "band": band})
    assert code == 0
    assert out == "score=50\nband=unknown\n"


def test_the_outputs_keep_the_format_of_each_action(tmp_path):
    root_dir, legacy_dir = tmp_path / "root", tmp_path / "legacy"
    root_dir.mkdir()
    legacy_dir.mkdir()
    _, root_out = _run_root(root_dir, {"score": 70, "band": "good"})
    _, legacy_out = _run_legacy(legacy_dir, {"score": 70, "band": "good"})
    assert root_out == "score=70\nband=good\n"
    assert legacy_out == "score=70\nband=good\nreport=geo-audit-report.json\n"

    report = tmp_path / "r.json"
    report.write_text(json.dumps({"score": 70, "band": "good"}))
    out = tmp_path / "o"
    assert _script("extract", "--notice", "--", str(report), str(out)).stdout == "::notice::GEO Score: 70/100 (good)\n"
    assert _script("extract", "--", str(report), str(out)).stdout == "GEO Score: 70/100 (good)\n"


# --- confronto con la soglia --------------------------------------------------------------

THRESHOLD_CASES = [
    ("70", "70", 0),
    ("100", "70", 0),
    ("69.5", "70", 1),
    ("0", "1", 1),
    ("nan", "70", 2),
    ("inf", "70", 2),
    ("-inf", "70", 2),
    ("101", "70", 2),
    ("-1", "70", 2),
    ("abc", "70", 2),
    ("", "70", 2),
]


@pytest.mark.parametrize(("score", "minimum", "expected"), THRESHOLD_CASES)
def test_the_threshold_comparator_has_three_distinct_outcomes(score, minimum, expected):
    assert _script("threshold", "--", score, minimum).returncode == expected


def _run_threshold_step(action, name, tmp_path, score, minimum):
    extra = {"GEO_ACTION_PATH": str(_action_path(action)), "GEO_SCORE": score}
    if action == ROOT_ACTION:
        extra.update({"IN_MIN_SCORE": minimum, "IN_THRESHOLD": "0"})
    else:
        extra["GEO_MIN_SCORE"] = minimum
    return _bash(_step_script(action, name), tmp_path, extra)


STEPS = [
    pytest.param(ROOT_ACTION, "Check score threshold", id="root"),
    pytest.param(LEGACY_ACTION, "Check minimum score", id="legacy"),
]


@pytest.mark.parametrize(("action", "name"), STEPS)
@pytest.mark.parametrize(("score", "minimum", "expected"), THRESHOLD_CASES)
def test_both_threshold_steps_fail_unless_the_score_meets_the_minimum(action, name, score, minimum, expected, tmp_path):
    result = _run_threshold_step(action, name, tmp_path, score, minimum)
    assert (result.returncode == 0) == (expected == 0)
    if expected == 2:
        assert "is not a number between 0 and 100" in result.stdout


@pytest.mark.parametrize(("action", "name"), STEPS)
def test_a_threshold_of_zero_skips_the_comparison(action, name, tmp_path):
    assert _run_threshold_step(action, name, tmp_path, "nan", "0").returncode == 0


@pytest.mark.parametrize("action", [ROOT_ACTION, LEGACY_ACTION])
def test_the_script_runs_in_isolated_mode_and_the_root_step_prints_a_notice(action):
    steps = yaml.safe_load((REPO / action).read_text(encoding="utf-8"))["runs"]["steps"]
    callers = [step["run"] for step in steps if "action_audit.py" in step.get("run", "")]
    assert all("python3 -I " in run for run in callers), "-I: ignore PYTHONPATH and the user's cwd"
    if action == ROOT_ACTION:
        assert any(" extract --notice " in run for run in callers)


def test_a_report_nested_too_deep_is_invalid_not_a_traceback(tmp_path):
    report = tmp_path / "deep.json"
    report.write_text("[" * 100000, encoding="utf-8")
    out = tmp_path / "out"
    done = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), "extract", str(report), str(out)],
        capture_output=True,
        text=True,
    )
    assert done.returncode == 2
    assert "Traceback" not in done.stderr
    assert not out.exists()
