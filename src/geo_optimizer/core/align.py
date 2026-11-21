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

from bs4 import BeautifulSoup, Comment, Doctype

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
from geo_optimizer.utils.html_blocks import BlockResolver
from geo_optimizer.utils.http import fetch_url
from geo_optimizer.utils.validators import normalize_url_scheme

_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_NOISE_TAGS = ("script", "style", "noscript", "template", "nav", "footer", "aside", "svg")
_HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")
_BLOCK_TAGS = frozenset(
    {
        "p",
        "li",
        "td",
        "th",
        "dd",
        "dt",
        "blockquote",
        "div",
        "section",
        "article",
        "main",
        "pre",
        "figcaption",
        "summary",
        *_HEADINGS,
    }
)
_QUERY_HEADERS = {
    "query",
    "queries",
    "top queries",
    "query principali",
    "prompt",
    "prompts",
    "grounding query",
    "grounding queries",
    "keyword",
    "keywords",
}


def tokenize(text: str) -> list[str]:
    """Lower-case terms of ``text`` without stopwords and one-letter tokens, in order, duplicates kept."""
    return [
        t
        for t in (w.casefold() for w in _WORD.findall(text or ""))
        if len(t) >= ALIGN_MIN_TOKEN_LEN and t not in ALIGN_STOPWORDS
    ]


def _stem(token: str) -> str:
    """Strip an English plural so that ``repairs`` and ``repair`` match. Other languages match on exact words."""
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        return token[:-1]
    return token


def _csv_column(raw: str) -> list[str] | None:
    """The query column of a CSV export, or None when ``raw`` is not a CSV with a recognised query header
    (or when the CSV module refuses it: a field over 131072 characters, a NUL byte)."""
    try:
        rows = csv.reader(io.StringIO(raw))
        header = next(rows, [])
        column = next((i for i, name in enumerate(header) if name.strip().casefold() in _QUERY_HEADERS), None)
        if column is None:
            return None
        return [row[column].strip() for row in rows if len(row) > column and row[column].strip()]
    except csv.Error:
        return None


def parse_prompts(raw: str, extra: tuple[str, ...] = ()) -> tuple[list[str], int]:
    """Read prompts from text: one per line (blank lines and ``#`` comments ignored), or a CSV whose header names
    a query column (Search Console and Bing exports, with or without a byte-order mark). ``extra`` prompts, for
    example those given on the command line, are added after the file is read, never parsed as CSV rows.
    Returns ``(prompts, skipped)``; duplicates, prompts over ``ALIGN_MAX_PROMPT_CHARS`` and everything past
    ``ALIGN_MAX_PROMPTS`` count as skipped."""
    raw = raw.lstrip("\ufeff")
    candidates = _csv_column(raw)
    if candidates is None:
        candidates = [ln.strip() for ln in raw.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    candidates = [*candidates, *(e.strip() for e in extra if e.strip())]
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
    """The page's text surfaces as ``(surface, text)``: title, meta description, h1, other headings, and passages.

    Passages are the text of each block element (paragraph, list item, cell, division, quotation), found in a
    single pass over the text nodes, each assigned to its nearest block ancestor: text kept in a plain ``div`` is
    read, and deeply nested markup costs time proportional to its size. Long blocks are cut into windows."""
    surfaces: list[tuple[str, str]] = []
    if soup.title and soup.title.get_text(strip=True):
        surfaces.append(("title", soup.title.get_text(" ", strip=True)))
    meta = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    if meta and meta.get("content", "").strip():
        surfaces.append(("meta_description", meta["content"].strip()))
    body = soup.body or soup
    for tag in body(_NOISE_TAGS):
        tag.decompose()
    for heading in body.find_all(_HEADINGS):
        text = heading.get_text(" ", strip=True)
        if text:
            surfaces.append(("h1" if heading.name == "h1" else "heading", text))
    resolver = BlockResolver(body, _BLOCK_TAGS)
    blocks: dict[int, tuple[str, list[str]]] = {}
    for node in body.find_all(string=True):
        if isinstance(node, (Comment, Doctype)) or not node.strip():
            continue
        owner, _ = resolver.resolve(node)
        name = getattr(owner, "name", "") or ""
        blocks.setdefault(id(owner), (name, []))[1].append(str(node).strip())
    step = max(1, ALIGN_PASSAGE_MAX_WORDS // 2)
    for name, parts in blocks.values():
        if name in _HEADINGS:  # already a heading surface
            continue
        words = " ".join(parts).split()
        if len(words) < ALIGN_PASSAGE_MIN_WORDS:
            continue
        for start in range(0, max(1, len(words) - step), step):
            surfaces.append(("passage", " ".join(words[start : start + ALIGN_PASSAGE_MAX_WORDS])))
    return surfaces


def align_prompts(prompts: list[str], surfaces: list[tuple[str, str]]) -> list[AlignItem]:
    """Score each prompt against the surfaces; items keep the order of ``prompts``. Terms are compared by their
    English-plural stem; ``matched_terms`` and ``missing_terms`` show the words as the prompt spells them."""
    tokenised = [(surface, text, {_stem(t) for t in tokenize(text)}) for surface, text in surfaces]
    page_terms: set[str] = set().union(*(t for _, _, t in tokenised)) if tokenised else set()
    items: list[AlignItem] = []
    for prompt in prompts:
        terms = list(dict.fromkeys(tokenize(prompt)))
        if not terms:
            continue
        stems = [_stem(t) for t in terms]
        best_score, best_surface, best_text, best_hits = 0.0, "", "", set()
        for surface, text, unit_terms in tokenised:
            hits = unit_terms.intersection(stems)
            score = len(hits) / len(stems) * ALIGN_SURFACE_WEIGHTS[surface]
            if score > best_score:
                best_score, best_surface, best_text, best_hits = score, surface, text, hits
        shown = round(best_score, 2)  # the status follows the number the report shows
        status = "covered" if shown >= ALIGN_COVERED_MIN else "partial" if shown >= ALIGN_PARTIAL_MIN else "uncovered"
        items.append(
            AlignItem(
                prompt=prompt,
                score=shown,
                status=status,
                surface=best_surface,
                matched_terms=[t for t, st in zip(terms, stems, strict=True) if st in best_hits],
                missing_terms=[t for t, st in zip(terms, stems, strict=True) if st not in page_terms],
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
