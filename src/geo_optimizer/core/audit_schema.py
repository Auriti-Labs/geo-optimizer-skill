from __future__ import annotations

import logging
import re
from decimal import Decimal
from typing import TYPE_CHECKING

from geo_optimizer.models.config import (
    AI_READINESS_SCHEMA_NAME_MIN_LEN,
    ARTICLE_TYPES,
    ORGANIZATION_TYPES,
    SCHEMA_ORG_REQUIRED,
    SCHEMA_RAW_SCHEMAS_CAP,
    SCHEMA_RICHNESS_HIGH,
    SCHEMA_RICHNESS_LOW,
    SCHEMA_RICHNESS_MED,
)
from geo_optimizer.models.results import SchemaResult
from geo_optimizer.utils.jsonld import first_object, iter_jsonld_objects, string_list
from geo_optimizer.utils.jsonld import schema_types as jsonld_types

if TYPE_CHECKING:
    from bs4 import BeautifulSoup

_logger = logging.getLogger(__name__)


_MIN_VISIBLE_QUESTIONS = 2
_QUESTION_MARKS = ("?", "？")  # ASCII and fullwidth (CJK) question mark
# Chrome that is not content: a heading inside it is a menu, a banner or a link list, not an FAQ
_NON_CONTENT_TAGS = {"a", "nav", "header", "footer", "aside"}
_NON_CONTENT_HINTS = ("cookie", "consent", "gdpr", "banner")


def _is_question_content(node) -> bool:
    """A question heading or summary that sits in the page content, not in a link or banner."""
    if node.find("a") is not None:  # a post title on a listing page links to the post
        return False
    for parent in node.parents:
        if getattr(parent, "name", None) in _NON_CONTENT_TAGS:
            return False
        attrs = getattr(parent, "attrs", None) or {}
        marker = " ".join([str(attrs.get("id", "")), " ".join(attrs.get("class", []) or [])]).lower()
        if any(hint in marker for hint in _NON_CONTENT_HINTS):
            return False
    return True


def _visible_strings(schema: dict) -> list[tuple[str, str]]:
    """Texts a schema declares that a visitor must also be able to read on the page, as ``(text, kind)`` pairs
    where kind is ``"text"`` or ``"price"``.

    ``name`` and ``headline`` of any schema; the question of every FAQPage entry; the price of a Product
    offer. Answers are not compared: their markup and whitespace differ from the declared text too often
    for an exact match to mean anything.
    """
    found: list[tuple[str, str]] = []
    for field in ("name", "headline"):
        value = schema.get(field)
        if isinstance(value, str) and len(value.strip()) >= AI_READINESS_SCHEMA_NAME_MIN_LEN:
            found.append((value, "text"))
    types = {t.lower() for t in jsonld_types(schema.get("@type"))}
    if "faqpage" in types:
        entities = schema.get("mainEntity")
        for item in entities if isinstance(entities, list) else [entities]:
            name = item.get("name") if isinstance(item, dict) else None
            if isinstance(name, str) and len(name.strip()) >= AI_READINESS_SCHEMA_NAME_MIN_LEN:
                found.append((name, "text"))
    if "product" in types:
        offers = schema.get("offers")
        for offer in offers if isinstance(offers, list) else [offers]:
            price = offer.get("price") if isinstance(offer, dict) else None
            if isinstance(price, (int, float)) and not isinstance(price, bool):
                price = _number_text(price)
            if isinstance(price, str) and price.strip():
                found.append((price.strip(), "price"))
    return found


def _number_text(value: int | float) -> str | None:
    """A JSON number as plain decimal text, without exponent and without the six-digit rounding of ``%g``.
    None for a value that is not a finite number (``nan``, ``inf``) or has more than 30 digits."""
    try:
        text = format(Decimal(repr(value)) if isinstance(value, float) else Decimal(value), "f")
    except (ArithmeticError, ValueError):
        return None
    return text if len(text.replace("-", "").replace(".", "")) <= 30 and text.lstrip("-")[:1].isdigit() else None


_GROUP_SEPARATORS = ("", ",", ".", " ", "\u00a0", "'")


def _price_spellings(price: str) -> set[str]:
    """The ways a visitor may see ``price`` written: with a ``.`` or ``,`` decimal mark, thousands grouped by a
    comma, a dot, a space or an apostrophe, and with or without trailing zero decimals (``19.9`` as ``19.90``)."""
    try:
        number = Decimal(price.strip())
    except (ArithmeticError, ValueError):
        return {price.strip().casefold()}
    whole, _, frac = format(number, "f").partition(".")
    frac = frac.rstrip("0")
    fractions = {frac, frac.ljust(2, "0")} if frac else {"", "00"}
    spellings: set[str] = set()
    for sep in _GROUP_SEPARATORS:
        grouped = whole if not sep else f"{int(whole):,}".replace(",", sep) if whole.lstrip("-").isdigit() else whole
        for decimal_mark in (".", ","):
            if sep == decimal_mark:
                continue
            for f in fractions:
                spellings.add(grouped + (decimal_mark + f if f else ""))
    return spellings


def _is_visible(text: str, kind: str, visible_text: str) -> bool:
    """Whether ``text`` appears in the visible page text. A price must stand alone as a number: ``1`` is not
    visible in "2019 items" and ``89`` is not visible in "89.5", while ``1089`` is visible as "1,089" or
    "1.089,00" and ``19.9`` as "19,90"."""
    needle = text.strip().casefold()
    if kind != "price":
        return needle in visible_text
    spellings = "|".join(re.escape(s) for s in sorted(_price_spellings(needle), key=len, reverse=True))
    return re.search(rf"(?<!\d)(?<!\d[.,' \u00a0])(?:{spellings})(?!\d|[.,]\d)", visible_text) is not None


def _visible_coverage(raw_schemas: list[dict], visible_text: str) -> bool:
    """True when at least one schema is checkable and EVERY checkable schema is fully visible on the page.

    Rubric v4 and earlier give the point as soon as one name or headline matches (``any``). Here a page whose
    FAQPage questions or product price do not appear in the text, next to a matching headline, does not pass.
    """
    checked = 0
    for schema in raw_schemas:
        strings = _visible_strings(schema)
        if not strings:
            continue
        checked += 1
        if not all(_is_visible(text, kind, visible_text) for text, kind in strings):
            return False
    return checked > 0


def _has_visible_faq(soup: BeautifulSoup) -> bool:
    """True when the page shows at least two questions as headings or accordion summaries.

    Deliberately simple (text ending in a question mark, 8 to 200 characters, outside links,
    navigation and cookie banners): it decides whether FAQ markup applies to the page, not how
    good the FAQ is. Accordions built from buttons or divs are not recognised.
    """
    questions = 0
    for node in soup.find_all(["h2", "h3", "h4", "summary", "dt"]):
        text = node.get_text(" ", strip=True)
        if 8 <= len(text) <= 200 and text.endswith(_QUESTION_MARKS) and _is_question_content(node):
            questions += 1
            if questions >= _MIN_VISIBLE_QUESTIONS:
                return True
    return False


def audit_schema(soup: BeautifulSoup | None, url: str) -> SchemaResult:
    """Check JSON-LD schema on homepage. Returns SchemaResult."""
    result = SchemaResult()
    if soup is None:
        return result
    result.has_visible_faq = _has_visible_faq(soup)

    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    if not scripts:
        return result

    def _count_parse_error(exc: Exception) -> None:
        _logger.debug("Invalid JSON schema ignored: %s", exc)
        result.json_parse_errors += 1  # fix #399: track errors for recommendations

    for schema in iter_jsonld_objects(soup, on_parse_error=_count_parse_error):
        try:
            # Solo i tipi stringa: un @type numerico o a oggetto finiva in found_types
            # e rompeva i moduli che ne costruiscono un set (es. audit_multimodal).
            schema_types = jsonld_types(schema.get("@type")) or ["unknown"]

            # Add the raw schema (cap at 50 to prevent memory bloat — fix #191)
            if len(result.raw_schemas) < SCHEMA_RAW_SCHEMAS_CAP:
                result.raw_schemas.append(schema)

            for t in schema_types:
                result.found_types.append(t)

                if t == "WebSite":
                    result.has_website = True
                elif t == "WebApplication":
                    result.has_webapp = True
                elif t == "FAQPage":
                    result.has_faq = True
                elif t in ARTICLE_TYPES:
                    result.has_article = True
                elif t in ORGANIZATION_TYPES:
                    result.has_organization = True
                elif t == "HowTo":
                    result.has_howto = True
                elif t in ("Person",):
                    result.has_person = True
                elif t == "Product":
                    result.has_product = True

                # Any valid schema type (not unknown) counts
                if t != "unknown":
                    result.any_schema_found = True

            # Check the sameAs property
            same_as = string_list(schema.get("sameAs"))
            if same_as:
                result.has_sameas = True
                result.sameas_urls.extend(same_as[:10])  # cap at 10

            # Check dateModified
            if schema.get("dateModified"):
                result.has_date_modified = True

        except (AttributeError, TypeError) as exc:
            # Defensive: a malformed-but-parseable JSON-LD object shaped unexpectedly
            # (fix #81). Actual JSON parse failures are counted by iter_jsonld_objects's
            # on_parse_error above, before a schema object like this one exists.
            _logger.debug("Invalid JSON schema ignored: %s", exc)
            result.json_parse_errors += 1  # fix #399: track errors for recommendations

    # Schema richness (Growth Marshal Feb 2026): count attributes per schema
    # Generic schema (@type + name + url = 3 attrs) performs WORSE than no schema
    # Rich schema (5+ attributes) → 61.7% citation rate vs 41.6% generic
    _GENERIC_KEYS = {"@context", "@type", "@id"}
    attr_counts = []
    for schema_obj in result.raw_schemas:
        # Count only relevant attributes (excluding @context, @type, @id)
        relevant_attrs = [k for k in schema_obj if k not in _GENERIC_KEYS]
        attr_counts.append(len(relevant_attrs))

    if attr_counts:
        result.avg_attributes_per_schema = round(sum(attr_counts) / len(attr_counts), 1)
        # Graduated scoring: 0pt generic, 1pt minimal, 2pt medium, 3pt rich (#394)
        avg = result.avg_attributes_per_schema
        if avg >= SCHEMA_RICHNESS_HIGH:
            result.schema_richness_score = 3
        elif avg >= SCHEMA_RICHNESS_MED:
            result.schema_richness_score = 2
        elif avg >= SCHEMA_RICHNESS_LOW:
            result.schema_richness_score = 1

        else:
            result.schema_richness_score = 0

    visible_root = soup.body or soup
    visible_text = " ".join(
        str(text)
        for text in visible_root.find_all(string=True)
        if text.parent and text.parent.name not in {"script", "style", "noscript", "template", "title"}
    ).casefold()
    result.visible_match = any(
        isinstance(schema.get(field), str)
        and len(schema[field].strip()) >= AI_READINESS_SCHEMA_NAME_MIN_LEN
        and schema[field].strip().casefold() in visible_text
        for schema in result.raw_schemas
        for field in ("name", "headline")
    )
    # Il <title> sta in <head>, fuori da body: un WebPage.name uguale al titolo è il caso più comune
    # e il titolo è contenuto che l'utente vede (scheda del browser, risultato di ricerca). Conta come
    # visibile solo per il controllo stretto: il lasco (v2-v4) resta invariato.
    title_text = soup.title.get_text(" ", strip=True).casefold() if soup.title else ""
    result.visible_match_strict = _visible_coverage(result.raw_schemas, f"{visible_text} {title_text}")

    # Schema completeness (gap #3): check required fields per SCHEMA_ORG_REQUIRED
    for schema_obj in result.raw_schemas:
        for t in jsonld_types(schema_obj.get("@type")):
            t_lower = t.lower()
            if t_lower in SCHEMA_ORG_REQUIRED:
                missing = [f for f in SCHEMA_ORG_REQUIRED[t_lower] if f not in schema_obj]
                if missing and t not in result.incomplete_schema_types:
                    result.schema_missing_fields[t] = missing
                    result.incomplete_schema_types.append(t)

    # #232: E-commerce GEO Profile — analyze Product schema richness
    if result.has_product:
        for schema_obj in result.raw_schemas:
            if "Product" in jsonld_types(schema_obj.get("@type")):
                offers = first_object(schema_obj.get("offers") or schema_obj.get("offer"))
                result.ecommerce_signals = {
                    "has_price": bool(offers.get("price") or offers.get("lowPrice")),
                    "has_availability": bool(offers.get("availability")),
                    "has_brand": bool(schema_obj.get("brand")),
                    "has_image": bool(schema_obj.get("image")),
                    "has_reviews": bool(schema_obj.get("aggregateRating") or schema_obj.get("review")),
                }
                result.ecommerce_signals["complete"] = all(
                    result.ecommerce_signals[k] for k in result.ecommerce_signals if k != "complete"
                )
                break

    return result
