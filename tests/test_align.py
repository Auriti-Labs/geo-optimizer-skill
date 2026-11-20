"""geo align: deterministic prompt-to-content alignment (offline; the page fetch is stubbed)."""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup
from click.testing import CliRunner

from geo_optimizer.cli.main import cli
from geo_optimizer.core.align import align_prompts, analyze_alignment, extract_surfaces, parse_prompts, tokenize
from geo_optimizer.models.config import ALIGN_MAX_PROMPT_CHARS, ALIGN_MAX_PROMPTS

HTML = """<html><head><title>Roof repair in Leeds | Acme Roofing</title>
<meta name="description" content="Emergency roof repair and leak fixing across Leeds."></head>
<body><nav>Menu pricing contact</nav><h1>Roof repair in Leeds</h1>
<h2>How much does a roof repair cost?</h2>
<p>Most small roof repairs in Leeds cost between two hundred and six hundred pounds, depending on access and slate type.</p>
<h3>Flat roof leaks</h3>
<p>We fix flat roof leaks with torch-on felt and give a ten year guarantee on every job we complete this year.</p>
<footer>Copyright Acme Roofing 2026 unsubscribe terms</footer></body></html>"""


def _soup() -> BeautifulSoup:
    return BeautifulSoup(HTML, "html.parser")


class TestTokenize:
    def test_drops_stopwords_short_tokens_and_case(self):
        assert tokenize("How MUCH does a Roof-repair cost in Leeds?") == ["much", "roof", "repair", "cost", "leeds"]

    def test_unicode_words_survive(self):
        assert tokenize("riparazione tetti a Milano") == ["riparazione", "tetti", "milano"]

    def test_empty_and_none(self):
        assert tokenize("") == [] and tokenize(None) == []  # type: ignore[arg-type]


class TestParsePrompts:
    def test_lines_comments_and_blanks(self):
        assert parse_prompts("# my list\n\nroof repair leeds\n  gutter cleaning \n") == (
            ["roof repair leeds", "gutter cleaning"],
            0,
        )

    def test_duplicates_are_skipped_case_and_space_insensitive(self):
        prompts, skipped = parse_prompts("Roof  repair\nroof repair\nother")
        assert prompts == ["Roof  repair", "other"] and skipped == 1

    def test_search_console_style_csv_uses_the_query_column(self):
        raw = "Top queries,Clicks,Impressions\nroof repair leeds,10,200\nflat roof cost,3,90\n"
        assert parse_prompts(raw) == (["roof repair leeds", "flat roof cost"], 0)

    def test_a_csv_without_a_query_header_is_read_as_lines(self):
        prompts, _ = parse_prompts("a,b\nroof,1\n")
        assert prompts == ["a,b", "roof,1"]

    def test_limits(self):
        prompts, skipped = parse_prompts("x" * (ALIGN_MAX_PROMPT_CHARS + 1) + "\nok\n")
        assert prompts == ["ok"] and skipped == 1
        many = "\n".join(f"prompt {i}" for i in range(ALIGN_MAX_PROMPTS + 5))
        prompts, skipped = parse_prompts(many)
        assert len(prompts) == ALIGN_MAX_PROMPTS and skipped == 5


class TestSurfaces:
    def test_surfaces_exclude_navigation_and_footer(self):
        texts = " ".join(t for _, t in extract_surfaces(_soup()))
        assert "Menu" not in texts and "unsubscribe" not in texts

    def test_surface_kinds(self):
        kinds = [k for k, _ in extract_surfaces(_soup())]
        assert kinds[:2] == ["title", "meta_description"]
        assert "h1" in kinds and "heading" in kinds and "passage" in kinds


class TestAlignment:
    def _items(self, *prompts: str):
        return align_prompts(list(prompts), extract_surfaces(_soup()))

    def test_a_prompt_that_matches_the_title_is_covered(self):
        item = self._items("roof repair leeds")[0]
        assert item.status == "covered" and item.surface in {"title", "h1"} and item.score == 1.0

    def test_partial_when_only_some_terms_share_a_surface(self):
        item = self._items("flat roof leaks cost leeds")[0]
        assert item.status in {"partial", "covered"} and 0 < item.score < 1.0

    def test_uncovered_lists_the_terms_found_nowhere(self):
        item = self._items("solar panel installation")[0]
        assert item.status == "uncovered" and item.score == 0.0
        assert item.missing_terms == ["solar", "panel", "installation"]

    def test_missing_terms_are_those_absent_from_the_whole_page(self):
        item = self._items("roof repair warranty")[0]
        assert item.missing_terms == ["warranty"]

    def test_a_prompt_of_only_stopwords_is_dropped(self):
        assert self._items("what is the") == []

    def test_order_is_the_input_order(self):
        assert [i.prompt for i in self._items("solar panel", "roof repair leeds")] == [
            "solar panel",
            "roof repair leeds",
        ]

    def test_deterministic(self):
        assert self._items("roof repair cost") == self._items("roof repair cost")


class TestAnalyze:
    def _ok(self):
        return Mock(status_code=200, text=HTML)

    def test_counts_and_mean(self):
        with patch("geo_optimizer.core.align.fetch_url", return_value=(self._ok(), None)):
            result = analyze_alignment(
                "example.com/roofs", ["roof repair leeds", "solar panel installation", "what is"], skipped=1
            )
        assert result.url == "https://example.com/roofs"
        assert (result.prompts, result.covered, result.uncovered) == (2, 1, 1)
        assert result.skipped_prompts == 2  # one from the caller, one dropped for having no terms
        assert result.mean_score == 0.5

    def test_fetch_error_is_reported_not_raised(self):
        with patch("geo_optimizer.core.align.fetch_url", return_value=(None, "Timeout (10s)")):
            result = analyze_alignment("https://example.com", ["roof"])
        assert result.error == "Timeout (10s)" and result.items == []


class TestCli:
    def _run(self, args, fetch=None):
        fetch = fetch or (Mock(status_code=200, text=HTML), None)
        with (
            patch("geo_optimizer.cli.align_cmd.validate_public_url", return_value=(True, "")),
            patch("geo_optimizer.core.align.fetch_url", return_value=fetch),
        ):
            return CliRunner().invoke(cli, ["align", *args])

    def test_json_output(self):
        out = self._run(["--url", "https://example.com", "--prompt", "roof repair leeds", "--format", "json"])
        assert out.exit_code == 0
        data = json.loads(out.output)
        assert data["covered"] == 1 and data["items"][0]["status"] == "covered" and "disclaimer" in data

    def test_text_output_names_the_missing_terms(self):
        out = self._run(["--url", "https://example.com", "--prompt", "solar panel installation"])
        assert out.exit_code == 0 and "nowhere on the page: solar, panel, installation" in out.output
        assert "not what any AI system would answer" in out.output

    def test_prompts_file(self, tmp_path):
        f = tmp_path / "p.txt"
        f.write_text("roof repair leeds\nflat roof leaks\n")
        out = self._run(["--url", "https://example.com", "--prompts", str(f), "--format", "json"])
        assert json.loads(out.output)["prompts"] == 2

    def test_no_prompts_is_an_error(self):
        out = self._run(["--url", "https://example.com"])
        assert out.exit_code == 1 and "No prompts" in out.output

    def test_unsafe_url_is_refused_before_fetching(self):
        with (
            patch("geo_optimizer.cli.align_cmd.validate_public_url", return_value=(False, "private address")),
            patch("geo_optimizer.core.align.fetch_url") as fetch,
        ):
            out = CliRunner().invoke(cli, ["align", "--url", "http://10.0.0.1", "--prompt", "x y"])
        assert out.exit_code == 1 and not fetch.called

    def test_fetch_error_exits_1(self):
        out = self._run(["--url", "https://example.com", "--prompt", "roof"], fetch=(None, "Connection failed"))
        assert out.exit_code == 1


class TestInputRobustness:
    def test_a_line_over_the_csv_field_limit_is_read_as_a_line_not_a_crash(self):
        prompts, skipped = parse_prompts("x" * 200_000 + "\nroof repair\n")
        assert prompts == ["roof repair"] and skipped == 1  # the long line is over the prompt length limit

    def test_command_line_prompts_are_added_after_a_csv_not_parsed_as_rows(self):
        raw = "Page,Query\n/a,roof repair\n"
        assert parse_prompts(raw, ("solar panels, cost and price",)) == (
            ["roof repair", "solar panels, cost and price"],
            0,
        )

    def test_byte_order_mark_does_not_hide_the_header(self):
        assert parse_prompts("﻿Query,Clicks\nroof repair,10\nflat roof,3\n") == (["roof repair", "flat roof"], 0)

    def test_italian_search_console_header(self):
        assert parse_prompts("Query principali,Clic\nriparazione tetti,10\n")[0] == ["riparazione tetti"]

    def test_utf8_sig_file_through_the_cli(self, tmp_path):
        f = tmp_path / "q.csv"
        f.write_bytes("﻿Query,Clicks\nroof repair leeds,10\n".encode())
        with (
            patch("geo_optimizer.cli.align_cmd.validate_public_url", return_value=(True, "")),
            patch("geo_optimizer.core.align.fetch_url", return_value=(Mock(status_code=200, text=HTML), None)),
        ):
            out = CliRunner().invoke(
                cli, ["align", "--url", "https://example.com", "--prompts", str(f), "--format", "json"]
            )
        assert out.exit_code == 0 and json.loads(out.output)["prompts"] == 1


class TestSurfacesOnRealisticMarkup:
    def _items(self, html: str, *prompts: str):
        return align_prompts(list(prompts), extract_surfaces(BeautifulSoup(html, "html.parser")))

    def test_text_kept_in_a_plain_div_is_read(self):
        item = self._items(
            "<body><div>Roof repair leeds cost guide for owners of older slate roofs</div></body>", "roof repair leeds"
        )[0]
        assert item.status == "covered" and item.surface == "passage"

    def test_a_page_wrapped_in_a_form_is_still_read(self):
        html = "<body><form><p>Roof repair in Leeds starts with a free survey of the damaged slates and flashing.</p></form></body>"
        assert self._items(html, "roof repair leeds")[0].status != "uncovered"

    def test_h4_headings_count(self):
        item = self._items("<body><h4>Roof repair Leeds</h4></body>", "roof repair leeds")[0]
        assert item.status == "covered" and item.surface == "heading"

    def test_english_plurals_match(self):
        item = self._items("<body><h2>Roof repair in Leeds</h2></body>", "roof repairs leeds")[0]
        assert item.status == "covered" and item.missing_terms == []

    def test_status_follows_the_rounded_score(self):
        # 5 of 6 terms in a passage: 5/6 * 0.8 = 0.666..., shown as 0.67, partial
        html = "<body><p>alpha beta gamma delta epsilon one two three four five</p></body>"
        item = self._items(html, "alpha beta gamma delta epsilon zeta")[0]
        assert item.score == 0.67 and item.status == "partial"

    def test_deeply_nested_markup_costs_time_proportional_to_its_size(self):
        import time

        html = (
            "<body>"
            + "<ul><li>" * 4000
            + "roof repair leeds today for local homes and shops"
            + "</li></ul>" * 4000
            + "</body>"
        )
        started = time.perf_counter()
        items = self._items(html, "roof repair leeds")
        assert time.perf_counter() - started < 5.0
        assert items[0].status == "covered"
