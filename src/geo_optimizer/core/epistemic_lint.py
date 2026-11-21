"""Epistemic lint: sentences on a page that make a claim without the support a reader (or an AI engine) needs.

Three families, all deterministic text heuristics with false positives:

- authority laundering: a statistic with no source, date or sample next to it, a badge or superlative with no link;
- relevance flooding: the same block repeated, or a block that is only a long list of short keywords;
- caveat omission: an absolute promise ("guaranteed", "always", "risk-free") with no qualifier in the same block.

A finding is a question to ask about the sentence. Nothing here is scored and no language model is used. The text
blocks are found in one pass, each text node assigned to its nearest block ancestor. ``core/`` does not print.
"""

from __future__ import annotations

import re
from collections import Counter

from bs4 import BeautifulSoup, Comment, Doctype

from geo_optimizer.models.config import (
    LINT_ABSOLUTE_RE,
    LINT_AUTHORITY_RE,
    LINT_DUPLICATE_BLOCKS_MIN,
    LINT_EVIDENCE_RE,
    LINT_EXCERPT_CHARS,
    LINT_KEYWORD_LIST_MAX_ITEM_WORDS,
    LINT_KEYWORD_LIST_MIN_ITEMS,
    LINT_MAX_FINDINGS,
    LINT_MIN_BLOCK_WORDS,
    LINT_NEGATION_RE,
    LINT_QUALIFIER_RE,
    LINT_STATISTIC_RE,
)
from geo_optimizer.models.results import LintFinding, LintResult
from geo_optimizer.utils.html_blocks import BlockResolver
from geo_optimizer.utils.http import fetch_url
from geo_optimizer.utils.validators import normalize_url_scheme

_STATISTIC = re.compile(LINT_STATISTIC_RE, re.IGNORECASE)
_EVIDENCE = re.compile(LINT_EVIDENCE_RE, re.IGNORECASE)
_AUTHORITY = re.compile(LINT_AUTHORITY_RE, re.IGNORECASE)
_ABSOLUTE = re.compile(LINT_ABSOLUTE_RE, re.IGNORECASE)
_QUALIFIER = re.compile(LINT_QUALIFIER_RE, re.IGNORECASE)
_NEGATION = re.compile(LINT_NEGATION_RE, re.IGNORECASE)
_SENTENCES = re.compile(r"(?<=[.!?])\s+")
_NOISE_TAGS = ("script", "style", "noscript", "template", "nav", "footer", "aside", "svg", "pre", "code", "kbd", "samp")
_BLOCK_TAGS = frozenset(
    {"p", "li", "td", "th", "dd", "dt", "blockquote", "div", "section", "article", "main", "figcaption", "summary"}
    | {"h1", "h2", "h3", "h4", "h5", "h6"}
)
_FAMILY = {
    "unsourced_statistic": "authority_laundering",
    "unsupported_authority": "authority_laundering",
    "duplicate_block": "relevance_flooding",
    "keyword_list": "relevance_flooding",
    "caveat_omitted": "caveat_omission",
}
_WHY = {
    "unsourced_statistic": "A figure with no source, date or sample in the block or beside it: say where it comes from.",
    "unsupported_authority": "A badge or superlative with no link to evidence in the block.",
    "duplicate_block": "The same block appears several times: repetition does not add information.",
    "keyword_list": "A block that is only a long list of short items reads as a keyword list, not as content.",
    "caveat_omitted": "An absolute promise with no qualifier (limits, conditions, 'up to', 'depends') in the block.",
}


def text_blocks(soup: BeautifulSoup) -> list[tuple[str, bool]]:
    """``(text, has_link)`` for each block of the page body, found in a single pass over the text nodes."""
    body = soup.body or soup
    for tag in body(_NOISE_TAGS):
        tag.decompose()
    resolver = BlockResolver(body, _BLOCK_TAGS)
    blocks: dict[int, list] = {}
    for node in body.find_all(string=True):
        if isinstance(node, (Comment, Doctype)) or not node.strip():
            continue
        owner, linked = resolver.resolve(node)
        entry = blocks.setdefault(id(owner), [[], False])
        entry[0].append(str(node).strip())
        entry[1] = entry[1] or linked
    return [(" ".join(parts), linked) for parts, linked in blocks.values() if parts]


def _excerpt(text: str, match: re.Match[str] | None = None) -> str:
    if match is None or len(text) <= LINT_EXCERPT_CHARS:
        return text[:LINT_EXCERPT_CHARS]
    start = max(0, match.start() - LINT_EXCERPT_CHARS // 3)
    return text[start : start + LINT_EXCERPT_CHARS]


def _promise(text: str) -> re.Match[str] | None:
    """The first absolute promise in ``text`` that is asserted: sentences that ask (``?``) or that deny or soften
    the promise in the few words before it (``does not guarantee``, ``almost always``) do not count."""
    offset = 0
    for sentence in _SENTENCES.split(text):
        start = text.find(sentence, offset)
        offset = start + len(sentence)
        if sentence.rstrip().endswith("?"):
            continue
        for match in _ABSOLUTE.finditer(sentence):
            if not _NEGATION.search(sentence[max(0, match.start() - 30) : match.start()]):
                return _ABSOLUTE.search(text, start + match.start())
    return None


def lint_blocks(blocks: list[tuple[str, bool]]) -> list[LintFinding]:
    """Apply the three families to ``blocks``. A block's neighbours count as its context for evidence."""
    findings: list[LintFinding] = []

    def add(rule: str, text: str, match: re.Match[str] | None = None) -> None:
        findings.append(LintFinding(rule=rule, family=_FAMILY[rule], excerpt=_excerpt(text, match), why=_WHY[rule]))

    for i, (text, linked) in enumerate(blocks):
        if len(text.split()) < LINT_MIN_BLOCK_WORDS:
            continue
        context = " ".join(b[0] for b in blocks[max(0, i - 1) : i + 2])
        stat = _STATISTIC.search(text)
        if stat and not linked and not _EVIDENCE.search(context):
            add("unsourced_statistic", text, stat)
        authority = _AUTHORITY.search(text)
        if authority and not linked:
            add("unsupported_authority", text, authority)
        absolute = _promise(text)
        if absolute and not _QUALIFIER.search(text):
            add("caveat_omitted", text, absolute)
        items = [part for part in re.split(r"[,|;•·]", text) if part.strip()]
        if len(items) >= LINT_KEYWORD_LIST_MIN_ITEMS and all(
            len(part.split()) <= LINT_KEYWORD_LIST_MAX_ITEM_WORDS for part in items
        ):
            add("keyword_list", text)
    repeated = Counter(" ".join(t.casefold().split()) for t, _ in blocks if len(t.split()) >= LINT_MIN_BLOCK_WORDS)
    for normal, count in repeated.items():
        if count >= LINT_DUPLICATE_BLOCKS_MIN:
            add("duplicate_block", f"{normal} (appears {count} times)")
    return findings


def analyze_lint(url: str) -> LintResult:
    """Fetch ``url`` (anti-SSRF checks included) and lint its text."""
    target = normalize_url_scheme(url)
    result = LintResult(url=target)
    response, error = fetch_url(target)
    if error or response is None:
        result.error = error or "No response"
        return result
    blocks = text_blocks(BeautifulSoup(response.text, "html.parser"))
    findings = lint_blocks(blocks)
    result.blocks_checked = len(blocks)
    result.counts = dict(Counter(f.rule for f in findings))
    result.truncated = len(findings) > LINT_MAX_FINDINGS
    result.findings = findings[:LINT_MAX_FINDINGS]
    return result
