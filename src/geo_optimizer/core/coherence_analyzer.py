"""
Cross-page semantic coherence analysis (#253).

Compares PageTermExtract from multiple pages to detect:
- Conflicting definitions (same term defined differently)
- Duplicate titles (identical or near-identical page titles)
- Mixed language (inconsistent lang attributes across pages)
"""

from __future__ import annotations

import re
from collections import defaultdict
from difflib import SequenceMatcher

from geo_optimizer.models.results import CoherenceIssue, PageTermExtract, SemanticCoherenceResult

_DUPLICATE_TITLE_THRESHOLD = 0.85
_PENALTY = {"high": 10, "medium": 5, "low": 2}


def analyze_coherence(extracts: list[PageTermExtract]) -> SemanticCoherenceResult:
    """Analyze terminology consistency across page extracts.

    Args:
        extracts: List of PageTermExtract from multiple pages.

    Returns:
        SemanticCoherenceResult with issues and coherence score.
    """
    if len(extracts) < 2:
        return SemanticCoherenceResult(checked=True, pages_analyzed=len(extracts))

    issues: list[CoherenceIssue] = []
    issues.extend(_check_conflicting_definitions(extracts))
    issues.extend(_check_duplicate_titles(extracts))
    issues.extend(_check_mixed_language(extracts))

    score = 100
    for issue in issues:
        score -= _PENALTY.get(issue.severity, 2)
    score = max(score, 0)

    langs = [e.language.split("-")[0] for e in extracts if e.language]
    if langs:
        most_common = max(set(langs), key=langs.count)
        lang_consistency = langs.count(most_common) / len(langs)
    else:
        lang_consistency = 1.0

    return SemanticCoherenceResult(
        checked=True,
        pages_analyzed=len(extracts),
        issues=issues,
        coherence_score=score,
        language_consistency=round(lang_consistency, 2),
    )


def _check_conflicting_definitions(extracts: list[PageTermExtract]) -> list[CoherenceIssue]:
    """Detect the same term defined differently across pages."""
    term_defs: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for ext in extracts:
        for defn in ext.definitions:
            term = _extract_defined_term(defn)
            if term:
                term_defs[term].append((ext.url, defn))

    issues: list[CoherenceIssue] = []
    for term, occurrences in term_defs.items():
        if len(occurrences) < 2:
            continue
        definitions = [d for _, d in occurrences]
        # Check if definitions are actually different
        if _definitions_conflict(definitions):
            pages = list({url for url, _ in occurrences})
            issues.append(
                CoherenceIssue(
                    issue_type="conflicting_definition",
                    severity="high",
                    description=f"Term '{term}' defined differently across {len(pages)} pages",
                    pages=pages,
                    terms=[term],
                )
            )
    return issues


def _check_duplicate_titles(extracts: list[PageTermExtract]) -> list[CoherenceIssue]:
    """Detect pages with identical or near-identical titles."""
    issues: list[CoherenceIssue] = []
    seen: set[tuple[int, int]] = set()

    for i, a in enumerate(extracts):
        if not a.title:
            continue
        for j, b in enumerate(extracts):
            if j <= i or not b.title:
                continue
            if (i, j) in seen:
                continue
            ratio = SequenceMatcher(None, a.title.lower(), b.title.lower()).ratio()
            if ratio >= _DUPLICATE_TITLE_THRESHOLD:
                seen.add((i, j))
                issues.append(
                    CoherenceIssue(
                        issue_type="duplicate_title",
                        severity="medium",
                        description=f"Near-duplicate titles (similarity {ratio:.0%}): '{a.title}'",
                        pages=[a.url, b.url],
                        terms=[a.title, b.title],
                    )
                )
    return issues


def _check_mixed_language(extracts: list[PageTermExtract]) -> list[CoherenceIssue]:
    """Detect inconsistent language attributes across pages."""
    lang_pages: dict[str, list[str]] = defaultdict(list)
    for ext in extracts:
        lang = ext.language.split("-")[0] if ext.language else ""
        if lang:
            lang_pages[lang].append(ext.url)

    if len(lang_pages) <= 1:
        return []

    most_common_lang = max(lang_pages, key=lambda k: len(lang_pages[k]))
    issues: list[CoherenceIssue] = []
    for lang, pages in lang_pages.items():
        if lang != most_common_lang:
            issues.append(
                CoherenceIssue(
                    issue_type="mixed_language",
                    severity="medium",
                    description=f"{len(pages)} page(s) in '{lang}' while majority is '{most_common_lang}'",
                    pages=pages,
                    terms=[lang, most_common_lang],
                )
            )
    return issues


def _extract_defined_term(definition: str) -> str:
    """Extract the subject term from a definition string."""
    match = re.match(r"^([A-Z][A-Za-z\s\-]{2,40}?)\s+(?:is|are|refers?\s+to|means?)", definition)
    return match.group(1).strip() if match else ""


def _definitions_conflict(definitions: list[str]) -> bool:
    """Check if multiple definitions of the same term actually differ."""
    if len(definitions) < 2:
        return False
    normalized = [d.lower().strip() for d in definitions]
    first = normalized[0]
    return any(SequenceMatcher(None, first, other).ratio() < 0.8 for other in normalized[1:])
