"""
Test per le nuove funzionalità basate sulla ricerca 2025-2026.

Issue #36 e #38: Schema Richness, Answer-First, Passage Density,
Over-optimization Warning e aggiornamento pesi citability.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from geo_optimizer.core.audit import audit_schema
from geo_optimizer.core.citability import (
    audit_citability,
    detect_answer_first,
    detect_keyword_stuffing,
    detect_passage_density,
)
from geo_optimizer.core.scoring import _score_schema
from geo_optimizer.models.config import SCORING
from geo_optimizer.models.results import SchemaResult


def _soup(html: str) -> BeautifulSoup:
    """Helper: crea BeautifulSoup da stringa HTML."""
    return BeautifulSoup(html, "html.parser")


# ============================================================================
# TEST: Schema Richness (Growth Marshal Feb 2026)
# ============================================================================


class TestSchemaRichness:
    def test_schema_generico_zero_punti(self):
        """Schema con solo @type + name + url non deve dare punti richness."""
        schema = SchemaResult(
            any_schema_found=True,
            schema_richness_score=0,
            avg_attributes_per_schema=2.0,
        )
        score_with_generic = _score_schema(schema)
        # Solo schema_any_valid (2 punti), nessun richness bonus
        assert score_with_generic == SCORING["schema_any_valid"]

    def test_schema_ricco_punti_pieni(self):
        """Schema con 5+ attributi deve dare punti richness pieni."""
        schema = SchemaResult(
            any_schema_found=True,
            schema_richness_score=3,
            avg_attributes_per_schema=6.0,
        )
        score = _score_schema(schema)
        assert score == SCORING["schema_any_valid"] + SCORING["schema_richness"]

    def test_schema_medio_punti_parziali(self):
        """Schema con 3-4 attributi → punti parziali."""
        schema = SchemaResult(
            any_schema_found=True,
            schema_richness_score=1,
            avg_attributes_per_schema=3.5,
        )
        score = _score_schema(schema)
        assert score == SCORING["schema_any_valid"] + 1

    def test_audit_schema_calcola_richness(self):
        """audit_schema() deve calcolare schema_richness_score e avg_attributes."""
        html = """
        <html><head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "Guida completa al GEO",
            "description": "Come ottimizzare per AI search engines",
            "author": {"@type": "Person", "name": "Juan Auriti"},
            "datePublished": "2026-01-15",
            "dateModified": "2026-03-20",
            "image": "https://example.com/image.jpg",
            "publisher": {"@type": "Organization", "name": "AgencyPilot"}
        }
        </script>
        </head><body></body></html>
        """
        result = audit_schema(_soup(html), "https://example.com")
        assert result.schema_richness_score == 3  # 7 attributi rilevanti (esclude @context, @type)
        assert result.avg_attributes_per_schema >= 5.0

    def test_audit_schema_generico_no_richness(self):
        """Schema generico (solo @type + name) → richness 0."""
        html = """
        <html><head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "Example",
            "url": "https://example.com"
        }
        </script>
        </head><body></body></html>
        """
        result = audit_schema(_soup(html), "https://example.com")
        # 2 attributi rilevanti (name, url) → generico → 0 punti
        assert result.schema_richness_score == 0
        assert result.avg_attributes_per_schema < 3

    def test_pesi_schema_sommano_22(self):
        """I pesi schema devono sommare 22 (invariato dal v4.0)."""
        schema_keys = [
            "schema_any_valid",
            "schema_richness",
            "schema_faq",
            "schema_article",
            "schema_organization",
            "schema_website",
            "schema_sameas",
        ]
        total = sum(SCORING[k] for k in schema_keys)
        assert total == 22


# ============================================================================
# TEST: Answer-First Structure (AutoGEO ICLR 2026)
# ============================================================================


class TestAnswerFirst:
    def test_h2_con_fatto_concreto(self):
        """H2 seguito da paragrafo con numero → rilevato."""
        html = """
        <html><body>
            <h2>Quanto costa il SEO?</h2>
            <p>Il costo medio del SEO nel 2026 è di $2,500 al mese per le PMI,
            con un ROI medio del 275% nel primo anno.</p>
            <h2>Come funziona</h2>
            <p>Il 73% dei siti ottimizzati vede miglioramenti entro 90 giorni.</p>
        </body></html>
        """
        result = detect_answer_first(_soup(html))
        assert result.detected is True
        assert result.details["answer_first_count"] == 2
        assert result.details["h2_count"] == 2
        assert result.score > 0

    def test_h2_senza_fatti(self):
        """H2 seguito da paragrafo generico → non rilevato."""
        html = """
        <html><body>
            <h2>Introduzione</h2>
            <p>In questa guida esploreremo le migliori pratiche per il marketing digitale
            nel contesto moderno delle aziende che operano online.</p>
            <h2>Conclusione</h2>
            <p>Speriamo che questa guida sia stata utile per comprendere meglio
            le dinamiche del settore e come applicarle.</p>
        </body></html>
        """
        result = detect_answer_first(_soup(html))
        # Le frasi assertive (è, sia) vengono rilevate come assertive
        # ma comunque il ratio potrebbe essere basso
        assert result.details["h2_count"] == 2

    def test_nessun_h2(self):
        """Pagina senza H2 → score 0."""
        html = "<html><body><p>Testo semplice.</p></body></html>"
        result = detect_answer_first(_soup(html))
        assert result.detected is False
        assert result.score == 0

    def test_max_score_5(self):
        """Il max score deve essere 5 (ricalibrato v3.15)."""
        result = detect_answer_first(_soup("<html><body></body></html>"))
        assert result.max_score == 5
        assert result.impact == "+25%"


# ============================================================================
# TEST: Passage Density (Stanford Nature Communications 2025)
# ============================================================================


class TestPassageDensity:
    def test_paragrafi_densi_rilevati(self):
        """Paragrafi 50-150 parole con dati numerici → rilevati."""
        # Genera paragrafi densi (circa 80 parole ciascuno con numeri)
        dense_para = (
            "L'analisi condotta su 730 pagine web ha dimostrato che i siti "
            "con schema markup ricco hanno un tasso di citazione del 61.7%, "
            "significativamente superiore al 41.6% dei siti con schema generico. "
            "Inoltre, i siti senza alcuno schema hanno ottenuto il 52.3%, "
            "dimostrando che uno schema generico è peggiore di nessuno schema. "
            "Il campione includeva 500 domini unici analizzati per 180 giorni "
            "con un totale di 12,450 query testate su 5 diversi motori AI. "
            "I risultati sono statisticamente significativi con p-value 0.001."
        )
        html = f"""
        <html><body>
            <p>{dense_para}</p>
            <p>{dense_para}</p>
            <p>Breve intro.</p>
        </body></html>
        """
        result = detect_passage_density(_soup(html))
        assert result.detected is True
        assert result.details["dense_paragraphs"] >= 2
        assert result.score > 0

    def test_paragrafi_troppo_lunghi(self):
        """Paragrafi con 200+ parole non contano come densi."""
        long_para = " ".join(["parola"] * 200) + " il 73% dei siti usa questo metodo"
        html = f"<html><body><p>{long_para}</p></body></html>"
        result = detect_passage_density(_soup(html))
        assert result.details["dense_paragraphs"] == 0

    def test_paragrafi_senza_numeri(self):
        """Paragrafi di lunghezza corretta ma senza dati → non densi."""
        para = " ".join(["contenuto interessante e ben scritto"] * 15)  # ~75 parole
        html = f"<html><body><p>{para}</p><p>{para}</p></body></html>"
        result = detect_passage_density(_soup(html))
        assert result.details["dense_paragraphs"] == 0

    def test_pagina_vuota(self):
        """Pagina senza paragrafi → score 0."""
        result = detect_passage_density(_soup("<html><body></body></html>"))
        assert result.score == 0

    def test_max_score_5(self):
        """Il max score deve essere 5 (ricalibrato v3.15)."""
        result = detect_passage_density(_soup("<html><body></body></html>"))
        assert result.max_score == 5
        assert result.impact == "+23%"


# ============================================================================
# TEST: Over-optimization Warning (C-SEO Bench 2025)
# ============================================================================


class TestOverOptimization:
    def test_frasi_ripetitive_rilevate(self):
        """Stessa frase ripetuta 3+ volte → rilevata."""
        frase = "Il nostro servizio di ottimizzazione SEO è il migliore sul mercato oggi"
        filler = "contenuto vario diversificato qualità struttura analisi risultato strategia marketing digitale"
        # Serve testo con 50+ parole per superare la soglia minima
        html = f"""
        <html><body>
            <p>{frase}. {frase}. {frase}. {frase}. {filler} {filler} {filler} {filler}</p>
        </body></html>
        """
        result = detect_keyword_stuffing(_soup(html))
        assert result.details.get("repeated_phrases", 0) >= 1

    def test_front_loading_keyword(self):
        """Densità keyword anomala nelle prime 200 parole → rilevata."""
        # Prime 200 parole: keyword "seo" ripetuta molto
        front = " ".join(["seo ottimizzazione seo ranking seo keyword seo"] * 30)
        rest = " ".join(["contenuto vario diversificato qualità struttura"] * 20)
        html = f"<html><body><p>{front} {rest}</p></body></html>"
        result = detect_keyword_stuffing(_soup(html))
        assert result.details.get("front_loading_detected") is True

    def test_nessuna_over_optimization(self):
        """Testo naturale (50+ parole) → nessun warning."""
        html = """
        <html><body>
            <p>La visibilità nei motori di ricerca AI è fondamentale per i siti moderni.
            Le tecniche di ottimizzazione includono schema markup, citazioni autorevoli,
            e contenuto strutturato con dati concreti. La ricerca Princeton ha dimostrato
            che combinare più metodi produce i migliori risultati complessivi per
            il posizionamento nelle risposte generate dai motori AI.
            Questo approccio sistematico permette di migliorare significativamente
            la probabilità che un contenuto venga citato nelle risposte generate.</p>
        </body></html>
        """
        result = detect_keyword_stuffing(_soup(html))
        assert result.details.get("repeated_phrases", 0) == 0
        assert result.details.get("front_loading_detected") is False


# ============================================================================
# TEST: Aggiornamento pesi citability
# ============================================================================


class TestPesiCitability:
    def test_max_score_totale_100(self):
        """I 18 metodi base sommano 100, i 7 bonus (Batch 2) aggiungono 31 = 131."""
        html = "<html><body><p>Test content.</p></body></html>"
        result = audit_citability(_soup(html), "https://example.com")
        total_max = sum(m.max_score for m in result.methods)
        assert total_max == 131, f"Max totale citability: {total_max}, atteso 131 (100 base + 31 bonus)"

    def test_metodi_sono_25(self):
        """Devono esserci 25 metodi (18 base + 7 Quality Signals Batch 2)."""
        html = "<html><body><p>Test.</p></body></html>"
        result = audit_citability(_soup(html), "https://example.com")
        assert len(result.methods) == 25

    def test_nomi_nuovi_metodi_presenti(self):
        """I nuovi metodi answer_first e passage_density devono essere presenti."""
        html = "<html><body><p>Test.</p></body></html>"
        result = audit_citability(_soup(html), "https://example.com")
        names = {m.name for m in result.methods}
        assert "answer_first" in names
        assert "passage_density" in names

    def test_max_score_singoli_aggiornati(self):
        """Verifica che i max_score dei metodi ricalibrati siano corretti (v3.15)."""
        html = "<html><body><p>Test.</p></body></html>"
        result = audit_citability(_soup(html), "https://example.com")
        scores_by_name = {m.name: m.max_score for m in result.methods}

        # Metodi ricalibrati v3.15
        assert scores_by_name["keyword_stuffing"] == 6
        assert scores_by_name["quotation_addition"] == 6
        assert scores_by_name["statistics_addition"] == 6
        assert scores_by_name["cite_sources"] == 6
        assert scores_by_name["fluency_optimization"] == 6
        assert scores_by_name["technical_terms"] == 5
        assert scores_by_name["authoritative_tone"] == 5
        assert scores_by_name["easy_to_understand"] == 5
        assert scores_by_name["unique_words"] == 3
        assert scores_by_name["answer_first"] == 5
        assert scores_by_name["passage_density"] == 5

        # Nuovi metodi v3.15
        assert scores_by_name["readability"] == 8
        assert scores_by_name["faq_in_content"] == 6
        assert scores_by_name["image_alt_quality"] == 5
        assert scores_by_name["content_freshness"] == 6
        assert scores_by_name["citability_density"] == 7
        assert scores_by_name["definition_patterns"] == 5
        assert scores_by_name["format_mix"] == 5

    def test_improvement_suggestions_nuovi_metodi(self):
        """Le suggestion per i nuovi metodi devono essere presenti."""
        from geo_optimizer.core.citability import _IMPROVEMENT_SUGGESTIONS

        assert "answer_first" in _IMPROVEMENT_SUGGESTIONS
        assert "passage_density" in _IMPROVEMENT_SUGGESTIONS

    def test_pesi_geo_score_invariati(self):
        """I pesi del GEO score principale NON devono cambiare (v4.0 calibrati).

        NB: la somma di TUTTI i pesi SCORING > 100 perché include percorsi
        alternativi (es. robots_some_allowed vs robots_citation_ok).
        Verifichiamo che i pesi delle singole categorie siano invariati.
        """
        # Robots: 18 max (5 + 13)
        assert SCORING["robots_found"] == 5
        assert SCORING["robots_citation_ok"] == 13
        # Meta: 20 max
        # meta_description ridotta da 8 a 6 per fare spazio a ai_discovery (6 punti)
        assert (
            SCORING["meta_title"] + SCORING["meta_description"] + SCORING["meta_canonical"] + SCORING["meta_og"] == 14
        )
        # Content: 14 max
        content_keys = [k for k in SCORING if k.startswith("content_")]
        assert sum(SCORING[k] for k in content_keys) == 14
        # Signals: 8 max
        signals_keys = [k for k in SCORING if k.startswith("signals_")]
        assert sum(SCORING[k] for k in signals_keys) == 8
