"""Test per audit_brand_entity e audit_signals (fix #333: gap copertura test)."""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from geo_optimizer.core.audit import audit_brand_entity, audit_signals
from geo_optimizer.core.audit_brand import _normalize_brand_name
from geo_optimizer.models.config import ABOUT_LINK_PATTERNS
from geo_optimizer.models.results import ContentResult, MetaResult, SchemaResult


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


# ============================================================================
# TEST: audit_signals
# ============================================================================


class TestAuditSignals:
    def test_signals_con_lang(self):
        """Pagina con lang attribute → has_lang = True."""
        html = '<html lang="it"><body><p>Contenuto</p></body></html>'
        result = audit_signals(_soup(html), SchemaResult())
        assert result.has_lang is True
        assert result.lang_value == "it"

    def test_signals_senza_lang(self):
        """Pagina senza lang attribute → has_lang = False."""
        html = "<html><body><p>Contenuto</p></body></html>"
        result = audit_signals(_soup(html), SchemaResult())
        assert result.has_lang is False

    def test_signals_con_rss(self):
        """Pagina con RSS feed → has_rss = True."""
        html = '<html><head><link type="application/rss+xml" href="/feed.xml"></head><body></body></html>'
        result = audit_signals(_soup(html), SchemaResult())
        assert result.has_rss is True
        assert result.rss_url == "/feed.xml"

    def test_signals_con_atom(self):
        """Pagina con Atom feed → has_rss = True."""
        html = '<html><head><link type="application/atom+xml" href="/atom.xml"></head><body></body></html>'
        result = audit_signals(_soup(html), SchemaResult())
        assert result.has_rss is True

    def test_signals_senza_rss(self):
        """Pagina senza feed → has_rss = False."""
        html = "<html><body><p>Contenuto</p></body></html>"
        result = audit_signals(_soup(html), SchemaResult())
        assert result.has_rss is False

    def test_signals_freshness_da_schema(self):
        """Freshness da dateModified nello schema → has_freshness = True."""
        schema = SchemaResult(raw_schemas=[{"@type": "Article", "dateModified": "2026-03-01"}])
        html = "<html><body><p>Contenuto</p></body></html>"
        result = audit_signals(_soup(html), schema)
        assert result.has_freshness is True
        assert "2026-03-01" in result.freshness_date

    def test_signals_freshness_da_meta(self):
        """Freshness da meta article:modified_time → has_freshness = True."""
        html = '<html><head><meta property="article:modified_time" content="2026-03-15"></head><body></body></html>'
        result = audit_signals(_soup(html), SchemaResult())
        assert result.has_freshness is True

    def test_signals_soup_none_safe(self):
        """Schema vuoto e pagina minimale non crashano."""
        html = "<html><body></body></html>"
        result = audit_signals(_soup(html), SchemaResult())
        assert result.has_lang is False
        assert result.has_rss is False
        assert result.has_freshness is False


# ============================================================================
# TEST: audit_brand_entity
# ============================================================================


def _base_html(title="Acme Corp", h1="Acme Corp", org_name="Acme Corp", extra_body=""):
    """HTML di base con schema Organization, title, h1 coerenti."""
    schema = f'{{"@type":"Organization","name":"{org_name}","url":"https://acme.com"}}'
    return f"""
    <html><head>
        <title>{title}</title>
        <meta property="og:title" content="{title}">
        <script type="application/ld+json">{schema}</script>
    </head><body>
        <h1>{h1}</h1>
        {extra_body}
    </body></html>
    """


class TestAuditBrandEntity:
    def test_brand_coerente(self):
        """Nome brand coerente tra title, h1, schema → brand_name_consistent = True."""
        html = _base_html()
        soup = _soup(html)
        schema = SchemaResult(
            raw_schemas=[{"@type": "Organization", "name": "Acme Corp"}],
            has_organization=True,
        )
        meta = MetaResult(has_title=True, title_text="Acme Corp", has_og_title=True)
        content = ContentResult(has_h1=True, h1_text="Acme Corp")
        result = audit_brand_entity(soup, schema, meta, content)
        assert result.brand_name_consistent is True
        assert "Acme Corp" in result.names_found

    def test_brand_incoerente(self):
        """Nomi tutti diversi (nessuno appare 2+ volte) → brand_name_consistent = False."""
        # HTML senza og:title per evitare che il title appaia 2 volte
        html = """<html><head>
            <title>Alpha</title>
            <script type="application/ld+json">{"@type":"Organization","name":"Beta"}</script>
        </head><body><h1>Gamma</h1></body></html>"""
        soup = _soup(html)
        schema = SchemaResult(
            raw_schemas=[{"@type": "Organization", "name": "Beta"}],
            has_organization=True,
        )
        meta = MetaResult(has_title=True, title_text="Alpha")
        content = ContentResult(has_h1=True, h1_text="Gamma")
        result = audit_brand_entity(soup, schema, meta, content)
        assert result.brand_name_consistent is False

    def test_primary_name_prefers_schema_org_over_positional_h1(self):
        """A sentence-style H1 with no separator (e.g. a hero heading) must not become the
        brand name just because it's positionally first; schema Organization name — structured
        data — outranks it (#perception, found via geoready.dev's own homepage)."""
        html = """<html><head>
            <title>Free AI SEO Audit for ChatGPT &amp; Perplexity — GeoReady</title>
            <script type="application/ld+json">{"@type":"Organization","name":"GeoReady"}</script>
        </head><body><h1>Find the gaps that keep your site out of AI answers.</h1></body></html>"""
        soup = _soup(html)
        schema = SchemaResult(
            raw_schemas=[{"@type": "Organization", "name": "GeoReady"}],
            has_organization=True,
        )
        meta = MetaResult(has_title=True, title_text="Free AI SEO Audit for ChatGPT & Perplexity — GeoReady")
        content = ContentResult(has_h1=True, h1_text="Find the gaps that keep your site out of AI answers.")
        result = audit_brand_entity(soup, schema, meta, content)
        assert result.primary_name == "GeoReady"
        # names_found keeps the raw candidate order — only primary_name is corrected
        assert result.names_found[0] == "Find the gaps that keep your site out of AI answers."

    def test_primary_name_prefers_website_over_organization_when_they_disagree(self):
        """Found live on this project's own geoready.dev homepage: WebSite and
        WebApplication schema both say "GeoReady" (the product/page subject),
        Organization schema says "Auriti Labs" (the publisher) — the two are
        legitimately different entities, and the page's own subject must win,
        not whichever schema type happened to be checked first."""
        html = """<html><head><title>GeoReady</title>
            <script type="application/ld+json">[
                {"@type":"Organization","name":"Auriti Labs"},
                {"@type":"WebSite","name":"GeoReady"},
                {"@type":["WebApplication","SoftwareApplication"],"name":"GeoReady"}
            ]</script>
        </head><body><h1>Find the gaps that keep your site out of AI answers.</h1></body></html>"""
        soup = _soup(html)
        schema = SchemaResult(
            raw_schemas=[
                {"@type": "Organization", "name": "Auriti Labs"},
                {"@type": "WebSite", "name": "GeoReady"},
                {"@type": ["WebApplication", "SoftwareApplication"], "name": "GeoReady"},
            ],
            has_organization=True,
        )
        meta = MetaResult(has_title=True, title_text="GeoReady")
        content = ContentResult(has_h1=True, h1_text="Find the gaps that keep your site out of AI answers.")
        result = audit_brand_entity(soup, schema, meta, content)
        assert result.primary_name == "GeoReady"

    def test_primary_name_uses_organization_when_no_website_schema(self):
        """No WebSite/WebApplication schema at all: Organization is still the only
        structured signal available and must still outrank positional guesses —
        this is the original #perception fix, still valid on its own terms."""
        html = """<html><head>
            <title>Free AI SEO Audit for ChatGPT &amp; Perplexity — GeoReady</title>
            <script type="application/ld+json">{"@type":"Organization","name":"GeoReady"}</script>
        </head><body><h1>Find the gaps that keep your site out of AI answers.</h1></body></html>"""
        soup = _soup(html)
        schema = SchemaResult(
            raw_schemas=[{"@type": "Organization", "name": "GeoReady"}],
            has_organization=True,
        )
        meta = MetaResult(has_title=True, title_text="Free AI SEO Audit for ChatGPT & Perplexity — GeoReady")
        content = ContentResult(has_h1=True, h1_text="Find the gaps that keep your site out of AI answers.")
        result = audit_brand_entity(soup, schema, meta, content)
        assert result.primary_name == "GeoReady"

    def test_primary_name_falls_back_to_most_frequent_without_schema(self):
        """No schema Organization name: fall back to the candidate that repeats across
        sources, not just whichever was found first."""
        html = """<html><head>
            <title>Acme</title>
            <meta property="og:title" content="Acme">
        </head><body><h1>Building the future of widgets</h1></body></html>"""
        soup = _soup(html)
        schema = SchemaResult(raw_schemas=[])
        meta = MetaResult(has_title=True, title_text="Acme", has_og_title=True)
        content = ContentResult(has_h1=True, h1_text="Building the future of widgets")
        result = audit_brand_entity(soup, schema, meta, content)
        assert result.primary_name == "Acme"

    def test_kg_pillars_wikipedia_wikidata(self):
        """sameAs con Wikipedia e Wikidata → kg_pillar_count >= 2."""
        schema_data = {
            "@type": "Organization",
            "name": "Acme",
            "sameAs": ["https://en.wikipedia.org/wiki/Acme", "https://www.wikidata.org/wiki/Q123"],
        }
        import json

        html = f"""<html><head>
            <title>Acme</title>
            <script type="application/ld+json">{json.dumps(schema_data)}</script>
        </head><body><h1>Acme</h1></body></html>"""
        schema = SchemaResult(
            raw_schemas=[schema_data],
            has_organization=True,
            has_sameas=True,
            sameas_urls=["https://en.wikipedia.org/wiki/Acme", "https://www.wikidata.org/wiki/Q123"],
        )
        result = audit_brand_entity(_soup(html), schema, MetaResult(), ContentResult())
        assert result.kg_pillar_count >= 2
        assert result.has_wikipedia is True
        assert result.has_wikidata is True

    def test_kg_pillars_zero(self):
        """Nessun sameAs → kg_pillar_count = 0."""
        schema = SchemaResult(
            raw_schemas=[{"@type": "Organization", "name": "Acme"}],
            has_organization=True,
        )
        html = _base_html()
        result = audit_brand_entity(_soup(html), schema, MetaResult(), ContentResult())
        assert result.kg_pillar_count == 0

    def test_about_link_presente(self):
        """Link /about nel body → has_about_link = True."""
        html = _base_html(extra_body='<a href="/about">About Us</a>')
        result = audit_brand_entity(_soup(html), SchemaResult(), MetaResult(), ContentResult())
        assert result.has_about_link is True

    def test_about_link_assente(self):
        """Nessun link about → has_about_link = False."""
        html = _base_html()
        result = audit_brand_entity(_soup(html), SchemaResult(), MetaResult(), ContentResult())
        assert result.has_about_link is False

    @pytest.mark.parametrize("pattern", ABOUT_LINK_PATTERNS)
    def test_about_link_tutti_i_pattern(self, pattern: str):
        """Ogni pattern in ABOUT_LINK_PATTERNS deve essere riconosciuto (#391)."""
        html = _base_html(extra_body=f'<a href="{pattern}">Link</a>')
        result = audit_brand_entity(_soup(html), SchemaResult(), MetaResult(), ContentResult())
        assert result.has_about_link is True, f"Pattern non riconosciuto: {pattern}"

    def test_contact_info_da_schema(self):
        """Organization con telephone → has_contact_info = True."""
        schema = SchemaResult(
            raw_schemas=[{"@type": "Organization", "name": "Acme", "telephone": "+1234567890"}],
        )
        html = _base_html()
        result = audit_brand_entity(_soup(html), schema, MetaResult(), ContentResult())
        assert result.has_contact_info is True

    def test_hreflang(self):
        """hreflang presente → has_hreflang = True."""
        html = '<html><head><link rel="alternate" hreflang="en" href="/en"><link rel="alternate" hreflang="it" href="/it"></head><body></body></html>'
        result = audit_brand_entity(_soup(html), SchemaResult(), MetaResult(), ContentResult())
        assert result.has_hreflang is True
        assert result.hreflang_count == 2

    def test_faq_depth(self):
        """FAQPage con 5 FAQ → faq_depth = 5."""
        faqs = [{"@type": "Question", "name": f"Q{i}"} for i in range(5)]
        schema = SchemaResult(
            raw_schemas=[{"@type": "FAQPage", "mainEntity": faqs}],
            has_faq=True,
        )
        html = _base_html()
        result = audit_brand_entity(_soup(html), schema, MetaResult(), ContentResult())
        assert result.faq_depth == 5

    def test_graph_spacchettamento(self):
        """Schema con @graph viene spacchettato per description match."""
        schema = SchemaResult(
            raw_schemas=[
                {
                    "@graph": [
                        {
                            "@type": "Organization",
                            "name": "Acme",
                            "description": "Leading provider of widgets and solutions",
                        },
                        {"@type": "WebSite", "name": "Acme"},
                    ]
                }
            ],
        )
        html = _base_html()
        meta = MetaResult(
            has_title=True,
            title_text="Acme",
            has_description=True,
            description_text="Leading provider of widgets and solutions",
        )
        result = audit_brand_entity(_soup(html), schema, meta, ContentResult())
        # Il @graph viene spacchettato e la description match funziona
        assert result.schema_desc_matches_meta is True


# ============================================================================
# TEST: Negative Signals severity bands (fix #333)
# ============================================================================


class TestNegativeSignalsSeverity:
    """Test per le bande di severity medium e low mancanti."""

    def test_severity_low(self):
        """Pochi segnali negativi → severity 'low'."""
        from geo_optimizer.core.audit import audit_negative_signals

        # Testo vario senza autore → scatta almeno no_author
        words = " ".join(f"word{i}" for i in range(300))
        html = f"<html><body><main><h1>Test Page</h1><p>{words}</p></main></body></html>"
        soup = _soup(html)
        content = ContentResult(word_count=300, has_h1=True, h1_text="Test Page", heading_count=1)
        meta = MetaResult(has_title=True, title_text="Test Page")
        result = audit_negative_signals(soup, html, content, meta, SchemaResult())
        assert result.signals_found >= 1
        assert result.severity in ("low", "medium")

    def test_severity_medium_o_high(self):
        """Pagina con popup + CTA eccessivi + no autore → severity medium o high."""
        from geo_optimizer.core.audit import audit_negative_signals

        # Popup classes + molti CTA + no author → 3+ segnali
        ctas = " ".join(["buy now sign up subscribe get started free trial"] * 10)
        html = f"""<html><body><main>
            <h1>Test</h1>
            <div class="modal popup">Buy now!</div>
            <p>{ctas}</p>
        </main></body></html>"""
        soup = _soup(html)
        content = ContentResult(word_count=100, has_h1=True, h1_text="Test", heading_count=1)
        meta = MetaResult(has_title=True, title_text="Test")
        result = audit_negative_signals(soup, html, content, meta, SchemaResult())
        assert result.signals_found >= 2
        assert result.severity in ("medium", "high")


# ============================================================================
# TEST: _normalize_brand_name — legal suffix stripping (#397)
# ============================================================================


class TestNormalizeBrandName:
    """Unit tests for _normalize_brand_name() — legal suffix normalization (#397)."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            # Common English suffixes
            ("Apple Inc.", "apple"),
            ("Apple Inc", "apple"),
            ("Acme Ltd.", "acme"),
            ("Acme Ltd", "acme"),
            ("Widget Corp.", "widget"),
            ("Widget Corp", "widget"),
            ("Holdings LLC", "holdings"),
            # German suffix
            ("Apple GmbH", "apple"),
            # Italian suffixes
            ("Auriti S.r.l.", "auriti"),
            ("Auriti S.p.A.", "auriti"),
            # No suffix — must remain unchanged
            ("Apple", "apple"),
            ("Microsoft", "microsoft"),
            # Mixed case must be handled
            ("ACME CORP.", "acme"),
            ("Foo Bar Ltd.", "foo bar"),
        ],
    )
    def test_suffix_stripped_at_end(self, raw: str, expected: str):
        """Legal suffix at end of name is removed correctly."""
        assert _normalize_brand_name(raw) == expected

    def test_suffix_in_middle_not_removed(self):
        """'Inc.' in the middle of a name must NOT be removed."""
        # "The Inc. Company" → the word "Inc." is not at the trailing position
        result = _normalize_brand_name("The Inc. Company")
        assert "company" in result
        assert result == "the inc. company"

    def test_no_match_different_brands(self):
        """Two completely different names must NOT match after normalization."""
        assert _normalize_brand_name("Apple Inc.") != _normalize_brand_name("Microsoft Ltd.")

    def test_whitespace_stripped(self):
        """Leading/trailing whitespace is stripped."""
        assert _normalize_brand_name("  Acme Ltd.  ") == "acme"

    def test_empty_string_safe(self):
        """Empty string does not crash."""
        assert _normalize_brand_name("") == ""


class TestBrandCoherenceWithLegalSuffixes:
    """Integration tests: brand_name_consistent with mixed legal suffixes (#397)."""

    def _build_inputs(self, title: str, h1: str, schema_name: str):
        """Helper: build soup + SchemaResult + MetaResult + ContentResult."""
        html = f"""<html><head>
            <title>{title}</title>
            <meta property="og:title" content="{title}">
            <script type="application/ld+json">{{"@type":"Organization","name":"{schema_name}"}}</script>
        </head><body><h1>{h1}</h1></body></html>"""
        soup = _soup(html)
        schema = SchemaResult(raw_schemas=[{"@type": "Organization", "name": schema_name}])
        meta = MetaResult(has_title=True, title_text=title, has_og_title=True)
        content = ContentResult(has_h1=True, h1_text=h1)
        return soup, schema, meta, content

    def test_inc_suffix_matches(self):
        """Title 'Apple' vs schema 'Apple Inc.' → brand_name_consistent = True."""
        soup, schema, meta, content = self._build_inputs("Apple", "Apple", "Apple Inc.")
        result = audit_brand_entity(soup, schema, meta, content)
        assert result.brand_name_consistent is True

    def test_ltd_suffix_matches(self):
        """Title 'Acme' vs schema 'Acme Ltd.' → brand_name_consistent = True."""
        soup, schema, meta, content = self._build_inputs("Acme", "Acme", "Acme Ltd.")
        result = audit_brand_entity(soup, schema, meta, content)
        assert result.brand_name_consistent is True

    def test_srl_suffix_matches(self):
        """Title 'Auriti' vs schema 'Auriti S.r.l.' → brand_name_consistent = True."""
        soup, schema, meta, content = self._build_inputs("Auriti", "Auriti", "Auriti S.r.l.")
        result = audit_brand_entity(soup, schema, meta, content)
        assert result.brand_name_consistent is True

    def test_gmbh_suffix_matches(self):
        """Title 'Apple' vs schema 'Apple GmbH' → brand_name_consistent = True."""
        soup, schema, meta, content = self._build_inputs("Apple", "Apple", "Apple GmbH")
        result = audit_brand_entity(soup, schema, meta, content)
        assert result.brand_name_consistent is True

    def test_different_brands_not_consistent(self):
        """All sources with different brand names must stay inconsistent after normalization.

        Uses four distinct base names so none appears >= 2 times even after suffix removal.
        Legal suffix removal must NOT falsely unify different brands.
        """
        # Each source carries a different base name: h1=Alpha, title=Beta, og:title=Gamma, schema=Delta
        html = """<html><head>
            <title>Alpha Corp.</title>
            <meta property="og:title" content="Gamma S.r.l.">
            <script type="application/ld+json">{"@type":"Organization","name":"Delta GmbH"}</script>
        </head><body><h1>Beta Ltd.</h1></body></html>"""
        soup = _soup(html)
        schema = SchemaResult(raw_schemas=[{"@type": "Organization", "name": "Delta GmbH"}])
        meta = MetaResult(has_title=True, title_text="Alpha Corp.", has_og_title=True)
        content = ContentResult(has_h1=True, h1_text="Beta Ltd.")
        result = audit_brand_entity(soup, schema, meta, content)
        assert result.brand_name_consistent is False
