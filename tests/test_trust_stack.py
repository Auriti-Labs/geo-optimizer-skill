"""Test per Trust Stack Score — 5-layer trust signal aggregation (#273)."""

from __future__ import annotations

from bs4 import BeautifulSoup

from geo_optimizer.core.trust_stack import audit_trust_stack
from geo_optimizer.models.results import (
    BrandEntityResult,
    ContentResult,
    MetaResult,
    NegativeSignalsResult,
    SchemaResult,
)


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def _base_html(extra_body: str = "") -> str:
    return f"<html><body><h1>Test</h1><p>Content here.</p>{extra_body}</body></html>"


def _defaults(**overrides):
    """Crea parametri default per audit_trust_stack con override."""
    params = {
        "soup": _soup(_base_html()),
        "base_url": "https://example.com",
        "response_headers": {},
        "brand_entity": BrandEntityResult(),
        "schema": SchemaResult(),
        "meta": MetaResult(),
        "content": ContentResult(),
        "negative_signals": NegativeSignalsResult(),
    }
    params.update(overrides)
    return params


# ============================================================================
# Layer 1: Technical Trust
# ============================================================================


class TestTechnicalTrust:
    def test_https_assegna_due_punti(self):
        result = audit_trust_stack(**_defaults(base_url="https://example.com"))
        assert result.technical.score >= 2
        assert "HTTPS" in result.technical.signals_found

    def test_http_zero_punti_https(self):
        result = audit_trust_stack(**_defaults(base_url="http://example.com"))
        assert "HTTPS" not in result.technical.signals_found

    def test_hsts_rilevato(self):
        headers = {"Strict-Transport-Security": "max-age=31536000"}
        result = audit_trust_stack(**_defaults(response_headers=headers))
        assert "HSTS" in result.technical.signals_found

    def test_csp_rilevato(self):
        headers = {"Content-Security-Policy": "default-src 'self'"}
        result = audit_trust_stack(**_defaults(response_headers=headers))
        assert "CSP" in result.technical.signals_found

    def test_xframe_rilevato(self):
        headers = {"X-Frame-Options": "DENY"}
        result = audit_trust_stack(**_defaults(response_headers=headers))
        assert "X-Frame-Options" in result.technical.signals_found

    def test_massimo_cinque_punti(self):
        headers = {
            "Strict-Transport-Security": "max-age=31536000",
            "Content-Security-Policy": "default-src 'self'",
            "X-Frame-Options": "DENY",
        }
        result = audit_trust_stack(**_defaults(
            base_url="https://example.com",
            response_headers=headers,
        ))
        assert result.technical.score == 5


# ============================================================================
# Layer 2: Identity Trust
# ============================================================================


class TestIdentityTrust:
    def test_brand_coerente(self):
        be = BrandEntityResult(brand_name_consistent=True)
        result = audit_trust_stack(**_defaults(brand_entity=be))
        assert "Brand name consistent" in result.identity.signals_found

    def test_about_contact(self):
        be = BrandEntityResult(has_about_link=True, has_contact_info=True)
        result = audit_trust_stack(**_defaults(brand_entity=be))
        assert "About page" in result.identity.signals_found
        assert "Contact info" in result.identity.signals_found

    def test_organization_schema(self):
        schema = SchemaResult(has_organization=True)
        result = audit_trust_stack(**_defaults(schema=schema))
        assert "Organization schema" in result.identity.signals_found

    def test_autore_da_negative_signals(self):
        ns = NegativeSignalsResult(has_author_signal=True)
        result = audit_trust_stack(**_defaults(negative_signals=ns))
        assert "Author identified" in result.identity.signals_found

    def test_vuoto_zero_punti(self):
        result = audit_trust_stack(**_defaults())
        assert result.identity.score == 0


# ============================================================================
# Layer 3: Social Trust
# ============================================================================


class TestSocialTrust:
    def test_sameas_singolo(self):
        schema = SchemaResult(has_sameas=True, sameas_urls=["https://linkedin.com/company/test"])
        result = audit_trust_stack(**_defaults(schema=schema))
        assert result.social.score >= 1

    def test_sameas_multipli(self):
        schema = SchemaResult(has_sameas=True, sameas_urls=["a", "b", "c"])
        result = audit_trust_stack(**_defaults(schema=schema))
        assert "Multiple sameAs (3+)" in result.social.signals_found

    def test_kg_pillar(self):
        be = BrandEntityResult(kg_pillar_count=2)
        result = audit_trust_stack(**_defaults(brand_entity=be))
        assert any("KG pillars" in s for s in result.social.signals_found)

    def test_testimonial_nel_dom(self):
        html = '<html><body><div class="testimonial"><p>Great product, really helped our team improve SEO significantly!</p></div></body></html>'
        result = audit_trust_stack(**_defaults(soup=_soup(html)))
        assert "Reviews/testimonials" in result.social.signals_found

    def test_social_link(self):
        html = '<html><body><a href="https://twitter.com/test">Twitter</a></body></html>'
        result = audit_trust_stack(**_defaults(soup=_soup(html)))
        assert any("Social profiles" in s for s in result.social.signals_found)


# ============================================================================
# Layer 4: Academic Trust
# ============================================================================


class TestAcademicTrust:
    def test_numeri_sufficienti(self):
        content = ContentResult(has_numbers=True, numbers_count=5)
        result = audit_trust_stack(**_defaults(content=content))
        assert any("Statistics cited" in s for s in result.academic.signals_found)

    def test_link_esterni(self):
        content = ContentResult(external_links_count=3)
        result = audit_trust_stack(**_defaults(content=content))
        assert any("External sources" in s for s in result.academic.signals_found)

    def test_link_autorevoli(self):
        html = '<html><body><a href="https://doi.org/10.1234/test">DOI</a></body></html>'
        result = audit_trust_stack(**_defaults(soup=_soup(html)))
        assert any("Authoritative" in s for s in result.academic.signals_found)

    def test_sezione_references(self):
        html = "<html><body><h2>References</h2><p>Source list</p></body></html>"
        result = audit_trust_stack(**_defaults(soup=_soup(html)))
        assert "References section" in result.academic.signals_found

    def test_sezione_fonti_italiano(self):
        html = "<html><body><h2>Fonti</h2><p>Elenco fonti</p></body></html>"
        result = audit_trust_stack(**_defaults(soup=_soup(html)))
        assert "References section" in result.academic.signals_found

    def test_statistiche_originali(self):
        html = "<html><body><p>42% degli utenti secondo lo studio. Il 78% dei report conferma il dato.</p></body></html>"
        result = audit_trust_stack(**_defaults(soup=_soup(html)))
        assert any("Original statistics" in s for s in result.academic.signals_found)


# ============================================================================
# Layer 5: Consistency Trust
# ============================================================================


class TestConsistencyTrust:
    def test_brand_coerente_due_punti(self):
        be = BrandEntityResult(brand_name_consistent=True)
        result = audit_trust_stack(**_defaults(brand_entity=be))
        # brand_name_consistent vale 2 punti nel layer consistency
        assert result.consistency.score >= 2

    def test_no_mixed_signals(self):
        ns = NegativeSignalsResult(has_mixed_signals=False)
        result = audit_trust_stack(**_defaults(negative_signals=ns))
        assert "No mixed signals" in result.consistency.signals_found

    def test_mixed_signals_perde_punto(self):
        ns = NegativeSignalsResult(has_mixed_signals=True, mixed_signal_detail="Title promises X, content delivers Y")
        result = audit_trust_stack(**_defaults(negative_signals=ns))
        assert "No mixed signals" not in result.consistency.signals_found

    def test_schema_desc_meta(self):
        be = BrandEntityResult(schema_desc_matches_meta=True)
        result = audit_trust_stack(**_defaults(brand_entity=be))
        assert "Schema description matches meta" in result.consistency.signals_found

    def test_date_modified(self):
        schema = SchemaResult(has_date_modified=True)
        result = audit_trust_stack(**_defaults(schema=schema))
        assert "dateModified present" in result.consistency.signals_found


# ============================================================================
# Composite Score & Grading
# ============================================================================


class TestComposite:
    def test_grade_a_massimo(self):
        """Tutti i segnali al massimo → grade A."""
        headers = {
            "Strict-Transport-Security": "max-age=31536000",
            "Content-Security-Policy": "default-src 'self'",
            "X-Frame-Options": "DENY",
        }
        be = BrandEntityResult(
            brand_name_consistent=True,
            has_about_link=True,
            has_contact_info=True,
            kg_pillar_count=3,
            schema_desc_matches_meta=True,
        )
        schema = SchemaResult(
            has_organization=True,
            has_person=True,
            has_sameas=True,
            sameas_urls=["a", "b", "c", "d"],
            has_date_modified=True,
        )
        content = ContentResult(
            has_numbers=True,
            numbers_count=10,
            external_links_count=5,
        )
        ns = NegativeSignalsResult(has_author_signal=True, has_mixed_signals=False)
        html = """<html><body>
            <div class="testimonial"><p>Amazing product that really changed how we approach search optimization completely!</p></div>
            <a href="https://twitter.com/test">T</a>
            <a href="https://doi.org/10.1234">DOI</a>
            <h2>References</h2>
            <p>42% degli utenti secondo lo studio. Il 78% dei report conferma.</p>
        </body></html>"""
        result = audit_trust_stack(
            soup=_soup(html),
            base_url="https://example.com",
            response_headers=headers,
            brand_entity=be,
            schema=schema,
            meta=MetaResult(),
            content=content,
            negative_signals=ns,
        )
        assert result.grade == "A"
        assert result.composite_score >= 22
        assert result.trust_level == "excellent"

    def test_grade_f_zero(self):
        """Nessun segnale → grade F."""
        result = audit_trust_stack(**_defaults(base_url="http://example.com"))
        assert result.grade in ("F", "D")
        assert result.composite_score <= 10

    def test_checked_true(self):
        result = audit_trust_stack(**_defaults())
        assert result.checked is True

    def test_composito_somma_layer(self):
        result = audit_trust_stack(**_defaults())
        expected = sum(
            layer.score
            for layer in [result.technical, result.identity, result.social, result.academic, result.consistency]
        )
        assert result.composite_score == expected
