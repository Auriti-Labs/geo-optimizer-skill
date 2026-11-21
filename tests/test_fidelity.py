"""geo fidelity: lexical check of an AI answer against the pages it cites (offline; fetches are stubbed)."""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from geo_optimizer.cli.main import cli
from geo_optimizer.core.fidelity import check_fidelity, split_claims
from geo_optimizer.models.config import FIDELITY_MAX_CLAIMS

PAGE = """<html><head><title>Acme CRM pricing</title></head><body>
<p>The Acme CRM starter plan costs 29 dollars per month and includes unlimited contacts for small teams.</p>
<p>Acme was founded in 2014 and its support team answers email within one business day on weekdays.</p>
</body></html>"""

ANSWER = (
    "The Acme CRM starter plan costs 29 dollars per month for small teams [1]. "
    "Acme was founded in 2014 and answers support email within one business day. "
    "The Acme CRM starter plan costs 49 dollars per month for small teams. "
    "Acme also ships a satellite telescope for amateur astronomers worldwide."
)


class TestSplit:
    def test_markers_bullets_and_short_sentences_are_handled(self):
        claims, skipped = split_claims("- First claim has enough words here [2].\nToo short.\n")
        assert claims == ["First claim has enough words here."]
        assert skipped == 1

    def test_claims_are_capped(self):
        claims, skipped = split_claims("\n".join(f"Sentence number {i} has plenty of words in it." for i in range(60)))
        assert len(claims) == FIDELITY_MAX_CLAIMS and skipped == 60 - FIDELITY_MAX_CLAIMS


class TestCheck:
    def _claims(self):
        return check_fidelity(ANSWER, {"https://acme.test/pricing": PAGE}).claims

    def test_a_sentence_carried_by_the_page_is_supported(self):
        assert self._claims()[0].status == "supported"
        assert self._claims()[0].best_source == "https://acme.test/pricing"

    def test_a_wrong_figure_holds_the_claim_at_partial(self):
        claim = self._claims()[2]
        assert claim.status == "partial" and claim.missing_numbers == ["49"]

    def test_a_sentence_about_something_else_is_unsupported(self):
        claim = self._claims()[3]
        assert claim.status == "unsupported" and "telescope" in claim.missing_terms

    def test_counts_and_rate(self):
        res = check_fidelity(ANSWER, {"https://acme.test/pricing": PAGE})
        assert (res.supported, res.partial, res.unsupported) == (2, 1, 1)
        assert res.support_rate == 0.5

    def test_no_claims_is_an_error(self):
        assert check_fidelity("Too short.", {"https://acme.test": PAGE}).error


class TestCli:
    def _run(self, tmp_path, fetch, *extra):
        answer = tmp_path / "answer.txt"
        answer.write_text(ANSWER, encoding="utf-8")
        with (
            patch("geo_optimizer.core.fidelity.fetch_url", side_effect=fetch),
            patch("geo_optimizer.cli.fidelity_cmd.validate_public_url", return_value=(True, "")),
        ):
            return CliRunner().invoke(
                cli, ["fidelity", "--answer", str(answer), "--source", "https://acme.test/pricing", *extra]
            )

    def test_json_output(self, tmp_path):
        res = self._run(tmp_path, lambda url: (Mock(text=PAGE), None), "--format", "json")
        assert res.exit_code == 0, res.output
        data = json.loads(res.output)
        assert data["supported"] == 2 and data["disclaimer"]

    def test_unreadable_source_fails_cleanly(self, tmp_path):
        res = self._run(tmp_path, lambda url: (None, "timeout"))
        assert res.exit_code == 1 and "could be read" in res.output

    def test_unsafe_source_is_refused_before_any_fetch(self, tmp_path):
        answer = tmp_path / "a.txt"
        answer.write_text(ANSWER, encoding="utf-8")
        with patch("geo_optimizer.core.fidelity.fetch_url") as fetch:
            res = CliRunner().invoke(cli, ["fidelity", "--answer", str(answer), "--source", "http://127.0.0.1/x"])
        assert res.exit_code == 1 and not fetch.called
