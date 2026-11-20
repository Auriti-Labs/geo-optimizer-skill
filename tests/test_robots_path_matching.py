"""Measurement of how robots.txt path rules are applied (RFC 9309 §2.2.2 and §2.2.3).

Two gaps are pinned as strict xfail, so the day one is fixed the test fails and says so:
  - the audit judges a bot at the root path only: `Disallow: /blog/` still reads as "allowed";
  - `*` and `$` in a rule path are treated as literal text, although RFC 9309 §2.2.3 defines them.
Fixing the first changes how a bot status is derived and so can move scores: it needs a decision on
score_version before it is done. These tests change no behaviour.
"""

from __future__ import annotations

import pytest

from geo_optimizer.utils.robots_parser import _is_path_allowed, classify_bot, parse_robots_txt


def _rules(text: str, bot: str = "GPTBot"):
    return parse_robots_txt(text)[bot]


def test_subpath_rule_is_understood_by_the_matcher():
    rules = _rules("User-agent: GPTBot\nDisallow: /blog/\n")
    assert _is_path_allowed("/blog/post", rules) is False
    assert _is_path_allowed("/docs/a", rules) is None


def test_longest_match_allow_beats_disallow_root():
    rules = _rules("User-agent: GPTBot\nDisallow: /\nAllow: /docs/\n")
    assert _is_path_allowed("/docs/a", rules) is True
    assert _is_path_allowed("/blog/post", rules) is False


def test_root_only_status_today_for_a_subpath_block():
    # Measured current behaviour: the bot is called allowed because only "/" is evaluated.
    status = classify_bot("GPTBot", "", parse_robots_txt("User-agent: GPTBot\nDisallow: /blog/\n"))
    assert status.status == "allowed"


@pytest.mark.xfail(strict=True, reason="status is derived from the root path only; /blog/ is blocked but not reported")
def test_subpath_block_should_not_read_as_fully_allowed():
    status = classify_bot("GPTBot", "", parse_robots_txt("User-agent: GPTBot\nDisallow: /blog/\n"))
    assert status.status != "allowed"


@pytest.mark.xfail(strict=True, reason="RFC 9309 §2.2.3: '*' matches any run of characters, here it is literal")
@pytest.mark.parametrize(
    ("rule", "path"),
    [("/private*", "/private/x"), ("/*/post", "/a/post")],
)
def test_star_wildcard_should_match(rule: str, path: str):
    assert _is_path_allowed(path, _rules(f"User-agent: GPTBot\nDisallow: {rule}\n")) is False


@pytest.mark.xfail(strict=True, reason="RFC 9309 §2.2.3: '$' anchors the end of the path, here it is literal")
def test_dollar_anchor_should_match():
    assert _is_path_allowed("/file.pdf", _rules("User-agent: GPTBot\nDisallow: /*.pdf$\n")) is False
