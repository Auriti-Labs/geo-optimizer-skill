"""Audit euristico dell'accuratezza fattuale di una pagina web."""

from __future__ import annotations

import re
from typing import Callable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from geo_optimizer.models.results import FactualAccuracyResult
from geo_optimizer.utils.http import fetch_url

_NUMERIC_CLAIM_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?%"
    r"|[$€£]\s?\d+(?:[.,]\d+)*"
    r"|\b\d+(?:[.,]\d+)?\s*(?:x|times|volte)\b"
    r"|\b\d+(?:[.,]\d+)?\s*(?:million|billion|thousand|milioni|miliardi)\b",
    re.IGNORECASE,
)
_EVIDENCE_CLAIM_RE = re.compile(
    r"\b(?:stud(?:y|ies)|research|survey|report|data)\s+(?:shows?|found|founds|suggests?|indicates?)\b"
    r"|\b(?:secondo|according to|as reported by|as noted by|source:|fonte:)\b",
    re.IGNORECASE,
)
_ATTRIBUTION_RE = re.compile(
    r"\b(?:according to|as reported by|as noted by|source:|fonte:|secondo|come riportato da|come indicato da)\b",
    re.IGNORECASE,
)
_ATTRIBUTION_SPLIT_RE = re.compile(
    r"\b(?:according to|as reported by|as noted by|source:|fonte:|secondo|come riportato da|come indicato da)\b",
    re.IGNORECASE,
)
_UNVERIFIABLE_RE = re.compile(
    r"\b(?:best|only|guaranteed|guarantee|always|never|revolutionary|industry-leading"
    r"|migliore|unico|garantit[oa]|sempre|mai|rivoluzionari[oa])\b",
    re.IGNORECASE,
)
_UPDATED_YEAR_RE = re.compile(
    r"\b(?:last\s+updated|updated|aggiornat[oa]\s+il|aggiornat[oa])\D{0,12}(20\d{2})\b",
    re.IGNORECASE,
)
_COPYRIGHT_YEAR_RE = re.compile(r"\b(?:copyright|©)\s*(20\d{2})\b", re.IGNORECASE)
_WORD_RE = re.compile(r"[a-z]{3,}")

_CONTEXT_STOPWORDS = {
    "about",
    "after",
    "also",
    "analysis",
    "because",
    "best",
    "claim",
    "data",
    "dati",
    "della",
    "delle",
    "dello",
    "does",
    "from",
    "guaranteed",
    "guarantee",
    "have",
    "https",
    "industry",
    "leading",
    "migliore",
    "nostro",
    "nostra",
    "only",
    "other",
    "our",
    "page",
    "per",
    "report",
    "results",
    "risultati",
    "site",
    "sono",
    "source",
    "study",
    "survey",
    "that",
    "their",
    "there",
    "these",
    "this",
    "una",
    "uno",
    "website",
    "with",
}
_CLAIM_TAGS = ("p", "li", "blockquote", "td", "th")
_MAX_SNIPPET = 160
_DEFAULT_MAX_SOURCE_CHECKS = 8


def run_factual_accuracy_audit(url: str, max_source_checks: int = _DEFAULT_MAX_SOURCE_CHECKS) -> FactualAccuracyResult:
    """Scarica una pagina e restituisce un audit fattuale euristico."""
    base_url = url.rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url

    response, err = fetch_url(base_url)
    # `response is None`: an HTTP error Response is falsy (requests sets __bool__ to
    # `ok`), so this used to claim the page was unreachable when it had answered.
    if err or response is None:
        return FactualAccuracyResult(
            checked=False,
            inconsistencies=[f"Unable to reach {base_url}: {err or 'connection failed'}"],
            severity="high",
        )
    if response.status_code not in (200, 203):
        return FactualAccuracyResult(
            checked=False,
            inconsistencies=[f"Page returned HTTP {response.status_code}"],
            severity="high",
        )

    soup = BeautifulSoup(response.text, "html.parser")
    return audit_factual_accuracy(
        soup=soup,
        html=response.text,
        base_url=base_url,
        max_source_checks=max_source_checks,
        link_fetcher=fetch_url,
    )


def audit_factual_accuracy(
    soup,
    html: str,
    base_url: str,
    max_source_checks: int = _DEFAULT_MAX_SOURCE_CHECKS,
    link_fetcher: Callable[[str], tuple[object | None, object | None]] | None = None,
) -> FactualAccuracyResult:
    """Analizza claims, attribuzioni, incoerenze e link sorgente rotti."""
    result = FactualAccuracyResult(checked=True)
    fetcher = link_fetcher or fetch_url

    seen_claims: set[str] = set()
    numeric_contexts: dict[str, set[str]] = {}
    source_links_to_check: list[str] = []

    for node in soup.find_all(_CLAIM_TAGS):
        text = _normalize_text(node.get_text(" ", strip=True))
        if len(text.split()) < 6:
            continue
        if text in seen_claims:
            continue
        seen_claims.add(text)

        has_numeric_claim = bool(_NUMERIC_CLAIM_RE.search(text))
        has_evidence_claim = bool(_EVIDENCE_CLAIM_RE.search(text))
        has_unverifiable_claim = bool(_UNVERIFIABLE_RE.search(text))
        if not (has_numeric_claim or has_evidence_claim or has_unverifiable_claim):
            continue

        result.claims_found += 1

        if has_unverifiable_claim:
            _append_unique(result.unverifiable_claims, _snippet(text))

        support_links = _extract_support_links(node, base_url)
        if support_links:
            for link in support_links:
                if link not in source_links_to_check:
                    source_links_to_check.append(link)

        if has_numeric_claim or has_evidence_claim:
            if support_links or _ATTRIBUTION_RE.search(text):
                result.claims_sourced += 1
            else:
                result.claims_unsourced += 1
                _append_unique(result.unsourced_claims, _snippet(text))

        if has_numeric_claim:
            context_key = _context_key(text)
            values = _extract_numeric_values(text)
            if context_key and values:
                numeric_contexts.setdefault(context_key, set()).update(values)

    _collect_date_inconsistencies(result, html)
    _collect_numeric_inconsistencies(result, numeric_contexts)
    _check_source_links(result, source_links_to_check, fetcher, max_source_checks)
    result.severity = _severity_for_result(result)
    return result


def _normalize_text(text: str) -> str:
    """Compatta spazi multipli e restituisce testo lineare."""
    return " ".join(text.split())


def _snippet(text: str) -> str:
    """Restituisce uno snippet corto e leggibile."""
    return text if len(text) <= _MAX_SNIPPET else text[: _MAX_SNIPPET - 3].rstrip() + "..."


def _append_unique(items: list[str], value: str) -> None:
    """Aggiunge un valore se non gia' presente."""
    if value and value not in items:
        items.append(value)


def _extract_support_links(node, base_url: str) -> list[str]:
    """Estrae link candidati a supporto fattuale dalla stessa unita' di testo."""
    parsed_base = urlparse(base_url)
    base_host = (parsed_base.hostname or "").lower()
    links: list[str] = []

    for anchor in node.find_all("a", href=True):
        href = (anchor.get("href") or "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        resolved = urljoin(base_url, href)
        parsed = urlparse(resolved)
        if parsed.scheme not in {"http", "https"}:
            continue
        host = (parsed.hostname or "").lower()
        if host == base_host and parsed.fragment:
            continue
        if resolved not in links:
            links.append(resolved)

    return links


def _context_key(text: str) -> str:
    """Normalizza un claim numerico per confrontare valori in conflitto."""
    head = _ATTRIBUTION_SPLIT_RE.split(text, maxsplit=1)[0]
    head = _NUMERIC_CLAIM_RE.sub(" ", head.lower())
    words = [w for w in _WORD_RE.findall(head) if w not in _CONTEXT_STOPWORDS]
    return " ".join(words[:4])


def _extract_numeric_values(text: str) -> set[str]:
    """Estrae valori numerici significativi per il confronto."""
    return {match.group(0).replace(" ", "") for match in _NUMERIC_CLAIM_RE.finditer(text)}


def _collect_numeric_inconsistencies(result: FactualAccuracyResult, numeric_contexts: dict[str, set[str]]) -> None:
    """Segnala contesti con piu' valori numerici incompatibili."""
    for context, values in numeric_contexts.items():
        if context and len(values) > 1:
            ordered = ", ".join(sorted(values))
            _append_unique(result.inconsistencies, f"Conflicting numeric claims for '{context}': {ordered}")


def _collect_date_inconsistencies(result: FactualAccuracyResult, html: str) -> None:
    """Segnala mismatch evidenti tra anno di update e copyright."""
    updated_years = [int(year) for year in _UPDATED_YEAR_RE.findall(html)]
    copyright_years = [int(year) for year in _COPYRIGHT_YEAR_RE.findall(html)]
    if updated_years and copyright_years and max(updated_years) > max(copyright_years):
        _append_unique(
            result.inconsistencies,
            f"Updated year {max(updated_years)} is newer than copyright year {max(copyright_years)}.",
        )


def _check_source_links(
    result: FactualAccuracyResult,
    links: list[str],
    fetcher: Callable[[str], tuple[object | None, object | None]],
    max_source_checks: int,
) -> None:
    """Verifica un numero limitato di link sorgente per intercettare 404 ed errori."""
    for link in links[: max(0, max_source_checks)]:
        result.source_links_checked += 1
        response, err = fetcher(link)
        # Same falsy-Response trap, but here the outcome is right for the wrong
        # reason: a link answering 4xx/5xx IS broken. Made explicit so it does not
        # read as an oversight.
        if err or response is None or not response.ok:
            _append_unique(result.broken_source_links, link)
            continue

        status_code = getattr(response, "status_code", 0)
        if status_code not in (200, 203):
            _append_unique(result.broken_source_links, link)


def _severity_for_result(result: FactualAccuracyResult) -> str:
    """Calcola una severity compatta per output CLI/MCP."""
    if not result.checked:
        return "high"
    if result.inconsistencies or len(result.broken_source_links) >= 2 or result.claims_unsourced >= 3:
        return "high"
    if result.broken_source_links or result.claims_unsourced or len(result.unverifiable_claims) >= 2:
        return "medium"
    if result.unverifiable_claims:
        return "low"
    return "clean"
