"""geo lint: deterministic epistemic lint of a page's claims (offline; the page fetch is stubbed)."""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup
from click.testing import CliRunner

from geo_optimizer.cli.main import cli
from geo_optimizer.core.epistemic_lint import analyze_lint, lint_blocks, text_blocks
from geo_optimizer.models.config import LINT_DUPLICATE_BLOCKS_MIN, LINT_MAX_FINDINGS


def _rules(html: str) -> list[str]:
    return [f.rule for f in lint_blocks(text_blocks(BeautifulSoup(f"<body>{html}</body>", "html.parser")))]


class TestAuthorityLaundering:
    def test_a_statistic_with_nothing_beside_it_is_flagged(self):
        assert "unsourced_statistic" in _rules(
            "<p>Our customers see a 47% increase in qualified leads every quarter.</p>"
        )

    def test_a_year_or_a_source_word_in_the_block_clears_it(self):
        assert "unsourced_statistic" not in _rules("<p>Traffic grew by 47% according to the 2025 benchmark we ran.</p>")
        assert "unsourced_statistic" not in _rules("<p>A study of 400 shops found a 31% lift in repeat orders.</p>")

    def test_a_link_in_the_block_clears_it(self):
        assert "unsourced_statistic" not in _rules(
            '<p>Churn fell by 12% across the <a href="/data">accounts we measured last quarter</a> for retail.</p>'
        )

    def test_evidence_in_the_neighbouring_block_counts(self):
        html = "<p>Source: internal survey, n = 220, March 2026.</p><p>Customers report 58% faster onboarding.</p>"
        assert "unsourced_statistic" not in _rules(html)

    def test_badges_without_a_link_are_flagged(self):
        assert "unsupported_authority" in _rules(
            "<p>We are the award-winning market leader in roofing across Leeds.</p>"
        )
        assert "unsupported_authority" not in _rules(
            '<p>We are <a href="/awards">award-winning</a> for roofing across Leeds, with the list on that page.</p>'
        )

    def test_italian_statistic(self):
        assert "unsourced_statistic" in _rules(
            "<p>I clienti ottengono il 40% di richieste in più ogni mese con noi.</p>"
        )


class TestRelevanceFlooding:
    def test_the_same_block_repeated_is_flagged(self):
        block = "<p>Best roof repair in Leeds and surrounding areas, call us today for a quote.</p>"
        assert "duplicate_block" in _rules(block * LINT_DUPLICATE_BLOCKS_MIN)
        assert "duplicate_block" not in _rules(block * (LINT_DUPLICATE_BLOCKS_MIN - 1))

    def test_a_block_that_is_only_a_keyword_list_is_flagged(self):
        keywords = ", ".join(f"roofer {i}" for i in range(25))
        assert "keyword_list" in _rules(f"<p>{keywords}</p>")

    def test_a_long_sentence_with_commas_is_not_a_keyword_list(self):
        assert "keyword_list" not in _rules(
            "<p>We repair slate roofs, fix leaking gutters, and replace flashing, always after a free survey of the damage.</p>"
        )


class TestCaveatOmission:
    def test_an_absolute_promise_without_a_qualifier_is_flagged(self):
        assert "caveat_omitted" in _rules(
            "<p>Our treatment is guaranteed to work and is completely risk-free for everyone.</p>"
        )

    def test_a_qualifier_in_the_block_clears_it(self):
        assert "caveat_omitted" not in _rules(
            "<p>The repair is guaranteed for ten years, unless the roof is altered by someone else afterwards.</p>"
        )

    def test_italian_promise(self):
        assert "caveat_omitted" in _rules(
            "<p>Il nostro servizio è garantito al cento per cento in tutta la provincia.</p>"
        )


class TestCleanAndShape:
    def test_ordinary_copy_has_no_findings(self):
        assert (
            _rules("<p>We repair roofs in Leeds. A survey takes about an hour and the quote is free of charge.</p>")
            == []
        )

    def test_navigation_and_footer_are_not_read(self):
        html = "<nav>Award-winning market leader, guaranteed always for everyone today</nav><footer>risk-free guaranteed</footer>"
        assert _rules(html) == []

    def test_short_blocks_are_ignored(self):
        assert _rules("<p>100% guaranteed</p>") == []


class TestAnalyzeAndCli:
    HTML = (
        "<html><body><h1>Roofing</h1>"
        "<p>Our customers see a 47% increase in qualified leads every quarter, guaranteed for everyone.</p></body></html>"
    )

    def _fetch(self, text=None, error=None):
        return (Mock(status_code=200, text=text or self.HTML), None) if error is None else (None, error)

    def test_counts_and_family(self):
        with patch("geo_optimizer.core.epistemic_lint.fetch_url", return_value=self._fetch()):
            result = analyze_lint("example.com")
        assert result.url == "https://example.com"
        assert result.counts == {"unsourced_statistic": 1, "caveat_omitted": 1}
        assert {f.family for f in result.findings} == {"authority_laundering", "caveat_omission"}

    def test_listing_is_capped_but_counts_are_complete(self):
        many = "".join(
            f"<p>Result number {i} shows a {i + 10}% jump in sales for all of our customers here.</p>"
            for i in range(80)
        )
        with patch(
            "geo_optimizer.core.epistemic_lint.fetch_url", return_value=self._fetch(text=f"<body>{many}</body>")
        ):
            result = analyze_lint("https://example.com")
        assert len(result.findings) == LINT_MAX_FINDINGS and result.truncated
        assert result.counts["unsourced_statistic"] == 80

    def test_fetch_error_is_reported(self):
        with patch("geo_optimizer.core.epistemic_lint.fetch_url", return_value=self._fetch(error="Timeout (10s)")):
            assert analyze_lint("https://example.com").error == "Timeout (10s)"

    def _run(self, args, fetch=None):
        with (
            patch("geo_optimizer.cli.lint_cmd.validate_public_url", return_value=(True, "")),
            patch("geo_optimizer.core.epistemic_lint.fetch_url", return_value=fetch or self._fetch()),
        ):
            return CliRunner().invoke(cli, ["lint", *args])

    def test_json(self):
        out = self._run(["--url", "https://example.com", "--format", "json"])
        data = json.loads(out.output)
        assert out.exit_code == 0 and data["counts"]["unsourced_statistic"] == 1 and "disclaimer" in data

    def test_text_names_the_families_and_the_disclaimer(self):
        out = self._run(["--url", "https://example.com"])
        assert "AUTHORITY WITHOUT EVIDENCE" in out.output and "PROMISE WITHOUT CAVEAT" in out.output
        assert "not a fact-check" in out.output

    def test_unsafe_url_is_refused_before_fetching(self):
        with (
            patch("geo_optimizer.cli.lint_cmd.validate_public_url", return_value=(False, "private address")),
            patch("geo_optimizer.core.epistemic_lint.fetch_url") as fetch,
        ):
            out = CliRunner().invoke(cli, ["lint", "--url", "http://10.0.0.1"])
        assert out.exit_code == 1 and not fetch.called

    def test_fetch_error_exits_1(self):
        assert self._run(["--url", "https://example.com"], fetch=(None, "Connection failed")).exit_code == 1


class TestPromiseIsAsserted:
    """False positives found by running the lint on geoready.dev: a sentence that denies, asks or softens."""

    def test_a_denial_is_not_a_promise(self):
        assert (
            _rules("<p>The score measures technical readiness; it does not guarantee citations in any answer.</p>")
            == []
        )
        assert (
            _rules("<p>This is a way to find gaps, not a formula for a guaranteed ranking gain in any engine.</p>")
            == []
        )

    def test_a_question_is_not_a_promise(self):
        assert _rules("<p>Does a high score guarantee that AI answers will cite my site in the end?</p>") == []

    def test_almost_always_is_softened(self):
        assert (
            _rules("<p>A site in the foundation band almost always has more to gain from fixing structure first.</p>")
            == []
        )

    def test_a_bare_always_is_not_a_promise(self):
        assert (
            _rules("<p>After a rewrite the pattern is always the same: a category regresses and the alert fires.</p>")
            == []
        )

    def test_an_asserted_promise_after_a_denial_in_another_sentence_is_still_flagged(self):
        assert "caveat_omitted" in _rules(
            "<p>We do not hide fees. Our repair is guaranteed to fix every leak for everyone.</p>"
        )

    def test_always_works_is_flagged(self):
        assert "caveat_omitted" in _rules(
            "<p>This method always works for every site, whatever the size, with no extra effort.</p>"
        )


class TestHostileInput:
    """Found by an independent review: two quadratic costs on hostile pages."""

    def test_the_statistic_pattern_is_linear_on_a_very_long_word(self):
        import re
        import time

        from geo_optimizer.models.config import LINT_STATISTIC_RE

        pattern = re.compile(LINT_STATISTIC_RE, re.IGNORECASE)
        for word in ("aument", "cresc", "riduc", "increase"):
            started = time.perf_counter()
            pattern.search(word + "a" * 200_000)
            assert time.perf_counter() - started < 1.0, word  # 14 s at 40000 characters before

    def test_deeply_nested_inline_markup_is_read_in_linear_time(self):
        import time

        html = "<body><p>" + "<span>word " * 20000 + "</span>" * 20000 + "</p></body>"
        started = time.perf_counter()
        blocks = text_blocks(BeautifulSoup(html, "html.parser"))
        assert time.perf_counter() - started < 6.0  # parsing is most of it; 30 s before
        assert len(blocks) == 1


class TestNotAClaim:
    def test_code_samples_are_not_read(self):
        assert (
            _rules("<pre>pow(38, -1, mod=97) 23 >>> 23 * 38 % 97 == 1 and the result is 23 percent exactly here</pre>")
            == []
        )
        assert (
            _rules("<p>Use <code>x % 97</code> to take the remainder of the division by ninety seven for the key.</p>")
            == []
        )
