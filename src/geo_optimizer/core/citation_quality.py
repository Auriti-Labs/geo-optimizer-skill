"""Valutazione qualitativa delle citazioni archiviate nelle risposte AI."""

from __future__ import annotations

import re

from geo_optimizer.models.results import AnswerCitation, AnswerSnapshot, CitationQualityReport, CitationQualityResult

_TIER_RULES = (
    (
        1,
        "recommended",
        (
            "recommend",
            "recommended",
            "top pick",
            "best choice",
            "best option",
            "consigliamo",
            "raccomand",
            "migliore scelta",
        ),
    ),
    (
        2,
        "highlighted",
        (
            "stands out",
            "stands apart",
            "strong option",
            "notable",
            "excellent for",
            "spicca",
            "si distingue",
            "ottima opzione",
        ),
    ),
    (
        3,
        "compared",
        (
            "compared",
            "compare",
            "versus",
            "vs.",
            "tools like",
            "alternative to",
            "alternatives",
            "confront",
            "paragon",
        ),
    ),
    (
        4,
        "listed",
        (
            "among others",
            "including",
            "for example",
            "for instance",
            "such as",
            "listed",
            "tra gli altri",
            "inclus",
        ),
    ),
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_SNIPPET_LIMIT = 180


def analyze_snapshot_citation_quality(
    snapshot: AnswerSnapshot,
    target_domain: str = "",
) -> CitationQualityReport:
    """Analizza il contesto di ciascuna citazione e assegna tier/score."""
    normalized_target = target_domain.lower().strip()
    entries: list[CitationQualityResult] = []
    total = len(snapshot.citations)

    for citation in snapshot.citations:
        if normalized_target and citation.domain != normalized_target:
            continue
        snippet = _context_snippet(snapshot.answer_text, citation)
        tier, label, cue = _tier_from_snippet(snippet)
        position_score = _position_score(citation.position, total)
        overall_score = max(1, (6 - tier) * 2 + position_score)
        entries.append(
            CitationQualityResult(
                url=citation.url,
                domain=citation.domain,
                position=citation.position,
                tier=tier,
                tier_label=label,
                cue=cue,
                position_score=position_score,
                overall_score=overall_score,
                context_snippet=snippet,
            )
        )

    entries.sort(key=lambda item: (-item.overall_score, item.position, item.url))
    return CitationQualityReport(
        snapshot_id=snapshot.snapshot_id,
        query=snapshot.query,
        model=snapshot.model,
        provider=snapshot.provider,
        recorded_at=snapshot.recorded_at,
        target_domain=normalized_target,
        total_citations=total,
        analyzed_citations=len(entries),
        entries=entries,
    )


def _tier_from_snippet(snippet: str) -> tuple[int, str, str]:
    """Determina il tier in base al linguaggio che circonda la citazione."""
    lowered = snippet.lower()
    for tier, label, cues in _TIER_RULES:
        for cue in cues:
            if cue in lowered:
                return tier, label, cue
    return 5, "mentioned", ""


def _position_score(position: int, total: int) -> int:
    """Attribuisce un bonus alle citazioni che compaiono prima nella risposta."""
    if total <= 1:
        return 5
    if position <= 1:
        return 5
    if position == 2:
        return 4
    if position <= 4:
        return 3
    if position <= 6:
        return 2
    return 1


def _context_snippet(answer_text: str, citation: AnswerCitation) -> str:
    """Estrae la frase o il contesto locale che contiene la citazione."""
    candidates = _SENTENCE_SPLIT_RE.split(answer_text)
    targets = [citation.url]
    if citation.domain:
        targets.append(citation.domain)
        host = citation.domain.split(".")[0]
        if host:
            targets.append(host.replace("-", " "))

    for sentence in candidates:
        lowered = sentence.lower()
        if any(target.lower() in lowered for target in targets if target):
            return _truncate(sentence.strip())

    index = answer_text.lower().find(citation.url.lower())
    if index == -1 and citation.domain:
        index = answer_text.lower().find(citation.domain.lower())
    if index == -1:
        return _truncate(answer_text.strip())

    start = max(0, index - 80)
    end = min(len(answer_text), index + max(len(citation.url), 60))
    return _truncate(answer_text[start:end].strip())


def _truncate(text: str) -> str:
    """Riduce lo snippet a una lunghezza leggibile."""
    compact = " ".join(text.split())
    if len(compact) <= _SNIPPET_LIMIT:
        return compact
    return compact[: _SNIPPET_LIMIT - 3].rstrip() + "..."
