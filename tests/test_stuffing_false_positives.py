"""Regression tests for #607: brand names and function words are not keyword stuffing."""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from geo_optimizer.core.audit_negative import audit_negative_signals
from geo_optimizer.core.citability import detect_keyword_stuffing
from geo_optimizer.models.results import ContentResult, MetaResult, SchemaResult
from geo_optimizer.utils.stopwords import brand_words, page_language, stop_words_for

# The two pages from the issue, verbatim (both invented, neither is stuffed)
PAGE_BRAND = (
    '<html lang="de"><body><main><h1>Velmora – Notizen für ruhige Abende</h1>'
    "<p>Velmora ist eine kleine App für Tagebuch und Atemübungen. Mit Velmora schreibst du abends drei Sätze "
    "über deinen Tag und wählst danach eine kurze Übung aus.</p>"
    "<p>Die Übungen dauern zwei bis zehn Minuten. Velmora erinnert dich nur, wenn du das möchtest, und speichert "
    "alle Einträge auf deinem Gerät.</p><h2>Was kostet Velmora?</h2>"
    "<p>Die Grundfunktionen sind kostenlos. Ein Abo schaltet weitere Übungen frei, lässt sich jederzeit kündigen "
    "und verlängert sich monatlich.</p>"
    "<p>Velmora gibt es für Android und iOS. Fragen beantworten wir gern per E-Mail.</p></main></body></html>"
)
PAGE_FUNCTION_WORDS = (
    '<html lang="de"><body><main><h1>Gärtnern auf dem Balkon</h1>'
    "<p>Ein Balkon ist oft kleiner, als man denkt, aber er reicht für Kräuter, Tomaten oder eine Erdbeere im "
    "Topf. Wichtig ist nicht die Größe, sondern das Licht.</p>"
    "<p>Wer nach Süden blickt, kann fast alles anbauen. Wer nach Norden blickt, sollte sich auf Salat, Minze "
    "oder Farne beschränken, denn diese Pflanzen brauchen nicht viel Sonne.</p>"
    "<p>Gießen sollte man lieber morgens oder abends, nicht in der Mittagshitze. Töpfe aus Ton halten das "
    "Wasser länger als Töpfe aus Kunststoff, sind aber schwerer.</p>"
    "<p>Pflanzen, die nicht winterhart sind, gehören ab Oktober nach drinnen.</p>"
    "<p>Dünger braucht man nicht oft. Einmal im Monat reicht meist, oder man nimmt Kompost, wenn man welchen "
    "hat.</p></main></body></html>"
)


def _negative(html: str):
    soup = BeautifulSoup(html, "html.parser")
    content = ContentResult(word_count=100, h1_text="x", heading_count=3, has_h1=True)
    meta = MetaResult(has_title=True, title_text="x", description_text="x")
    return audit_negative_signals(soup, html, content, meta, SchemaResult())


def _citability(html: str):
    return detect_keyword_stuffing(BeautifulSoup(html, "html.parser"))


@pytest.mark.parametrize("html", [PAGE_BRAND, PAGE_FUNCTION_WORDS], ids=["brand", "function-words"])
def test_issue_pages_are_not_stuffing(html):
    assert _negative(html).has_keyword_stuffing is False
    method = _citability(html)
    assert method.score == 6
    assert method.details["suspicious_keywords"] == {}


def _stuffed(lang: str, word: str, head: str = "<h1>Titel</h1>") -> str:
    filler = " ".join(f"begriff{chr(97 + i % 26)}{chr(97 + i // 26)}x" for i in range(80))
    return f'<html lang="{lang}"><body><main>{head}<p>{" ".join([word] * 30)} {filler}</p></main></body></html>'


def test_real_german_stuffing_is_still_detected():
    html = _stuffed("de", "Gartenerde")
    assert _negative(html).stuffed_word == "gartenerde"
    assert "gartenerde" in _citability(html).details["suspicious_keywords"]


def test_umlaut_and_eszett_words_stay_whole():
    """`größe` must not be split at the ß (the old [a-zà-ú] class cut at ß and ü)."""
    assert "größe" in _citability(_stuffed("de", "Größe")).details["suspicious_keywords"]


@pytest.mark.parametrize(
    "head",
    [
        '<meta property="og:site_name" content="Velmora"><h1>Titel</h1>',
        '<script type="application/ld+json">{"@type": "Organization", "name": "Velmora"}</script><h1>Titel</h1>',
        '<script type="application/ld+json">{"@graph": [{"@type": ["WebSite"], "name": "Velmora"}]}</script>',
        "<title>Preise | Velmora</title><h1>Titel</h1>",
        "<h1>Velmora – Notizen für Abende</h1>",
    ],
    ids=["og", "jsonld-org", "jsonld-graph", "title-suffix", "h1-prefix"],
)
def test_brand_signals_are_excluded(head):
    html = _stuffed("de", "Velmora", head)
    assert _negative(html).has_keyword_stuffing is False
    assert _citability(html).details["suspicious_keywords"] == {}


def test_long_title_segment_is_a_topic_not_a_brand():
    """A long title segment is the page's own subject, so stuffing it is still caught."""
    html = _stuffed("de", "Gartenerde", "<title>Gartenerde richtig kaufen und lagern | Shop</title>")
    assert _negative(html).stuffed_word == "gartenerde"


def test_declared_language_without_a_list_skips_the_check():
    html = _stuffed("ja", "keyword")
    assert _negative(html).has_keyword_stuffing is False
    assert _citability(html).score == 6


def test_missing_lang_uses_every_list():
    """No lang attribute: German function words are still ignored."""
    assert _negative(PAGE_FUNCTION_WORDS.replace(' lang="de"', "")).has_keyword_stuffing is False


def test_few_uses_are_never_stuffing_in_citability():
    """Four uses in a short text exceed 2.5% by density but stay below the minimum count."""
    filler = " ".join(f"begriff{chr(97 + i % 26)}{chr(97 + i // 26)}x" for i in range(70))
    html = f'<html lang="de"><body><main><p>{" ".join(["Gartenerde"] * 4)} {filler}</p></main></body></html>'
    assert _citability(html).details["suspicious_keywords"] == {}


def test_helpers():
    soup = BeautifulSoup('<html lang="de-AT"><head><title>Seite | Marke</title></head></html>', "html.parser")
    assert page_language(soup) == "de"
    assert brand_words(soup) == {"seite", "marke"}
    assert stop_words_for("xx") is None
    assert "und" in stop_words_for("de") and "und" in stop_words_for("")
