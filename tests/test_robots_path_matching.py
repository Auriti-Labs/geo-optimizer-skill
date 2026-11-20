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


# ── hostile and equivalence checks for the wildcard matcher ──────────────────


def test_many_stars_do_not_backtrack():
    """A regex built from this rule takes minutes on this path; the matcher answers at once."""
    import time

    rules = _rules("User-agent: GPTBot\nDisallow: /" + "a*" * 12 + "b\n")
    started = time.perf_counter()
    assert _is_path_allowed("/" + "a" * 5000, rules, wildcards=True) is None
    assert time.perf_counter() - started < 1.0


def test_matcher_agrees_with_a_regex_reference():
    """Exhaustive over a small alphabet: the two-pointer matcher equals the regex it replaces."""
    import itertools
    import re

    from geo_optimizer.utils.robots_parser import _rule_matches

    def reference(rule: str, path: str) -> bool:
        anchored = rule.endswith("$")
        body = rule[:-1] if anchored else rule
        pattern = ".*".join(re.escape(p) for p in body.split("*")) + (r"\Z" if anchored else "")
        return re.match(pattern, path, re.DOTALL) is not None

    rule_chars, path_chars = "ab*$", "ab"
    rules = ["".join(c) for n in range(1, 6) for c in itertools.product(rule_chars, repeat=n)]
    paths = ["".join(c) for n in range(0, 7) for c in itertools.product(path_chars, repeat=n)]
    for rule in rules:
        for path in paths:
            assert _rule_matches(rule, path, wildcards=True) == reference(rule, path), (rule, path)


def test_home_page_keeps_the_partial_status_in_v5():
    """Disallow: / with a specific Allow is "partial" for the site, on the home page as before."""
    parsed = _parsed("User-agent: GPTBot\nDisallow: /\nAllow: /public/\n")
    assert classify_bot("GPTBot", "", parsed).status == "partial"
    assert classify_bot("GPTBot", "", parsed, page_path="/", wildcards=True).status == "partial"
    assert classify_bot("GPTBot", "", parsed, page_path="/public/a", wildcards=True).status == "allowed"
    assert classify_bot("GPTBot", "", parsed, page_path="/private", wildcards=True).status == "blocked"


def test_root_with_wildcards_uses_rfc_matching():
    parsed = _parsed("User-agent: GPTBot\nDisallow: /*\n")
    assert classify_bot("GPTBot", "", parsed, page_path="/", wildcards=True).status == "blocked"


@pytest.mark.parametrize(
    ("rule", "path", "expected"),
    [
        ("/caf%C3%A9", "/café", False),  # raw non-ASCII path against an escaped rule
        ("/café", "/caf%C3%A9", False),  # and the other way round
        ("/a%2fb", "/a%2Fb", False),  # hex case does not matter
        ("/%7Euser", "/~user", False),  # an escaped unreserved character is the character
        ("/a%2Fb", "/a/b", None),  # but %2F is not "/"
    ],
)
def test_percent_encoding_is_normalised_with_wildcards(rule: str, path: str, expected):
    rules = _rules(f"User-agent: GPTBot\nDisallow: {rule}\n")
    assert _is_path_allowed(path, rules, wildcards=True) is expected


def test_default_matching_does_not_normalise():
    rules = _rules("User-agent: GPTBot\nDisallow: /caf%C3%A9\n")
    assert _is_path_allowed("/café", rules) is None  # rubrics v1-v4 unchanged
