"""Citation fidelity: do the pages an AI answer cites carry the words of what the answer says?

Deterministic, no language model. The answer is cut into sentences; each sentence is scored against every cited
page with the same lexical measure as ``geo align``, and the best page wins. A figure in the sentence (a price, a
percentage, a year) must appear in that page's text, otherwise the sentence is held at "partial". The result is a
check that the cited text is *about* the claim, never proof that the claim is true.
``core/`` does not print.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from geo_optimizer.core.align import _stem, align_prompts, extract_surfaces, tokenize
from geo_optimizer.models.config import (
    ALIGN_COVERED_MIN,
    ALIGN_PARTIAL_MIN,
    FIDELITY_MAX_ANSWER_CHARS,
    FIDELITY_MAX_CLAIMS,
    FIDELITY_MAX_SOURCES,
    FIDELITY_MIN_CLAIM_WORDS,
)
from geo_optimizer.models.results import FidelityClaim, FidelityResult
from geo_optimizer.utils.http import fetch_url
from geo_optimizer.utils.validators import normalize_url_scheme

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_MARKERS = re.compile(r"\s*(?:\[\d{1,3}\]|\(\d{1,3}\)(?=\s|$))")  # [1] / (1) footnote markers
_LEAD = re.compile(r"^[\s>*#\-•\d.)]+(?=\D)")  # bullets and list numbering
_NUMBER = re.compile(r"\d[\d.,]*")


def split_claims(answer: str) -> tuple[list[str], int]:
    """Sentences of ``answer`` long enough to be a claim, and how many were skipped (short, or over the cap)."""
    claims: list[str] = []
    skipped = 0
    for raw in _SENTENCE_SPLIT.split(answer[:FIDELITY_MAX_ANSWER_CHARS]):
        sentence = _LEAD.sub("", _MARKERS.sub("", raw)).strip()
        if not sentence:
            continue
        if len(sentence.split()) < FIDELITY_MIN_CLAIM_WORDS or len(claims) >= FIDELITY_MAX_CLAIMS:
            skipped += 1
            continue
        claims.append(sentence)
    return claims, skipped


def _numbers(text: str) -> list[str]:
    """Figures of ``text`` with thousands separators and a trailing dot removed, in order, without duplicates."""
    return list(dict.fromkeys(n.rstrip(".,").replace(",", "") for n in _NUMBER.findall(text)))


def check_fidelity(answer: str, pages: dict[str, str]) -> FidelityResult:
    """Score the sentences of ``answer`` against ``pages`` (URL to HTML). Pure: no network."""
    result = FidelityResult(sources=list(pages))
    claims, result.skipped_sentences = split_claims(answer)
    if not claims:
        result.error = f"No claims: the answer has no sentence of at least {FIDELITY_MIN_CLAIM_WORDS} words"
        return result
    page_surfaces: dict[str, list[tuple[str, str]]] = {}
    page_text: dict[str, str] = {}
    for url, html in pages.items():
        surfaces = extract_surfaces(BeautifulSoup(html, "html.parser"))
        page_surfaces[url] = surfaces
        page_text[url] = " ".join(text for _, text in surfaces)
    all_stems = {_stem(t) for text in page_text.values() for t in tokenize(text)}
    for sentence in claims:
        best_score, best_url = 0.0, ""
        for url, surfaces in page_surfaces.items():
            items = align_prompts([sentence], surfaces)
            if items and items[0].score > best_score:
                best_score, best_url = items[0].score, url
        terms = list(dict.fromkeys(tokenize(sentence)))
        missing_numbers = (
            [n for n in _numbers(sentence) if n not in page_text[best_url].replace(",", "")] if best_url else []
        )
        status = (
            "supported"
            if best_score >= ALIGN_COVERED_MIN
            else "partial"
            if best_score >= ALIGN_PARTIAL_MIN
            else "unsupported"
        )
        if missing_numbers and status == "supported":
            status = "partial"  # the words are there but a figure of the claim is not
        result.claims.append(
            FidelityClaim(
                claim=sentence,
                status=status,
                score=best_score,
                best_source=best_url,
                missing_terms=[t for t in terms if _stem(t) not in all_stems],
                missing_numbers=missing_numbers,
            )
        )
    result.supported = sum(c.status == "supported" for c in result.claims)
    result.partial = sum(c.status == "partial" for c in result.claims)
    result.unsupported = sum(c.status == "unsupported" for c in result.claims)
    result.support_rate = round(result.supported / len(result.claims), 2)
    return result


def analyze_fidelity(answer: str, urls: list[str]) -> FidelityResult:
    """Fetch the cited ``urls`` (anti-SSRF checks included) and run :func:`check_fidelity`."""
    pages: dict[str, str] = {}
    unreachable: list[str] = []
    for url in list(dict.fromkeys(urls))[:FIDELITY_MAX_SOURCES]:
        target = normalize_url_scheme(url)
        response, error = fetch_url(target)
        if error or response is None:
            unreachable.append(target)
        else:
            pages[target] = response.text
    if not pages:
        return FidelityResult(error="None of the cited pages could be read", unreachable_sources=unreachable)
    result = check_fidelity(answer, pages)
    result.unreachable_sources = unreachable
    return result
