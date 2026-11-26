"""Shared conformance cases (``conformance/*.json``): the Python engine and the JS core must agree.

The same files are run by ``integrations/core/test/conformance.test.mjs``. A case lists the engines that run it:
rules the Python engine has no counterpart for (sitemap checks) carry ``"engines": ["js"]`` and are skipped here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from geo_optimizer.core.audit_google_ai import check_canonical, parse_robots_directives
from geo_optimizer.utils.robots_parser import classify_bot, parse_robots_txt

CONFORMANCE = Path(__file__).resolve().parent.parent / "conformance"


def _cases():
    for path in sorted(CONFORMANCE.glob("*.json")):
        suite = json.loads(path.read_text(encoding="utf-8"))
        for case in suite["cases"]:
            if "python" in case["engines"]:
                yield pytest.param(suite["rule"], case, id=f"{suite['rule']}: {case['name']}")


def _robots(inp):
    rules = parse_robots_txt(inp["robots"])
    status = classify_bot(inp["bot"], "", rules, page_path=inp["path"], wildcards=True).status
    return {"blocked": status == "blocked"}


def _canonical(inp):
    soup = BeautifulSoup(inp["html"], "html.parser")
    directives = parse_robots_directives(soup, {})
    return {"status": check_canonical(soup, inp["url"], directives).status}


def _jsonld(inp):
    try:
        json.loads(inp["block"])
    except json.JSONDecodeError:
        return {"valid": False}
    return {"valid": True}


RUNNERS = {"robots-ai-bots": _robots, "canonical": _canonical, "jsonld-valid": _jsonld}


@pytest.mark.parametrize(("rule", "case"), _cases())
def test_python_engine_matches_the_shared_case(rule, case):
    assert RUNNERS[rule](case["input"]) == case["expect"]


def test_every_python_case_has_a_runner():
    rules = {rule for rule, _ in (p.values for p in _cases())}
    assert rules <= set(RUNNERS)
