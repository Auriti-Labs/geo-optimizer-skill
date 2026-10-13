"""Tests for ``AuditResult.recommendations_by_category`` (additive JSON field, schema_version 1).

Contract under test:
- keys are ``score_breakdown`` categories of the active rubric plus ``"other"``;
- every string of ``recommendations`` is in exactly one group (multiset equality);
- relative order inside a group matches ``recommendations``;
- ``recommendations`` itself is byte-identical to the pre-change output (golden file).
"""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

import pytest
from click.testing import CliRunner

from geo_optimizer.core.audit import (
    build_categorized_recommendations,
    build_recommendations,
    group_recommendations_by_category,
    run_full_audit,
)
from geo_optimizer.models.config import CATEGORY_MAX, CATEGORY_MAX_V2, RECOMMENDATION_OTHER_CATEGORY
from geo_optimizer.models.results import AuditResult
from tests import recommendation_scenarios as sc

_GOLDEN = json.loads((Path(__file__).parent / "fixtures" / "recommendations_golden.json").read_text(encoding="utf-8"))
_GOLDEN_SCENARIOS = _GOLDEN["scenarios"]

OTHER = RECOMMENDATION_OTHER_CATEGORY


# ─── Shared invariants ───────────────────────────────────────────────────────


def _assert_contract(
    recommendations: list[str], by_category: dict[str, list[str]], score_max: dict[str, int] | None
) -> None:
    """The invariants the platform relies on."""
    # (a) multiset union == recommendations
    flattened = [text for items in by_category.values() for text in items]
    assert Counter(flattened) == Counter(recommendations)
    assert len(flattened) == len(recommendations)

    # (b) relative order inside each category is the order in the flat list.
    # Consume the flat list left to right: each group must be a subsequence of it.
    # Duplicated strings need position tracking, so match greedily per group.
    for category, items in by_category.items():
        assert items, f"empty group {category!r} must be omitted"
        it = iter(recommendations)
        assert all(any(text == candidate for candidate in it) for text in items), (
            f"order of {category!r} differs from recommendations"
        )

    # Keys: only categories of the active rubric, plus "other"
    if score_max is not None:
        assert set(by_category) <= set(score_max) | {OTHER}


# ─── Builder level ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("name", sorted(sc.scenarios()))
def test_builder_scenarios_flat_list_matches_pre_change_golden(name: str) -> None:
    """(d) Direct builder scenarios: the flat list is identical to the old implementation's output."""
    assert build_recommendations(**sc.scenarios()[name]) == _GOLDEN_SCENARIOS[name]


@pytest.mark.parametrize("name", sorted(sc.scenarios()))
def test_builder_scenarios_pairs_agree_with_flat_list_and_contract(name: str) -> None:
    """(a)(b) Flat list == texts of the categorised pairs; grouped view honours the contract."""
    kwargs = sc.scenarios()[name]
    pairs = build_categorized_recommendations(**kwargs)
    flat = build_recommendations(**kwargs)
    grouped = group_recommendations_by_category(pairs)

    assert [text for _, text in pairs] == flat
    # google_ai recommendations only exist when a v2 flow passes a checked GoogleAiReadinessResult
    score_max = CATEGORY_MAX_V2 if kwargs.get("google_ai") else (kwargs.get("category_max") or CATEGORY_MAX)
    _assert_contract(flat, grouped, score_max)


def test_group_recommendations_keeps_order_and_omits_empty_groups() -> None:
    pairs = [("robots", "r1"), ("other", "o1"), ("robots", "r2"), ("meta", "m1"), ("other", "o2")]
    grouped = group_recommendations_by_category(pairs)
    assert grouped == {"robots": ["r1", "r2"], "other": ["o1", "o2"], "meta": ["m1"]}
    assert group_recommendations_by_category([]) == {}


def test_build_recommendations_signature_is_unchanged() -> None:
    """Callers passing positional arguments (as tests and plugins do) keep working."""
    import inspect

    params = list(inspect.signature(build_recommendations).parameters)
    assert params == list(inspect.signature(build_categorized_recommendations).parameters)
    assert params[:6] == ["base_url", "robots", "llms", "schema", "meta", "content"]
    assert params[-1] == "category_max"


# ─── Category mapping (documented in the builder docstring and the JSON contract) ──


def _category_of(pairs: list[tuple[str, str]], needle: str) -> str:
    matches = [category for category, text in pairs if needle in text]
    assert len(matches) == 1, f"{needle!r} matched {len(matches)} recommendations"
    return matches[0]


def test_worst_case_mapping_per_recommendation() -> None:
    pairs = build_categorized_recommendations(**sc.worst_case_inputs())

    # Critical bucket: categorised by the producing detector, not by bucket
    assert _category_of(pairs, "X-Robots-Tag: noindex") == "meta"
    assert _category_of(pairs, "noai directive") == "meta"
    assert _category_of(pairs, "LLM prompt instructions") == OTHER
    assert _category_of(pairs, "Prompt injection in HTML comments") == OTHER
    assert _category_of(pairs, "Hidden text detected") == OTHER
    assert _category_of(pairs, "user-generated content (comments, reviews)") == OTHER

    # Scored categories
    assert _category_of(pairs, "[G-INDEX]") == "google_ai"
    assert _category_of(pairs, "Update robots.txt") == "robots"
    assert _category_of(pairs, "Crawl-delay") == "robots"
    assert _category_of(pairs, "Create /llms.txt") == "llms"
    assert _category_of(pairs, "<title>") == "meta"
    assert _category_of(pairs, "canonical") == "meta"
    assert _category_of(pairs, "Open Graph") == "meta"
    assert _category_of(pairs, "meta description") == "meta"
    assert _category_of(pairs, "consistent brand name") == "brand_entity"
    assert _category_of(pairs, "sameAs links in Organization schema") == "brand_entity"
    assert _category_of(pairs, "WebSite JSON-LD") == "schema"
    assert _category_of(pairs, "parse errors") == "schema"
    assert _category_of(pairs, "Complete Product schema") == "schema"
    assert _category_of(pairs, "single H1") == "content"
    assert _category_of(pairs, "numerical data") == "content"
    assert _category_of(pairs, "lang attribute") == "signals"
    assert _category_of(pairs, "RSS/Atom") == "signals"
    assert _category_of(pairs, "/.well-known/ai.txt") == "ai_discovery"

    # No scored category
    assert _category_of(pairs, "promotional CTAs") == OTHER
    assert _category_of(pairs, "Keyword stuffing") == OTHER
    assert _category_of(pairs, "potentialAction") == OTHER
    assert _category_of(pairs, "images lack descriptive alt text") == OTHER
    assert _category_of(pairs, "VideoObject") == OTHER


def test_ugc_advisory_is_other_and_stays_before_content_items() -> None:
    """The advisory used to live in the content list; its position must not move."""
    kwargs = sc.ugc_advisory_inputs()
    pairs = build_categorized_recommendations(**kwargs)
    texts = [text for _, text in pairs]
    ugc = next(i for i, text in enumerate(texts) if "exposes user-generated content" in text)
    numbers = next(i for i, text in enumerate(texts) if "numerical data" in text)
    assert pairs[ugc][0] == OTHER
    assert pairs[numbers][0] == "content"
    assert ugc < numbers


def test_reordering_by_recoverable_points_moves_categories_together_with_their_text() -> None:
    """With a score_breakdown the order changes, and each text keeps its own category."""
    static = build_categorized_recommendations(**sc.scenarios()["worst_static"])
    reordered = build_categorized_recommendations(**sc.scenarios()["worst_v2_breakdown"])
    assert [t for _, t in static] != [t for _, t in reordered]
    assert Counter(static) == Counter(reordered)


# ─── Real build path: run_full_audit on an all-failing site ──────────────────


@pytest.mark.parametrize(
    ("name", "score_version", "score_max"),
    [
        ("full_sync_all_failing_v2", 2, CATEGORY_MAX_V2),
        ("full_sync_all_failing_v1", 1, CATEGORY_MAX),
        ("full_async_all_failing_v2", 2, CATEGORY_MAX_V2),
    ],
)
def test_all_failing_site_contract_and_golden(name: str, score_version: int, score_max: dict[str, int]) -> None:
    """(a)(b)(d) Real orchestration: contract holds and the flat list equals the pre-change output."""
    result = sc.full_audit_scenarios()[name]
    assert result.score_version == score_version
    assert result.recommendations == _GOLDEN_SCENARIOS[name]
    _assert_contract(result.recommendations, result.recommendations_by_category, score_max)


def test_all_failing_site_robots_meta_signals_land_in_their_keys() -> None:
    """(c) The free categories of the platform gate are identifiable from the real build path."""
    result = sc.run_all_failing_sync(2)
    by_category = result.recommendations_by_category

    assert any(text.startswith("Create robots.txt") for text in by_category["robots"])
    assert any("<title>" in text for text in by_category["meta"])
    assert any("Open Graph" in text for text in by_category["meta"])
    assert any("lang attribute" in text for text in by_category["signals"])
    assert any("RSS/Atom" in text for text in by_category["signals"])
    # v2 rubric: google_ai checks are their own key
    assert any(text.startswith("[G-") for text in by_category["google_ai"])
    # None of the robots/meta/signals recommendations leaks into another key
    for category in ("robots", "meta", "signals"):
        for text in by_category[category]:
            assert not any(text in other for key, other in by_category.items() if key != category)


def test_v1_rubric_has_no_google_ai_key() -> None:
    result = sc.run_all_failing_sync(1)
    assert "google_ai" not in result.recommendations_by_category
    assert set(result.recommendations_by_category) <= set(CATEGORY_MAX) | {OTHER}


@pytest.mark.parametrize("score_version", [1, 2])
def test_cdn_and_js_warnings_are_other(score_version: int) -> None:
    """The CDN/WAF and JS-rendering warnings are appended after the builder and belong to no scored category."""
    result = sc.build_result_with_cdn_and_js(score_version)
    assert result.recommendations_by_category[OTHER] == [
        text for text in result.recommendations if "blocks AI crawlers" in text or "requires JavaScript" in text
    ]
    assert len(result.recommendations_by_category[OTHER]) == 2
    assert result.recommendations == _GOLDEN_SCENARIOS[f"build_result_cdn_js_v{score_version}"]
    _assert_contract(
        result.recommendations,
        result.recommendations_by_category,
        CATEGORY_MAX_V2 if score_version == 2 else CATEGORY_MAX,
    )


def test_healthy_site_has_no_empty_groups() -> None:
    """A result with nothing to recommend serialises to an empty mapping."""
    result = AuditResult(url="https://example.com")
    assert result.recommendations == []
    assert result.recommendations_by_category == {}


# ─── Error paths ─────────────────────────────────────────────────────────────


def test_unreachable_site_files_the_message_under_other() -> None:
    from unittest.mock import patch

    with patch("geo_optimizer.core.audit.fetch_url", return_value=(None, "Connection refused")):
        result = run_full_audit("https://example.com")

    assert result.error
    assert len(result.recommendations) == 1
    assert result.recommendations_by_category == {OTHER: result.recommendations}
    assert result.recommendations_by_category[OTHER] is not result.recommendations  # independent list


@pytest.mark.parametrize("status", [403, 503])
def test_http_error_files_the_message_under_other(status: int) -> None:
    from unittest.mock import Mock, patch

    response = Mock(status_code=status, text="blocked", content=b"blocked", headers={})
    with patch("geo_optimizer.core.audit.fetch_url", return_value=(response, None)):
        result = run_full_audit("https://blocked.example")

    assert result.error == f"HTTP {status}"
    assert len(result.recommendations) == 1
    assert result.recommendations_by_category == {OTHER: result.recommendations}


def test_async_error_paths_are_consistent() -> None:
    import asyncio
    from unittest.mock import AsyncMock, Mock, patch

    from geo_optimizer.core.audit import run_full_audit_async

    base = "https://example.com"
    unreachable = {base: (None, "Connection refused")}
    http_error = {base: (Mock(status_code=503, text="x", content=b"x", headers={}), None)}
    for responses in (unreachable, http_error):
        with patch("geo_optimizer.utils.http_async.fetch_urls_async", new=AsyncMock(return_value=responses)):
            result = asyncio.run(run_full_audit_async(base))
        assert result.error
        assert result.recommendations_by_category == {OTHER: result.recommendations}
        assert len(result.recommendations) == 1


# ─── Serialisation: web JSON, CLI JSON, cache round trip ─────────────────────


def _to_web_dict(result: AuditResult) -> dict:
    import importlib

    pytest.importorskip("fastapi", reason="FastAPI non installato (pip install geo-optimizer-skill[web])")
    os.environ.setdefault("GEO_STATIC_DIR", str(Path(__file__).parent.parent / "frontend/dist"))
    return importlib.import_module("geo_optimizer.web.app")._audit_result_to_dict(result)


def test_web_dict_contains_the_field_and_matches_recommendations() -> None:
    """(e) Same schema_version, additive field, consistent with the flat list."""
    result = sc.run_all_failing_sync(2)
    data = _to_web_dict(result)

    assert data["schema_version"] == 1
    assert data["recommendations"] == result.recommendations
    assert data["recommendations_by_category"] == result.recommendations_by_category
    _assert_contract(data["recommendations"], data["recommendations_by_category"], data["score_max"])
    # Must survive JSON serialisation unchanged
    assert json.loads(json.dumps(data))["recommendations_by_category"] == data["recommendations_by_category"]


def test_web_dict_default_result_has_empty_mapping() -> None:
    data = _to_web_dict(AuditResult(url="https://example.com"))
    assert data["recommendations_by_category"] == {}


@pytest.mark.parametrize("status", [None, 503])
def test_web_dict_error_path_is_consistent(status: int | None) -> None:
    """(f) Unreachable / HTTP-error results expose {"other": [...]} equal to their recommendations."""
    from unittest.mock import Mock, patch

    fetch_result = (None, "Connection refused") if status is None else (Mock(status_code=status, headers={}), None)
    with patch("geo_optimizer.core.audit.fetch_url", return_value=fetch_result):
        result = run_full_audit("https://example.com")

    data = _to_web_dict(result)
    assert data["error"]
    assert data["recommendations_by_category"] == {OTHER: data["recommendations"]}


def test_web_cache_round_trip_preserves_the_field() -> None:
    """A cached web payload restores recommendations_by_category; a legacy payload restores an empty dict."""
    import importlib

    pytest.importorskip("fastapi")
    os.environ.setdefault("GEO_STATIC_DIR", str(Path(__file__).parent.parent / "frontend/dist"))
    app_module = importlib.import_module("geo_optimizer.web.app")

    data = _to_web_dict(sc.run_all_failing_sync(2))
    restored = app_module._dict_to_audit_result(data)
    assert restored.recommendations_by_category == data["recommendations_by_category"]

    legacy = {k: v for k, v in data.items() if k != "recommendations_by_category"}
    assert app_module._dict_to_audit_result(legacy).recommendations_by_category == {}


def test_cli_json_contains_the_field() -> None:
    """The CLI JSON formatter emits the same field, consistent with its recommendations."""
    from geo_optimizer.cli.formatters import format_audit_json

    result = sc.run_all_failing_sync(2)
    data = json.loads(format_audit_json(result))

    assert data["recommendations"] == result.recommendations
    assert data["recommendations_by_category"] == result.recommendations_by_category
    _assert_contract(data["recommendations"], data["recommendations_by_category"], data["score_max"])


def test_cli_json_error_path_is_consistent() -> None:
    from unittest.mock import patch

    from geo_optimizer.cli.formatters import format_audit_json

    with patch("geo_optimizer.core.audit.fetch_url", return_value=(None, "Connection refused")):
        result = run_full_audit("https://example.com")
    data = json.loads(format_audit_json(result))
    assert data["recommendations_by_category"] == {OTHER: data["recommendations"]}


def test_geo_audit_cli_json_output_has_the_field() -> None:
    """End to end through ``geo audit --format json`` with the network mocked."""
    from unittest.mock import patch

    from geo_optimizer.cli.main import cli

    result = sc.run_all_failing_sync(2)
    # httpx hidden: the CLI then takes the sync path, which is the mocked one (same pattern as test_cli.py)
    with (
        patch.dict("sys.modules", {"httpx": None}),
        patch("geo_optimizer.cli.audit_cmd.run_full_audit", return_value=result),
    ):
        invocation = CliRunner().invoke(cli, ["audit", "--url", "https://example.com", "--format", "json"])

    assert invocation.exit_code == 0, invocation.output
    payload = json.loads(invocation.output[invocation.output.index("{") :])
    assert payload["recommendations_by_category"] == result.recommendations_by_category
