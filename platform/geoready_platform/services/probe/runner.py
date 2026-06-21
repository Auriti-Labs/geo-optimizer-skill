"""Probe orchestrator: enqueue + execute.

Mirrors services/audits.py, with two deliberate differences:
- Probes query AI engines ABOUT the business and never crawl the entity site,
  so there is **no ownership-verification gate** (approved decision). Auth +
  per-org daily quota still apply.
- Every persisted Perception row records full provenance (provider, model,
  taxonomy_version, prompt, raw_response, timestamp) so historical comparisons
  stay valid as scoring/taxonomy evolve.
"""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from geoready_platform.config import get_settings
from geoready_platform.core_bridge.probe_adapter import resolve_probe_provider, run_prompt
from geoready_platform.db.base import session_scope
from geoready_platform.db.models import AuditStatus, BusinessEntity, Perception, ProbeRun
from geoready_platform.services.entities import get_entity
from geoready_platform.services.probe import hallucination, prompt_generator, share_of_model
from geoready_platform.services.probe.analysis import analyze_response
from geoready_platform.services.probe.share_of_model import AnalyzedResponse
from geoready_platform.services.probe.taxonomy import CATEGORY_BY_KEY


class ProbeQuotaExceededError(Exception):
    pass


class ProbeRunNotFoundError(Exception):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _domain_of(website_url: str) -> str:
    parsed = urlparse(website_url if "://" in website_url else f"https://{website_url}")
    return (parsed.netloc or parsed.path).split("/")[0].lower()


def _check_quota(session: Session, org_id: str) -> None:
    settings = get_settings()
    since = _utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    count = session.execute(
        select(func.count(ProbeRun.id)).where(ProbeRun.org_id == org_id, ProbeRun.created_at >= since)
    ).scalar_one()
    if count >= settings.free_probes_per_day:
        raise ProbeQuotaExceededError(f"Daily probe quota ({settings.free_probes_per_day}) reached")


def enqueue_probe(session: Session, *, org_id: str, entity_id: str) -> ProbeRun:
    """Create a queued probe run. Auth + quota only — NO ownership gate."""
    entity = get_entity(session, org_id=org_id, entity_id=entity_id)
    _check_quota(session, org_id)

    run = ProbeRun(
        entity_id=entity.id,
        org_id=org_id,
        status=AuditStatus.queued.value,
        taxonomy_version=prompt_generator.current_taxonomy_version(),
    )
    session.add(run)
    session.flush()
    run_id = run.id

    # Commit before dispatch so the worker (eager or remote) can read the run.
    session.commit()

    from geoready_platform.workers.probe_task import run_probe_job

    settings = get_settings()
    if settings.celery_eager:
        run_probe_job.apply(args=[run_id])
    else:
        run_probe_job.delay(run_id)

    return run


def get_probe(session: Session, *, org_id: str, run_id: str) -> ProbeRun:
    run = session.execute(
        select(ProbeRun).where(ProbeRun.id == run_id, ProbeRun.org_id == org_id)
    ).scalar_one_or_none()
    if run is None:
        raise ProbeRunNotFoundError(run_id)
    return run


def execute_probe_run(run_id: str) -> None:
    """Run all prompts for a probe, persist per-prompt Perceptions + run metrics."""
    settings = get_settings()

    # Phase A: load run + entity facts, mark running.
    with session_scope() as session:
        run = session.get(ProbeRun, run_id)
        if run is None:
            raise ProbeRunNotFoundError(run_id)
        entity = session.get(BusinessEntity, run.entity_id)
        if entity is None:
            run.status = AuditStatus.failed.value
            run.error = "Entity missing at execution time"
            run.completed_at = _utcnow()
            return
        run.status = AuditStatus.running.value
        run.started_at = _utcnow()
        facts = {
            "name": entity.canonical_name,
            "category": entity.category,
            "city": entity.geo,
            "domain": _domain_of(entity.website_url),
        }
        org_id = entity.org_id
        entity_id = entity.id
        taxonomy_version = run.taxonomy_version
        session.flush()

    # Resolve provider once.
    provider, api_key = resolve_probe_provider(settings.probe_provider)
    if not provider or not api_key:
        with session_scope() as session:
            run = session.get(ProbeRun, run_id)
            if run is not None:
                run.status = AuditStatus.failed.value
                run.error = (
                    "No AI provider configured. Set PERPLEXITY_API_KEY (recommended: real web-grounded "
                    "answers) or OPENAI_API_KEY / ANTHROPIC_API_KEY."
                )
                run.completed_at = _utcnow()
        return

    prompts = prompt_generator.generate_prompts(
        name=facts["name"],
        category=facts["category"],
        city=facts["city"],
        country=None,
        max_prompts=settings.probe_max_prompts,
    )

    # Phase B: run prompts OUTSIDE any DB transaction (network I/O).
    rows: list[dict] = []
    analyzed: list[AnalyzedResponse] = []
    model_seen = ""
    answered = 0

    for gp in prompts:
        resp = run_prompt(gp.text, provider=provider, api_key=api_key)
        model_seen = model_seen or resp.model
        cat = CATEGORY_BY_KEY.get(gp.category)
        counts_for_factual = bool(cat and cat.counts_for_factual)
        is_answered = not resp.error and bool(resp.text.strip())
        answered += 1 if is_answered else 0

        signals = analyze_response(
            text=resp.text,
            citations=resp.citations,
            name=facts["name"],
            domain=facts["domain"],
        )
        flags = (
            hallucination.detect_flags(
                text=resp.text,
                category_key=gp.category,
                brand_mentioned=signals.brand_mentioned,
                name=facts["name"],
                city=facts["city"],
                counts_for_factual=counts_for_factual,
            )
            if is_answered
            else []
        )

        analyzed.append(
            AnalyzedResponse(
                category=gp.category,
                answered=is_answered,
                brand_mentioned=signals.brand_mentioned,
                competitor_domains=signals.competitor_domains,
                competitor_names=signals.competitor_names,
            )
        )
        rows.append(
            {
                "prompt_category": gp.category,
                "prompt": gp.text,
                "provider": resp.provider,
                "model": resp.model,
                "raw_response": resp.text,
                "recommended": signals.brand_mentioned if (cat and cat.counts_for_share) else None,
                "brand_mentioned": signals.brand_mentioned,
                "domain_cited": signals.domain_cited,
                "competitors_named": signals.competitor_domains + signals.competitor_names,
                "flags": [f.__dict__ for f in flags],
                "error": resp.error,
            }
        )

    som = share_of_model.compute_share_of_model(analyzed)
    run_flags = [
        {**f, "perception_index": i}
        for i, row in enumerate(rows)
        for f in row["flags"]
    ]

    # Phase C: persist everything.
    with session_scope() as session:
        run = session.get(ProbeRun, run_id)
        if run is None:
            raise ProbeRunNotFoundError(run_id)
        run.status = AuditStatus.complete.value
        run.provider = provider
        run.model = model_seen
        run.prompt_count = len(rows)
        run.answered_count = answered
        run.share_of_model = som.share_of_model
        run.recommended_count = som.recommended_count
        run.competitors = som.competitors
        run.flags = run_flags
        run.completed_at = _utcnow()

        for row in rows:
            session.add(
                Perception(
                    entity_id=entity_id,
                    org_id=org_id,
                    probe_run_id=run_id,
                    engine=provider,
                    provider=row["provider"],
                    model=row["model"],
                    taxonomy_version=taxonomy_version,
                    prompt_category=row["prompt_category"],
                    prompt=row["prompt"],
                    raw_response=row["raw_response"],
                    recommended=row["recommended"],
                    brand_mentioned=row["brand_mentioned"],
                    domain_cited=row["domain_cited"],
                    competitors_named=row["competitors_named"],
                    flags=row["flags"],
                    details={"error": row["error"]} if row["error"] else None,
                )
            )
