"""
Test per la funzionalità AI Discovery (geo-checklist.dev standard).

Copre: audit endpoint, scoring, raccomandazioni, summary validation, faq count.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from geo_optimizer.core.audit import (
    audit_ai_discovery,
    _audit_ai_discovery_from_responses,
    build_recommendations,
)
from geo_optimizer.core.scoring import _score_ai_discovery, compute_score_breakdown
from geo_optimizer.models.config import SCORING
from geo_optimizer.models.results import (
    AiDiscoveryResult,
    ContentResult,
    LlmsTxtResult,
    MetaResult,
    RobotsResult,
    SchemaResult,
    SignalsResult,
)


# ─── Helper per mock HTTP ────────────────────────────────────────────────────


def _mock_response(status_code: int, text: str = ""):
    """Crea un mock di risposta HTTP."""
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    return r


# ─── Test audit_ai_discovery (sync) ─────────────────────────────────────────


class TestAuditAiDiscovery:
    """Test per audit_ai_discovery con mock HTTP."""

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_tutti_endpoint_presenti(self, mock_fetch):
        """Verifica che tutti e 4 gli endpoint vengano rilevati."""
        summary = json.dumps({"name": "Test Site", "description": "A test site", "url": "https://example.com"})
        faq = json.dumps([{"question": "Q1?", "answer": "A1"}, {"question": "Q2?", "answer": "A2"}])
        service = json.dumps({"capabilities": ["search", "chat"]})

        # Mappa URL → risposta
        responses = {
            "https://example.com/.well-known/ai.txt": (_mock_response(200, "User-agent: *\nAllow: /"), None),
            "https://example.com/ai/summary.json": (_mock_response(200, summary), None),
            "https://example.com/ai/faq.json": (_mock_response(200, faq), None),
            "https://example.com/ai/service.json": (_mock_response(200, service), None),
        }
        mock_fetch.side_effect = lambda url: responses.get(url, (None, "not found"))

        result = audit_ai_discovery("https://example.com")

        assert result.has_well_known_ai is True
        assert result.has_summary is True
        assert result.has_faq is True
        assert result.has_service is True
        assert result.summary_valid is True
        assert result.faq_count == 2
        assert result.endpoints_found == 4

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_nessun_endpoint_presente(self, mock_fetch):
        """Verifica risultato quando tutti gli endpoint sono 404."""
        mock_fetch.return_value = (_mock_response(404), None)

        result = audit_ai_discovery("https://example.com")

        assert result.has_well_known_ai is False
        assert result.has_summary is False
        assert result.has_faq is False
        assert result.has_service is False
        assert result.endpoints_found == 0

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_summary_senza_campi_richiesti(self, mock_fetch):
        """summary.json presente ma senza name/description → summary_valid=False."""
        # JSON valido ma senza i campi richiesti
        summary_invalid = json.dumps({"url": "https://example.com"})

        responses = {
            "https://example.com/.well-known/ai.txt": (_mock_response(404), None),
            "https://example.com/ai/summary.json": (_mock_response(200, summary_invalid), None),
            "https://example.com/ai/faq.json": (_mock_response(404), None),
            "https://example.com/ai/service.json": (_mock_response(404), None),
        }
        mock_fetch.side_effect = lambda url: responses.get(url, (None, "not found"))

        result = audit_ai_discovery("https://example.com")

        assert result.has_summary is True
        assert result.summary_valid is False
        assert result.endpoints_found == 1

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_summary_con_campi_validi(self, mock_fetch):
        """summary.json con name e description → summary_valid=True."""
        summary_valid = json.dumps({"name": "MySite", "description": "Descrizione del sito"})

        responses = {
            "https://example.com/.well-known/ai.txt": (_mock_response(404), None),
            "https://example.com/ai/summary.json": (_mock_response(200, summary_valid), None),
            "https://example.com/ai/faq.json": (_mock_response(404), None),
            "https://example.com/ai/service.json": (_mock_response(404), None),
        }
        mock_fetch.side_effect = lambda url: responses.get(url, (None, "not found"))

        result = audit_ai_discovery("https://example.com")

        assert result.has_summary is True
        assert result.summary_valid is True

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_faq_formato_dict_con_faqs(self, mock_fetch):
        """faq.json con formato {faqs: [...]} conta correttamente."""
        faq_data = json.dumps({"faqs": [{"q": "Q1", "a": "A1"}, {"q": "Q2", "a": "A2"}, {"q": "Q3", "a": "A3"}]})

        responses = {
            "https://example.com/.well-known/ai.txt": (_mock_response(404), None),
            "https://example.com/ai/summary.json": (_mock_response(404), None),
            "https://example.com/ai/faq.json": (_mock_response(200, faq_data), None),
            "https://example.com/ai/service.json": (_mock_response(404), None),
        }
        mock_fetch.side_effect = lambda url: responses.get(url, (None, "not found"))

        result = audit_ai_discovery("https://example.com")

        assert result.has_faq is True
        assert result.faq_count == 3

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_json_invalido_non_conta(self, mock_fetch):
        """Endpoint con JSON invalido → non viene contato."""
        responses = {
            "https://example.com/.well-known/ai.txt": (_mock_response(404), None),
            "https://example.com/ai/summary.json": (_mock_response(200, "not json{{{"), None),
            "https://example.com/ai/faq.json": (_mock_response(200, "<html>404</html>"), None),
            "https://example.com/ai/service.json": (_mock_response(200, "broken"), None),
        }
        mock_fetch.side_effect = lambda url: responses.get(url, (None, "not found"))

        result = audit_ai_discovery("https://example.com")

        assert result.has_summary is False
        assert result.has_faq is False
        assert result.has_service is False
        assert result.endpoints_found == 0

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_errore_connessione(self, mock_fetch):
        """Errore di connessione → risultato vuoto."""
        mock_fetch.return_value = (None, "Connection refused")

        result = audit_ai_discovery("https://example.com")

        assert result.endpoints_found == 0
        assert result.has_well_known_ai is False


# ─── Test _audit_ai_discovery_from_responses (async path) ────────────────────


class TestAuditAiDiscoveryFromResponses:
    """Test per il percorso async con risposte pre-scaricate."""

    def test_tutte_risposte_valide(self):
        """Risposte HTTP 200 valide → tutti gli endpoint rilevati."""
        r_ai = _mock_response(200, "User-agent: *\nAllow: /")
        r_summary = _mock_response(200, json.dumps({"name": "Test", "description": "Desc"}))
        r_faq = _mock_response(200, json.dumps([{"q": "Q1", "a": "A1"}]))
        r_service = _mock_response(200, json.dumps({"type": "api"}))

        result = _audit_ai_discovery_from_responses(r_ai, r_summary, r_faq, r_service)

        assert result.has_well_known_ai is True
        assert result.has_summary is True
        assert result.summary_valid is True
        assert result.has_faq is True
        assert result.has_service is True
        assert result.endpoints_found == 4

    def test_risposte_none(self):
        """Risposte None (fetch fallito) → risultato vuoto."""
        result = _audit_ai_discovery_from_responses(None, None, None, None)

        assert result.endpoints_found == 0
        assert result.has_well_known_ai is False


# ─── Test scoring ────────────────────────────────────────────────────────────


class TestAiDiscoveryScoring:
    """Test per il calcolo del punteggio AI discovery."""

    def test_score_tutti_presenti(self):
        """Tutti gli endpoint presenti → punteggio massimo (6)."""
        ai_disc = AiDiscoveryResult(
            has_well_known_ai=True,
            has_summary=True,
            has_faq=True,
            has_service=True,
            summary_valid=True,
            endpoints_found=4,
        )
        score = _score_ai_discovery(ai_disc)
        expected = (
            SCORING["ai_discovery_well_known"]
            + SCORING["ai_discovery_summary"]
            + SCORING["ai_discovery_faq"]
            + SCORING["ai_discovery_service"]
        )
        assert score == expected
        assert score == 6

    def test_score_nessun_endpoint(self):
        """Nessun endpoint → punteggio 0."""
        ai_disc = AiDiscoveryResult()
        assert _score_ai_discovery(ai_disc) == 0

    def test_score_none(self):
        """ai_discovery=None → punteggio 0."""
        assert _score_ai_discovery(None) == 0

    def test_score_summary_presente_ma_invalido(self):
        """summary.json presente ma senza campi richiesti → 0 punti per summary."""
        ai_disc = AiDiscoveryResult(
            has_summary=True,
            summary_valid=False,
            endpoints_found=1,
        )
        score = _score_ai_discovery(ai_disc)
        # Solo summary presente ma invalido → 0 punti (non conta)
        assert score == 0

    def test_score_solo_well_known(self):
        """Solo /.well-known/ai.txt → 2 punti."""
        ai_disc = AiDiscoveryResult(has_well_known_ai=True, endpoints_found=1)
        assert _score_ai_discovery(ai_disc) == SCORING["ai_discovery_well_known"]

    def test_breakdown_include_ai_discovery(self):
        """compute_score_breakdown include ai_discovery nel breakdown."""
        robots = RobotsResult()
        llms = LlmsTxtResult()
        schema = SchemaResult()
        meta = MetaResult()
        content = ContentResult()
        signals = SignalsResult()
        ai_disc = AiDiscoveryResult(has_well_known_ai=True, has_faq=True, endpoints_found=2)

        breakdown = compute_score_breakdown(robots, llms, schema, meta, content, signals, ai_disc)

        assert "ai_discovery" in breakdown
        assert breakdown["ai_discovery"] == SCORING["ai_discovery_well_known"] + SCORING["ai_discovery_faq"]

    def test_totale_scoring_100(self):
        """Verifica che il totale massimo SCORING sia 100."""
        # Calcola il massimo raggiungibile per ogni categoria
        max_robots = SCORING["robots_found"] + SCORING["robots_citation_ok"]
        max_llms = (
            SCORING["llms_found"]
            + SCORING["llms_h1"]
            + SCORING["llms_blockquote"]
            + SCORING["llms_sections"]
            + SCORING["llms_links"]
            + SCORING["llms_depth"]
            + SCORING["llms_depth_high"]
            + SCORING["llms_full"]
        )
        max_schema = (
            SCORING["schema_any_valid"]
            + SCORING["schema_richness"]
            + SCORING["schema_faq"]
            + SCORING["schema_article"]
            + SCORING["schema_organization"]
            + SCORING["schema_website"]
            + SCORING["schema_sameas"]
        )
        max_meta = SCORING["meta_title"] + SCORING["meta_description"] + SCORING["meta_canonical"] + SCORING["meta_og"]
        max_content = (
            SCORING["content_h1"]
            + SCORING["content_numbers"]
            + SCORING["content_links"]
            + SCORING["content_word_count"]
            + SCORING["content_heading_hierarchy"]
            + SCORING["content_lists_or_tables"]
            + SCORING["content_front_loading"]
        )
        max_signals = SCORING["signals_lang"] + SCORING["signals_rss"] + SCORING["signals_freshness"]
        max_ai_disc = (
            SCORING["ai_discovery_well_known"]
            + SCORING["ai_discovery_summary"]
            + SCORING["ai_discovery_faq"]
            + SCORING["ai_discovery_service"]
        )

        max_brand_entity = (
            SCORING["brand_entity_coherence"]
            + SCORING["brand_kg_readiness"]
            + SCORING["brand_about_contact"]
            + SCORING["brand_geo_identity"]
            + SCORING["brand_topic_authority"]
        )

        total = max_robots + max_llms + max_schema + max_meta + max_content + max_signals + max_ai_disc + max_brand_entity
        assert total == 100, f"Totale massimo SCORING è {total}, dovrebbe essere 100"


# ─── Test raccomandazioni ────────────────────────────────────────────────────


class TestAiDiscoveryRecommendations:
    """Test per le raccomandazioni AI discovery."""

    def test_raccomandazioni_endpoint_mancanti(self):
        """Endpoint mancanti → raccomandazioni generate."""
        robots = RobotsResult(found=True, citation_bots_ok=True)
        llms = LlmsTxtResult(found=True)
        schema = SchemaResult(has_website=True, has_faq=True)
        meta = MetaResult(has_description=True)
        content = ContentResult(has_numbers=True, has_links=True)
        ai_disc = AiDiscoveryResult()  # tutto assente

        recs = build_recommendations("https://example.com", robots, llms, schema, meta, content, ai_disc)

        # Verifica che ci siano raccomandazioni per ai_discovery
        ai_recs = [r for r in recs if "ai" in r.lower() or "well-known" in r.lower()]
        assert len(ai_recs) >= 3  # well-known, summary, faq, service

    def test_nessuna_raccomandazione_se_tutto_presente(self):
        """Tutti gli endpoint presenti → nessuna raccomandazione AI."""
        robots = RobotsResult(found=True, citation_bots_ok=True)
        llms = LlmsTxtResult(found=True)
        schema = SchemaResult(has_website=True, has_faq=True)
        meta = MetaResult(has_description=True)
        content = ContentResult(has_numbers=True, has_links=True)
        ai_disc = AiDiscoveryResult(
            has_well_known_ai=True,
            has_summary=True,
            summary_valid=True,
            has_faq=True,
            has_service=True,
            endpoints_found=4,
        )

        recs = build_recommendations("https://example.com", robots, llms, schema, meta, content, ai_disc)

        # Nessuna raccomandazione AI-discovery specifica
        ai_recs = [
            r
            for r in recs
            if "well-known" in r.lower()
            or "summary.json" in r.lower()
            or "faq.json" in r.lower()
            or "service.json" in r.lower()
        ]
        assert len(ai_recs) == 0
