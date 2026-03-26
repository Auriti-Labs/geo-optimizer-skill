"""
Test per geo_optimizer.core.citability — 18 metodi (Princeton GEO + content analysis).

Ogni metodo viene testato con HTML costruito ad hoc per verificare
detection e scoring. Zero chiamate HTTP.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from geo_optimizer.core.citability import (
    audit_citability,
    detect_attribution,
    detect_authoritative_tone,
    detect_blog_structure,
    detect_boilerplate_ratio,
    detect_chatgpt_shopping,
    detect_chunk_quotability,
    detect_citability_density,
    detect_cite_sources,
    detect_comparison_content,
    detect_content_decay,
    detect_content_freshness,
    detect_definition_patterns,
    detect_easy_to_understand,
    detect_eeat,
    detect_faq_in_content,
    detect_fluency,
    detect_format_mix,
    detect_image_alt_quality,
    detect_keyword_stuffing,
    detect_negative_signals,
    detect_nuance_signals,
    detect_quotations,
    detect_readability,
    detect_shopping_readiness,
    detect_snippet_ready,
    detect_statistics,
    detect_technical_terms,
    detect_unique_words,
    detect_voice_search,
    detect_multi_platform,
    detect_entity_disambiguation,
    detect_first_party_data,
    detect_stale_data,
    detect_social_proof,
    detect_accessibility_signals,
    detect_conversion_funnel,
    detect_temporal_coherence,
    detect_anchor_text_quality,
    detect_international_geo,
    detect_crawl_budget,
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
# TEST: Attribution Completeness (+12%) — Batch 2
# ============================================================================


class TestAttribution:
    def test_attribuzione_inline(self):
        html = """
        <html><body>
            <p>According to recent studies, AI adoption grew by 300%.
            Smith (2024) found that content quality matters most.
            As reported by MIT, the trend will continue.</p>
        </body></html>
        """
        result = detect_attribution(_soup(html))
        assert result.detected is True
        assert result.details["inline_attributions"] >= 2
        assert result.score > 0

    def test_nessuna_attribuzione(self):
        html = "<html><body><p>Il contenuto è importante per tutti i siti web moderni.</p></body></html>"
        result = detect_attribution(_soup(html))
        assert result.detected is False
        assert result.details["inline_attributions"] == 0

    def test_footnote_sup(self):
        html = """
        <html><body>
            <p>AI visibility is growing rapidly<sup>1</sup>.
            Content quality matters<sup>2</sup>.
            Research confirms this trend<sup>3</sup>.</p>
        </body></html>
        """
        result = detect_attribution(_soup(html))
        assert result.details["footnotes"] >= 3


# ============================================================================
# TEST: Negative Signals Detection (-15%) — Batch 2
# ============================================================================


class TestNegativeSignals:
    def test_nessun_segnale_negativo(self):
        html = """
        <html><body>
            <meta name="author" content="Dr. Smith">
            <p>This comprehensive guide covers AI optimization strategies.
            The research shows clear patterns in content quality metrics.
            Understanding these patterns helps improve visibility.</p>
        </body></html>
        """
        result = detect_negative_signals(_soup(html))
        assert result.score >= 4
        assert result.details["has_author"] is True

    def test_auto_promozione_eccessiva(self):
        html = """
        <html><body>
            <h2>Our Amazing Product</h2>
            <p>Buy now our incredible tool. Sign up today for free.
            Subscribe to our newsletter. Get started immediately.
            Try free for 30 days. Order now with discount.
            Click here to buy. Don't miss this limited time offer.</p>
        </body></html>
        """
        result = detect_negative_signals(_soup(html))
        assert result.details["cta_count"] >= 2
        assert result.score < 5

    def test_thin_content(self):
        html = """
        <html><body>
            <h2>Complex Topic Analysis</h2>
            <p>Short text here.</p>
        </body></html>
        """
        result = detect_negative_signals(_soup(html))
        assert result.details["is_thin_content"] is True


# ============================================================================
# TEST: Comparison Content (+10%) — Batch 2
# ============================================================================


class TestComparisonContent:
    def test_vs_heading_e_tabella(self):
        html = """
        <html><body>
            <h2>WordPress vs Shopify</h2>
            <table>
                <tr><th>Feature</th><th>WordPress</th><th>Shopify</th></tr>
                <tr><td>Prezzo</td><td>Free</td><td>$29/mo</td></tr>
                <tr><td>Hosting</td><td>Self</td><td>Included</td></tr>
                <tr><td>Plugin</td><td>60k+</td><td>8k+</td></tr>
                <tr><td>SEO</td><td>Excellent</td><td>Good</td></tr>
            </table>
        </body></html>
        """
        result = detect_comparison_content(_soup(html))
        assert result.detected is True
        assert result.details["vs_headings"] >= 1
        assert result.details["large_tables"] >= 1

    def test_nessun_confronto(self):
        html = "<html><body><h2>Guide</h2><p>Simple text without comparisons.</p></body></html>"
        result = detect_comparison_content(_soup(html))
        assert result.detected is False

    def test_pro_contro(self):
        html = """
        <html><body>
            <h2>Pros and Cons of Static Sites</h2>
            <p>There are advantages and disadvantages to consider.</p>
        </body></html>
        """
        result = detect_comparison_content(_soup(html))
        assert result.detected is True
        assert result.details["pro_con_sections"] >= 1


# ============================================================================
# TEST: E-E-A-T Composite (+15%) — Batch 2
# ============================================================================


class TestEeat:
    def test_trust_links_completi(self):
        html = """
        <html><body>
            <a href="/privacy-policy">Privacy Policy</a>
            <a href="/terms-of-service">Terms of Service</a>
            <a href="/about">About Us</a>
            <a href="/contact">Contact</a>
            <link rel="canonical" href="https://example.com/page">
        </body></html>
        """
        result = detect_eeat(_soup(html))
        assert result.detected is True
        assert result.details["trust_link_count"] >= 4
        assert result.details["is_https"] is True

    def test_nessun_segnale_eeat(self):
        html = "<html><body><p>Content without any trust signals.</p></body></html>"
        result = detect_eeat(_soup(html))
        assert result.details["trust_link_count"] == 0
        assert result.score == 0


# ============================================================================
# TEST: Content Decay Detection (-10%) — Batch 2
# ============================================================================


class TestContentDecay:
    def test_contenuto_aggiornato(self):
        html = """
        <html><body>
            <script type="application/ld+json">
            {"@type": "Article", "dateModified": "2026-02-01"}
            </script>
            <p>In 2026, AI search is evolving rapidly.</p>
        </body></html>
        """
        result = detect_content_decay(_soup(html))
        assert result.score >= 4
        assert result.details["is_recently_modified"] is True

    def test_contenuto_con_anni_vecchi(self):
        html = """
        <html><body>
            <p>As of 2022, the market was growing. In 2021, we saw major changes.
            Back in 2020, everything shifted. The 2019 data shows clear trends.</p>
        </body></html>
        """
        result = detect_content_decay(_soup(html))
        assert len(result.details["old_year_references"]) >= 2
        assert result.score < 5


# ============================================================================
# TEST: Content-to-Boilerplate Ratio (+8%) — Batch 2
# ============================================================================


class TestBoilerplateRatio:
    def test_buon_rapporto_con_main(self):
        html = """
        <html><body>
            <nav>Menu item 1 | Menu item 2</nav>
            <main>
                <p>This is the main content of the page with substantial text
                that forms the core of the article. It contains detailed analysis
                and valuable information for the reader.</p>
                <p>Additional paragraph with more useful content that readers
                actually want to read and search engines should index.</p>
            </main>
            <footer>Copyright 2026</footer>
        </body></html>
        """
        result = detect_boilerplate_ratio(_soup(html))
        assert result.details["method"] == "main_tag"
        assert result.details["ratio"] > 0.3

    def test_testo_insufficiente(self):
        html = "<html><body><p>Hi.</p></body></html>"
        result = detect_boilerplate_ratio(_soup(html))
        assert result.score == 2  # Score neutro per testo insufficiente

    def test_euristica_senza_main(self):
        html = """
        <html><body>
            <nav>Nav menu with some text here for navigation</nav>
            <header>Header section with logo and title</header>
            <div>
                <p>Main content paragraph one with detailed information about the topic.</p>
                <p>Main content paragraph two with more analysis and data.</p>
            </div>
            <footer>Footer with copyright and links</footer>
        </body></html>
        """
        result = detect_boilerplate_ratio(_soup(html))
        assert result.details["method"] == "heuristic"


# ============================================================================
# TEST: Nuance/Honesty Signals (+5%) — Batch 2
# ============================================================================


class TestNuanceSignals:
    def test_contenuto_con_nuance(self):
        html = """
        <html><body>
            <p>AI optimization improves visibility. However, it has limitations.
            On the other hand, not every site needs it. Nevertheless, the
            trade-offs are worth considering.</p>
            <h3>Limitations</h3>
            <p>The main drawbacks include complexity and maintenance cost.</p>
        </body></html>
        """
        result = detect_nuance_signals(_soup(html))
        assert result.detected is True
        assert result.details["nuance_patterns"] >= 3
        assert result.details["nuance_headings"] >= 1

    def test_contenuto_senza_nuance(self):
        html = """
        <html><body>
            <p>This is the best tool ever. It works perfectly for everyone.
            There are no problems at all. Everything is amazing.</p>
        </body></html>
        """
        result = detect_nuance_signals(_soup(html))
        assert result.detected is False
        assert result.score == 0


# ============================================================================
# TEST: Snippet-Ready Content (#249)
# ============================================================================


class TestSnippetReady:
    def test_definizione_dopo_heading(self):
        html = """
        <html><body>
            <h2>What is GEO?</h2>
            <p>GEO is the practice of optimizing content for AI search engines.</p>
            <h2>Key Benefits</h2>
            <p>SEO refers to traditional search optimization techniques.</p>
            <h3>Details</h3>
            <p>Some additional context here without definition.</p>
        </body></html>
        """
        result = detect_snippet_ready(_soup(html))
        assert result.detected is True
        assert result.details["snippet_ready_sections"] >= 2
        assert result.score > 0

    def test_domanda_con_risposta_breve(self):
        html = """
        <html><body>
            <h2>How does it work?</h2>
            <p>It works by analyzing structured data and content signals.</p>
        </body></html>
        """
        result = detect_snippet_ready(_soup(html))
        assert result.detected is True
        assert result.details["snippet_ready_sections"] >= 1

    def test_nessun_heading(self):
        html = "<html><body><p>Solo testo.</p></body></html>"
        result = detect_snippet_ready(_soup(html))
        assert result.detected is False
        assert result.score == 0


# ============================================================================
# TEST: Chunk Quotability (#229)
# ============================================================================


class TestChunkQuotability:
    def test_paragrafi_quotabili(self):
        # Paragrafo di ~60 parole con dato concreto
        words = " ".join(["word"] * 55)
        html = f"""
        <html><body>
            <p>In 2024 the market grew by 35% reaching $82 billion.
            {words} This represents a significant shift.</p>
            <p>{words} The growth rate was 25% year over year with data backing it up.</p>
        </body></html>
        """
        result = detect_chunk_quotability(_soup(html))
        assert result.detected is True
        assert result.details["quotable_paragraphs"] >= 1

    def test_paragrafi_troppo_corti(self):
        html = """
        <html><body>
            <p>Short text.</p>
            <p>Another short one.</p>
        </body></html>
        """
        result = detect_chunk_quotability(_soup(html))
        assert result.detected is False
        assert result.details["candidate_paragraphs"] == 0


# ============================================================================
# TEST: Blog Structure (#230)
# ============================================================================


class TestBlogStructure:
    def test_blog_completo(self):
        html = """
        <html><body>
            <script type="application/ld+json">
            {
                "@type": "BlogPosting",
                "datePublished": "2025-01-15",
                "dateModified": "2025-03-01",
                "author": {"@type": "Person", "name": "Juan"},
                "articleSection": "SEO",
                "keywords": ["GEO", "AI"]
            }
            </script>
            <div class="author-bio">Juan — 15 years WordPress developer</div>
            <p>Contenuto del blog.</p>
        </body></html>
        """
        result = detect_blog_structure(_soup(html))
        assert result.detected is True
        assert result.details["has_article_schema"] is True
        assert result.details["has_dates"] is True
        assert result.details["has_author"] is True
        assert result.score >= 3

    def test_nessun_schema_article(self):
        html = """
        <html><body>
            <script type="application/ld+json">
            {"@type": "WebSite", "name": "Example"}
            </script>
            <p>Non è un blog.</p>
        </body></html>
        """
        result = detect_blog_structure(_soup(html))
        assert result.detected is False
        assert result.score == 0
        assert result.details["has_article_schema"] is False


# ============================================================================
# TEST: AI Shopping Readiness (#277)
# ============================================================================


class TestShoppingReadiness:
    def test_product_completo(self):
        html = """
        <html><body>
            <script type="application/ld+json">
            {
                "@type": "Product",
                "name": "GEO Optimizer Pro",
                "offers": {
                    "price": "99.00",
                    "availability": "https://schema.org/InStock"
                },
                "aggregateRating": {
                    "ratingValue": "4.8",
                    "reviewCount": "150"
                }
            }
            </script>
        </body></html>
        """
        result = detect_shopping_readiness(_soup(html))
        assert result.detected is True
        assert result.score == 3
        assert result.details["has_price"] is True
        assert result.details["has_availability"] is True
        assert result.details["has_review_count"] is True

    def test_nessun_product_schema(self):
        html = "<html><body><p>Nessun prodotto.</p></body></html>"
        result = detect_shopping_readiness(_soup(html))
        assert result.detected is False
        assert result.score == 0
        assert result.details["has_product_schema"] is False


# ============================================================================
# TEST: ChatGPT Shopping Feed (#275)
# ============================================================================


class TestChatgptShopping:
    def test_product_completo_chatgpt(self):
        html = """
        <html><body>
            <script type="application/ld+json">
            {
                "@type": "Product",
                "name": "GEO Optimizer Pro",
                "image": "https://example.com/img.jpg",
                "brand": {"@type": "Brand", "name": "Auriti Labs"},
                "offers": {
                    "price": "99.00",
                    "availability": "https://schema.org/InStock"
                }
            }
            </script>
        </body></html>
        """
        result = detect_chatgpt_shopping(_soup(html))
        assert result.detected is True
        assert result.score == 3
        assert result.details["fields_present"] == 5

    def test_product_parziale(self):
        html = """
        <html><body>
            <script type="application/ld+json">
            {
                "@type": "Product",
                "name": "GEO Optimizer",
                "offers": {"price": "49.00"}
            }
            </script>
        </body></html>
        """
        result = detect_chatgpt_shopping(_soup(html))
        assert result.detected is False
        assert result.details["fields_present"] == 2

    def test_nessun_product(self):
        html = "<html><body><p>No product.</p></body></html>"
        result = detect_chatgpt_shopping(_soup(html))
        assert result.detected is False
        assert result.score == 0


# ============================================================================
# TEST: Somma pesi = 100 + bonus
# ============================================================================


class TestWeightSum:
    def test_somma_max_score_base_100_con_bonus(self):
        """Verifica che i 18 metodi base sommano 100, i 7 bonus aggiungono 31."""
        html = "<html><body><p>Test content.</p></body></html>"
        result = audit_citability(_soup(html), "https://example.com")
        # 18 metodi base = 100, 7 bonus batch2 = 31, 5 bonus batch3+4 = 18, 8 bonus batchA = 27, 4 bonus batchB = 13, totale = 189
        total_max = sum(m.max_score for m in result.methods)
        assert total_max == 189, f"Somma max_score = {total_max}, atteso 189 (100 base + 31 batch2 + 18 batch3+4 + 27 batchA + 13 batchB)"
        # Ma il total_score è sempre cappato a 100
        assert result.total_score <= 100


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
        assert len(result.methods) == 42

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
        # Quality Signals Batch 2
        assert "attribution_completeness" in names
        assert "no_negative_signals" in names
        assert "comparison_content" in names
        assert "eeat_signals" in names
        assert "no_content_decay" in names
        assert "boilerplate_ratio" in names
        assert "nuance_signals" in names
        # Quality Signals Batch 3+4
        assert "snippet_ready" in names
        assert "chunk_quotability" in names
        assert "blog_structure" in names
        assert "shopping_readiness" in names
        assert "chatgpt_shopping" in names
        # Quality Signals Batch A v3.16.0
        assert "voice_search_ready" in names
        assert "multi_platform" in names
        assert "entity_disambiguation" in names
        assert "first_party_data" in names
        assert "no_stale_data" in names
        assert "social_proof" in names
        assert "accessibility_signals" in names
        assert "conversion_funnel" in names

    def test_pagina_vuota(self):
        result = audit_citability(_soup("<html><body></body></html>"), "https://example.com")
        assert result.total_score >= 0
        assert len(result.methods) == 42

    def test_top_improvements_generate(self):
        result = audit_citability(_soup("<html><body><p>Testo semplice.</p></body></html>"), "https://example.com")
        assert len(result.top_improvements) > 0
        assert any("+" in imp for imp in result.top_improvements)


# ============================================================================
# TEST: Voice/Conversational Search (+5%) — Batch A v3.16.0
# ============================================================================


class TestVoiceSearch:
    def test_rileva_heading_domanda(self):
        html = """
        <html><body>
            <h2>What is SEO?</h2>
            <p>SEO is the practice of optimizing websites for search engines.</p>
            <h2>How do I improve my rankings?</h2>
            <p>Focus on content quality and technical optimization.</p>
        </body></html>
        """
        result = detect_voice_search(_soup(html))
        assert result.detected
        assert result.score >= 2
        assert result.details["question_headings"] >= 2
        assert result.details["concise_answers"] >= 1

    def test_nessuna_domanda(self):
        html = "<html><body><h2>SEO Guide</h2><p>Some content here.</p></body></html>"
        result = detect_voice_search(_soup(html))
        assert not result.detected
        assert result.score == 0

    def test_speakable_schema(self):
        html = """
        <html><body>
            <script type="application/ld+json">
            {"@type": "WebPage", "speakable": {"@type": "SpeakableSpecification", "cssSelector": [".intro"]}}
            </script>
            <p>Content here.</p>
        </body></html>
        """
        result = detect_voice_search(_soup(html))
        assert result.detected
        assert result.details["has_speakable_schema"]


# ============================================================================
# TEST: Multi-Platform Presence (+10%) — Batch A v3.16.0
# ============================================================================


class TestMultiPlatform:
    def test_rileva_piattaforme_da_sameas(self):
        html = """
        <html><body>
            <script type="application/ld+json">
            {"@type": "Organization", "name": "Test", "sameAs": [
                "https://github.com/test",
                "https://linkedin.com/in/test",
                "https://twitter.com/test",
                "https://www.youtube.com/test",
                "https://medium.com/@test"
            ]}
            </script>
        </body></html>
        """
        result = detect_multi_platform(_soup(html))
        assert result.detected
        assert result.score == 4
        assert result.details["platform_count"] == 5

    def test_poche_piattaforme(self):
        html = """
        <html><body>
            <script type="application/ld+json">
            {"@type": "Organization", "sameAs": ["https://github.com/test"]}
            </script>
        </body></html>
        """
        result = detect_multi_platform(_soup(html))
        assert not result.detected
        assert result.score == 0


# ============================================================================
# TEST: Entity Disambiguation (+8%) — Batch A v3.16.0
# ============================================================================


class TestEntityDisambiguation:
    def test_nomi_consistenti(self):
        html = """
        <html>
        <head>
            <title>AgencyPilot</title>
            <meta property="og:title" content="AgencyPilot">
            <script type="application/ld+json">
            {"@type": "Organization", "name": "AgencyPilot", "sameAs": [
                "https://github.com/test", "https://twitter.com/test",
                "https://linkedin.com/test", "https://youtube.com/test"
            ]}
            </script>
        </head>
        <body><p>AgencyPilot is a SaaS for WordPress management.</p></body>
        </html>
        """
        result = detect_entity_disambiguation(_soup(html))
        assert result.detected
        assert result.score >= 2

    def test_nomi_inconsistenti(self):
        html = """
        <html>
        <head>
            <title>AgencyPilot</title>
            <meta property="og:title" content="Something Else">
        </head>
        <body><p>Random content here.</p></body>
        </html>
        """
        result = detect_entity_disambiguation(_soup(html))
        assert result.score <= 1


# ============================================================================
# TEST: First-Party Data (+12%) — Batch A v3.16.0
# ============================================================================


class TestFirstPartyData:
    def test_rileva_ricerca_propria(self):
        html = """
        <html><body>
            <h2>Methodology</h2>
            <p>Our research analyzed 500 websites over 6 months.
            We found that 73% of sites lack proper schema markup.
            Our data shows a clear correlation between freshness and rankings.</p>
        </body></html>
        """
        result = detect_first_party_data(_soup(html))
        assert result.detected
        assert result.score >= 3
        assert result.details["has_methodology_section"]

    def test_nessun_dato_proprio(self):
        html = "<html><body><p>SEO is important for websites.</p></body></html>"
        result = detect_first_party_data(_soup(html))
        assert not result.detected
        assert result.score == 0


# ============================================================================
# TEST: Stale Data Detection (-10%) — Batch A v3.16.0
# ============================================================================


class TestStaleData:
    def test_contenuto_pulito(self):
        html = "<html><body><p>Fresh content about modern SEO in 2026.</p></body></html>"
        result = detect_stale_data(_soup(html))
        assert result.detected  # detected = pulito (nessuna penalità)
        assert result.score == 4

    def test_copyright_vecchio(self):
        html = """
        <html><body>
            <p>Some content</p>
            <footer>© 2022 Old Company. All rights reserved.</footer>
        </body></html>
        """
        result = detect_stale_data(_soup(html))
        assert not result.detected
        assert result.score <= 2
        assert result.details["old_copyright_in_footer"]

    def test_riferimenti_stale(self):
        html = """
        <html><body>
            <p>As of 2023, the market was growing. In 2022, we saw changes.
            The data from 2021 shows interesting trends.</p>
        </body></html>
        """
        result = detect_stale_data(_soup(html))
        assert not result.detected
        assert result.score < 4


# ============================================================================
# TEST: Social Proof (+8%) — Batch A v3.16.0
# ============================================================================


class TestSocialProof:
    def test_rileva_testimonial_e_rating(self):
        html = """
        <html><body>
            <div class="testimonial">
                <blockquote>"Great product!"<footer>— John Doe</footer></blockquote>
            </div>
            <script type="application/ld+json">
            {"@type": "Product", "aggregateRating": {"@type": "AggregateRating",
             "ratingValue": "4.5", "reviewCount": "150"}}
            </script>
            <img alt="Certified Partner Badge" src="/badge.png">
        </body></html>
        """
        result = detect_social_proof(_soup(html))
        assert result.detected
        assert result.score == 3

    def test_nessun_social_proof(self):
        html = "<html><body><p>Simple text without any proof.</p></body></html>"
        result = detect_social_proof(_soup(html))
        assert result.score == 0


# ============================================================================
# TEST: Accessibility Signals (+5%) — Batch A v3.16.0
# ============================================================================


class TestAccessibilitySignals:
    def test_rileva_html_semantico(self):
        html = """
        <html><body>
            <a href="#main">Skip to content</a>
            <header><nav role="navigation">Menu</nav></header>
            <main role="main"><p>Content</p></main>
            <footer>Footer</footer>
        </body></html>
        """
        result = detect_accessibility_signals(_soup(html))
        assert result.detected
        assert result.score == 3

    def test_nessun_segnale_accessibilita(self):
        html = "<html><body><div>Content in a div only.</div></body></html>"
        result = detect_accessibility_signals(_soup(html))
        assert result.score == 0


# ============================================================================
# TEST: AI Conversion Funnel (+8%) — Batch A v3.16.0
# ============================================================================


class TestConversionFunnel:
    def test_rileva_cta_pricing_contatto(self):
        html = """
        <html><body>
            <a href="/pricing">View Plans</a>
            <a href="mailto:info@example.com">Contact us</a>
            <button>Get Started</button>
        </body></html>
        """
        result = detect_conversion_funnel(_soup(html))
        assert result.detected
        assert result.score == 3
        assert result.details["has_cta"]
        assert result.details["has_pricing_link"]
        assert result.details["has_contact"]

    def test_nessun_funnel(self):
        html = "<html><body><p>Just some informational text.</p></body></html>"
        result = detect_conversion_funnel(_soup(html))
        assert result.score == 0


# ============================================================================
# TEST: Temporal Signal Coherence (+8%) — Batch B v3.16.0
# ============================================================================


class TestTemporalCoherence:
    def test_date_coerenti_schema_e_testo(self):
        """Date in schema e nel testo entro 30 giorni → punteggio pieno."""
        html = """
        <html><body>
            <script type="application/ld+json">
            {"@type": "Article", "dateModified": "2026-03-01"}
            </script>
            <p>Last updated: 2026-03-10</p>
        </body></html>
        """
        result = detect_temporal_coherence(_soup(html))
        assert result.detected
        assert result.score == 4
        assert result.details["is_coherent"]
        assert result.details["date_count"] >= 2

    def test_date_incoerenti(self):
        """Date con differenza > 90 giorni → score basso."""
        html = """
        <html><body>
            <script type="application/ld+json">
            {"@type": "Article", "dateModified": "2025-01-15"}
            </script>
            <p>Last updated: 2025-12-01</p>
        </body></html>
        """
        result = detect_temporal_coherence(_soup(html))
        assert not result.detected
        assert result.details["is_incoherent"]
        assert result.score == 0

    def test_una_sola_data(self):
        """Solo una data trovata → score 1."""
        html = """
        <html><body>
            <script type="application/ld+json">
            {"@type": "Article", "dateModified": "2026-03-15"}
            </script>
            <p>Some text without visible dates.</p>
        </body></html>
        """
        result = detect_temporal_coherence(_soup(html))
        assert result.score == 1
        assert result.details["date_count"] == 1

    def test_nessuna_data(self):
        """Nessuna data trovata → score 0."""
        html = "<html><body><p>No dates anywhere.</p></body></html>"
        result = detect_temporal_coherence(_soup(html))
        assert result.score == 0
        assert result.details["date_count"] == 0

    def test_date_da_meta_tag(self):
        """Date da meta tag article:modified_time coerenti con schema."""
        html = """
        <html>
        <head>
            <meta property="article:modified_time" content="2026-03-05">
        </head>
        <body>
            <script type="application/ld+json">
            {"@type": "Article", "dateModified": "2026-03-10"}
            </script>
        </body></html>
        """
        result = detect_temporal_coherence(_soup(html))
        assert result.detected
        assert result.score == 4
        assert result.details["is_coherent"]


# ============================================================================
# TEST: Internal Link Anchor Text (+5%) — Batch B v3.16.0
# ============================================================================


class TestAnchorTextQuality:
    def test_anchor_descrittivi(self):
        """Tutti anchor descrittivi → punteggio pieno."""
        html = """
        <html><body>
            <a href="/guide/wordpress-security">Complete WordPress security guide</a>
            <a href="/blog/seo-tips">Advanced SEO optimization tips</a>
            <a href="/docs/api-reference">Full API reference documentation</a>
        </body></html>
        """
        result = detect_anchor_text_quality(_soup(html), "https://example.com")
        assert result.detected
        assert result.score == 3
        assert result.details["descriptive_ratio"] >= 0.8

    def test_anchor_generici(self):
        """Tutti anchor generici → score 0."""
        html = """
        <html><body>
            <a href="/page1">click here</a>
            <a href="/page2">read more</a>
            <a href="/page3">here</a>
            <a href="/page4">learn more</a>
        </body></html>
        """
        result = detect_anchor_text_quality(_soup(html), "https://example.com")
        assert result.score == 0
        assert result.details["generic_count"] == 4

    def test_mix_anchor(self):
        """Mix di anchor generici e descrittivi → score intermedio."""
        html = """
        <html><body>
            <a href="/guide">Complete WordPress security guide</a>
            <a href="/page">click here</a>
            <a href="/docs">Full documentation reference</a>
        </body></html>
        """
        result = detect_anchor_text_quality(_soup(html), "https://example.com")
        assert result.score >= 1

    def test_link_esterni_ignorati(self):
        """Link esterni non contano nel calcolo."""
        html = """
        <html><body>
            <a href="https://other.com/page">click here</a>
            <a href="/internal">Great internal documentation page</a>
        </body></html>
        """
        result = detect_anchor_text_quality(_soup(html), "https://example.com")
        assert result.details["total_internal_links"] == 1
        assert result.details["descriptive_count"] == 1

    def test_nessun_link_interno(self):
        """Nessun link interno → score neutro."""
        html = "<html><body><p>No links at all.</p></body></html>"
        result = detect_anchor_text_quality(_soup(html), "https://example.com")
        assert result.score == 2  # Score neutro
        assert result.details["total_internal_links"] == 0


# ============================================================================
# TEST: International GEO (+5%) — Batch B v3.16.0
# ============================================================================


class TestInternationalGeo:
    def test_sito_multilingua_completo(self):
        """Hreflang + inLanguage → punteggio pieno."""
        html = """
        <html lang="en">
        <head>
            <link rel="alternate" hreflang="en" href="https://example.com/en/">
            <link rel="alternate" hreflang="it" href="https://example.com/it/">
            <link rel="alternate" hreflang="es" href="https://example.com/es/">
            <script type="application/ld+json">
            {"@type": "WebPage", "inLanguage": "en"}
            </script>
        </head>
        <body><p>Content here.</p></body>
        </html>
        """
        result = detect_international_geo(_soup(html))
        assert result.detected
        assert result.score == 3
        assert result.details["is_multilingual"]
        assert result.details["hreflang_count"] == 3

    def test_sito_monolingua_non_penalizzato(self):
        """Sito senza hreflang → score 0, ma non penalizzato."""
        html = '<html lang="en"><body><p>English only site.</p></body></html>'
        result = detect_international_geo(_soup(html))
        assert not result.detected
        assert result.score == 0
        assert not result.details["is_multilingual"]

    def test_hreflang_senza_schema(self):
        """Solo hreflang senza inLanguage → score parziale."""
        html = """
        <html lang="en">
        <head>
            <link rel="alternate" hreflang="en" href="https://example.com/en/">
            <link rel="alternate" hreflang="fr" href="https://example.com/fr/">
        </head>
        <body><p>Content here.</p></body>
        </html>
        """
        result = detect_international_geo(_soup(html))
        assert result.detected
        assert result.score >= 1
        assert result.details["hreflang_count"] == 2


# ============================================================================
# TEST: AI Crawl Budget (+5%) — Batch B v3.16.0
# ============================================================================


class TestCrawlBudget:
    def test_pagina_normale(self):
        """Pagina senza restrizioni → punteggio pieno."""
        html = """
        <html>
        <head>
            <meta name="robots" content="index, follow">
            <link rel="sitemap" href="/sitemap.xml">
        </head>
        <body><p>Normal content.</p></body>
        </html>
        """
        result = detect_crawl_budget(_soup(html))
        assert result.detected
        assert result.score == 3
        assert not result.details["has_noindex"]
        assert result.details["has_sitemap_link"]

    def test_noindex_penalita(self):
        """Meta robots noindex → forte penalità."""
        html = """
        <html>
        <head>
            <meta name="robots" content="noindex, follow">
        </head>
        <body><p>Hidden content.</p></body>
        </html>
        """
        result = detect_crawl_budget(_soup(html))
        assert not result.detected
        assert result.details["has_noindex"]
        assert result.score <= 1

    def test_nofollow_penalita(self):
        """Meta robots nofollow → penalità."""
        html = """
        <html>
        <head>
            <meta name="robots" content="index, nofollow">
        </head>
        <body><p>Content without follow.</p></body>
        </html>
        """
        result = detect_crawl_budget(_soup(html))
        assert result.details["has_nofollow"]
        assert result.score < 3

    def test_noindex_nofollow_combinati(self):
        """Meta robots noindex + nofollow → penalità massima."""
        html = """
        <html>
        <head>
            <meta name="robots" content="noindex, nofollow">
        </head>
        <body><p>Completely blocked content.</p></body>
        </html>
        """
        result = detect_crawl_budget(_soup(html))
        assert result.score == 0
        assert result.details["has_noindex"]
        assert result.details["has_nofollow"]

    def test_pagina_pulita_senza_sitemap(self):
        """Pagina senza restrizioni e senza sitemap link → score pieno."""
        html = "<html><head></head><body><p>Clean page.</p></body></html>"
        result = detect_crawl_budget(_soup(html))
        assert result.detected
        assert result.score == 3
        assert not result.details["has_sitemap_link"]
