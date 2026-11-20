"""geo fanout: sub-intent coverage from fixed templates (offline; the page fetch is stubbed)."""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup
from click.testing import CliRunner

from geo_optimizer.cli.main import cli
from geo_optimizer.core.align import extract_surfaces
from geo_optimizer.core.fanout import analyze_fanout, expand, score_families
from geo_optimizer.models.config import FANOUT_FAMILIES, FANOUT_MAX_SEED_CHARS

HTML = """<html><head><title>CRM software pricing | Acme</title></head><body>
<h1>CRM software pricing</h1>
<h2>CRM software price: how much does CRM software cost</h2>
<p>Acme CRM software pricing plans start free and move to a paid tier once your team grows past five people.</p>
<h2>Is CRM software worth it? CRM software reviews and pros and cons</h2>
<p>Customers describe the pros and cons of our CRM software in the reviews listed further down this page today.</p>
</body></html>"""


def _families(html: str, seed: str):
    return {f.family: f for f in score_families(seed, extract_surfaces(BeautifulSoup(html, "html.parser")))}


class TestExpand:
    def test_every_family_is_expanded_with_the_topic(self):
        out = expand("  CRM   software ")
        assert set(out) == set(FANOUT_FAMILIES)
        assert out["price"][0] == "CRM software price"
        assert all("CRM software" in q for qs in out.values() for q in qs)

    def test_a_long_seed_is_cut(self):
        assert all(len(q) < FANOUT_MAX_SEED_CHARS + 60 for qs in expand("x " * 500).values() for q in qs)


class TestCoverage:
    def test_price_and_reviews_are_covered_and_others_are_not(self):
        f = _families(HTML, "CRM software")
        assert f["price"].status in {"covered", "partial"} and f["price"].mean_score > 0.4
        assert f["reviews"].mean_score > 0.4
        assert f["free_options"].mean_score < f["price"].mean_score
        assert f["comparison"].status == "uncovered"

    def test_a_page_about_something_else_scores_low_everywhere(self):
        f = _families(
            "<body><h1>Garden furniture sale</h1><p>Teak benches and tables for patios and lawns this season.</p></body>",
            "CRM software",
        )
        assert all(fam.status == "uncovered" for fam in f.values())

    def test_added_words_only_count_on_a_surface_that_speaks_of_the_topic(self):
        html = "<body><h2>Garden furniture price list: reviews, pros and cons of teak</h2><h1>CRM software</h1></body>"
        f = _families(html, "CRM software")
        assert f["price"].mean_score == 0.0 and f["reviews"].mean_score == 0.0

    def test_missing_terms_name_the_words_to_write(self):
        f = _families(HTML, "CRM software")
        flat = {t for item in f["comparison"].items for t in item.missing_terms}
        assert "alternatives" in flat or "compared" in flat


class TestAnalyzeAndCli:
    def _fetch(self, error=None):
        return (Mock(status_code=200, text=HTML), None) if error is None else (None, error)

    def test_counts(self):
        with patch("geo_optimizer.core.fanout.fetch_url", return_value=self._fetch()):
            result = analyze_fanout("example.com", "CRM software")
        assert result.url == "https://example.com" and len(result.families) == len(FANOUT_FAMILIES)
        assert result.covered + result.partial + result.uncovered == len(FANOUT_FAMILIES)
        assert result.uncovered >= 1

    def test_fetch_error(self):
        with patch("geo_optimizer.core.fanout.fetch_url", return_value=self._fetch("Timeout (10s)")):
            assert analyze_fanout("https://example.com", "x").error == "Timeout (10s)"

    def _run(self, args, fetch=None):
        with (
            patch("geo_optimizer.cli.fanout_cmd.validate_public_url", return_value=(True, "")),
            patch("geo_optimizer.core.fanout.fetch_url", return_value=fetch or self._fetch()),
        ):
            return CliRunner().invoke(cli, ["fanout", *args])

    def test_json(self):
        out = self._run(["--url", "https://example.com", "--topic", "CRM software", "--format", "json"])
        data = json.loads(out.output)
        assert out.exit_code == 0 and data["seed"] == "CRM software" and len(data["families"]) == len(FANOUT_FAMILIES)

    def test_text_shows_families_and_the_disclaimer(self):
        out = self._run(["--url", "https://example.com", "--topic", "CRM software"])
        assert "SUB-INTENT COVERAGE" in out.output and "comparison" in out.output
        assert "fixed checklist" in out.output

    def test_empty_topic_is_an_error(self):
        assert self._run(["--url", "https://example.com", "--topic", "  "]).exit_code == 1

    def test_unsafe_url_is_refused_before_fetching(self):
        with (
            patch("geo_optimizer.cli.fanout_cmd.validate_public_url", return_value=(False, "private address")),
            patch("geo_optimizer.core.fanout.fetch_url") as fetch,
        ):
            out = CliRunner().invoke(cli, ["fanout", "--url", "http://10.0.0.1", "--topic", "x y"])
        assert out.exit_code == 1 and not fetch.called

    def test_fetch_error_exits_1(self):
        assert (
            self._run(["--url", "https://example.com", "--topic", "x"], fetch=(None, "Connection failed")).exit_code
            == 1
        )
