"""Rubric v5: v4 plus a page-aware robots check and a stricter schema visibility check.

v2 stays the default; v1 to v4 numbers must not change.
"""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup
from click.testing import CliRunner

from geo_optimizer.cli.main import cli
from geo_optimizer.core.audit import _robots_judgement
from geo_optimizer.core.audit_robots import _audit_robots_from_response
from geo_optimizer.core.audit_schema import audit_schema
from geo_optimizer.core.scoring import _score_schema
from geo_optimizer.models.config import (
    CATEGORY_MAX_BY_VERSION,
    DEFAULT_SCORE_VERSION,
    ROBOTS_PARTIAL_BY_VERSION,
    SCORING_BY_VERSION,
)
from geo_optimizer.models.results import SchemaResult


def _page(jsonld: dict, body: str) -> SchemaResult:
    html = f'<html><body>{body}<script type="application/ld+json">{json.dumps(jsonld)}</script></body></html>'
    return audit_schema(BeautifulSoup(html, "html.parser"), "https://x.test/")


class TestVersionTable:
    def test_default_is_v5(self):
        assert DEFAULT_SCORE_VERSION == 5

    def test_v5_is_v4_with_the_strict_switch(self):
        v4, v5 = SCORING_BY_VERSION[4], SCORING_BY_VERSION[5]
        assert {k: v for k, v in v5.items() if k != "schema_visible_strict"} == v4
        assert v5["schema_visible_strict"] == 1 and "schema_visible_strict" not in v4
        assert CATEGORY_MAX_BY_VERSION[5] == CATEGORY_MAX_BY_VERSION[4]
        assert ROBOTS_PARTIAL_BY_VERSION[5] == ROBOTS_PARTIAL_BY_VERSION[4]


class TestSchemaVisibility:
    FAQ = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "name": "Shipping questions",
        "mainEntity": [
            {
                "@type": "Question",
                "name": "How long does delivery take?",
                "acceptedAnswer": {"@type": "Answer", "text": "Two days."},
            },
            {"@type": "Question", "name": "Do you ship abroad?", "acceptedAnswer": {"@type": "Answer", "text": "Yes."}},
        ],
    }

    def test_everything_visible_passes_both(self):
        r = _page(
            self.FAQ, "<h1>Shipping questions</h1><h2>How long does delivery take?</h2><h2>Do you ship abroad?</h2>"
        )
        assert r.visible_match and r.visible_match_strict

    def test_headline_matches_but_a_question_is_hidden(self):
        r = _page(self.FAQ, "<h1>Shipping questions</h1><h2>How long does delivery take?</h2>")
        assert r.visible_match is True  # v1-v4 behaviour, unchanged
        assert r.visible_match_strict is False

    def test_product_price_must_be_visible(self):
        product = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Blue chair",
            "offers": {"@type": "Offer", "price": 89},
        }
        assert _page(product, "<h1>Blue chair</h1><p>Only 89 today</p>").visible_match_strict is True
        assert _page(product, "<h1>Blue chair</h1><p>Ask for a quote</p>").visible_match_strict is False

    def test_every_checkable_schema_counts(self):
        org = {"@context": "https://schema.org", "@type": "Organization", "name": "Acme Hidden Name"}
        r = _page(org, "<h1>Welcome home</h1>")
        assert r.visible_match_strict is False

    def test_no_checkable_schema_is_not_a_pass(self):
        assert (
            _page({"@context": "https://schema.org", "@type": "WebSite"}, "<h1>Hello</h1>").visible_match_strict
            is False
        )

    def test_v5_scores_the_strict_flag_older_versions_the_old_one(self):
        def pts(schema: SchemaResult, v: int) -> int:
            return _score_schema(schema, SCORING_BY_VERSION[v], None, CATEGORY_MAX_BY_VERSION[v]["schema"])

        loose = SchemaResult(any_schema_found=True, visible_match=True, visible_match_strict=False)
        strict = SchemaResult(any_schema_found=True, visible_match=True, visible_match_strict=True)
        assert pts(loose, 2) == pts(strict, 2)  # v1-v4 never read the strict flag
        assert pts(loose, 4) == pts(strict, 4)
        assert pts(loose, 5) < pts(strict, 5)  # v5 does
        assert pts(strict, 5) == pts(strict, 4)  # when everything is visible v5 gives what v4 gives


class _Response:
    """Minimal stand-in for a fetched robots.txt response."""

    status_code = 200

    def __init__(self, text: str) -> None:
        self.text = text


class TestRobotsOnThePage:
    ROBOTS = "User-agent: GPTBot\nDisallow: /blog/\n\nUser-agent: ClaudeBot\nDisallow: /*.pdf$\n"

    def test_judgement_keeps_the_requested_path_slash_scheme_and_params(self):
        assert _robots_judgement("https://x.test/blog/", 5)["page_path"] == "/blog/"
        assert _robots_judgement("x.test/blog/", 5)["page_path"] == "/blog/"  # no scheme typed
        assert _robots_judgement("https://x.test/a;b=1?c=2", 5)["page_path"] == "/a;b=1?c=2"

    def test_judgement_kwargs_only_from_v5(self):
        assert _robots_judgement("https://x.test/blog/p", 4) == {}
        assert _robots_judgement("https://x.test/blog/p?a=1", 5) == {"page_path": "/blog/p?a=1", "wildcards": True}
        assert _robots_judgement("https://x.test", 5) == {"page_path": "/", "wildcards": True}

    def test_v5_blocks_the_bot_on_a_blocked_page_older_rubrics_do_not(self):
        r = _Response(self.ROBOTS)
        old = _audit_robots_from_response(r)
        new = _audit_robots_from_response(r, **_robots_judgement("https://x.test/blog/p", 5))
        assert "GPTBot" in old.bots_allowed and "GPTBot" not in old.bots_blocked
        assert "GPTBot" in new.bots_blocked

    def test_v5_wildcard_on_a_pdf_page(self):
        r = _Response(self.ROBOTS)
        new = _audit_robots_from_response(r, **_robots_judgement("https://x.test/file.pdf", 5))
        assert "ClaudeBot" in new.bots_blocked


def test_cli_accepts_score_version_5():
    out = CliRunner().invoke(cli, ["audit", "--help"])
    assert out.exit_code == 0 and "--score-version [1|2|3|4|5|6]" in out.output


class TestHostileJsonLd:
    def test_a_huge_integer_price_does_not_raise(self):
        """json.loads accepts integers of thousands of digits; formatting one as a float used to overflow."""
        html = (
            "<html><body><h1>Widget thing</h1><script type='application/ld+json'>"
            '{"@type":"Product","name":"Widget thing","offers":{"price":' + "1" + "0" * 400 + "}}"
            "</script></body></html>"
        )
        result = audit_schema(BeautifulSoup(html, "html.parser"), "https://x.test/")
        assert result.visible_match is True  # unchanged old behaviour
        assert result.visible_match_strict is True  # the unusable price is skipped, the name still matches


class TestFullAuditPath:
    """run_full_audit with a stubbed network: the page path reaches the robots check."""

    ROBOTS = "User-agent: GPTBot\nDisallow: /blog/\n"

    def _audit(self, url: str, version: int):
        from geo_optimizer.core.audit import run_full_audit

        html = "<html lang='en'><head><title>Blog</title></head><body><h1>Blog</h1><p>Posts.</p></body></html>"

        def fake_fetch(u, *args, **kwargs):
            if u.endswith("/robots.txt"):
                return Mock(status_code=200, text=self.ROBOTS, content=self.ROBOTS.encode(), headers={}), None
            if u.rstrip("/").endswith("/blog"):
                return Mock(status_code=200, text=html, content=html.encode(), headers={}), None
            return None, "Not found"

        with (
            patch("geo_optimizer.core.audit.fetch_url", side_effect=fake_fetch),
            patch("geo_optimizer.core.audit.check_markdown_negotiation", return_value=False),
        ):
            return run_full_audit(url, score_version=version)

    def test_v5_blocks_the_bot_on_a_section_page_with_a_trailing_slash(self):
        assert "GPTBot" in self._audit("https://example.com/blog/", 5).robots.bots_blocked

    def test_v4_still_reads_the_root_only(self):
        result = self._audit("https://example.com/blog/", 4)
        assert "GPTBot" not in result.robots.bots_blocked and "GPTBot" in result.robots.bots_allowed


class TestPriceMustStandAlone:
    PRODUCT = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Blue chair",
        "offers": {"@type": "Offer", "price": "1"},
    }

    def test_one_is_not_visible_inside_another_number(self):
        assert _page(self.PRODUCT, "<h1>Blue chair</h1><p>2019 items sold</p>").visible_match_strict is False
        assert _page(self.PRODUCT, "<h1>Blue chair</h1><p>Price: 1 EUR</p>").visible_match_strict is True

    def test_a_longer_decimal_is_not_the_price(self):
        product = {**self.PRODUCT, "offers": {"@type": "Offer", "price": 89}}
        assert _page(product, "<h1>Blue chair</h1><p>Only 89.5 today</p>").visible_match_strict is False
        assert _page(product, "<h1>Blue chair</h1><p>Only 89. Today.</p>").visible_match_strict is True

    def test_decimal_comma_spelling_is_accepted(self):
        product = {**self.PRODUCT, "offers": {"@type": "Offer", "price": "19.90"}}
        assert _page(product, "<h1>Blue chair</h1><p>19,90 €</p>").visible_match_strict is True


class TestPriceSpellings:
    """A product price is read from JSON as a number and matched against how people write it."""

    def _strict(self, price, text: str) -> bool:
        product = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Blue chair",
            "offers": {"@type": "Offer", "price": price},
        }
        return _page(product, f"<h1>Blue chair</h1><p>{text}</p>").visible_match_strict

    def test_trailing_zero_decimals(self):
        assert self._strict(19.9, "19.90 EUR") and self._strict(19.9, "19,90 €")

    def test_six_digit_and_larger_prices_are_not_rounded(self):
        assert self._strict(12999.99, "12999.99")
        assert self._strict(1234567, "1234567 units")
        assert self._strict(129999.5, "129,999.50")

    def test_thousands_separators(self):
        for text in ("1,089", "1.089", "1 089", "1'089", "1.089,00"):
            assert self._strict(1089, text), text

    def test_other_numbers_do_not_count(self):
        assert not self._strict(89, "Only 89.5 today")
        assert not self._strict(89, "Only 1,089 today")
        assert not self._strict(5, "from 3,5 EUR")

    def test_a_value_that_is_not_a_finite_number_is_skipped_not_matched(self):
        assert self._strict(float("inf"), "any text")  # the name still matches; the price cannot be checked


class TestDefaultIsV5:
    def test_an_audit_without_a_version_uses_v5(self):
        from geo_optimizer.core.audit import run_full_audit

        html = "<html lang='en'><head><title>T</title></head><body><h1>T</h1><p>x</p></body></html>"
        resp = Mock(status_code=200, text=html, content=html.encode(), headers={})
        with (
            patch("geo_optimizer.core.audit.fetch_url", return_value=(resp, None)),
            patch("geo_optimizer.core.audit.check_markdown_negotiation", return_value=False),
        ):
            assert run_full_audit("https://example.com").score_version == 5

    def test_the_default_is_strict_about_a_faq_question_that_is_not_on_the_page(self):
        schema = _page(
            {
                "@type": "FAQPage",
                "name": "Shop",
                "mainEntity": [{"@type": "Question", "name": "Hidden question here?"}],
            },
            "<h1>Shop</h1><p>Welcome.</p>",
        )
        assert schema.visible_match is True  # the loose check v2 used
        assert schema.visible_match_strict is False  # the one the default now applies


class TestDefaultAuditIsStrict:
    """End to end: the audit without a version loses the visibility point that v4 still gives."""

    HTML = (
        "<html lang='en'><head><title>Shop</title>"
        '<script type="application/ld+json">'
        '{"@type": "FAQPage", "name": "Shop", "mainEntity": '
        '[{"@type": "Question", "name": "Hidden question here?", '
        '"acceptedAnswer": {"@type": "Answer", "text": "Hidden answer."}}]}'
        "</script></head><body><h1>Shop</h1><p>Welcome.</p></body></html>"
    )

    def _audit(self, **kwargs):
        from geo_optimizer.core.audit import run_full_audit

        resp = Mock(status_code=200, text=self.HTML, content=self.HTML.encode(), headers={})
        with (
            patch("geo_optimizer.core.audit.fetch_url", return_value=(resp, None)),
            patch("geo_optimizer.core.audit.check_markdown_negotiation", return_value=False),
        ):
            return run_full_audit("https://example.com", **kwargs)

    def test_default_takes_the_visibility_point_away_where_v4_gives_it(self):
        default, v4 = self._audit(), self._audit(score_version=4)
        assert v4.schema.visible_match is True and default.schema.visible_match_strict is False
        assert default.score_version == 5
        assert default.score_breakdown["schema"] < v4.score_breakdown["schema"]


def test_the_mcp_tool_defaults_to_the_engine_default():
    import inspect

    from geo_optimizer.mcp.server import geo_audit

    assert inspect.signature(geo_audit).parameters["score_version"].default == DEFAULT_SCORE_VERSION


def test_the_cli_option_defaults_to_the_engine_default():
    from geo_optimizer.cli.audit_cmd import audit

    option = next(p for p in audit.params if p.name == "score_version")
    assert option.default == str(DEFAULT_SCORE_VERSION)
