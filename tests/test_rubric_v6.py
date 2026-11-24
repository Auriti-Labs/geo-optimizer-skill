"""Rubric v6: v5 plus an access gate that caps the score of a page AI crawlers cannot read.

v2 stays the default; v1 to v5 numbers must not change.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

from geo_optimizer.core.access_gate import apply_access_gate, evaluate_access_gate
from geo_optimizer.core.audit import run_full_audit
from geo_optimizer.models.config import (
    ACCESS_GATE_SCORE_CAP,
    CATEGORY_MAX_BY_VERSION,
    CITATION_BOTS,
    DEFAULT_SCORE_VERSION,
    JS_CRITICAL_WORDS,
    SCORE_BANDS,
    SCORING_BY_VERSION,
)
from geo_optimizer.models.results import AuditResult, CdnAiCrawlerResult, JsRenderingResult, MetaResult, RobotsResult


def _result(**kw) -> AuditResult:
    base = {"url": "https://x.test", "score": 90, "band": "excellent", "http_status": 200, "score_version": 6}
    return AuditResult(**{**base, **kw})


class TestVersionTable:
    def test_default_is_v5_and_v6_has_v5_weights(self):
        assert DEFAULT_SCORE_VERSION == 5
        assert SCORING_BY_VERSION[6] == SCORING_BY_VERSION[5]
        assert CATEGORY_MAX_BY_VERSION[6] == CATEGORY_MAX_BY_VERSION[5]

    def test_the_cap_is_the_top_of_the_foundation_band(self):
        assert SCORE_BANDS["foundation"][1] == ACCESS_GATE_SCORE_CAP


class TestGate:
    def test_clean_page_passes(self):
        assert evaluate_access_gate(_result()).status == "pass"

    def test_http_error_blocks(self):
        gate = evaluate_access_gate(_result(http_status=403))
        assert gate.status == "blocked" and "HTTP 403" in gate.reasons[0]

    def test_blanket_cdn_block_blocks_and_a_targeted_one_warns(self):
        blanket = CdnAiCrawlerResult(checked=True, browser_status=200, any_blocked=True, block_pattern="blanket")
        targeted = CdnAiCrawlerResult(
            checked=True,
            browser_status=200,
            any_blocked=True,
            block_pattern="targeted",
            bot_results=[
                {"bot": "GPTBot", "blocked": False, "challenge_detected": False},
                {"bot": "Googlebot", "blocked": True, "challenge_detected": False},
            ],
        )
        assert evaluate_access_gate(_result(cdn_check=blanket)).status == "blocked"
        warn = evaluate_access_gate(_result(cdn_check=targeted))
        assert warn.status == "warn" and warn.warnings == ["A CDN or firewall refuses some crawlers tested: Googlebot"]

    def test_a_cdn_comparison_needs_a_browser_answer_to_compare_with(self):
        # stackoverflow.com: the browser request got 403 as well, so "every AI crawler blocked" says nothing about AI
        no_baseline = CdnAiCrawlerResult(checked=True, browser_status=403, any_blocked=True, block_pattern="blanket")
        gate = evaluate_access_gate(_result(cdn_check=no_baseline))
        assert gate.status == "pass" and gate.reasons == [] and gate.warnings == []

    def test_noindex_header_blocks(self):
        assert evaluate_access_gate(_result(meta=MetaResult(x_robots_noindex=True))).status == "blocked"

    def test_every_citation_bot_disallowed_blocks_but_some_only_warn(self):
        every = RobotsResult(found=True, bots_blocked=sorted(CITATION_BOTS))
        some = RobotsResult(found=True, bots_blocked=["PerplexityBot"])
        assert evaluate_access_gate(_result(robots=every)).status == "blocked"
        gate = evaluate_access_gate(_result(robots=some))
        assert gate.status == "warn" and "PerplexityBot" in gate.warnings[0]

    def test_an_empty_application_shell_blocks(self):
        # excalidraw.com, measured: js_dependent, empty root, 1 word
        shell = JsRenderingResult(checked=True, js_dependent=True, has_empty_root=True, raw_word_count=1)
        gate = evaluate_access_gate(_result(js_rendering=shell))
        assert gate.status == "blocked" and gate.reasons == [
            "Empty application shell: 1 word in the raw HTML, the rest needs JavaScript"
        ]

    def test_a_tiny_static_page_only_warns(self):
        # example.com, measured: js_dependent by the word thresholds, no empty root, 25 words
        tiny = JsRenderingResult(checked=True, js_dependent=True, has_empty_root=False, raw_word_count=25)
        gate = evaluate_access_gate(_result(js_rendering=tiny))
        assert gate.status == "warn" and "25 words" in gate.warnings[0]

    def test_a_shell_with_enough_words_only_warns(self):
        partial = JsRenderingResult(
            checked=True, js_dependent=True, has_empty_root=True, raw_word_count=JS_CRITICAL_WORDS + 150
        )
        assert evaluate_access_gate(_result(js_rendering=partial)).status == "warn"

    def test_noai_warns(self):
        assert evaluate_access_gate(_result(meta=MetaResult(has_noai=True))).status == "warn"

    def test_a_missing_robots_file_does_not_block(self):
        assert evaluate_access_gate(_result(robots=RobotsResult(found=False))).status == "pass"


class TestCap:
    def test_blocked_caps_score_and_band_and_records_the_original(self):
        r = _result(score=93, band="excellent", http_status=403)
        apply_access_gate(r)
        assert (r.score, r.band, r.access_gate.score_before_cap) == (ACCESS_GATE_SCORE_CAP, "foundation", 93)

    def test_blocked_below_the_cap_changes_nothing(self):
        r = _result(score=40, band="foundation", http_status=403)
        apply_access_gate(r)
        assert r.score == 40 and r.access_gate.score_before_cap is None and r.access_gate.status == "blocked"

    def test_warn_and_pass_never_lower_the_score(self):
        r = _result(score=90, meta=MetaResult(has_noai=True))
        apply_access_gate(r)
        assert r.score == 90 and r.access_gate.status == "warn"


class TestFullAudit:
    PAGE = "<html lang='en'><head><title>Home</title></head><body><h1>Home</h1><p>Hello there.</p></body></html>"
    NOINDEX_PAGE_HEADERS = {"X-Robots-Tag": "noindex"}

    def _audit(self, version: int, headers=None):
        def fake_fetch(u, *a, **k):
            if (
                u.endswith("/robots.txt")
                or "/.well-known/" in u
                or u.endswith(("llms.txt", "llms-full.txt"))
                or "/ai/" in u
            ):
                return None, "Not found"
            return Mock(status_code=200, text=self.PAGE, content=self.PAGE.encode(), headers=headers or {}), None

        with (
            patch("geo_optimizer.core.audit.fetch_url", side_effect=fake_fetch),
            patch("geo_optimizer.core.audit.check_markdown_negotiation", return_value=False),
        ):
            return run_full_audit("https://example.com", score_version=version)

    def test_older_rubrics_do_not_evaluate_the_gate(self):
        for v in (2, 5):
            assert self._audit(v, self.NOINDEX_PAGE_HEADERS).access_gate.status == "not_evaluated"

    def test_v6_blocks_a_noindex_page_and_v5_scores_are_unchanged(self):
        v5, v6 = self._audit(5, self.NOINDEX_PAGE_HEADERS), self._audit(6, self.NOINDEX_PAGE_HEADERS)
        assert v6.access_gate.status == "blocked" and "noindex" in v6.access_gate.reasons[0]
        assert v6.score_breakdown == v5.score_breakdown  # same weights, only the cap differs
        assert v6.score == min(v5.score, ACCESS_GATE_SCORE_CAP)


class TestPageThatAnswersAnError:
    """Measured on real sites (nytimes.com, httpbin.org/status/403): the audit stops at the first request, scores the
    page 0 and never reaches the checks. v6 still says why."""

    class _Response:
        def __init__(self, status: int) -> None:
            self.status_code = status
            self.text = "<html><body>x</body></html>"
            self.headers: dict[str, str] = {}
            self.url = "https://blocked.example"

        def __bool__(self) -> bool:  # requests: falsy for 4xx and 5xx
            return self.status_code < 400

    def test_sync_v6_names_the_block_and_older_rubrics_do_not(self):
        for status in (403, 404, 429, 503):
            with patch("geo_optimizer.core.audit.fetch_url", return_value=(self._Response(status), None)):
                v6 = run_full_audit("https://blocked.example", score_version=6)
                v5 = run_full_audit("https://blocked.example", score_version=5)
            assert v6.access_gate.status == "blocked" and v6.access_gate.reasons == [f"The page answers HTTP {status}"]
            assert v6.score == 0 and v6.error == f"HTTP {status}"
            assert v5.access_gate.status == "not_evaluated"

    def test_async_v6_names_the_block(self):
        import asyncio
        from unittest.mock import AsyncMock

        from geo_optimizer.core.audit import run_full_audit_async

        responses = {"https://blocked.example": (self._Response(403), None)}
        with patch("geo_optimizer.utils.http_async.fetch_urls_async", new=AsyncMock(return_value=responses)):
            result = asyncio.run(run_full_audit_async("https://blocked.example", score_version=6))
        assert result.access_gate.status == "blocked" and "HTTP 403" in result.access_gate.reasons[0]

    def test_a_connection_failure_is_not_a_block(self):
        with patch("geo_optimizer.core.audit.fetch_url", return_value=(None, "Timeout (10s)")):
            result = run_full_audit("https://down.example", score_version=6)
        assert result.access_gate.status == "not_evaluated"


class TestJsonOutput:
    """Found by an independent review: the CLI JSON dropped the gate, so a capped score came without its reason."""

    def _json(self, **kw) -> dict:
        import json

        from geo_optimizer.cli.formatters import format_audit_json

        return json.loads(format_audit_json(_result(**kw)))

    def test_v6_json_carries_the_gate_and_the_cap(self):
        r = _result(score=93, band="excellent", http_status=200, meta=MetaResult(x_robots_noindex=True))
        apply_access_gate(r)
        import json

        from geo_optimizer.cli.formatters import format_audit_json

        gate = json.loads(format_audit_json(r))["access_gate"]
        assert gate["status"] == "blocked" and gate["score_before_cap"] == 93 and "noindex" in gate["reasons"][0]

    def test_v5_json_keeps_exactly_its_keys(self):
        assert "access_gate" not in self._json(score_version=5)
