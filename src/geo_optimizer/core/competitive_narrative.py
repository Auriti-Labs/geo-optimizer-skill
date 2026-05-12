"""Competitive Narrative Analysis - LLM-powered analysis of how competitors are described.

Analisi narrativa competitiva: usa LLM per estrarre come i competitor vengono
descritti dagli LLM (adjectives, frames, positioning). confronta il positioning
con il proprio e identifica gap di narrative.

Base: Princeton KDD 2024, AutoGEO ICLR 2026 - citability and content quality.
"""

from __future__ import annotations

import json as _json
import logging
from dataclasses import dataclass, field
from typing import Any

from geo_optimizer.core.audit import run_full_audit
from geo_optimizer.core.llm_client import query_llm
from geo_optimizer.models.results import AuditResult

logger = logging.getLogger(__name__)

# Pattern noti di prompt injection da rimuovere dai dati scrapati
_PROMPT_INJECTION_PATTERNS = [
    "ignore all previous instructions",
    "ignore previous",
    "disregard everything",
    "forget everything",
    "### system:",
    "### instruction:",
    "### human:",
    "### assistant:",
    "### user:",
    "[INST]",
    "[/INST]",
    "<|im_start|>",
    "<|im_end|>",
    "<|system|>",
    "<|user|>",
    "<|assistant|>",
    "system:",
    "assistant:",
]


def _sanitize_prompt_input(text: str, max_len: int = 500) -> str:
    """Sanitizza testo scrapato prima di interpolarlo in un LLM prompt.

    Rimuove pattern noti di prompt injection e tronca a max_len caratteri.
    """
    if not isinstance(text, str):
        text = str(text)
    text = text.strip()
    lower = text.lower()
    for pattern in _PROMPT_INJECTION_PATTERNS:
        if pattern in lower:
            text = text.replace(pattern, "")
            text = text.replace(pattern.title(), "")
            text = text.replace(pattern.upper(), "")
            text = text.replace(pattern.capitalize(), "")
    return text[:max_len].strip()


@dataclass
class CompetitorNarrative:
    """Narrazione estratta per un singolo competitor."""

    url: str
    brand_name: str = ""
    dominant_adjectives: list[str] = field(default_factory=list)  # e.g., "enterprise", "budget", "premium"
    key_frames: list[str] = field(default_factory=list)  # e.g., "AI-first", "developer-friendly"
    positioning: str = ""  # 1-liner positioning statement
    credibility_signals: list[str] = field(default_factory=list)  # trust indicators found
    content_gaps: list[str] = field(default_factory=list)  # narrative elements missing
    confidence: float = 0.0  # LLM confidence in this analysis
    score: int = 0  # GEO score (from audit), for display purposes
    has_error: bool = False  # LLM analysis failed for this competitor


@dataclass
class CompetitiveGap:
    """Gap di narrative tra il target e un competitor."""

    category: str  # e.g., "positioning", "credibility", "features"
    gap_type: str  # "missing", "weak", "opposing"
    competitor_url: str
    competitor_narrative: str
    target_missing: str
    suggested_content: str  # cosa aggiungere per colmare il gap
    impact: int  # punti GEO potenziali


@dataclass
class CompetitiveNarrativeResult:
    """Risultato completo dell'analisi competitiva narrativa."""

    target_url: str
    competitors: list[CompetitorNarrative] = field(default_factory=list)
    competitive_gaps: list[CompetitiveGap] = field(default_factory=list)
    summary: str = ""  # executive summary
    llm_usage: dict[str, int] = field(default_factory=dict)  # provider -> token count
    target_audit: AuditResult | None = None


# ─── LLM Prompts ──────────────────────────────────────────────────────────────


_NARRATIVE_EXTRACTOR_PROMPT = """Analizza come l'AI crawler (ChatGPT, Perplexity, Claude) potrebbe descrivere questo brand.

Page info:
- URL: {url}
- Brand name(s): {brand_names}
- H1: {h1}
- Title: {title}
- Description: {description}
- Content word count: {word_count}
- Key sections: {sections}

Richieste:
1. Estrai 3-5 aggettivi dominanti che definiscono questo brand
2. Identifica 2-4 "frames" o positioning chiave (es. "AI-first", "developer-friendly", "enterprise-grade")
3. Scrivi una frase di posizionamento (massimo 15 parole)
4. Estrai segnali di credibilità presenti (case study, testimonials, certifications)
5. Segnala cosa potrebbe mancare in termini di narrative (es. "nessuna menzione di sostenibilità")

Rispondi in JSON con struttura:
{{
  "dominant_adjectives": ["...", "..."],
  "key_frames": ["...", "..."],
  "positioning": "...",
  "credibility_signals": ["...", "..."],
  "content_gaps": ["...", "..."],
  "confidence": 0.85
}}""".strip()


_COMPETITIVE_COMPARISON_PROMPT = """Confronta il posizionamento di due brand nello stesso settore.

Brand Target (il tuo):
- URL: {target_url}
- Brand name: {target_brand}
- Positioning: {target_positioning}
- Key frames: {target_frames}

Brand Competitor:
- URL: {competitor_url}
- Brand name: {competitor_name}
- Positioning: {competitor_positioning}
- Key frames: {competitor_frames}

Richieste:
1. Quali sono le principali differenze di positioning?
2. Quali segmenti di mercato il competitor copre che mancano al target?
3. Quali signal manca al target che il competitor ha?
4. Quale contenuto dovrebbe creare il target per colmare il gap?

Rispondi in JSON con struttura:
{{
  "positioning_gap": "descrizione del gap principale",
  "missing_market_segment": "segmento mancante",
  "missing_signals": ["signal1", "signal2"],
  "suggested_content": "idea contenuto per colmare il gap",
  "geo_impact": 3  // 1-5, stima impatto GEO
}}""".strip()


# ─── Core Functions ───────────────────────────────────────────────────────────


def extract_competitor_narrative(url: str, audit: AuditResult) -> CompetitorNarrative:
    """Estrae la narrazione di un competitor usando LLM, basandosi sull'audit già eseguito.

    Args:
        url: URL del competitor
        audit: AuditResult già computed per questo URL

    Returns:
        CompetitorNarrative con adjectives, frames, positioning, score
    """
    result = CompetitorNarrative(url=url, score=audit.score, brand_name=audit.meta.title_text or "")

    # Build content summary from audit
    brand_names = audit.brand_entity.names_found if audit.brand_entity else []
    if not brand_names and audit.meta.title_text:
        # Fallback da meta
        # Estrai brand name da title (prima parte prima di separatori)
        for sep in (" — ", " - ", " | ", " · "):
            if sep in audit.meta.title_text:
                brand_names = [audit.meta.title_text.split(sep)[0].strip()]
                break
        if not brand_names:
            brand_names = [audit.meta.title_text[:100]]

    h1 = audit.content.h1_text if audit.content.h1_text else ""
    title = audit.meta.title_text or ""
    description = audit.meta.description_text or ""
    word_count = audit.content.word_count or 0

    # Sanitizza input scrapati prima di interpolarli nel prompt LLM
    safe_brand_names = [_sanitize_prompt_input(b, max_len=100) for b in brand_names[:3]]
    safe_h1 = _sanitize_prompt_input(h1, max_len=200)
    safe_title = _sanitize_prompt_input(title, max_len=200)
    safe_description = _sanitize_prompt_input(description, max_len=200)

    # Estrai section headers per contesto
    sections = []
    # Cerca H2 nel content (se available)
    if hasattr(audit, "_raw_html") and audit._raw_html:
        # Questo campo non esiste in AuditResult - use content heading_count
        sections = [f"H2 section (count: {audit.content.heading_count})"]
    else:
        sections = ["Headings structure present"]

    # Build prompt
    prompt = _NARRATIVE_EXTRACTOR_PROMPT.format(
        url=url,
        brand_names=", ".join(safe_brand_names) if safe_brand_names else "Unknown",
        h1=safe_h1 if safe_h1 else "None",
        title=safe_title if safe_title else "None",
        description=safe_description if safe_description else "None",
        word_count=word_count,
        sections=", ".join(sections),
    )

    # Query LLM
    system = "You are a marketing analyst specialized in AI search visibility and brand positioning."
    response = query_llm(prompt, system=system, max_tokens=512)

    if response.error:
        logger.warning("LLM query failed for %s: %s", url, response.error)
        result.positioning = "Unable to analyze - LLM unavailable"
        return result

    # Parse JSON response
    try:
        data = _json.loads(response.text)
        result.dominant_adjectives = data.get("dominant_adjectives", [])[:5]
        result.key_frames = data.get("key_frames", [])[:4]
        result.positioning = data.get("positioning", "")[:200]
        result.credibility_signals = data.get("credibility_signals", [])[:5]
        result.content_gaps = data.get("content_gaps", [])[:5]
        result.confidence = float(data.get("confidence", 0.5))
    except (_json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning("Failed to parse LLM response for %s: %s", url, exc)
        # Fallback values
        result.positioning = "Unable to parse analysis"
        result.confidence = 0.0

    return result


def run_competitive_narrative_analysis(
    target_url: str,
    competitor_urls: list[str],
) -> CompetitiveNarrativeResult:
    """Esegue analisi competitiva narrativa completa.

    Processo:
    1. Audit target
    2. Audit each competitor
    3. Extract narrative for each competitor
    4. Compare target vs competitors
    5. Generate gaps and recommendations

    Args:
        target_url: URL da analizzare (il proprio sito)
        competitor_urls: Lista di competitor URL

    Returns:
        CompetitiveNarrativeResult con gap e recommendations
    """
    result = CompetitiveNarrativeResult(target_url=target_url)

    # Audit target
    try:
        from geo_optimizer.utils.validators import validate_public_url

        # Anti-SSRF validation
        safe, reason = validate_public_url(target_url)
        if not safe:
            result.summary = f"Error: Invalid target URL - {reason}"
            return result

        target_audit = run_full_audit(target_url)
    except Exception as exc:
        result.summary = f"Error auditing target: {exc}"
        return result

    result.target_audit = target_audit  # Store for later use

    # Audit each competitor
    for url in competitor_urls:
        try:
            safe, reason = validate_public_url(url)
            if not safe:
                logger.warning("Skipping invalid URL: %s - %s", url, reason)
                continue

            competitor_audit = run_full_audit(url)
            narrative = extract_competitor_narrative(url, competitor_audit)
            result.competitors.append(narrative)
        except Exception as exc:
            logger.warning("Failed to audit competitor %s: %s", url, exc)
            # Add minimal competitor entry with error
            result.competitors.append(CompetitorNarrative(url=url, positioning=f"Error: {exc}"))

    if not result.competitors:
        result.summary = "Could not analyze any competitors - all URLs invalid or unavailable"
        return result

    # Generate competitive gaps
    result.competitive_gaps = _build_competitive_gaps(target_audit, result.competitors)

    # Generate summary
    result.summary = _build_summary(target_audit, result.competitors, result.competitive_gaps)

    return result


def _build_competitive_gaps(
    target_audit: AuditResult,
    competitors: list[CompetitorNarrative],
) -> list[CompetitiveGap]:
    """Confronta target vs competitors e genera gap di narrative."""
    gaps: list[CompetitiveGap] = []

    # Extract target info
    target_brand = target_audit.meta.title_text or ""
    for sep in (" — ", " - ", " | ", " · "):
        if sep in target_brand:
            target_brand = target_brand.split(sep)[0].strip()
            break

    target_frames = []

    # Extract frames from content signals
    if target_audit.content.word_count > 1000:
        target_frames.append("comprehensive")
    if target_audit.schema.has_faq:
        target_frames.append("authoritative")
    if target_audit.signals.has_rss:
        target_frames.append("active")

    for competitor in competitors:
        if competitor.positioning.startswith("Error") or competitor.positioning.startswith("Unable"):
            continue

        # Determine gap type
        gap_type = "missing"
        if competitor.confidence < 0.5:
            gap_type = "weak"

        # Build gap entry
        if competitor.content_gaps:
            for gap in competitor.content_gaps[:2]:  # Max 2 gaps per competitor
                gaps.append(
                    CompetitiveGap(
                        category="narrative",
                        gap_type=gap_type,
                        competitor_url=competitor.url,
                        competitor_narrative=competitor.positioning,
                        target_missing=gap,
                        suggested_content=f"Add content addressing: {gap}",
                        impact=2,  # Default impact
                    )
                )

    # Deduplicate
    seen = set()
    unique_gaps: list[CompetitiveGap] = []
    for candidate in gaps:
        key = (candidate.gap_type, candidate.target_missing)
        if key not in seen:
            seen.add(key)
            unique_gaps.append(candidate)

    return unique_gaps


def _build_summary(
    target_audit: AuditResult,
    competitors: list[CompetitorNarrative],
    gaps: list[CompetitiveGap],
) -> str:
    """Costruisce un executive summary dell'analisi."""
    if not competitors:
        return "No competitors analyzed"

    # Score comparison
    target_score = target_audit.score

    # Count gaps
    gap_count = len(gaps)

    # Build summary
    summary = f"Target score: {target_score}/100. Analyzed {len(competitors)} competitor(s). "
    if gap_count > 0:
        summary += f"Found {gap_count} narrative gap(s) where competitors outperform target. "
        summary += "Focus content efforts on closing these positioning gaps."
    else:
        summary += "No significant narrative gaps detected."

    return summary


# ─── API Helper Functions ──────────────────────────────────────────────────────


def format_competitive_narrative(result: CompetitiveNarrativeResult) -> dict[str, Any]:
    """Format competitive narrative result as dictionary for API response."""
    return {
        "target_url": result.target_url,
        "target_score": result.target_audit.score if result.target_audit is not None else 0,
        "target_band": result.target_audit.band if result.target_audit is not None else "critical",
        "competitors": [
            {
                "url": c.url,
                "brand_name": c.brand_name,
                "dominant_adjectives": c.dominant_adjectives,
                "key_frames": c.key_frames,
                "positioning": c.positioning,
                "credibility_signals": c.credibility_signals,
                "content_gaps": c.content_gaps,
                "confidence": c.confidence,
                "has_error": c.has_error,
            }
            for c in result.competitors
        ],
        "competitive_gaps": [
            {
                "category": g.category,
                "gap_type": g.gap_type,
                "competitor_url": g.competitor_url,
                "competitor_narrative": g.competitor_narrative,
                "target_missing": g.target_missing,
                "suggested_content": g.suggested_content,
                "impact": g.impact,
            }
            for g in result.competitive_gaps
        ],
        "summary": result.summary,
        "llm_usage": getattr(result, "llm_usage", {}),
    }


def get_competitor_narratives_for_audit(audit: AuditResult, competitor_urls: list[str]) -> list[CompetitorNarrative]:
    """Estrae narratives da una lista di URLs usando audit già eseguito come base.

    Args:
        audit: AuditResult (per il brand name extraction)
        competitor_urls: URLs da analizzare

    Returns:
        List of CompetitorNarrative
    """
    narratives = []
    for url in competitor_urls:
        narratives.append(CompetitorNarrative(url=url, brand_name=audit.meta.title_text or "Unknown"))
    return narratives
