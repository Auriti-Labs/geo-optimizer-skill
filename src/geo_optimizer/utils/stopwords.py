"""Function-word lists and brand-name helpers for the keyword-stuffing checks.

A word that merely repeats the page's own brand, or a language's function words
("und", "nicht", "les"), is not keyword stuffing. Both stuffing checks
(`audit_negative` and `citability`) share this module so they cannot drift apart.
"""

from __future__ import annotations

import json
import re

from geo_optimizer.utils.jsonld import schema_types as jsonld_types


def _words(text: str) -> frozenset[str]:
    return frozenset(text.split())


# Lists hold function words only (articles, pronouns, prepositions, conjunctions,
# auxiliaries). shortcut: not exhaustive, extend a list when a real page shows a leak.
_LISTS: dict[str, frozenset[str]] = {
    "en": _words(
        "about after all also an and any are as at be been before between but by can could did do does each "
        "for from had has have her here him his how if in into is it its may might more most no not of on "
        "only or our over shall she should so some such than that the their them then there these they this "
        "those through to under very was were what when where which while who whom why will with would you "
        "your"
    ),
    "it": _words(
        "agli al alla alle allo anche che chi come con cui da dai dal dalla dalle degli dei del della delle "
        "di dove essere fra gli ha hanno il la le lo loro ma molto nei nel nella nelle non ogni per più poi "
        "quando quella quello questa queste questi questo se sia solo sono stato su sua sul sulla suo suoi "
        "tra un una uno"
    ),
    "de": _words(
        "ab aber alle alles als am an auch auf aus bei beim bis dann das dass dein dem den denn der des die "
        "diese dieser dieses du durch ein eine einem einen einer eines er es euer für gegen gern haben hat "
        "hatte ich ihr im ist jede jeder jedes kann können man mehr mein meist mit muss müssen nach nicht "
        "noch nur oder oft ohne schon sehr sein seit sich sie sind soll sollen um und unser unter vom von war "
        "waren weil welche welcher wenn werden wie will wir wird wollen wurde wurden während zu zum zur über"
    ),
    "fr": _words(
        "aussi avait avec avoir car ce ces cet cette chez comme dans de des donc dont du elle elles entre est "
        "et il ils je la le les leur leurs ma mais mes mon ni notre nous on ont ou où par pas plus pour quand "
        "que qui quoi sa sans se ses si son sont sous sur ta tes ton très tu un une vers votre vous était "
        "être"
    ),
    "es": _words(
        "al como con cual cuando de del desde donde el ella en entre era es esa ese eso esta estar estas este "
        "estos está están fue ha había han hasta hay la las le les lo los mi mis muy más no nuestro o para "
        "pero por porque que quien se ser sin sobre son su sus también tu tus tú un una unas unos vuestro y "
        "yo él"
    ),
    "pt": _words(
        "a ao aos as até com como da das de desde do dos e ela ele em entre era essa esse esta estar estas "
        "este estes está estão eu foi há isso mais mas meu minha muito na nas no nos não o onde os ou para "
        "por porque qual quando que quem se sem ser seu seus sobre sua suas são também teu tu tua um uma umas "
        "uns à às é"
    ),
    "nl": _words(
        "aan alle alleen als bij dan dat de deze die dit door een en had hebben heeft heel het hij hoe ik in "
        "is jij jullie kan kunnen maar meer men met moet moeten naar niet nog of om onder ook op over tegen "
        "uit van voor wanneer want waren was werd werden wij worden wordt zal ze zij zijn zonder zullen"
    ),
}
ALL_STOP_WORDS: frozenset[str] = frozenset().union(*_LISTS.values())

# Title separators used between a page title and the site name ("Page | Brand")
_TITLE_SEP = re.compile(r"\s+[|–—·:\-]\s+")
_WORD = re.compile(r"[^\W\d_]{3,}")


def page_language(soup) -> str:
    """Primary subtag of `<html lang>` ("de-AT" -> "de"), or "" when absent."""
    html_tag = soup.find("html")
    return (html_tag.get("lang") or "").strip().lower().split("-")[0].split("_")[0] if html_tag else ""


def stop_words_for(lang: str) -> frozenset[str] | None:
    """Function words for `lang`; the union of every list when the language is unknown.

    Returns None when a language is declared but has no list: the caller should skip
    the stuffing check instead of counting that language's function words as keywords.
    """
    if not lang:
        return ALL_STOP_WORDS
    return _LISTS.get(lang)


def brand_words(soup) -> set[str]:
    """Lowercase words of the page's own brand: og:site_name, JSON-LD name, short title/H1 prefix or suffix."""
    names: list[str] = []
    og = soup.find("meta", attrs={"property": "og:site_name"})
    if og and og.get("content"):
        names.append(og["content"])
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (ValueError, TypeError):
            continue
        for node in data.get("@graph", [data]) if isinstance(data, dict) else data:
            if not isinstance(node, dict) or not {"Organization", "WebSite", "Brand"} & set(
                jsonld_types(node.get("@type"))
            ):
                continue
            if isinstance(node.get("name"), str):
                names.append(node["name"])
    # "Brand - Tagline" in <title> or <h1>: only a short segment can be a brand,
    # a long one is the page's own topic.
    for heading in (soup.title, soup.find("h1")):
        text = heading.get_text(" ", strip=True) if heading else ""
        parts = _TITLE_SEP.split(text)
        if len(parts) > 1:
            names.extend(p for p in (parts[0], parts[-1]) if len(p.split()) <= 3)
    return {w for name in names for w in _WORD.findall(name.lower())}
