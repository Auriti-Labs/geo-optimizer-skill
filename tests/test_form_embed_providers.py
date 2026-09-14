"""Test that forms embedded via a known third-party provider (Tally, Typeform,
etc.) are credited toward has_labeled_forms, not scored as "no form found."

Before this fix, the accessible-forms check in audit_webmcp.py only looked
at soup.find_all("form") — native <form> elements in the fetched HTML. A form
embedded via a cross-origin <iframe> (a very common pattern for small-business
contact forms: Tally, Typeform, HubSpot, JotForm, Google Forms, ...) has its
fields on a completely separate page this static fetch never sees, so it was
always scored as having no accessible form — even though these providers
build accessible (labeled) markup into their hosted forms by default.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from geo_optimizer.core.audit import audit_webmcp_readiness
from geo_optimizer.models.config import KNOWN_FORM_EMBED_HOSTS
from geo_optimizer.models.results import SchemaResult


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


class TestKnownFormEmbedHostsConstant:
    def test_includes_common_providers(self):
        for expected in ("tally.so", "typeform.com", "jotform.com", "docs.google.com"):
            assert expected in KNOWN_FORM_EMBED_HOSTS


class TestAuditWebmcpRecognizesEmbeddedFormProviders:
    def test_tally_iframe_via_src_is_recognized(self):
        html = '<html><body><iframe src="https://tally.so/embed/abc123"></iframe></body></html>'
        soup = _soup(html)
        result = audit_webmcp_readiness(soup, html, SchemaResult())
        assert result.has_labeled_forms is True
        assert result.has_embedded_form_provider is True

    def test_tally_iframe_via_data_src_is_recognized(self):
        """Tally's real embed snippet leaves src empty and sets the URL on
        data-tally-src until its loader script runs — this must still count."""
        html = '<html><body><iframe data-tally-src="https://tally.so/embed/abc123" src=""></iframe></body></html>'
        soup = _soup(html)
        result = audit_webmcp_readiness(soup, html, SchemaResult())
        assert result.has_labeled_forms is True
        assert result.has_embedded_form_provider is True

    def test_typeform_iframe_is_recognized(self):
        html = '<html><body><iframe src="https://mycompany.typeform.com/to/abc123"></iframe></body></html>'
        soup = _soup(html)
        result = audit_webmcp_readiness(soup, html, SchemaResult())
        assert result.has_labeled_forms is True

    def test_unknown_iframe_provider_is_not_recognized(self):
        html = '<html><body><iframe src="https://random-unknown-host.example/embed"></iframe></body></html>'
        soup = _soup(html)
        result = audit_webmcp_readiness(soup, html, SchemaResult())
        assert result.has_labeled_forms is False
        assert result.has_embedded_form_provider is False

    def test_no_iframe_at_all_is_unaffected(self):
        html = "<html><body><p>No form here.</p></body></html>"
        soup = _soup(html)
        result = audit_webmcp_readiness(soup, html, SchemaResult())
        assert result.has_labeled_forms is False

    def test_native_labeled_form_takes_precedence_and_still_works(self):
        """Regression guard: a native accessible <form> must keep working
        unchanged, without needing has_embedded_form_provider."""
        html = (
            '<html><body><form action="/submit" method="post">'
            '<label for="email">Email</label><input id="email" name="email">'
            "</form></body></html>"
        )
        soup = _soup(html)
        result = audit_webmcp_readiness(soup, html, SchemaResult())
        assert result.has_labeled_forms is True
        assert result.has_embedded_form_provider is False

    def test_native_unlabeled_form_plus_known_provider_iframe_is_recognized(self):
        """A page can have both an inaccessible native form and a known
        provider iframe elsewhere — the iframe should still be credited."""
        html = (
            '<html><body><form action="/submit"><input name="q"></form>'
            '<iframe src="https://tally.so/embed/abc123"></iframe></body></html>'
        )
        soup = _soup(html)
        result = audit_webmcp_readiness(soup, html, SchemaResult())
        assert result.has_labeled_forms is True
        assert result.has_embedded_form_provider is True
