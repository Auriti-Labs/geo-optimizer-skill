"""Test that in-page anchor links (href="#about") are recognized as an
About/trust-signal link, not just dedicated URL paths (href="/about").

Before this fix, ABOUT_LINK_PATTERNS in models/config.py only listed
"/"-prefixed path patterns, so a single-page site — which has no dedicated
/about URL, only a same-page section — always failed this check even with a
permanently visible "About" link in its nav (e.g. <a href="#about">About</a>).
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from geo_optimizer.core.audit import audit_brand_entity
from geo_optimizer.core.audit_schema import audit_schema
from geo_optimizer.models.config import ABOUT_LINK_PATTERNS
from geo_optimizer.models.results import ContentResult, MetaResult


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def _has_about_link(html: str) -> bool:
    soup = _soup(html)
    schema_result = audit_schema(soup, "https://example.com/")
    result = audit_brand_entity(soup, schema_result, MetaResult(), ContentResult())
    return result.has_about_link


class TestAboutLinkPatternsConstant:
    def test_still_contains_original_path_patterns(self):
        """Regression guard: the original /about-style patterns must stay."""
        for expected in ("/about", "/chi-siamo", "/team"):
            assert expected in ABOUT_LINK_PATTERNS

    def test_contains_anchor_equivalents(self):
        for expected in ("#about", "#chi-siamo", "#team"):
            assert expected in ABOUT_LINK_PATTERNS


class TestAuditBrandRecognizesAnchorAboutLinks:
    def test_anchor_about_link_is_recognized(self):
        """A single-page site's nav anchor should count as an About link."""
        html = '<html><body><nav><a href="#about">About</a></nav></body></html>'
        assert _has_about_link(html) is True

    def test_dedicated_about_url_still_recognized(self):
        """Regression guard: the original dedicated-URL case must keep working."""
        html = '<html><body><nav><a href="/about">About</a></nav></body></html>'
        assert _has_about_link(html) is True

    def test_anchor_with_suffix_is_recognized(self):
        html = '<html><body><nav><a href="#about-us">About Us</a></nav></body></html>'
        assert _has_about_link(html) is True

    def test_unrelated_anchor_is_not_recognized(self):
        html = '<html><body><nav><a href="#pricing">Pricing</a></nav></body></html>'
        assert _has_about_link(html) is False

    def test_no_links_at_all(self):
        html = "<html><body><p>No nav here.</p></body></html>"
        assert _has_about_link(html) is False
