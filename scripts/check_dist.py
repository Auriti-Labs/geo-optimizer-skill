"""Fail a release when a built sdist or wheel is not clean.

Run after ``python -m build``:  python scripts/check_dist.py dist/*

Checks, per archive:
  - the file is not larger than MAX_BYTES (a CLI has no business shipping megabytes);
  - no ``__pycache__`` directory and no ``.pyc`` file;
  - no ``.po`` source: only the compiled ``.mo`` belongs to the package (#135).
Exit code 0 when every archive passes, 1 otherwise. Standard library only.
"""

from __future__ import annotations

import sys
import tarfile
import zipfile
from pathlib import Path

MAX_BYTES = 5 * 1024 * 1024


def _names(path: Path) -> list[str]:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as zf:
            return zf.namelist()
    with tarfile.open(path) as tf:
        return tf.getnames()


def problems(path: Path) -> list[str]:
    """Return one message per problem found in ``path`` (empty list means clean)."""
    found: list[str] = []
    size = path.stat().st_size
    if size > MAX_BYTES:
        found.append(f"{path.name}: {size} bytes, over the {MAX_BYTES} limit")
    names = _names(path)
    if any("__pycache__" in n or n.endswith(".pyc") for n in names):
        found.append(f"{path.name}: contains __pycache__ or .pyc files")
    if any(n.endswith(".po") for n in names):
        found.append(f"{path.name}: contains .po sources (only .mo belongs in the package)")
    return found


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: check_dist.py <sdist-or-wheel> ...", file=sys.stderr)
        return 1
    bad = [msg for arg in argv for msg in problems(Path(arg))]
    for msg in bad:
        print(f"FAIL {msg}", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
