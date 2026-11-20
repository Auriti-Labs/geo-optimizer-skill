"""Rubric v5: v4 plus a page-aware robots check and a stricter schema visibility check.

v2 stays the default; v1 to v4 numbers must not change.
"""

from __future__ import annotations

import json

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
    def test_default_stays_v2(self):
        assert DEFAULT_SCORE_VERSION == 2

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
    assert out.exit_code == 0 and "--score-version [1|2|3|4|5]" in out.output


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
