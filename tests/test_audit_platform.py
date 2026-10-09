from __future__ import annotations

from geo_optimizer.core.audit_platform import _score_google_ai
from geo_optimizer.models.results import (
    CitabilityResult,
    ContentResult,
    MetaResult,
    RobotsResult,
    SchemaResult,
)


def _google(robots: RobotsResult, schema: SchemaResult | None = None):
    return _score_google_ai(
        robots,
        schema or SchemaResult(),
        MetaResult(),
        ContentResult(),
        CitabilityResult(),
    )


def test_google_extended_does_not_score_and_is_not_recommended():
    only_ext = _google(RobotsResult(found=True, bots_allowed=["Google-Extended"]))
    neither = _google(RobotsResult(found=True))

    assert only_ext.score == neither.score
    assert not any("Google-Extended" in recommendation for recommendation in neither.recommendations)


def test_googlebot_allowed_scores():
    allowed = _google(RobotsResult(found=True, bots_allowed=["Googlebot"]))
    blocked = _google(RobotsResult(found=True, bots_blocked=["Googlebot"]))

    assert allowed.score - blocked.score == 10
    assert any("Googlebot" in recommendation for recommendation in blocked.recommendations)


def test_googlebot_missing_scores_same_as_allowed():
    allowed = _google(RobotsResult(found=True, bots_allowed=["Googlebot"]))
    missing = _google(RobotsResult(found=True, bots_missing=["Googlebot"]))

    assert missing.score == allowed.score


def test_max_richness_reaches_top_branch():
    rich = _google(RobotsResult(), SchemaResult(any_schema_found=True, schema_richness_score=3))
    basic = _google(RobotsResult(), SchemaResult(any_schema_found=True, schema_richness_score=1))

    assert rich.score - basic.score == 10
