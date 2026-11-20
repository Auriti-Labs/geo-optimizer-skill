"""Tests for scripts/check_dist.py (synthetic archives, no build)."""

from __future__ import annotations

import importlib.util
import tarfile
import zipfile
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location("check_dist", Path(__file__).parent.parent / "scripts" / "check_dist.py")
check_dist = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check_dist)


def _wheel(tmp_path: Path, names: list[str]) -> Path:
    p = tmp_path / "pkg-1.0-py3-none-any.whl"
    with zipfile.ZipFile(p, "w") as zf:
        for n in names:
            zf.writestr(n, "x")
    return p


def _sdist(tmp_path: Path, names: list[str]) -> Path:
    p = tmp_path / "pkg-1.0.tar.gz"
    with tarfile.open(p, "w:gz") as tf:
        for n in names:
            f = tmp_path / "f.txt"
            f.write_text("x")
            tf.add(f, arcname=n)
    return p


def test_clean_archives_pass(tmp_path):
    assert check_dist.problems(_wheel(tmp_path, ["pkg/a.py", "pkg/loc/en.mo"])) == []
    assert check_dist.problems(_sdist(tmp_path, ["pkg-1.0/a.py"])) == []


def test_pycache_and_pyc_fail(tmp_path):
    assert check_dist.problems(_wheel(tmp_path, ["pkg/__pycache__/a.cpython-312.pyc"]))
    assert check_dist.problems(_sdist(tmp_path, ["pkg-1.0/a.pyc"]))


def test_po_source_fails(tmp_path):
    out = check_dist.problems(_wheel(tmp_path, ["pkg/loc/en.po"]))
    assert out and ".po" in out[0]


def test_oversize_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(check_dist, "MAX_BYTES", 10)
    assert any("limit" in m for m in check_dist.problems(_wheel(tmp_path, ["pkg/a.py"])))


def test_main_exit_codes(tmp_path):
    assert check_dist.main([str(_wheel(tmp_path, ["pkg/a.py"]))]) == 0
    assert check_dist.main([str(_sdist(tmp_path, ["pkg-1.0/x.pyc"]))]) == 1
    assert check_dist.main([]) == 1
