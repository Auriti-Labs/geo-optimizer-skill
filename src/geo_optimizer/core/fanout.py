"""Sub-intent coverage: which of the usual commercial follow-up questions a page speaks to, for one seed topic.

Deterministic, no language model. The seed is expanded with fixed templates (``FANOUT_FAMILIES``). Each generated
query is scored on the words the template adds to the topic ("price", "alternatives", "reviews"), not on the topic's own
words, which every query shares and which would flatter every family. Those words only count in a surface that also
speaks of the topic (at least half of its terms). A family is as covered as the mean of its queries. The families are
a hand-written checklist, not what any answer engine issues.
``core/`` does not print.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from geo_optimizer.core.align import _stem, extract_surfaces, tokenize
from geo_optimizer.models.config import (
    ALIGN_BEST_PASSAGE_CHARS,
    ALIGN_COVERED_MIN,
    ALIGN_PARTIAL_MIN,
    ALIGN_SURFACE_WEIGHTS,
    FANOUT_FAMILIES,
    FANOUT_MAX_SEED_CHARS,
)
from geo_optimizer.models.results import AlignItem, FanoutFamily, FanoutResult
from geo_optimizer.utils.http import fetch_url
from geo_optimizer.utils.validators import normalize_url_scheme


def expand(seed: str) -> dict[str, list[str]]:
    """The generated queries per family for ``seed`` (whitespace collapsed, length capped)."""
    topic = " ".join(seed.split())[:FANOUT_MAX_SEED_CHARS]
    return {family: [t.format(t=topic) for t in templates] for family, templates in FANOUT_FAMILIES.items()}


def _score_query(query: str, topic_stems: set[str], surfaces: list[tuple[str, str, set[str]]]) -> AlignItem | None:
    """Score one generated query on its added words; None when the template adds none."""
    terms = [t for t in dict.fromkeys(tokenize(query)) if _stem(t) not in topic_stems]
    if not terms:
        return None
    stems = [_stem(t) for t in terms]
    page_terms: set[str] = set().union(*(u for _, _, u in surfaces)) if surfaces else set()
    best, best_surface, best_text, best_hits = 0.0, "", "", set()
    for surface, text, unit in surfaces:
        if topic_stems and len(unit & topic_stems) / len(topic_stems) < 0.5:
            continue  # this surface is not about the topic
        hits = unit.intersection(stems)
        score = len(hits) / len(stems) * ALIGN_SURFACE_WEIGHTS[surface]
        if score > best:
            best, best_surface, best_text, best_hits = score, surface, text, hits
    shown = round(best, 2)
    return AlignItem(
        prompt=query,
        score=shown,
        status="covered" if shown >= ALIGN_COVERED_MIN else "partial" if shown >= ALIGN_PARTIAL_MIN else "uncovered",
        surface=best_surface,
        matched_terms=[t for t, st in zip(terms, stems, strict=True) if st in best_hits],
        missing_terms=[t for t, st in zip(terms, stems, strict=True) if st not in page_terms],
        best_text=best_text[:ALIGN_BEST_PASSAGE_CHARS],
    )


def score_families(seed: str, surfaces: list[tuple[str, str]]) -> list[FanoutFamily]:
    """Score every family against ``surfaces``."""
    topic_stems = {_stem(t) for t in tokenize(seed)}
    tokenised = [(surface, text, {_stem(t) for t in tokenize(text)}) for surface, text in surfaces]
    families: list[FanoutFamily] = []
    for family, queries in expand(seed).items():
        items = [i for i in (_score_query(q, topic_stems, tokenised) for q in queries) if i is not None]
        mean = round(sum(i.score for i in items) / len(items), 2) if items else 0.0
        status = "covered" if mean >= ALIGN_COVERED_MIN else "partial" if mean >= ALIGN_PARTIAL_MIN else "uncovered"
        families.append(FanoutFamily(family=family, status=status, mean_score=mean, items=items))
    return families


def analyze_fanout(url: str, seed: str) -> FanoutResult:
    """Fetch ``url`` (anti-SSRF checks included) and measure sub-intent coverage for ``seed``."""
    target = normalize_url_scheme(url)
    result = FanoutResult(url=target, seed=" ".join(seed.split())[:FANOUT_MAX_SEED_CHARS])
    if not tokenize(result.seed):
        # Without topic words nothing ties a query to the topic, and every added word would count anywhere on the page.
        result.error = "The topic has no searchable words"
        return result
    response, error = fetch_url(target)
    if error or response is None:
        result.error = error or "No response"
        return result
    result.families = score_families(seed, extract_surfaces(BeautifulSoup(response.text, "html.parser")))
    result.covered = sum(f.status == "covered" for f in result.families)
    result.partial = sum(f.status == "partial" for f in result.families)
    result.uncovered = sum(f.status == "uncovered" for f in result.families)
    return result
