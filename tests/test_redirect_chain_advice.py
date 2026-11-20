"""Advice on long redirect chains: shown from REDIRECT_CHAIN_WARN_HOPS hops, never scored."""

from __future__ import annotations

from geo_optimizer.core.audit import _redirect_hops, build_recommendations
from geo_optimizer.models.config import REDIRECT_CHAIN_WARN_HOPS
from geo_optimizer.models.results import (
    ContentResult,
    GoogleAiReadinessResult,
    LlmsTxtResult,
    MetaResult,
    RobotsResult,
    SchemaResult,
)


def _recs(hops: int) -> list[str]:
    google_ai = GoogleAiReadinessResult(checked=True, redirect_hops=hops)
    return build_recommendations(
        "https://x.test/",
        RobotsResult(),
        LlmsTxtResult(),
        SchemaResult(),
        MetaResult(),
        ContentResult(),
        google_ai=google_ai,
    )


def test_no_advice_below_the_threshold():
    assert not any("redirects" in r for r in _recs(REDIRECT_CHAIN_WARN_HOPS - 1))


def test_advice_at_the_threshold_names_the_count():
    advice = [r for r in _recs(REDIRECT_CHAIN_WARN_HOPS) if "redirects" in r]
    assert advice and f"{REDIRECT_CHAIN_WARN_HOPS} times" in advice[0]


def test_advice_does_not_depend_on_the_other_recommendations():
    assert len([r for r in _recs(5) if "redirects" in r]) == 1


def test_hops_read_from_a_response():
    class _R:
        redirect_hops = 2

    class _NoCount:
        pass

    assert _redirect_hops(_R()) == 2
    assert _redirect_hops(_NoCount()) == 0
    assert _redirect_hops(None) == 0


def test_a_mock_response_never_counts_as_a_hop():
    from unittest.mock import MagicMock

    assert _redirect_hops(MagicMock()) == 0
