"""Rubric v3: robots.txt is scored as access, not as the presence of a file.

Everything else in v3 is v2's. v2 stays the default and keeps its numbers.
"""

from __future__ import annotations

import pytest

from geo_optimizer.core.audit import build_categorized_recommendations
from geo_optimizer.core.scoring import _score_robots
from geo_optimizer.models.config import (
    CATEGORY_MAX_BY_VERSION,
    DEFAULT_SCORE_VERSION,
    ROBOTS_PARTIAL_BY_VERSION,
    SCORING_BY_VERSION,
)
from geo_optimizer.models.results import (
    ContentResult,
    LlmsTxtResult,
    MetaResult,
    RobotsResult,
    SchemaResult,
)


def _score(robots: RobotsResult, version: int) -> int:
    return _score_robots(robots, SCORING_BY_VERSION[version], ROBOTS_PARTIAL_BY_VERSION[version])


ABSENT = RobotsResult(found=False, status_code=404)  # no robots.txt: crawlers may fetch everything
WILDCARD = RobotsResult(found=True, bots_allowed=["GPTBot"], citation_bots_ok=True, citation_bots_explicit=False)
EXPLICIT = RobotsResult(found=True, bots_allowed=["GPTBot"], citation_bots_ok=True, citation_bots_explicit=True)
SOME = RobotsResult(found=True, bots_allowed=["GPTBot"], bots_blocked=["ClaudeBot"], citation_bots_ok=False)
BLOCKED = RobotsResult(found=True, bots_blocked=["GPTBot", "ClaudeBot"], citation_bots_ok=False)
UNREADABLE = RobotsResult(found=False, status_code=503)  # server error: crawlers assume a full block
# a file with no rule for any AI bot (empty, or only a Sitemap line): every bot is "missing"
NO_AI_RULES = RobotsResult(found=True, bots_missing=["GPTBot", "ClaudeBot"], citation_bots_ok=False)


class TestVersionTable:
    def test_default_stays_v2(self):
        assert DEFAULT_SCORE_VERSION == 2

    def test_v3_keeps_the_v2_category_budget(self):
        assert CATEGORY_MAX_BY_VERSION[3] == CATEGORY_MAX_BY_VERSION[2]

    def test_v3_changes_only_robots_weights(self):
        v2, v3 = SCORING_BY_VERSION[2], SCORING_BY_VERSION[3]
        changed = {k for k in v2.keys() | v3.keys() if v2.get(k) != v3.get(k)}
        assert changed == {"robots_found", "robots_citation_ok", "robots_absent_ok", "robots_wildcard_full"}


class TestRobotsScore:
    @pytest.mark.parametrize(
        ("robots", "v2", "v3"),
        [
            (ABSENT, 0, 14),  # a missing file restricts nothing
            (WILDCARD, 11, 14),  # wildcard permission is as good as an explicit one
            (EXPLICIT, 14, 14),
            (SOME, 11, 11),  # only some bots allowed: partial in both
            (BLOCKED, 3, 0),  # v2 paid 3 points for the file existing
            (NO_AI_RULES, 3, 14),  # restricts nothing, same as a missing file
            (UNREADABLE, 0, 0),  # could not be read: no points in v3
        ],
    )
    def test_v2_unchanged_and_v3_scores_access(self, robots, v2, v3):
        assert _score(robots, 2) == v2
        assert _score(robots, 3) == v3

    def test_v3_never_exceeds_the_category_maximum(self):
        for robots in (ABSENT, WILDCARD, EXPLICIT, SOME, BLOCKED, NO_AI_RULES, UNREADABLE):
            assert _score(robots, 3) <= CATEGORY_MAX_BY_VERSION[3]["robots"]


class TestRecommendation:
    def _recs(self, robots: RobotsResult, version: int) -> list[str]:
        recs = build_categorized_recommendations(
            "https://example.com",
            robots,
            LlmsTxtResult(),
            SchemaResult(),
            MetaResult(),
            ContentResult(),
            score_version=version,
        )
        return [text for category, text in recs if category == "robots"]

    def test_missing_robots_is_a_finding_in_v2_only(self):
        assert any("Create robots.txt" in t for t in self._recs(ABSENT, 2))
        assert not any("Create robots.txt" in t for t in self._recs(ABSENT, 3))

    def test_restricted_bots_still_a_finding_in_v3(self):
        assert any("Update robots.txt" in t for t in self._recs(BLOCKED, 3))


class TestFromRealRobotsFiles:
    """Parse real robots.txt text, so the scorer is checked against the parser's output."""

    @staticmethod
    def _score_text(text: str, version: int) -> int:
        from unittest.mock import Mock

        from geo_optimizer.core.audit_robots import _audit_robots_from_response

        response = Mock(status_code=200, text=text)
        return _score(_audit_robots_from_response(response), version)

    @pytest.mark.parametrize(
        ("text", "v3"),
        [
            ("", 14),
            ("Sitemap: https://example.com/sitemap.xml\n", 14),
            ("User-agent: *\nDisallow: /wp-admin/\n", 14),
            ("User-agent: *\nDisallow: /\n", 0),
        ],
    )
    def test_v3(self, text, v3):
        assert self._score_text(text, 3) == v3


class TestEndToEnd:
    def test_breakdown_robots_for_version_3(self):
        from geo_optimizer.core.scoring import compute_score_breakdown

        args = {"llms": LlmsTxtResult(), "schema": SchemaResult(), "meta": MetaResult(), "content": ContentResult()}
        assert compute_score_breakdown(ABSENT, version=3, **args)["robots"] == 14
        assert compute_score_breakdown(ABSENT, version=2, **args)["robots"] == 0

    def test_cli_accepts_score_version_3(self):
        from geo_optimizer.cli.audit_cmd import audit

        option = next(p for p in audit.params if p.name == "score_version")
        assert "3" in option.type.choices

    def test_fixer_estimate_uses_the_version_scorer(self):
        from geo_optimizer.core.fixer import FixItem, _estimate_score_after
        from geo_optimizer.models.results import AuditResult

        fix = [FixItem(category="robots", description="d", content="c", file_name="robots.txt", action="create")]
        result = AuditResult(url="https://example.com", score=50, score_version=3, robots=ABSENT)
        assert _estimate_score_after(result, fix) == 50  # already full in v3: nothing to gain


class TestUnreadableRobots:
    """RFC 9309: a 4xx means no robots.txt (everything may be fetched); 5xx, 429 or no response means unknown."""

    @pytest.mark.parametrize(
        ("status", "v3"), [(404, 14), (410, 14), (403, 14), (401, 14), (429, 0), (500, 0), (503, 0), (0, 0)]
    )
    def test_missing_file_score_follows_the_status(self, status, v3):
        robots = RobotsResult(found=False, status_code=status)
        assert _score(robots, 3) == v3
        assert _score(robots, 2) == 0  # v2 never gave points for a missing file

    @pytest.mark.parametrize(("status", "found"), [(200, True), (404, False), (503, False), (429, False)])
    def test_parser_records_the_status(self, status, found):
        from unittest.mock import Mock

        from geo_optimizer.core.audit_robots import _audit_robots_from_response

        # requests.Response is falsy for 4xx/5xx: the status must survive that
        response = Mock(status_code=status, text="User-agent: *\nAllow: /\n")
        response.__bool__ = lambda self: status < 400
        result = _audit_robots_from_response(response)
        assert (result.status_code, result.found) == (status, found)

    def test_no_response_at_all_is_status_zero(self):
        from geo_optimizer.core.audit_robots import _audit_robots_from_response

        assert _audit_robots_from_response(None).status_code == 0

    def _recs(self, robots: RobotsResult) -> list[str]:
        from geo_optimizer.core.audit import build_categorized_recommendations

        recs = build_categorized_recommendations(
            "https://example.com",
            robots,
            LlmsTxtResult(),
            SchemaResult(),
            MetaResult(),
            ContentResult(),
            score_version=3,
        )
        return [text for category, text in recs if category == "robots"]

    def test_unreadable_robots_is_a_finding_in_v3_but_a_missing_one_is_not(self):
        assert self._recs(ABSENT) == []
        assert any("could not be read (HTTP 503)" in t for t in self._recs(UNREADABLE))
        assert any("no response" in t for t in self._recs(RobotsResult(found=False, status_code=0)))
