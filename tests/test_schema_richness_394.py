"""
Test per il gradino intermedio schema_richness — Enhancement #394.

Verifica che lo scoring sia graduato in 4 livelli:
  - avg >= 5 attrs → 3pt (rich)
  - avg >= 4 attrs → 2pt (medium)
  - avg >= 3 attrs → 1pt (minimal)
  - avg  < 3 attrs → 0pt (generic / no schema)
"""

from __future__ import annotations

import json

from bs4 import BeautifulSoup

from geo_optimizer.core.audit_schema import audit_schema
from geo_optimizer.models.config import (
    SCHEMA_RICHNESS_HIGH,
    SCHEMA_RICHNESS_LOW,
    SCHEMA_RICHNESS_MED,
    SCORING,
)


def _soup(html: str) -> BeautifulSoup:
    """Helper: costruisce BeautifulSoup da stringa HTML."""
    return BeautifulSoup(html, "html.parser")


def _schema_html(schema_dict: dict) -> str:
    """Helper: wrappa un dict come script JSON-LD in pagina HTML minimale."""
    blob = json.dumps(schema_dict)
    return f'<html><head><script type="application/ld+json">{blob}</script></head><body></body></html>'


# ============================================================================
# TEST: costanti di soglia in config.py
# ============================================================================


class TestSchemaRichnessConstants:
    def test_high_threshold_is_five(self):
        """SCHEMA_RICHNESS_HIGH deve essere 5 (schema ricco)."""
        assert SCHEMA_RICHNESS_HIGH == 5

    def test_med_threshold_is_four(self):
        """SCHEMA_RICHNESS_MED deve essere 4 (schema medio)."""
        assert SCHEMA_RICHNESS_MED == 4

    def test_low_threshold_is_three(self):
        """SCHEMA_RICHNESS_LOW deve essere 3 (schema minimale)."""
        assert SCHEMA_RICHNESS_LOW == 3

    def test_max_score_unchanged(self):
        """Il peso SCORING['schema_richness'] deve rimanere 3 (invariato)."""
        assert SCORING["schema_richness"] == 3


# ============================================================================
# TEST: scoring graduato tramite audit_schema()
# ============================================================================


class TestSchemaRichnessGraduatedScoring:
    def test_rich_schema_six_attrs_returns_three_points(self):
        """Schema con 6 attributi rilevanti (avg >= 5) → 3pt."""
        # Arrange: 6 attributi rilevanti (escluso @context, @type)
        html = _schema_html(
            {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": "GEO Guide",
                "description": "Guida completa",
                "author": {"@type": "Person", "name": "Auriti"},
                "datePublished": "2026-01-01",
                "dateModified": "2026-03-01",
                "image": "https://example.com/img.jpg",
            }
        )
        # Act
        result = audit_schema(_soup(html), "https://example.com")
        # Assert
        assert result.schema_richness_score == 3
        assert result.avg_attributes_per_schema >= SCHEMA_RICHNESS_HIGH

    def test_medium_schema_four_point_five_attrs_returns_two_points(self):
        """Schema con media 4.5 attributi rilevanti (>= 4 e < 5) → 2pt."""
        # Due schema: uno con 5 e uno con 4 → media 4.5
        html = f"""<html><head>
        <script type="application/ld+json">
        [{
            json.dumps(
                {
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    "name": "Acme",
                    "url": "https://acme.com",
                    "description": "Desc",
                    "logo": "https://acme.com/logo.png",
                    "telephone": "+39 02 12345",
                }
            )
        },
        {
            json.dumps(
                {
                    "@context": "https://schema.org",
                    "@type": "WebSite",
                    "name": "Acme Site",
                    "url": "https://acme.com",
                    "description": "Desc",
                    "inLanguage": "it",
                }
            )
        }]
        </script></head><body></body></html>"""
        result = audit_schema(_soup(html), "https://example.com")
        assert result.schema_richness_score == 2
        assert SCHEMA_RICHNESS_MED <= result.avg_attributes_per_schema < SCHEMA_RICHNESS_HIGH

    def test_minimal_schema_three_point_five_attrs_returns_one_point(self):
        """Schema con media 3.5 attributi rilevanti (>= 3 e < 4) → 1pt."""
        # Due schema: uno con 4 e uno con 3 → media 3.5
        html = f"""<html><head>
        <script type="application/ld+json">
        [{
            json.dumps(
                {
                    "@context": "https://schema.org",
                    "@type": "WebSite",
                    "name": "Example",
                    "url": "https://example.com",
                    "description": "Test",
                    "potentialAction": {},
                }
            )
        },
        {
            json.dumps(
                {
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    "name": "Example Org",
                    "url": "https://example.com",
                    "description": "Org desc",
                }
            )
        }]
        </script></head><body></body></html>"""
        result = audit_schema(_soup(html), "https://example.com")
        assert result.schema_richness_score == 1
        assert SCHEMA_RICHNESS_LOW <= result.avg_attributes_per_schema < SCHEMA_RICHNESS_MED

    def test_generic_schema_two_attrs_returns_zero_points(self):
        """Schema generico con 2 attributi rilevanti (< 3) → 0pt."""
        html = _schema_html(
            {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": "Example",
                "url": "https://example.com",
            }
        )
        result = audit_schema(_soup(html), "https://example.com")
        assert result.schema_richness_score == 0
        assert result.avg_attributes_per_schema < SCHEMA_RICHNESS_LOW

    def test_no_schema_returns_zero_points_and_zero_avg(self):
        """Pagina senza schema JSON-LD → richness 0pt, avg_attributes 0."""
        html = "<html><head></head><body><p>No schema here.</p></body></html>"
        result = audit_schema(_soup(html), "https://example.com")
        assert result.schema_richness_score == 0
        assert result.avg_attributes_per_schema == 0.0
        assert result.any_schema_found is False


# ============================================================================
# TEST: boundary values (exact thresholds)
# ============================================================================


class TestSchemaRichnessThresholdBoundaries:
    def test_exactly_five_attrs_returns_three_points(self):
        """Esattamente 5 attributi rilevanti → 3pt (boundary SCHEMA_RICHNESS_HIGH)."""
        html = _schema_html(
            {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": "Title",
                "description": "Desc",
                "author": {"@type": "Person", "name": "Author"},
                "datePublished": "2026-01-01",
                "image": "https://example.com/img.jpg",
            }
        )
        result = audit_schema(_soup(html), "https://example.com")
        assert result.avg_attributes_per_schema == 5.0
        assert result.schema_richness_score == 3

    def test_exactly_four_attrs_returns_two_points(self):
        """Esattamente 4 attributi rilevanti → 2pt (boundary SCHEMA_RICHNESS_MED)."""
        html = _schema_html(
            {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "Acme",
                "url": "https://acme.com",
                "description": "Desc",
                "logo": "https://acme.com/logo.png",
            }
        )
        result = audit_schema(_soup(html), "https://example.com")
        assert result.avg_attributes_per_schema == 4.0
        assert result.schema_richness_score == 2

    def test_exactly_three_attrs_returns_one_point(self):
        """Esattamente 3 attributi rilevanti → 1pt (boundary SCHEMA_RICHNESS_LOW)."""
        html = _schema_html(
            {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": "Example",
                "url": "https://example.com",
                "description": "A site",
            }
        )
        result = audit_schema(_soup(html), "https://example.com")
        assert result.avg_attributes_per_schema == 3.0
        assert result.schema_richness_score == 1

    def test_two_attrs_returns_zero_points(self):
        """2 attributi rilevanti → 0pt (sotto SCHEMA_RICHNESS_LOW)."""
        html = _schema_html(
            {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": "Example",
                "url": "https://example.com",
            }
        )
        result = audit_schema(_soup(html), "https://example.com")
        assert result.avg_attributes_per_schema == 2.0
        assert result.schema_richness_score == 0
