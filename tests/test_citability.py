"""
Test per geo_optimizer.core.citability — 18 metodi (Princeton GEO + content analysis).

Ogni metodo viene testato con HTML costruito ad hoc per verificare
detection e scoring. Zero chiamate HTTP.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from geo_optimizer.core.citability import (
    audit_citability,
    detect_authoritative_tone,
    detect_citability_density,
    detect_cite_sources,
    detect_content_freshness,
    detect_definition_patterns,
    detect_easy_to_understand,
    detect_faq_in_content,
    detect_fluency,
    detect_format_mix,
    detect_image_alt_quality,
    detect_keyword_stuffing,
    detect_quotations,
    detect_readability,
    detect_statistics,
    detect_technical_terms,
    detect_unique_words,
)


def _soup(html: str) -> BeautifulSoup:
    """Helper: crea BeautifulSoup da stringa HTML."""
    return BeautifulSoup(html, "html.parser")


# ============================================================================
# TEST: Cite Sources (+27%)
# ============================================================================


class TestCiteSources:
    def test_rileva_link_autorevoli(self):
        html = """
        <html><body>
            <p>Secondo <a href="https://en.wikipedia.org/wiki/SEO">Wikipedia</a>,
            il SEO è fondamentale. Vedi anche
            <a href="https://www.nature.com/articles/123">Nature</a> e
            <a href="https://arxiv.org/abs/2311.09735">ArXiv</a>.</p>
        </body></html>
        """
        result = detect_cite_sources(_soup(html), "https://example.com")
        assert result.detected is True
        assert result.details["authoritative_links"] >= 3
        assert result.score > 0

    def test_solo_link_interni_non_rileva(self):
        html = """
        <html><body>
            <a href="https://example.com/page1">Page 1</a>
            <a href="https://example.com/page2">Page 2</a>
        </body></html>
        """
        result = detect_cite_sources(_soup(html), "https://example.com")
        assert result.detected is False
        assert result.details["authoritative_links"] == 0

    def test_sezione_references(self):
        html = """
        <html><body>
            <h2>References</h2>
            <p>Some content here</p>
        </body></html>
        """
        result = detect_cite_sources(_soup(html), "https://example.com")
        assert result.detected is True
        assert result.details["has_reference_section"] is True


# ============================================================================
# TEST: Quotation Addition (+41%)
# ============================================================================


class TestQuotations:
    def test_blockquote_rilevato(self):
        html = """
        <html><body>
            <blockquote>La qualità del contenuto è fondamentale.</blockquote>
            <p>Testo normale.</p>
        </body></html>
        """
        result = detect_quotations(_soup(html))
        assert result.detected is True
        assert result.details["blockquotes"] == 1

    def test_citazione_attribuita_nel_testo(self):
        html = """
        <html><body>
            <p>\u201cLa tecnologia è il futuro dell'educazione\u201d \u2014 Albert Einstein</p>
        </body></html>
        """
        result = detect_quotations(_soup(html))
        assert result.detected is True
        assert result.details["attributed_quotes"] >= 1

    def test_nessuna_citazione(self):
        html = "<html><body><p>Testo semplice senza citazioni.</p></body></html>"
        result = detect_quotations(_soup(html))
        assert result.detected is False


# ============================================================================
# TEST: Statistics Addition (+33%)
# ============================================================================


class TestStatistics:
    def test_percentuali_e_valute(self):
        html = """
        <html><body>
            <p>Il 73% degli utenti preferisce mobile. Il mercato vale $2.5 billion.
            La crescita è del 12.5% anno su anno, con 1,234,567 utenti attivi.</p>
        </body></html>
        """
        result = detect_statistics(_soup(html))
        assert result.detected is True
        assert result.details["stat_matches"] >= 3

    def test_tabella_con_dati(self):
        html = """
        <html><body>
            <table><tr><td>Metrica</td><td>Valore</td></tr>
            <tr><td>Conversioni</td><td>45%</td></tr></table>
        </body></html>
        """
        result = detect_statistics(_soup(html))
        assert result.details["tables_with_data"] >= 1

    def test_testo_senza_numeri(self):
        html = "<html><body><p>Il contenuto è importante per la visibilità online.</p></body></html>"
        result = detect_statistics(_soup(html))
        assert result.detected is False


# ============================================================================
# TEST: Fluency Optimization (+29%)
# ============================================================================


class TestFluency:
    def test_paragrafi_lunghi_con_connettivi(self):
        html = """
        <html><body>
            <p>La visibilità AI è fondamentale per i siti moderni. Pertanto, è necessario
            ottimizzare il contenuto per i motori di ricerca generativi. Inoltre, la struttura
            del testo deve essere chiara e ben organizzata per facilitare la comprensione.</p>
            <p>Di conseguenza, i siti che adottano queste pratiche vedono miglioramenti
            significativi nella loro posizione. Tuttavia, non tutti i metodi producono
            gli stessi risultati, come dimostrato dalla ricerca Princeton.</p>
            <p>In particolare, la combinazione di fluidità e statistiche produce
            i migliori risultati complessivi secondo i dati sperimentali.</p>
            <p>Ad esempio, i siti che usano connettivi logici tra i paragrafi
            ottengono un punteggio più alto nella valutazione di citabilità.</p>
            <p>Infine, è importante notare che la qualità del testo è più
            importante della quantità di contenuto pubblicato.</p>
        </body></html>
        """
        result = detect_fluency(_soup(html))
        assert result.detected is True
        assert result.details["connective_count"] >= 4

    def test_pagina_vuota(self):
        html = "<html><body></body></html>"
        result = detect_fluency(_soup(html))
        assert result.detected is False


# ============================================================================
# TEST: Technical Terms (+18%)
# ============================================================================


class TestTechnicalTerms:
    def test_acronimi_e_codice(self):
        html = """
        <html><body>
            <p>L'API REST usa JSON-LD per i dati strutturati (RFC 9309).
            Il framework supporta HTTP/2 e TLS v1.3.</p>
            <code>schema.validate(data)</code>
        </body></html>
        """
        result = detect_technical_terms(_soup(html))
        assert result.detected is True
        assert result.details["code_blocks"] >= 1

    def test_testo_generico(self):
        html = "<html><body><p>Il nostro sito offre servizi di qualità per tutti.</p></body></html>"
        result = detect_technical_terms(_soup(html))
        assert result.score < 5


# ============================================================================
# TEST: Authoritative Tone (+16%)
# ============================================================================


class TestAuthoritativeTone:
    def test_bio_autore_e_credenziali(self):
        html = """
        <html><body>
            <p>Research shows that AI visibility is crucial. Studies demonstrate
            a clear correlation between content quality and citation rates.</p>
            <div class="author-bio">
                <p>Dr. Jane Smith, PhD — Senior Researcher at MIT</p>
            </div>
            <meta name="author" content="Dr. Jane Smith">
        </body></html>
        """
        result = detect_authoritative_tone(_soup(html))
        assert result.detected is True
        assert result.details["has_author_bio"] is True
        assert len(result.details["credentials"]) >= 1

    def test_tono_incerto(self):
        html = """
        <html><body>
            <p>Maybe this could possibly help. It might be somewhat useful,
            sort of. Perhaps you should kind of try it.</p>
        </body></html>
        """
        result = detect_authoritative_tone(_soup(html))
        assert result.details["hedge_markers"] >= 3


# ============================================================================
# TEST: Easy-to-Understand (+14%)
# ============================================================================


class TestEasyToUnderstand:
    def test_struttura_chiara(self):
        html = """
        <html><body><article>
            <h2>Come funziona</h2>
            <p>Il sistema analizza il contenuto.</p>
            <h2>FAQ</h2>
            <p>Domande frequenti sul servizio.</p>
            <h2>Come iniziare</h2>
            <p>Segui questi passaggi.</p>
            <h3>Passo uno</h3>
            <p>Registrati sul sito.</p>
        </article></body></html>
        """
        result = detect_easy_to_understand(_soup(html))
        assert result.detected is True
        assert result.details["h2_count"] >= 3

    def test_testo_lungo_senza_struttura(self):
        html = "<html><body><p>" + "Parola. " * 200 + "</p></body></html>"
        result = detect_easy_to_understand(_soup(html))
        # Frasi molto corte ("Parola.") → penalizzazione
        assert result.score <= 5


# ============================================================================
# TEST: Unique Words (+7%)
# ============================================================================


class TestUniqueWords:
    def test_vocabolario_ricco(self):
        # Genera testo con parole diverse
        words = [
            f"technology innovation digital transformation artificial intelligence"
            f" machine learning neural network optimization algorithm performance"
            f" database infrastructure architecture deployment monitoring"
            for _ in range(10)
        ]
        html = f"<html><body><p>{' '.join(words)}</p></body></html>"
        result = detect_unique_words(_soup(html))
        assert result.details.get("ttr", 0) > 0

    def test_testo_troppo_corto(self):
        html = "<html><body><p>Breve.</p></body></html>"
        result = detect_unique_words(_soup(html))
        assert result.detected is False


# ============================================================================
# TEST: Keyword Stuffing (-9%)
# ============================================================================


class TestKeywordStuffing:
    def test_nessun_stuffing(self):
        html = """
        <html><body>
            <p>Il marketing digitale comprende diverse strategie di comunicazione.
            La visibilità online è fondamentale per le aziende moderne.
            Le tecniche di ottimizzazione evolvono costantemente.</p>
        </body></html>
        """
        result = detect_keyword_stuffing(_soup(html))
        assert result.detected is False
        assert result.score >= 6  # Bonus pieno

    def test_stuffing_rilevato(self):
        # Ripeti più parole ossessivamente
        stuffed = "ottimizzazione ottimizzazione seo seo ranking ranking keyword keyword "
        filler = "contenuto qualità web analisi risultato strategia digitale marketing "
        html = f"<html><body><p>{stuffed * 15}{filler * 3}</p></body></html>"
        result = detect_keyword_stuffing(_soup(html))
        assert result.detected is True
        assert result.score < 10  # Penalizzato


# ============================================================================
# TEST: Readability Score (+15%)
# ============================================================================


class TestReadability:
    def test_testo_leggibile(self):
        # Testo con frasi di media lunghezza (Grade ~7-8)
        html = """
        <html><body>
            <h2>Come funziona</h2>
            <p>This tool checks your site. It finds problems fast. The score shows how well
            your content works. Most sites need small fixes. Better content means more traffic.
            Simple words help readers understand. Short sentences work best for AI engines.</p>
            <h2>Why it matters</h2>
            <p>Search engines read your text. They pick the best answers for users. If your
            writing is clear and simple, you win. Complex text loses readers quickly. The data
            shows that grade six to eight works best for maximum AI citations.</p>
        </body></html>
        """
        result = detect_readability(_soup(html))
        assert result.max_score == 8
        assert result.score >= 0

    def test_testo_troppo_corto(self):
        html = "<html><body><p>Breve.</p></body></html>"
        result = detect_readability(_soup(html))
        assert result.detected is False


# ============================================================================
# TEST: FAQ-in-Content Check (+12%)
# ============================================================================


class TestFaqInContent:
    def test_heading_con_domanda(self):
        html = """
        <html><body>
            <h2>What is GEO?</h2>
            <p>GEO stands for Generative Engine Optimization. It helps your content
            appear in AI search results like ChatGPT and Perplexity.</p>
            <h2>How does it work?</h2>
            <p>The tool analyzes your HTML content and checks 18 different factors
            that influence AI citation probability.</p>
        </body></html>
        """
        result = detect_faq_in_content(_soup(html))
        assert result.detected is True
        assert result.details["faq_patterns_found"] >= 2

    def test_details_summary(self):
        html = """
        <html><body>
            <details>
                <summary>What is citability?</summary>
                <p>Citability measures how likely AI engines are to cite your content
                when answering user queries.</p>
            </details>
        </body></html>
        """
        result = detect_faq_in_content(_soup(html))
        assert result.detected is True

    def test_nessuna_faq(self):
        html = "<html><body><h2>Overview</h2><p>Some text here.</p></body></html>"
        result = detect_faq_in_content(_soup(html))
        assert result.detected is False


# ============================================================================
# TEST: Image Alt Text Quality (+8%)
# ============================================================================


class TestImageAltQuality:
    def test_alt_descrittivi(self):
        html = """
        <html><body>
            <img src="chart.png" alt="Bar chart showing 73% increase in AI citations after optimization">
            <img src="screenshot.png" alt="Screenshot of the GEO optimizer dashboard with score breakdown">
        </body></html>
        """
        result = detect_image_alt_quality(_soup(html))
        assert result.detected is True
        assert result.details["descriptive_alt"] == 2

    def test_alt_generici(self):
        html = """
        <html><body>
            <img src="a.png" alt="image">
            <img src="b.png" alt="photo">
            <img src="c.png" alt="img001">
        </body></html>
        """
        result = detect_image_alt_quality(_soup(html))
        assert result.details["generic_alt"] >= 3
        assert result.score < 3

    def test_alt_mancanti(self):
        html = """
        <html><body>
            <img src="a.png">
            <img src="b.png" alt="">
        </body></html>
        """
        result = detect_image_alt_quality(_soup(html))
        assert result.details["missing_alt"] == 2

    def test_nessuna_immagine(self):
        html = "<html><body><p>No images here.</p></body></html>"
        result = detect_image_alt_quality(_soup(html))
        assert result.score == 3  # Score neutro


# ============================================================================
# TEST: Content Freshness Warning (+10%)
# ============================================================================


class TestContentFreshness:
    def test_json_ld_recente(self):
        html = """
        <html><body>
            <script type="application/ld+json">
            {"@type": "Article", "dateModified": "2026-03-01", "datePublished": "2025-12-01"}
            </script>
            <p>In 2026, AI search engines dominate.</p>
        </body></html>
        """
        result = detect_content_freshness(_soup(html))
        assert result.detected is True
        assert result.details["is_fresh"] is True

    def test_contenuto_vecchio(self):
        html = """
        <html><body>
            <script type="application/ld+json">
            {"@type": "Article", "dateModified": "2024-01-15"}
            </script>
            <p>Back in 2024 things were different.</p>
        </body></html>
        """
        result = detect_content_freshness(_soup(html))
        assert result.details["is_fresh"] is False

    def test_nessuna_data(self):
        html = "<html><body><p>Content without any date signals.</p></body></html>"
        result = detect_content_freshness(_soup(html))
        assert result.details["date_modified"] is None


# ============================================================================
# TEST: Citability Density (+15%)
# ============================================================================


class TestCitabilityDensity:
    def test_paragrafi_densi(self):
        html = """
        <html><body>
            <p>In 2025, Google processed 8.5 billion searches per day. The AI search
            market grew by 357% according to Stanford Research. Dr. Smith confirmed
            these findings at the MIT Conference in Cambridge.</p>
            <p>The $82.2 billion market represents a 25% CAGR since 2020.
            Microsoft invested $13 billion in OpenAI while Google spent
            $10 billion on DeepMind operations in London.</p>
        </body></html>
        """
        result = detect_citability_density(_soup(html))
        assert result.detected is True
        assert result.details["dense_paragraphs"] >= 1

    def test_paragrafi_generici(self):
        html = """
        <html><body>
            <p>the content is important for websites and good content helps with visibility
            because many people agree that quality matters in the modern digital landscape
            and we should always try to improve our writing skills every single day.</p>
        </body></html>
        """
        result = detect_citability_density(_soup(html))
        assert result.details["dense_paragraphs"] == 0


# ============================================================================
# TEST: Definition Pattern Detection (+10%)
# ============================================================================


class TestDefinitionPatterns:
    def test_definizioni_dopo_heading(self):
        html = """
        <html><body>
            <h1>GEO Optimization Guide</h1>
            <p>GEO is a methodology for optimizing content for AI search engines.
            It was developed by researchers at Princeton University.</p>
            <h2>Citability Score</h2>
            <p>Citability refers to the probability that an AI engine will cite
            your content when answering a user query.</p>
        </body></html>
        """
        result = detect_definition_patterns(_soup(html))
        assert result.detected is True
        assert result.details["definitions_found"] >= 2

    def test_nessuna_definizione(self):
        html = """
        <html><body>
            <h1>Tips</h1>
            <p>Follow these steps to improve your site.</p>
            <h2>Step 1</h2>
            <p>Start by checking your content quality.</p>
        </body></html>
        """
        result = detect_definition_patterns(_soup(html))
        # "Start by" non matcha il pattern di definizione
        assert result.details["definitions_found"] <= 1


# ============================================================================
# TEST: Response Format Mix (+8%)
# ============================================================================


class TestFormatMix:
    def test_mix_completo(self):
        html = """
        <html><body>
            <p>Introduction paragraph.</p>
            <p>Another paragraph with details.</p>
            <p>Third paragraph for good measure.</p>
            <ul><li>Item 1</li><li>Item 2</li></ul>
            <table><tr><td>Data</td><td>Value</td></tr></table>
        </body></html>
        """
        result = detect_format_mix(_soup(html))
        assert result.detected is True
        assert result.details["has_paragraphs"] is True
        assert result.details["has_lists"] is True
        assert result.details["has_tables"] is True
        assert result.score >= 4

    def test_solo_paragrafi(self):
        html = """
        <html><body>
            <p>Only paragraphs here.</p>
            <p>Nothing else.</p>
            <p>Just text.</p>
        </body></html>
        """
        result = detect_format_mix(_soup(html))
        assert result.detected is False
        assert result.score <= 1

    def test_mix_parziale(self):
        html = """
        <html><body>
            <p>Text paragraph.</p>
            <p>Another paragraph.</p>
            <p>Third one.</p>
            <ul><li>A list item</li></ul>
        </body></html>
        """
        result = detect_format_mix(_soup(html))
        assert result.detected is True
        assert result.score >= 2


# ============================================================================
# TEST: Somma pesi = 100
# ============================================================================


class TestWeightSum:
    def test_somma_max_score_uguale_100(self):
        """Verifica che la somma di tutti i max_score sia esattamente 100."""
        html = "<html><body><p>Test content.</p></body></html>"
        result = audit_citability(_soup(html), "https://example.com")
        total_max = sum(m.max_score for m in result.methods)
        assert total_max == 100, f"Somma max_score = {total_max}, atteso 100"


# ============================================================================
# TEST: Orchestratore audit_citability
# ============================================================================


class TestAuditCitability:
    def test_pagina_completa(self):
        html = """
        <html><body>
            <article>
                <meta name="author" content="Dr. Smith">
                <h1>Guida completa al GEO</h1>
                <p>Research shows that AI search engines are growing rapidly.
                According to studies, the market grew by 357% in 2025.
                Furthermore, the adoption rate is accelerating.</p>

                <blockquote cite="https://arxiv.org">"The impact of GEO methods
                is significant" — Princeton Research Team</blockquote>

                <h2>Statistiche chiave</h2>
                <p>Il 73% dei siti non è ottimizzato. Il mercato vale $82.2 billion.
                La crescita è del 25% CAGR.</p>

                <h2>Come funziona</h2>
                <p>L'API REST usa JSON-LD per strutturare i dati (RFC 9309).
                Il protocollo HTTP/2 migliora le performance.</p>
                <code>geo audit --url https://example.com</code>

                <h2>FAQ</h2>
                <p>Domande frequenti sul servizio.</p>

                <h2>References</h2>
                <p><a href="https://arxiv.org/abs/2311.09735">Princeton GEO Paper</a></p>
                <p><a href="https://en.wikipedia.org/wiki/SEO">Wikipedia SEO</a></p>

                <div class="author-bio">
                    <p>Dr. Smith, PhD — Senior Researcher</p>
                </div>
            </article>
        </body></html>
        """
        result = audit_citability(_soup(html), "https://example.com")

        assert result.total_score > 0
        assert result.grade in ("low", "medium", "high", "excellent")
        assert len(result.methods) == 18

        # Verifica che ogni metodo abbia un nome
        names = {m.name for m in result.methods}
        assert "cite_sources" in names
        assert "quotation_addition" in names
        assert "statistics_addition" in names
        assert "keyword_stuffing" in names
        # Nuovi metodi v3.15
        assert "readability" in names
        assert "faq_in_content" in names
        assert "image_alt_quality" in names
        assert "content_freshness" in names
        assert "citability_density" in names
        assert "definition_patterns" in names
        assert "format_mix" in names

    def test_pagina_vuota(self):
        result = audit_citability(_soup("<html><body></body></html>"), "https://example.com")
        assert result.total_score >= 0
        assert len(result.methods) == 18

    def test_top_improvements_generate(self):
        result = audit_citability(_soup("<html><body><p>Testo semplice.</p></body></html>"), "https://example.com")
        assert len(result.top_improvements) > 0
        assert any("+" in imp for imp in result.top_improvements)
