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


ABSENT = RobotsResult(found=False)
WILDCARD = RobotsResult(found=True, bots_allowed=["GPTBot"], citation_bots_ok=True, citation_bots_explicit=False)
EXPLICIT = RobotsResult(found=True, bots_allowed=["GPTBot"], citation_bots_ok=True, citation_bots_explicit=True)
SOME = RobotsResult(found=True, bots_allowed=["GPTBot"], bots_blocked=["ClaudeBot"], citation_bots_ok=False)
BLOCKED = RobotsResult(found=True, bots_blocked=["GPTBot", "ClaudeBot"], citation_bots_ok=False)


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
        ],
    )
    def test_v2_unchanged_and_v3_scores_access(self, robots, v2, v3):
        assert _score(robots, 2) == v2
        assert _score(robots, 3) == v3

    def test_v3_never_exceeds_the_category_maximum(self):
        for robots in (ABSENT, WILDCARD, EXPLICIT, SOME, BLOCKED):
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
