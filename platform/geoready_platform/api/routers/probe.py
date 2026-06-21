"""AI Perception Probe endpoints.

Auth + per-org quota only — probes do NOT require ownership verification
(they query AI engines about the business and never crawl the entity's site).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from geoready_platform.api.deps import Principal, get_db, get_principal
from geoready_platform.db.models import Perception, ProbeRun
from geoready_platform.schemas.probe import PerceptionOut, ProbeEnqueuedOut, ProbeRunOut
from geoready_platform.services import entities as entity_svc
from geoready_platform.services.probe import runner as probe_svc

router = APIRouter(tags=["probe"])


@router.post("/v1/entities/{entity_id}/probes", response_model=ProbeEnqueuedOut, status_code=202)
def enqueue_probe(
    entity_id: str,
    session: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> ProbeEnqueuedOut:
    try:
        run = probe_svc.enqueue_probe(session, org_id=principal.org_id, entity_id=entity_id)
    except entity_svc.EntityNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entity not found") from None
    except probe_svc.ProbeQuotaExceededError as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc)) from None
    return ProbeEnqueuedOut(probe_run_id=run.id, status=run.status)


@router.get("/v1/probes/{run_id}", response_model=ProbeRunOut)
def get_probe(
    run_id: str,
    session: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> ProbeRunOut:
    try:
        run = probe_svc.get_probe(session, org_id=principal.org_id, run_id=run_id)
    except probe_svc.ProbeRunNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Probe run not found") from None
    return ProbeRunOut.model_validate(run)


@router.get("/v1/probes/{run_id}/responses", response_model=list[PerceptionOut])
def list_probe_responses(
    run_id: str,
    session: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> list[PerceptionOut]:
    # Ensure the run belongs to the caller's org before returning responses.
    try:
        probe_svc.get_probe(session, org_id=principal.org_id, run_id=run_id)
    except probe_svc.ProbeRunNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Probe run not found") from None

    rows = (
        session.execute(
            select(Perception)
            .where(Perception.probe_run_id == run_id, Perception.org_id == principal.org_id)
            .order_by(Perception.probed_at.asc())
        )
        .scalars()
        .all()
    )
    return [PerceptionOut.model_validate(r) for r in rows]


@router.get("/v1/entities/{entity_id}/probes", response_model=list[ProbeRunOut])
def list_entity_probes(
    entity_id: str,
    session: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> list[ProbeRunOut]:
    try:
        entity_svc.get_entity(session, org_id=principal.org_id, entity_id=entity_id)
    except entity_svc.EntityNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entity not found") from None

    rows = (
        session.execute(
            select(ProbeRun)
            .where(ProbeRun.entity_id == entity_id, ProbeRun.org_id == principal.org_id)
            .order_by(ProbeRun.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [ProbeRunOut.model_validate(r) for r in rows]
