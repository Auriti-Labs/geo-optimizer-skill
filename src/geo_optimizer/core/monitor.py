"""Monitoraggio passivo della visibilita' AI per un dominio."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlparse

from geo_optimizer.core.audit import run_full_audit
from geo_optimizer.core.history import HistoryStore
from geo_optimizer.models.config import (
    BOT_TIERS,
    CITATION_BOTS,
    DEFAULT_HISTORY_RETENTION_DAYS,
    MONITOR_BANDS,
    MONITOR_SCORING,
    SCORING,
)
from geo_optimizer.models.results import AuditResult, HistoryResult, MonitorResult, MonitorSignal

_MAX_BRAND_SCORE = sum(value for key, value in SCORING.items() if key.startswith("brand_"))


def normalize_monitor_domain(domain: str) -> str:
    """Normalizza input domain/url verso la homepage canonica del dominio."""
    raw = domain.strip()
    if not raw.lower().startswith(("http://", "https://")):
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    scheme = parsed.scheme or "https"
    hostname = (parsed.hostname or "").lower()
    return f"{scheme}://{hostname}"


def run_passive_monitor(
    domain: str,
    use_cache: bool = False,
    project_config=None,
    save_history: bool = True,
    retention_days: int = DEFAULT_HISTORY_RETENTION_DAYS,
    history_db: Path | None = None,
) -> MonitorResult:
    """Esegue il monitor passivo per un dominio riusando audit + history locale."""
    normalized = normalize_monitor_domain(domain)
    audit_result = run_full_audit(normalized, use_cache=use_cache, project_config=project_config)

    history_result = None
    store = HistoryStore(history_db)
    if save_history and not audit_result.error:
        store.save_audit_result(audit_result, retention_days=retention_days)
    history_result = store.build_history_result(normalized, retention_days=retention_days)

    return build_passive_monitor_result(audit_result, history_result)


def build_passive_monitor_result(
    audit_result: AuditResult, history_result: HistoryResult | None = None
) -> MonitorResult:
    """Costruisce uno snapshot di monitoraggio da audit e history opzionale."""
    signals = [
        _citation_bot_signal(audit_result),
        _user_fetch_signal(audit_result),
        _llms_signal(audit_result),
        _ai_discovery_signal(audit_result),
        _entity_signal(audit_result),
        _trust_signal(audit_result),
        _momentum_signal(history_result),
    ]
    visibility_score = sum(signal.score for signal in signals)
    recommendations = _build_monitor_recommendations(audit_result, history_result, signals)
    parsed = urlparse(audit_result.url)

    return MonitorResult(
        domain=parsed.hostname or audit_result.url,
        url=audit_result.url,
        timestamp=audit_result.timestamp,
        visibility_score=visibility_score,
        band=_monitor_band(visibility_score),
        total_snapshots=history_result.total_snapshots if history_result else 0,
        score_delta=history_result.score_delta if history_result else None,
        latest_geo_score=audit_result.score,
        latest_geo_band=audit_result.band,
        signals=signals,
        recommendations=recommendations,
        error=audit_result.error,
    )


def _citation_bot_signal(audit_result: AuditResult) -> MonitorSignal:
    """Valuta quanto il dominio sia accessibile ai citation bot critici."""
    allowed = sorted(set(audit_result.robots.bots_allowed) & set(CITATION_BOTS))
    max_score = int(MONITOR_SCORING["citation_bot_access"])
    score = round(max_score * (len(allowed) / max(1, len(CITATION_BOTS))))
    status = "strong" if len(allowed) == len(CITATION_BOTS) else "partial" if allowed else "missing"
    return MonitorSignal(
        key="citation_bot_access",
        label="Citation bot access",
        score=score,
        max_score=max_score,
        status=status,
        details={
            "allowed_bots": allowed,
            "missing_bots": sorted(set(CITATION_BOTS) - set(allowed)),
            "robots_found": audit_result.robots.found,
        },
    )


def _user_fetch_signal(audit_result: AuditResult) -> MonitorSignal:
    """Valuta l'accesso on-demand dei bot user-tier."""
    user_bots = set(BOT_TIERS["user"])
    allowed = sorted(set(audit_result.robots.bots_allowed) & user_bots)
    max_score = int(MONITOR_SCORING["user_fetch_access"])
    score = round(max_score * (len(allowed) / max(1, len(user_bots))))
    status = "strong" if score >= max_score * 0.7 else "partial" if score > 0 else "missing"
    return MonitorSignal(
        key="user_fetch_access",
        label="User fetch bot access",
        score=score,
        max_score=max_score,
        status=status,
        details={
            "allowed_bots": allowed,
            "tracked_bots": sorted(user_bots),
        },
    )


def _llms_signal(audit_result: AuditResult) -> MonitorSignal:
    """Valuta la readiness di llms.txt come surface organizzativa AI."""
    max_score = int(MONITOR_SCORING["llms_readiness"])
    score = 0
    if audit_result.llms.found:
        score += 7
    if audit_result.llms.has_h1 or audit_result.llms.has_blockquote:
        score += 3
    if audit_result.llms.has_sections:
        score += 3
    if audit_result.llms.has_links:
        score += 2
    score = min(score, max_score)
    status = "strong" if score >= 12 else "partial" if score > 0 else "missing"
    return MonitorSignal(
        key="llms_readiness",
        label="llms.txt readiness",
        score=score,
        max_score=max_score,
        status=status,
        details={
            "found": audit_result.llms.found,
            "sections": audit_result.llms.has_sections,
            "links": audit_result.llms.has_links,
            "word_count": audit_result.llms.word_count,
        },
    )


def _ai_discovery_signal(audit_result: AuditResult) -> MonitorSignal:
    """Valuta gli endpoint AI discovery esposti dal dominio."""
    max_score = int(MONITOR_SCORING["ai_discovery_readiness"])
    endpoints = int(audit_result.ai_discovery.endpoints_found or 0)
    score = round(max_score * (endpoints / 4))
    status = "strong" if endpoints >= 3 else "partial" if endpoints > 0 else "missing"
    return MonitorSignal(
        key="ai_discovery_readiness",
        label="AI discovery endpoints",
        score=score,
        max_score=max_score,
        status=status,
        details={
            "endpoints_found": endpoints,
            "has_well_known_ai": audit_result.ai_discovery.has_well_known_ai,
            "has_summary": audit_result.ai_discovery.has_summary,
            "has_faq": audit_result.ai_discovery.has_faq,
            "has_service": audit_result.ai_discovery.has_service,
        },
    )


def _entity_signal(audit_result: AuditResult) -> MonitorSignal:
    """Valuta segnali di entity/brand alignment utili alla visibilita' AI."""
    max_score = int(MONITOR_SCORING["entity_strength"])
    raw_score = int(audit_result.score_breakdown.get("brand_entity", 0))
    score = round(max_score * (raw_score / max(1, _MAX_BRAND_SCORE)))
    status = "strong" if score >= 11 else "partial" if score > 0 else "missing"
    return MonitorSignal(
        key="entity_strength",
        label="Brand & entity strength",
        score=score,
        max_score=max_score,
        status=status,
        details={
            "brand_name_consistent": audit_result.brand_entity.brand_name_consistent,
            "kg_pillar_count": audit_result.brand_entity.kg_pillar_count,
            "has_about_link": audit_result.brand_entity.has_about_link,
            "has_contact_info": audit_result.brand_entity.has_contact_info,
        },
    )


def _trust_signal(audit_result: AuditResult) -> MonitorSignal:
    """Valuta la forza complessiva del trust stack come readiness indiretta."""
    max_score = int(MONITOR_SCORING["trust_strength"])
    composite = int(audit_result.trust_stack.composite_score or 0)
    score = round(max_score * (composite / 25))
    status = "strong" if score >= 11 else "partial" if score > 0 else "missing"
    return MonitorSignal(
        key="trust_strength",
        label="Trust stack strength",
        score=score,
        max_score=max_score,
        status=status,
        details={
            "composite_score": composite,
            "grade": audit_result.trust_stack.grade,
            "trust_level": audit_result.trust_stack.trust_level,
        },
    )


def _momentum_signal(history_result: HistoryResult | None) -> MonitorSignal:
    """Valuta il trend recente del dominio nella history locale."""
    max_score = int(MONITOR_SCORING["momentum"])
    if history_result is None or history_result.total_snapshots == 0:
        return MonitorSignal(
            key="momentum",
            label="Trend momentum",
            score=max_score // 2,
            max_score=max_score,
            status="unknown",
            details={"reason": "no_history"},
        )

    delta = history_result.score_delta
    if delta is None:
        score = max_score // 2
        status = "unknown"
    elif delta >= 5:
        score = max_score
        status = "strong"
    elif delta > 0:
        score = 8
        status = "strong"
    elif delta == 0:
        score = 6
        status = "stable"
    elif delta > -5:
        score = 3
        status = "weak"
    else:
        score = 1
        status = "weak"

    return MonitorSignal(
        key="momentum",
        label="Trend momentum",
        score=score,
        max_score=max_score,
        status=status,
        details={
            "total_snapshots": history_result.total_snapshots,
            "score_delta": delta,
            "regression_detected": history_result.regression_detected,
        },
    )


def _build_monitor_recommendations(
    audit_result: AuditResult,
    history_result: HistoryResult | None,
    signals: list[MonitorSignal],
) -> list[str]:
    """Restituisce azioni prioritarie per il monitor passivo."""
    recommendations: list[str] = []
    signal_map = {signal.key: signal for signal in signals}

    if signal_map["citation_bot_access"].status != "strong":
        recommendations.append(
            "Open access for all citation-critical bots in robots.txt to improve AI answer eligibility."
        )
    if signal_map["llms_readiness"].status == "missing":
        recommendations.append("Publish a structured llms.txt file to expose key pages and topical sections.")
    if signal_map["ai_discovery_readiness"].status == "missing":
        recommendations.append("Add /.well-known/ai.txt and /ai/*.json endpoints for machine-readable discovery.")
    if signal_map["entity_strength"].status != "strong":
        recommendations.append(
            "Strengthen brand/entity signals with sameAs links, About page, and Organization schema."
        )
    if history_result and history_result.regression_detected:
        recommendations.append(
            "Latest local snapshot regressed vs previous run; review recent deploys before visibility drops compound."
        )

    for item in audit_result.recommendations:
        if item not in recommendations:
            recommendations.append(item)
        if len(recommendations) >= 5:
            break

    return recommendations


def _monitor_band(score: int) -> str:
    """Mappa il punteggio passive-monitor alla fascia descrittiva."""
    for band, (min_score, max_score) in MONITOR_BANDS.items():
        if min_score <= score <= max_score:
            return band
    return "low"


def monitor_result_to_dict(result: MonitorResult) -> dict[str, object]:
    """Helper serializzabile per i formatter JSON."""
    return asdict(result)
