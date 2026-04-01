"""
Test per la funzionalità AI Discovery (geo-checklist.dev standard).

Copre: audit endpoint, scoring, raccomandazioni, summary validation, faq count.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from geo_optimizer.core.audit import (
    _audit_ai_discovery_from_responses,
    audit_ai_discovery,
    build_recommendations,
)
from geo_optimizer.core.scoring import _score_ai_discovery, compute_score_breakdown
from geo_optimizer.models.config import (
    AI_DISCOVERY_FAQ_ANSWER_MIN_LEN,
    AI_DISCOVERY_FAQ_QUESTION_MIN_LEN,
    AI_DISCOVERY_SERVICE_NAME_MIN_LEN,
    AI_DISCOVERY_SUMMARY_DESC_MIN_LEN,
    AI_DISCOVERY_SUMMARY_NAME_MIN_LEN,
    SCORING,
)
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

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_tutti_endpoint_presenti(self, mock_fetch):
        """Verifica che tutti e 4 gli endpoint vengano rilevati."""
        summary = json.dumps({"name": "Test Site", "description": "A test site with enough description length for validation", "url": "https://example.com"})
        faq = json.dumps([{"question": "What is this service?", "answer": "This is a valid answer with enough text"}, {"question": "How does it work exactly?", "answer": "Another answer that meets the minimum length"}])
        service = json.dumps({"name": "Test Service", "capabilities": ["search", "chat"]})

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

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_nessun_endpoint_presente(self, mock_fetch):
        """Verifica risultato quando tutti gli endpoint sono 404."""
        mock_fetch.return_value = (_mock_response(404), None)

        result = audit_ai_discovery("https://example.com")

        assert result.has_well_known_ai is False
        assert result.has_summary is False
        assert result.has_faq is False
        assert result.has_service is False
        assert result.endpoints_found == 0

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
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

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_summary_con_campi_validi(self, mock_fetch):
        """summary.json con name (>=3 char) e description (>=20 char) → summary_valid=True."""
        summary_valid = json.dumps({"name": "MySite", "description": "Descrizione del sito web"})

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

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_faq_formato_dict_con_faqs(self, mock_fetch):
        """faq.json con formato {faqs: [...]} conta correttamente."""
        faq_data = json.dumps({"faqs": [
            {"question": "What is GEO Optimizer?", "answer": "A valid answer with enough text for the check"},
            {"question": "How does scoring work?", "answer": "Another answer meeting minimum length requirement"},
            {"question": "What bots are supported?", "answer": "Third answer also meeting the validation threshold"},
        ]})

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

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
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

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
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
        r_summary = _mock_response(200, json.dumps({"name": "Test Site", "description": "A full description for the test site"}))
        r_faq = _mock_response(200, json.dumps([{"question": "What is this?", "answer": "This is a valid answer with enough length"}]))
        r_service = _mock_response(200, json.dumps({"name": "Test API", "capabilities": ["search"]}))

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


# ─── Test validazione strict #389 ───────────────────────────────────────────


class TestSummaryJsonValidation:
    """Test validazione strict per summary.json (#389)."""

    def _make_responses(self, summary_text: str):
        """Helper: crea risposte mock con solo summary.json presente."""
        responses = {
            "https://example.com/.well-known/ai.txt": (MagicMock(status_code=404), None),
            "https://example.com/ai/summary.json": (MagicMock(status_code=200, text=summary_text), None),
            "https://example.com/ai/faq.json": (MagicMock(status_code=404), None),
            "https://example.com/ai/service.json": (MagicMock(status_code=404), None),
        }
        return lambda url: responses.get(url, (None, "not found"))

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_summary_valido_con_lunghezze_minime(self, mock_fetch):
        """summary.json con name >= 3 char e description >= 20 char → summary_valid=True."""
        # name = 3 char (limite minimo), description = esattamente 20 char
        name = "ABC"
        description = "A" * AI_DISCOVERY_SUMMARY_DESC_MIN_LEN
        payload = json.dumps({"name": name, "description": description})
        mock_fetch.side_effect = self._make_responses(payload)

        result = audit_ai_discovery("https://example.com")

        assert result.has_summary is True
        assert result.summary_valid is True

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_summary_name_troppo_corto(self, mock_fetch):
        """summary.json con name < 3 char → summary_valid=False."""
        # name = 2 char (sotto la soglia minima)
        payload = json.dumps({"name": "AB", "description": "A valid description with enough length"})
        mock_fetch.side_effect = self._make_responses(payload)

        result = audit_ai_discovery("https://example.com")

        assert result.has_summary is True
        assert result.summary_valid is False

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_summary_description_troppo_corta(self, mock_fetch):
        """summary.json con description < 20 char → summary_valid=False."""
        # description = 19 char (sotto la soglia minima)
        payload = json.dumps({"name": "ValidName", "description": "Too short desc"})
        mock_fetch.side_effect = self._make_responses(payload)

        result = audit_ai_discovery("https://example.com")

        assert result.has_summary is True
        assert result.summary_valid is False

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_summary_description_mancante(self, mock_fetch):
        """summary.json senza description → summary_valid=False."""
        payload = json.dumps({"name": "ValidName"})
        mock_fetch.side_effect = self._make_responses(payload)

        result = audit_ai_discovery("https://example.com")

        assert result.has_summary is True
        assert result.summary_valid is False

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_summary_name_mancante(self, mock_fetch):
        """summary.json senza name → summary_valid=False."""
        payload = json.dumps({"description": "A valid description with enough length for validation"})
        mock_fetch.side_effect = self._make_responses(payload)

        result = audit_ai_discovery("https://example.com")

        assert result.has_summary is True
        assert result.summary_valid is False

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_summary_constants_values(self, mock_fetch):
        """Verifica che le costanti di validazione abbiano i valori attesi."""
        assert AI_DISCOVERY_SUMMARY_NAME_MIN_LEN == 3
        assert AI_DISCOVERY_SUMMARY_DESC_MIN_LEN == 20


class TestFaqJsonValidation:
    """Test validazione strict per faq.json (#389)."""

    def _make_responses(self, faq_text: str):
        """Helper: crea risposte mock con solo faq.json presente."""
        responses = {
            "https://example.com/.well-known/ai.txt": (MagicMock(status_code=404), None),
            "https://example.com/ai/summary.json": (MagicMock(status_code=404), None),
            "https://example.com/ai/faq.json": (MagicMock(status_code=200, text=faq_text), None),
            "https://example.com/ai/service.json": (MagicMock(status_code=404), None),
        }
        return lambda url: responses.get(url, (None, "not found"))

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_faq_valido_lista_con_question_e_answer(self, mock_fetch):
        """faq.json lista con question >= 10 char e answer >= 20 char → faq_count corretto."""
        payload = json.dumps([
            {"question": "What is this service?", "answer": "This service provides optimization for AI engines"},
            {"question": "How does it work?", "answer": "It analyzes your site and returns scored recommendations"},
        ])
        mock_fetch.side_effect = self._make_responses(payload)

        result = audit_ai_discovery("https://example.com")

        assert result.has_faq is True
        assert result.faq_count == 2

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_faq_lista_vuota(self, mock_fetch):
        """faq.json con faqs=[] → faq_count=0."""
        payload = json.dumps({"faqs": []})
        mock_fetch.side_effect = self._make_responses(payload)

        result = audit_ai_discovery("https://example.com")

        assert result.has_faq is True
        assert result.faq_count == 0

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_faq_item_senza_question(self, mock_fetch):
        """faq.json con item senza question → non contato."""
        payload = json.dumps([
            {"answer": "A valid answer with enough length for this test"},
        ])
        mock_fetch.side_effect = self._make_responses(payload)

        result = audit_ai_discovery("https://example.com")

        assert result.has_faq is True
        assert result.faq_count == 0

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_faq_item_senza_answer(self, mock_fetch):
        """faq.json con item senza answer → non contato."""
        payload = json.dumps([
            {"question": "What is this service?"},
        ])
        mock_fetch.side_effect = self._make_responses(payload)

        result = audit_ai_discovery("https://example.com")

        assert result.has_faq is True
        assert result.faq_count == 0

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_faq_question_troppo_corta(self, mock_fetch):
        """faq.json con question < 10 char → item non contato."""
        payload = json.dumps([
            {"question": "Short?", "answer": "A valid answer that is long enough for the validation check"},
        ])
        mock_fetch.side_effect = self._make_responses(payload)

        result = audit_ai_discovery("https://example.com")

        assert result.has_faq is True
        assert result.faq_count == 0

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_faq_answer_troppo_corta(self, mock_fetch):
        """faq.json con answer < 20 char → item non contato."""
        payload = json.dumps([
            {"question": "What is this service?", "answer": "Short answer."},
        ])
        mock_fetch.side_effect = self._make_responses(payload)

        result = audit_ai_discovery("https://example.com")

        assert result.has_faq is True
        assert result.faq_count == 0

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_faq_mix_validi_e_invalidi(self, mock_fetch):
        """faq.json con item validi e invalidi → conta solo i validi."""
        payload = json.dumps([
            # Valido
            {"question": "What is this service?", "answer": "A complete and valid answer for the validation check"},
            # Question troppo corta
            {"question": "Why?", "answer": "A complete and valid answer for the validation check"},
            # Answer troppo corta
            {"question": "What is this service?", "answer": "Too short"},
            # Entrambi mancanti
            {},
        ])
        mock_fetch.side_effect = self._make_responses(payload)

        result = audit_ai_discovery("https://example.com")

        assert result.has_faq is True
        assert result.faq_count == 1

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_faq_formato_dict_con_faqs_validi(self, mock_fetch):
        """faq.json {faqs: [...]} con item validi → faq_count corretto."""
        payload = json.dumps({"faqs": [
            {"question": "What is GEO Optimizer?", "answer": "GEO Optimizer is a toolkit for Generative Engine Optimization"},
        ]})
        mock_fetch.side_effect = self._make_responses(payload)

        result = audit_ai_discovery("https://example.com")

        assert result.has_faq is True
        assert result.faq_count == 1

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_faq_constants_values(self, mock_fetch):
        """Verifica che le costanti di validazione FAQ abbiano i valori attesi."""
        assert AI_DISCOVERY_FAQ_QUESTION_MIN_LEN == 10
        assert AI_DISCOVERY_FAQ_ANSWER_MIN_LEN == 20


class TestServiceJsonValidation:
    """Test validazione strict per service.json (#389)."""

    def _make_responses(self, service_text: str):
        """Helper: crea risposte mock con solo service.json presente."""
        responses = {
            "https://example.com/.well-known/ai.txt": (MagicMock(status_code=404), None),
            "https://example.com/ai/summary.json": (MagicMock(status_code=404), None),
            "https://example.com/ai/faq.json": (MagicMock(status_code=404), None),
            "https://example.com/ai/service.json": (MagicMock(status_code=200, text=service_text), None),
        }
        return lambda url: responses.get(url, (None, "not found"))

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_service_valido_con_name_e_capabilities(self, mock_fetch):
        """service.json con name >= 3 char e capabilities non vuote → has_service=True."""
        payload = json.dumps({"name": "GEO API", "capabilities": ["audit", "fix", "schema"]})
        mock_fetch.side_effect = self._make_responses(payload)

        result = audit_ai_discovery("https://example.com")

        assert result.has_service is True
        assert result.endpoints_found == 1

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_service_senza_name(self, mock_fetch):
        """service.json senza name → has_service=False."""
        payload = json.dumps({"capabilities": ["audit", "fix"]})
        mock_fetch.side_effect = self._make_responses(payload)

        result = audit_ai_discovery("https://example.com")

        assert result.has_service is False
        assert result.endpoints_found == 0

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_service_name_troppo_corto(self, mock_fetch):
        """service.json con name < 3 char → has_service=False."""
        payload = json.dumps({"name": "AB", "capabilities": ["audit"]})
        mock_fetch.side_effect = self._make_responses(payload)

        result = audit_ai_discovery("https://example.com")

        assert result.has_service is False

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_service_senza_capabilities(self, mock_fetch):
        """service.json senza capabilities → has_service=False."""
        payload = json.dumps({"name": "GEO API"})
        mock_fetch.side_effect = self._make_responses(payload)

        result = audit_ai_discovery("https://example.com")

        assert result.has_service is False

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_service_capabilities_lista_vuota(self, mock_fetch):
        """service.json con capabilities=[] → has_service=False."""
        payload = json.dumps({"name": "GEO API", "capabilities": []})
        mock_fetch.side_effect = self._make_responses(payload)

        result = audit_ai_discovery("https://example.com")

        assert result.has_service is False

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_service_capabilities_non_lista(self, mock_fetch):
        """service.json con capabilities non lista (stringa) → has_service=False."""
        payload = json.dumps({"name": "GEO API", "capabilities": "audit,fix"})
        mock_fetch.side_effect = self._make_responses(payload)

        result = audit_ai_discovery("https://example.com")

        assert result.has_service is False

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_service_qualsiasi_json_valido_non_sufficiente(self, mock_fetch):
        """service.json con JSON valido ma senza i campi richiesti → has_service=False."""
        payload = json.dumps({"type": "api", "version": "1.0"})
        mock_fetch.side_effect = self._make_responses(payload)

        result = audit_ai_discovery("https://example.com")

        assert result.has_service is False

    @patch("geo_optimizer.core.audit_ai_discovery.fetch_url")
    def test_service_constants_values(self, mock_fetch):
        """Verifica che le costanti di validazione service abbiano i valori attesi."""
        assert AI_DISCOVERY_SERVICE_NAME_MIN_LEN == 3
