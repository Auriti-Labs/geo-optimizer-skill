"""
Test per geo_optimizer.core.citability — 9 metodi Princeton GEO.

Ogni metodo viene testato con HTML costruito ad hoc per verificare
detection e scoring. Zero chiamate HTTP.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from geo_optimizer.core.citability import (
    audit_citability,
    detect_authoritative_tone,
    detect_cite_sources,
    detect_easy_to_understand,
    detect_fluency,
    detect_keyword_stuffing,
    detect_quotations,
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
        assert result.score >= 10  # Bonus pieno

    def test_stuffing_rilevato(self):
        # Ripeti più parole ossessivamente
        stuffed = "ottimizzazione ottimizzazione seo seo ranking ranking keyword keyword "
        filler = "contenuto qualità web analisi risultato strategia digitale marketing "
        html = f"<html><body><p>{stuffed * 15}{filler * 3}</p></body></html>"
        result = detect_keyword_stuffing(_soup(html))
        assert result.detected is True
        assert result.score < 10  # Penalizzato


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
        assert len(result.methods) == 11

        # Verifica che ogni metodo abbia un nome
        names = {m.name for m in result.methods}
        assert "cite_sources" in names
        assert "quotation_addition" in names
        assert "statistics_addition" in names
        assert "keyword_stuffing" in names

    def test_pagina_vuota(self):
        result = audit_citability(_soup("<html><body></body></html>"), "https://example.com")
        assert result.total_score >= 0
        assert len(result.methods) == 11

    def test_top_improvements_generate(self):
        result = audit_citability(_soup("<html><body><p>Testo semplice.</p></body></html>"), "https://example.com")
        assert len(result.top_improvements) > 0
        assert any("+" in imp for imp in result.top_improvements)
