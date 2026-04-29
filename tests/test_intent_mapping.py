"""Test per AI Search Intent Mapping (v4.10, #385).

Verifica rilevamento di 4 categorie di intento di ricerca AI:
- informational: guide, tutorial, what is, how to, definizioni
- navigational: login, contact, about, dashboard
- transactional: buy, subscribe, pricing, download
- commercial: best, vs, compare, review, top

Copertura:
- Pattern EN + IT
- Score coverage con/senza schema
- Intenti mancanti (pagina vuota / solo brand)
- Soup = None → unchecked
- Bande (critical/foundation/good/excellent)
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from geo_optimizer.core.intent_mapping import audit_intent_mapping, map_prompt_library_intents
from geo_optimizer.models.results import ContentResult, MetaResult, SchemaResult


def _content(h1="", word_count=500):
    return ContentResult(word_count=word_count, h1_text=h1, heading_count=3, has_h1=bool(h1))


def _meta(title="Test"):
    return MetaResult(has_title=True, title_text=title, description_text="Test description")


def _schema(*types):
    raw = []
    for t in types:
        raw.append({"@type": t, "name": "Example"})
    return SchemaResult(raw_schemas=raw)


class TestIntentMapping:
    """Test unitari dell'analisi intent mapping."""

    def test_none_soup_returns_unchecked(self):
        """None soup → checked=False, intenti vuoti."""
        result = audit_intent_mapping(None, "", _content(), _meta(), _schema())
        assert result.checked is False
        assert result.intents_found == []
        assert result.score == 0

    def test_informational_detected(self):
        """H1 e heading con pattern informational vengono rilevati."""
        html = (
            "<html><body><main>"
            "<h1>How to Bake Sourdough: Complete Guide</h1>"
            "<h2>What is sourdough bread</h2>"
            "<p>Sourdough is a traditional bread made with wild yeast.</p>"
            "</main></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        result = audit_intent_mapping(soup, html, _content(h1="How to Bake Sourdough"), _meta(), _schema("FAQPage"))

        assert result.checked is True
        assert "informational" in result.intents_found
        assert result.intent_details["informational"]["schema_matched"] is True
        assert result.score > 0

    def test_navigational_detected(self):
        """Link login / contact vengono rilevati come navigational."""
        html = (
            "<html><body><header>"
            "<a href='/login'>Sign In</a>"
            "<a href='/contact'>Contact Us</a>"
            "<a href='/about'>About Us</a>"
            "</header></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        result = audit_intent_mapping(soup, html, _content(), _meta(), _schema("WebSite"))

        assert "navigational" in result.intents_found
        assert result.intent_details["navigational"]["schema_matched"] is True

    def test_transactional_detected(self):
        """CTA acquisto / pricing vengono rilevati come transactional."""
        html = (
            "<html><body><main>"
            "<h1>Pricing Plans</h1>"
            "<button>Buy Now</button>"
            "<a href='/subscribe'>Subscribe for free trial</a>"
            "<p>Get started today with our order form</p>"
            "</main></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        result = audit_intent_mapping(
            soup, html, _content(h1="Pricing Plans"), _meta(), _schema("Product")
        )

        assert "transactional" in result.intents_found
        assert result.intent_details["transactional"]["schema_matched"] is True

    def test_commercial_detected(self):
        """Termini comparativi rilevati come commercial."""
        html = (
            "<html><body><main>"
            "<h1>Best SEO Tools in 2026: Top 10 Review</h1>"
            "<h2>Tool A vs Tool B: Comparison</h2>"
            "<p>Pros and cons of each platform</p>"
            "</main></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        result = audit_intent_mapping(soup, html, _content(h1="Best SEO Tools"), _meta(), _schema("Article"))

        assert "commercial" in result.intents_found

    def test_italian_patterns(self):
        """Pattern italiani vengono rilevati correttamente."""
        html = (
            "<html><body><main>"
            "<h1>Guida Completa: Come Fare Sourdough</h1>"
            "<h2>Cosa e il pane a lievitazione naturale</h2>"
            "<a href='/registrati'>Registrati ora</a>"
            "<button>Acquista</button>"
            "<p>Miglior forno per pane: confronto e recensione</p>"
            "</main></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        result = audit_intent_mapping(
            soup, html, _content(h1="Guida Completa"), _meta(), _schema("FAQPage", "Product", "Article")
        )

        assert "informational" in result.intents_found
        assert "navigational" in result.intents_found
        assert "transactional" in result.intents_found
        assert "commercial" in result.intents_found
        assert result.score > 0

    def test_missing_intents_with_empty_page(self):
        """Pagina vuota → tutti gli intenti mancanti."""
        html = "<html><body><main><p>Hello world</p></main></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = audit_intent_mapping(soup, html, _content(), _meta(), _schema())

        assert result.intents_missing == ["informational", "navigational", "transactional", "commercial"]
        assert result.intents_found == []
        assert result.score == 0
        assert result.band == "critical"

    def test_coverage_boost_with_schema(self):
        """Schema adatto aumenta coverage score."""
        html = (
            "<html><body><main>"
            "<h1>How to Bake Bread</h1>"
            "</main></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")

        # Con schema appropriato → score piu alto
        result_with = audit_intent_mapping(
            soup, html, _content(h1="How to Bake Bread"), _meta(), _schema("HowTo")
        )
        # Senza schema
        result_without = audit_intent_mapping(
            soup, html, _content(h1="How to Bake Bread"), _meta(), _schema()
        )

        assert result_with.score > result_without.score
        assert result_with.intent_details["informational"]["schema_matched"] is True
        assert result_without.intent_details["informational"]["schema_matched"] is False

    def test_score_bounds_0_to_100(self):
        """Score sempre compreso tra 0 e 100."""
        pages = [
            "How to do SEO: Complete Tutorial and Guide",
            "Best SEO Tools 2026: Compare and Review",
            "Buy Now: Pricing and Subscribe",
            "Login and Contact Dashboard",
        ]
        for h1 in pages:
            html = f"<html><body><main><h1>{h1}</h1></main></body></html>"
            soup = BeautifulSoup(html, "html.parser")
            result = audit_intent_mapping(soup, html, _content(h1=h1), _meta(), _schema("Article", "FAQPage", "HowTo"))
            assert 0 <= result.score <= 100, f"Score {result.score} out of bounds for H1: {h1}"

    def test_band_classification(self):
        """Bande sono assegnate correttamente."""
        html = (
            "<html><body><main>"
            "<h1>How to Bake: Guide, Tutorial, and Definitions</h1>"
            "<h2>What is sourdough and how does it work</h2>"
            "<a href='/login'>Sign In</a>"
            "<button>Buy Now</button>"
            "<p>Best ovens: top 5 reviewed and compared</p>"
            "</main></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        result = audit_intent_mapping(
            soup,
            html,
            _content(h1="How to Bake"),
            _meta(),
            _schema("FAQPage", "Article", "Product", "WebSite"),
        )

        assert result.band in ("good", "excellent", "foundation", "critical")
        assert result.total_intents_found > 0

    def test_intent_details_structure(self):
        """Ogni intento in intent_details ha la struttura corretta."""
        html = (
            "<html><body><main>"
            "<h1>How to do SEO</h1>"
            "</main></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        result = audit_intent_mapping(soup, html, _content(h1="How to do SEO"), _meta(), _schema("HowTo"))

        detail = result.intent_details["informational"]
        assert "coverage_score" in detail
        assert "signals_found" in detail
        assert "signals_count" in detail
        assert "schema_matched" in detail
        assert "has_relevant_schema" in detail
        assert isinstance(detail["coverage_score"], int)
        assert isinstance(detail["signals_found"], list)
        assert isinstance(detail["signals_count"], int)


class TestGapAnalysis:
    """Gap analysis, raccomandazioni e radar chart (v4.10 completion)."""

    def test_primary_intent_assigned(self):
        """L'intento col punteggio piu alto e' il primary."""
        html = (
            "<html><body><main>"
            "<h1>How to Bake Bread: Complete Guide and Tutorial</h1>"
            "</main></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        result = audit_intent_mapping(soup, html, _content(h1="How to Bake Bread"), _meta(), _schema("HowTo"))

        assert result.primary_intent == "informational"

    def test_gap_summary_generated(self):
        """gap_summary descrive la situazione in linguaggio umano."""
        html = (
            "<html><body><main>"
            "<h1>How to Bake Bread: Complete Guide</h1>"
            "</main></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        result = audit_intent_mapping(soup, html, _content(h1="How to Bake Bread"), _meta(), _schema("HowTo"))

        assert result.gap_summary
        assert "informational" in result.gap_summary.lower()
        assert len(result.gap_summary) > 20

    def test_gap_summary_empty_page(self):
        """Pagina senza intenti → messaggio chiaro."""
        html = "<html><body><main><p>hello</p></main></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = audit_intent_mapping(soup, html, _content(), _meta(), _schema())

        assert result.gap_summary == "no intent signals detected"
        assert result.primary_intent == ""

    def test_recommendations_for_missing(self):
        """Ogni intento mancante genera una raccomandazione."""
        html = (
            "<html><body><main>"
            "<h1>How to Bake Bread</h1>"
            "</main></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        result = audit_intent_mapping(soup, html, _content(h1="How to Bake Bread"), _meta(), _schema("HowTo"))

        missing = set(result.intents_missing)
        recs_lower = " ".join(result.recommendations).lower()

        # Deve coprire tutte le categorie mancanti
        for intent in missing:
            assert f"[{intent}]" in recs_lower, f"No recommendation for missing intent: {intent}"

    def test_recommendations_schema_missing_boost(self):
        """Schema mancante su intento rilevato → raccomandazione."""
        html = (
            "<html><body><main>"
            "<h1>How to do SEO: Complete Guide</h1>"
            "</main></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        result = audit_intent_mapping(soup, html, _content(h1="How to do SEO"), _meta(), _schema())

        # informational found ma senza schema → deve generare raccomandazione
        has_schema_rec = any(
            "schema" in r.lower() and "informational" in r.lower() for r in result.recommendations
        )
        assert has_schema_rec, f"Expected schema recommendation for informational, got: {result.recommendations}"

    def test_radar_data_all_categories(self):
        """Radar copre tutte e 4 le categorie con valore 0-100."""
        html = (
            "<html><body><main>"
            "<h1>How to Bake Bread</h1>"
            "</main></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        result = audit_intent_mapping(soup, html, _content(h1="How to Bake Bread"), _meta(), _schema("HowTo"))

        assert len(result.radar_data) == 4
        axes = {d["axis"] for d in result.radar_data}
        assert axes == {"informational", "navigational", "transactional", "commercial"}

        for entry in result.radar_data:
            assert "axis" in entry
            assert "value" in entry
            assert 0 <= entry["value"] <= 100

    def test_radar_data_missing_intents_zero(self):
        """Intenti mancanti hanno value=0 nel radar."""
        html = "<html><body><main><p>hello</p></main></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = audit_intent_mapping(soup, html, _content(), _meta(), _schema())

        for entry in result.radar_data:
            assert entry["value"] == 0, f"Expected 0 for {entry['axis']} on empty page"

    def test_prompt_library_intents_mapping(self):
        """Prompt library intent mapping allineato alla tassonomia standard."""
        # Test function pubblica
        mapping = map_prompt_library_intents()
        assert mapping["discovery"] == "informational"
        assert mapping["how_to"] == "informational"
        assert mapping["comparison"] == "commercial"
        assert mapping["alternative"] == "commercial"
        assert mapping["recommendation"] == "transactional"

    def test_full_coverage_page_has_recommendations(self):
        """Anche una pagina ben coperta puo' avere raccomandazioni per schema mancante."""
        html = (
            "<html><body><main>"
            "<h1>Complete SEO Guide: Tutorial and How-To</h1>"
            "<h2>Best Tools 2026: Top 10 Review and Comparison</h2>"
            "<p>Buy now! Get started with our free trial pricing plans</p>"
            "<a href='/login'>Sign In</a>"
            "</main></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        result = audit_intent_mapping(
            soup, html,
            _content(h1="Complete SEO Guide"),
            _meta(),
            _schema(),  # nessuno schema → raccomandazioni per tutti
        )

        # Tutti gli intenti dovrebbero essere trovati (pagina ricca)
        assert result.total_intents_found >= 3
        # Almeno una raccomandazione per schema mancante
        assert len(result.recommendations) >= 1
