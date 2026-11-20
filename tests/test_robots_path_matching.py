"""How robots.txt path rules are applied (RFC 9309 §2.2.2 and §2.2.3).

Default behaviour (rubrics v1 to v4) is pinned: a bot is judged on the root path, and ``*`` and ``$`` in a rule
are ordinary characters. The opt-in behaviour (``page_path`` / ``wildcards``, used by rubric v5) judges the bot
on the page and applies RFC 9309 wildcard matching.
"""

from __future__ import annotations

import pytest

from geo_optimizer.utils.robots_parser import _is_path_allowed, classify_bot, parse_robots_txt


def _parsed(text: str):
    return parse_robots_txt(text)


def _rules(text: str, bot: str = "GPTBot"):
    return _parsed(text)[bot]


# ── default behaviour, unchanged ─────────────────────────────────────────────


def test_subpath_rule_is_understood_by_the_matcher():
    rules = _rules("User-agent: GPTBot\nDisallow: /blog/\n")
    assert _is_path_allowed("/blog/post", rules) is False
    assert _is_path_allowed("/docs/a", rules) is None


def test_longest_match_allow_beats_disallow_root():
    rules = _rules("User-agent: GPTBot\nDisallow: /\nAllow: /docs/\n")
    assert _is_path_allowed("/docs/a", rules) is True
    assert _is_path_allowed("/blog/post", rules) is False


def test_default_status_reads_the_root_only():
    # Rubrics v1-v4: a block on /blog/ does not change the bot's status.
    assert classify_bot("GPTBot", "", _parsed("User-agent: GPTBot\nDisallow: /blog/\n")).status == "allowed"


def test_default_treats_star_and_dollar_as_literal():
    assert _is_path_allowed("/private/x", _rules("User-agent: GPTBot\nDisallow: /private*\n")) is None
    assert _is_path_allowed("/file.pdf", _rules("User-agent: GPTBot\nDisallow: /*.pdf$\n")) is None


# ── opt-in: judged on the page, RFC 9309 matching ────────────────────────────


def test_page_path_blocked_by_subpath_rule():
    parsed = _parsed("User-agent: GPTBot\nDisallow: /blog/\n")
    assert classify_bot("GPTBot", "", parsed, page_path="/blog/post").status == "blocked"
    assert classify_bot("GPTBot", "", parsed, page_path="/docs/a").status == "allowed"


def test_page_path_allow_overrides_a_wider_disallow():
    parsed = _parsed("User-agent: GPTBot\nDisallow: /\nAllow: /docs/\n")
    assert classify_bot("GPTBot", "", parsed, page_path="/docs/a").status == "allowed"
    assert classify_bot("GPTBot", "", parsed, page_path="/blog/p").status == "blocked"


def test_missing_agent_stays_missing_with_a_page_path():
    parsed = _parsed("User-agent: Googlebot\nDisallow: /blog/\n")
    assert classify_bot("GPTBot", "", parsed, page_path="/blog/p").status == "missing"


@pytest.mark.parametrize(
    ("rule", "path", "expected"),
    [
        ("/private*", "/private/x", False),
        ("/private*", "/public/x", None),
        ("/*/post", "/a/post", False),
        ("/*/post", "/a/other", None),
        ("/*.pdf$", "/file.pdf", False),
        ("/*.pdf$", "/file.pdf?x=1", None),
        ("/*.pdf$", "/file.pdfx", None),
        ("/fish$", "/fish", False),
        ("/fish$", "/fish/salmon", None),
        ("/a.b", "/axb", None),  # a dot is a dot, not "any character"
    ],
)
def test_wildcards(rule: str, path: str, expected):
    rules = _rules(f"User-agent: GPTBot\nDisallow: {rule}\n")
    assert _is_path_allowed(path, rules, wildcards=True) is expected


def test_wildcard_longest_match_with_allow():
    rules = _rules("User-agent: GPTBot\nDisallow: /*.pdf$\nAllow: /public/*.pdf$\n")
    assert _is_path_allowed("/a/x.pdf", rules, wildcards=True) is False
    assert _is_path_allowed("/public/x.pdf", rules, wildcards=True) is True
