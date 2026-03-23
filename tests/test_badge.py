"""
Test per geo_optimizer.web.badge.

Verifica generate_badge_svg: SVG valido, bande di colore, testo score,
badge di errore, sanitizzazione label XSS.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from geo_optimizer.web.badge import BAND_COLORS, generate_badge_svg


# ─── Test: badge normale ──────────────────────────────────────────────────────


def test_badge_good_contiene_score_e_label():
    """generate_badge_svg con score=73 e band='good' restituisce SVG con '73/100'."""
    # Arrange / Act
    svg = generate_badge_svg(score=73, band="good")

    # Assert: testo score presente
    assert "73/100" in svg
    assert "GEO Score" in svg


def test_badge_good_e_xml_valido():
    """generate_badge_svg produce SVG ben formato (XML valido)."""
    # Arrange / Act
    svg = generate_badge_svg(score=73, band="good")

    # Assert: parseable senza eccezioni
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")


def test_badge_excellent_usa_colore_verde():
    """Band 'excellent' usa il colore verde (#22c55e)."""
    # Arrange / Act
    svg = generate_badge_svg(score=95, band="excellent")

    # Assert
    assert BAND_COLORS["excellent"] in svg
    assert "95/100" in svg


def test_badge_foundation_usa_colore_giallo():
    """Band 'foundation' usa il colore giallo (#eab308)."""
    # Arrange / Act
    svg = generate_badge_svg(score=55, band="foundation")

    # Assert
    assert BAND_COLORS["foundation"] in svg
    assert "55/100" in svg


def test_badge_critical_usa_colore_rosso():
    """Band 'critical' usa il colore rosso (#ef4444)."""
    # Arrange / Act
    svg = generate_badge_svg(score=30, band="critical")

    # Assert
    assert BAND_COLORS["critical"] in svg
    assert "30/100" in svg


def test_badge_band_sconosciuta_fallback_a_critical():
    """Band sconosciuta viene normalizzata a 'critical'."""
    # Arrange / Act
    svg = generate_badge_svg(score=50, band="invalid_band")

    # Assert: usa il colore di fallback
    assert BAND_COLORS["critical"] in svg


def test_badge_score_clampato_a_zero():
    """Score negativo viene clampato a 0."""
    # Arrange / Act
    svg = generate_badge_svg(score=-10, band="critical")

    # Assert
    assert "0/100" in svg


def test_badge_score_clampato_a_cento():
    """Score superiore a 100 viene clampato a 100."""
    # Arrange / Act
    svg = generate_badge_svg(score=150, band="excellent")

    # Assert
    assert "100/100" in svg


# ─── Test: badge di errore ────────────────────────────────────────────────────


def test_badge_errore_contiene_testo_error():
    """generate_badge_svg con error=True restituisce SVG con testo 'Error'."""
    # Arrange / Act
    svg = generate_badge_svg(score=0, band="critical", error=True)

    # Assert
    assert "Error" in svg
    assert "0/100" not in svg


def test_badge_errore_e_xml_valido():
    """Badge di errore produce SVG ben formato (XML valido)."""
    # Arrange / Act
    svg = generate_badge_svg(score=0, band="critical", error=True)

    # Assert
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")


def test_badge_errore_usa_colore_grigio():
    """Badge di errore usa il colore grigio (#999999)."""
    # Arrange / Act
    svg = generate_badge_svg(score=0, band="critical", error=True)

    # Assert
    assert "#999999" in svg


def test_badge_errore_con_label_personalizzata():
    """Badge di errore accetta label personalizzata."""
    # Arrange / Act
    svg = generate_badge_svg(score=0, band="critical", label="My Site", error=True)

    # Assert
    assert "My Site" in svg
    assert "Error" in svg


# ─── Test: sanitizzazione label ──────────────────────────────────────────────


def test_badge_label_xss_viene_escapata():
    """Caratteri speciali nella label vengono escapati per prevenire XSS."""
    # Arrange
    label_xss = '<script>alert("xss")</script>'

    # Act
    svg = generate_badge_svg(score=50, band="good", label=label_xss)

    # Assert: il tag <script> non deve essere presente come testo literal non escapato
    assert "<script>" not in svg
    # Le entità HTML devono essere presenti
    assert "&lt;" in svg or "&#x27;" in svg or "&amp;" in svg


def test_badge_label_personalizzata_appare_nel_svg():
    """Label personalizzata appare nell'SVG generato."""
    # Arrange / Act
    svg = generate_badge_svg(score=80, band="good", label="Il Mio Sito")

    # Assert
    assert "Il Mio Sito" in svg


def test_badge_label_lunga_viene_troncata():
    """Label più lunga di 50 caratteri viene troncata."""
    # Arrange
    label_lunga = "A" * 100  # 100 caratteri, massimo 50

    # Act
    svg = generate_badge_svg(score=50, band="good", label=label_lunga)

    # Assert: la label nell'SVG non supera 50 caratteri
    assert "A" * 51 not in svg


# ─── Test: struttura SVG ─────────────────────────────────────────────────────


def test_badge_ha_attributi_accessibilita():
    """Il badge SVG contiene attributi di accessibilità (role, aria-label)."""
    # Arrange / Act
    svg = generate_badge_svg(score=73, band="good")

    # Assert
    assert 'role="img"' in svg
    assert "aria-label" in svg
    assert "<title>" in svg


def test_badge_ha_dimensioni_altezza_20():
    """Il badge SVG ha altezza 20px come Shields.io."""
    # Arrange / Act
    svg = generate_badge_svg(score=73, band="good")

    # Assert
    assert 'height="20"' in svg
