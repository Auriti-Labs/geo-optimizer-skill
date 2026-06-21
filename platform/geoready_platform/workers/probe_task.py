"""The probe Celery task. Thin wrapper over services.probe.runner."""

from __future__ import annotations

import logging

from geoready_platform.config import get_settings
from geoready_platform.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
_settings = get_settings()


@celery_app.task(
    name="geoready_platform.run_probe_job",
    bind=True,
    max_retries=0,
    # Probes fan out to several LLM calls; allow generous headroom over a single audit.
    time_limit=_settings.audit_timeout_seconds * 6,
    soft_time_limit=_settings.audit_timeout_seconds * 6 - 10,
)
def run_probe_job(self, run_id: str) -> str:  # noqa: ANN001 — Celery self
    from geoready_platform.services.probe.runner import execute_probe_run

    logger.info("Running probe job %s", run_id)
    execute_probe_run(run_id)
    return run_id
