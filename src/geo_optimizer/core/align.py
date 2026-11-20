"""Prompt-to-content alignment: how well a page's own text answers the prompts you care about.

Deterministic and offline once the page is fetched: no language model, no embedding, no extra network. For each
prompt it measures how many of the prompt's terms appear together in one surface of the page (title, h1, meta
description, a heading, a passage), weighted by how prominent the surface is, and keeps the best surface. The
result is a lexical measure. It is not what ChatGPT, Perplexity or Google would answer, and it says so.

``core/`` does not print: the CLI formats the result.
"""

from __future__ import annotations

import csv
import io
import re

from bs4 import BeautifulSoup

from geo_optimizer.models.config import (
    ALIGN_BEST_PASSAGE_CHARS,
    ALIGN_COVERED_MIN,
    ALIGN_MAX_PROMPT_CHARS,
    ALIGN_MAX_PROMPTS,
    ALIGN_MIN_TOKEN_LEN,
    ALIGN_PARTIAL_MIN,
    ALIGN_PASSAGE_MAX_WORDS,
    ALIGN_PASSAGE_MIN_WORDS,
    ALIGN_STOPWORDS,
    ALIGN_SURFACE_WEIGHTS,
)
from geo_optimizer.models.results import AlignItem, AlignResult
from geo_optimizer.utils.http import fetch_url
from geo_optimizer.utils.validators import normalize_url_scheme

_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_NOISE_TAGS = ("script", "style", "noscript", "template", "nav", "footer", "aside", "form", "svg")
_QUERY_HEADERS = {"query", "queries", "top queries", "prompt", "prompts", "grounding query", "grounding queries"}


def tokenize(text: str) -> list[str]:
    """Lower-case terms of ``text`` without stopwords and one-letter tokens, in order, duplicates kept."""
    return [
        t
        for t in (w.casefold() for w in _WORD.findall(text or ""))
        if len(t) >= ALIGN_MIN_TOKEN_LEN and t not in ALIGN_STOPWORDS
    ]


def parse_prompts(raw: str) -> tuple[list[str], int]:
    """Read prompts from text: one per line (blank lines and ``#`` comments ignored), or a CSV whose header names
    a query column (Search Console and Bing exports). Returns ``(prompts, skipped)``; duplicates, prompts over
    ``ALIGN_MAX_PROMPT_CHARS`` and everything past ``ALIGN_MAX_PROMPTS`` count as skipped."""
    lines = [ln.strip() for ln in raw.splitlines()]
    candidates: list[str] = [ln for ln in lines if ln and not ln.startswith("#")]
    first = next(csv.reader(io.StringIO(raw)), [])
    column = next((i for i, name in enumerate(first) if name.strip().casefold() in _QUERY_HEADERS), None)
    if column is not None:
        rows = csv.reader(io.StringIO(raw))
        next(rows, None)
        candidates = [row[column].strip() for row in rows if len(row) > column and row[column].strip()]
    prompts: list[str] = []
    seen: set[str] = set()
    skipped = 0
    for prompt in candidates:
        key = " ".join(prompt.casefold().split())
        if key in seen or len(prompt) > ALIGN_MAX_PROMPT_CHARS or len(prompts) >= ALIGN_MAX_PROMPTS:
            skipped += 1
            continue
        seen.add(key)
        prompts.append(prompt)
    return prompts, skipped


def extract_surfaces(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """The page's text surfaces as ``(surface, text)``: title, meta description, h1, h2 and h3, and passages
    (paragraphs, list items, table cells and definitions, long ones cut into windows)."""
    surfaces: list[tuple[str, str]] = []
    if soup.title and soup.title.get_text(strip=True):
        surfaces.append(("title", soup.title.get_text(" ", strip=True)))
    meta = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    if meta and meta.get("content", "").strip():
        surfaces.append(("meta_description", meta["content"].strip()))
    body = soup.body or soup
    for tag in body(_NOISE_TAGS):
        tag.decompose()
    for heading in body.find_all(["h1", "h2", "h3"]):
        text = heading.get_text(" ", strip=True)
        if text:
            surfaces.append(("h1" if heading.name == "h1" else "heading", text))
    for block in body.find_all(["p", "li", "td", "dd", "blockquote"]):
        words = block.get_text(" ", strip=True).split()
        if len(words) < ALIGN_PASSAGE_MIN_WORDS:
            continue
        step = max(1, ALIGN_PASSAGE_MAX_WORDS // 2)
        for start in range(0, max(1, len(words) - step), step):
            surfaces.append(("passage", " ".join(words[start : start + ALIGN_PASSAGE_MAX_WORDS])))
    return surfaces


def align_prompts(prompts: list[str], surfaces: list[tuple[str, str]]) -> list[AlignItem]:
    """Score each prompt against the surfaces; items keep the order of ``prompts``."""
    tokenised = [(surface, text, set(tokenize(text))) for surface, text in surfaces]
    page_terms: set[str] = set().union(*(t for _, _, t in tokenised)) if tokenised else set()
    items: list[AlignItem] = []
    for prompt in prompts:
        terms = list(dict.fromkeys(tokenize(prompt)))
        if not terms:
            continue
        best_score, best_surface, best_text, best_hits = 0.0, "", "", set()
        for surface, text, unit_terms in tokenised:
            hits = unit_terms.intersection(terms)
            score = len(hits) / len(terms) * ALIGN_SURFACE_WEIGHTS[surface]
            if score > best_score:
                best_score, best_surface, best_text, best_hits = score, surface, text, hits
        status = (
            "covered"
            if best_score >= ALIGN_COVERED_MIN
            else "partial"
            if best_score >= ALIGN_PARTIAL_MIN
            else "uncovered"
        )
        items.append(
            AlignItem(
                prompt=prompt,
                score=round(best_score, 2),
                status=status,
                surface=best_surface,
                matched_terms=[t for t in terms if t in best_hits],
                missing_terms=[t for t in terms if t not in page_terms],
                best_text=best_text[:ALIGN_BEST_PASSAGE_CHARS],
            )
        )
    return items


def analyze_alignment(url: str, prompts: list[str], skipped: int = 0) -> AlignResult:
    """Fetch ``url`` (anti-SSRF checks included) and align ``prompts`` with its text."""
    target = normalize_url_scheme(url)
    result = AlignResult(url=target, skipped_prompts=skipped)
    response, error = fetch_url(target)
    if error or response is None:
        result.error = error or "No response"
        return result
    items = align_prompts(prompts, extract_surfaces(BeautifulSoup(response.text, "html.parser")))
    result.items = items
    result.prompts = len(items)
    result.skipped_prompts += len(prompts) - len(items)
    result.covered = sum(i.status == "covered" for i in items)
    result.partial = sum(i.status == "partial" for i in items)
    result.uncovered = sum(i.status == "uncovered" for i in items)
    result.mean_score = round(sum(i.score for i in items) / len(items), 2) if items else 0.0
    return result
