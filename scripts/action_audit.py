"""Shared validation for the two composite GitHub Actions (``action.yml`` and ``.github/actions/geo-audit``).

Both Actions call this script instead of carrying their own copy of the checks. Standard library only,
Python 3.9+, so it runs on whatever interpreter ``actions/setup-python`` installed.

Subcommands:

  extract REPORT GITHUB_OUTPUT [--notice] [--export-report]
      Read the JSON report, validate score and band, append ``score=`` and ``band=`` to GITHUB_OUTPUT
      (plus ``report=REPORT`` with ``--export-report``). Exit 0 when valid, 2 when the report is missing
      or unparsable, is not an object, carries an ``error`` field, or the score is missing, boolean,
      not a number, not finite or outside 0-100. Nothing is written on failure: no fallback score.
      A band that is not a short safe token (newline, ``=``, ...) is exported as ``unknown``.

  threshold SCORE MIN_SCORE
      Exit 0 when SCORE meets MIN_SCORE, 1 when it is below, 2 when SCORE is not a finite number
      between 0 and 100 (a score that cannot be read never counts as "threshold met").

``report`` is a path chosen by the calling YAML (a fixed file name), never user input: it is only echoed
back as ``report=``. The legacy action reaches this script through ``$GEO_ACTION_PATH/../../..``, so a copy
of ``.github/actions/geo-audit`` taken without ``scripts/`` fails closed (missing file, non-zero exit).

The calling step prints the user-facing ``::error::`` annotation from the exit code; this script only
writes the specific reason to stderr.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys

EXIT_OK = 0
EXIT_BELOW = 1
EXIT_INVALID = 2

_SAFE_BAND = re.compile(r"[A-Za-z0-9_-]{1,32}")


class InvalidReport(Exception):
    """The report cannot provide a trustworthy score."""


def _valid_score(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value) and 0 <= value <= 100


def read_report(path: str) -> tuple[int | float, str]:
    """Return ``(score, band)`` from the report at ``path`` or raise :class:`InvalidReport`."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError, RecursionError, MemoryError) as exc:
        raise InvalidReport(f"cannot read a JSON report from {path!r}: {type(exc).__name__}") from exc
    if not isinstance(data, dict):
        raise InvalidReport("the report is not a JSON object")
    if data.get("error"):
        raise InvalidReport("the report carries an error field")
    score = data.get("score")
    if not _valid_score(score):
        raise InvalidReport(f"score {repr(score)[:40]} is not a number between 0 and 100")
    band = str(data.get("band") or "unknown")
    if not _SAFE_BAND.fullmatch(band):
        band = "unknown"
    return score, band


def extract(report: str, github_output: str, notice: bool = False, export_report: bool = False) -> int:
    try:
        score, band = read_report(report)
    except InvalidReport as exc:
        print(f"invalid audit result: {exc}", file=sys.stderr)
        return EXIT_INVALID
    lines = f"score={score}\nband={band}\n"
    if export_report:
        lines += f"report={report}\n"
    with open(github_output, "a", encoding="utf-8") as out:
        out.write(lines)
    prefix = "::notice::" if notice else ""
    print(f"{prefix}GEO Score: {score}/100 ({band})")
    return EXIT_OK


def threshold(score: str, min_score: str) -> int:
    try:
        value = float(score)
    except ValueError:
        print(f"score {score!r} is not a number", file=sys.stderr)
        return EXIT_INVALID
    if not _valid_score(value):
        print(f"score {score!r} is not a finite number between 0 and 100", file=sys.stderr)
        return EXIT_INVALID
    return EXIT_BELOW if value < float(min_score) else EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_extract = sub.add_parser("extract", help="validate the report and export score and band")
    p_extract.add_argument("report")
    p_extract.add_argument("github_output")
    p_extract.add_argument("--notice", action="store_true", help="print the score as a ::notice:: annotation")
    p_extract.add_argument("--export-report", action="store_true", help="also export report=<path>")

    p_threshold = sub.add_parser("threshold", help="compare a score with the minimum score")
    p_threshold.add_argument("score")
    p_threshold.add_argument("min_score")

    args = parser.parse_args(argv)
    if args.command == "extract":
        return extract(args.report, args.github_output, notice=args.notice, export_report=args.export_report)
    return threshold(args.score, args.min_score)


if __name__ == "__main__":
    sys.exit(main())
