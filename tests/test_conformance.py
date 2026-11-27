"""Shared conformance cases (``conformance/*.json``): the Python engine and the JS core must agree.

The same files are run by ``integrations/core/test/conformance.test.mjs``. A case lists the engines that run it:
rules the Python engine has no counterpart for (sitemap checks) carry ``"engines": ["js"]`` and are skipped here.

The suite guards itself: a missing rule file, a file with no cases, a case with a missing, empty or unknown
``engines`` value, and a Python case that is declared but not collected all fail the run instead of being skipped.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from geo_optimizer.core.audit_google_ai import check_canonical, parse_robots_directives
from geo_optimizer.core.audit_schema import audit_schema
from geo_optimizer.utils.robots_parser import classify_bot, parse_robots_txt

CONFORMANCE = Path(__file__).resolve().parent.parent / "conformance"

# The rule files both runners expect. A missing file must fail, not shrink the suite.
EXPECTED_FILES = {
    "canonical.json": "canonical",
    "jsonld.json": "jsonld-valid",
    "robots.json": "robots-ai-bots",
    "sitemap-indexable.json": "sitemap-indexable",
    "sitemap.json": "sitemap-lastmod",
}
ENGINES = {"python", "js"}
# Rules the Python engine has no counterpart for: a case of these rules may not declare "python".
JS_ONLY_RULES = {"sitemap-indexable", "sitemap-lastmod"}


def _suites():
    return [(path, json.loads(path.read_text(encoding="utf-8"))) for path in sorted(CONFORMANCE.glob("*.json"))]


def _declares_python(case) -> bool:
    engines = case.get("engines")
    return isinstance(engines, list) and "python" in engines


def _cases():
    for _path, suite in _suites():
        for case in suite.get("cases") or []:
            if _declares_python(case):
                yield pytest.param(suite["rule"], case, id=f"{suite['rule']}: {case['name']}")


def _robots_text(robots):
    """`robots` is a string, or a list of `{text, repeat}` parts to join (fixtures over the 500 KiB limit)."""
    if isinstance(robots, list):
        return "".join(part["text"] * part["repeat"] for part in robots)
    return robots


def _robots(inp):
    rules = parse_robots_txt(_robots_text(inp["robots"]))
    status = classify_bot(inp["bot"], "", rules, page_path=inp["path"], wildcards=True).status
    return {"blocked": status == "blocked"}


def _canonical(inp):
    soup = BeautifulSoup(inp["html"], "html.parser")
    directives = parse_robots_directives(soup, {})
    return {"status": check_canonical(soup, inp["url"], directives).status}


def _jsonld(inp):
    if "html" in inp:
        # End to end: the same parser and extraction path the audit uses (audit.py builds an html.parser soup).
        soup = BeautifulSoup(inp["html"], "html.parser")
        return {"invalid": audit_schema(soup, inp.get("url", "https://example.com/")).json_parse_errors}
    try:
        json.loads(inp["block"])
    except json.JSONDecodeError:
        return {"valid": False}
    return {"valid": True}


RUNNERS = {"robots-ai-bots": _robots, "canonical": _canonical, "jsonld-valid": _jsonld}


def _declared_python() -> int:
    return sum(1 for _path, suite in _suites() for case in suite.get("cases") or [] if _declares_python(case))


def test_the_expected_rule_files_are_present():
    found = {path.name: suite.get("rule") for path, suite in _suites()}
    missing = sorted(set(EXPECTED_FILES) - set(found))
    assert not missing, f"conformance files missing: {missing}"
    assert found == EXPECTED_FILES, "conformance/ must hold exactly the expected files, each with its rule"


def test_every_file_has_cases():
    empty = [path.name for path, suite in _suites() if not isinstance(suite.get("cases"), list) or not suite["cases"]]
    assert not empty, f"conformance files with no cases: {empty}"


def test_every_case_declares_known_engines():
    bad = []
    for path, suite in _suites():
        for i, case in enumerate(suite.get("cases") or []):
            where = f"{path.name}#{i} {case.get('name')!r}"
            engines = case.get("engines")
            if not {"name", "input", "expect"} <= set(case):
                bad.append(f"{where}: missing name/input/expect")
            if not isinstance(engines, list) or not engines:
                bad.append(f"{where}: engines missing or empty")
                continue
            unknown = [e for e in engines if e not in ENGINES]
            if unknown:
                bad.append(f"{where}: unknown engines {unknown}")
            if len(set(engines)) != len(engines):
                bad.append(f"{where}: duplicate engines")
    assert not bad, "\n".join(bad)


def test_every_case_is_run_by_an_engine_that_has_a_runner():
    orphans = []
    for path, suite in _suites():
        for case in suite.get("cases") or []:
            if _declares_python(case) and (suite.get("rule") not in RUNNERS or suite.get("rule") in JS_ONLY_RULES):
                orphans.append(f"{path.name}: {case.get('name')!r} declares python but Python has no runner")
            if not any(e in ENGINES for e in case.get("engines") or []):
                orphans.append(f"{path.name}: {case.get('name')!r} is run by no engine")
    assert not orphans, "\n".join(orphans)


def test_every_python_case_has_a_runner():
    rules = {rule for rule, _ in (p.values for p in _cases())}
    assert rules <= set(RUNNERS)


def test_every_declared_python_case_is_collected():
    assert len(list(_cases())) == _declared_python()


@pytest.mark.parametrize(("rule", "case"), _cases())
def test_python_engine_matches_the_shared_case(rule, case):
    assert RUNNERS[rule](case["input"]) == case["expect"]
