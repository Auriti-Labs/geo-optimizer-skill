"""FastAPI application factory for the platform API.

Mounted independently from the OSS ``geo_optimizer.web`` demo. Structured
logging is configured with request/org/entity context; raw crawled HTML and
credentials are never logged.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from geoready_platform import __version__
from geoready_platform.api.routers import audits, entities, health, orgs, probe

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="GeoReady AI Visibility Platform API",
        version=__version__,
        description=(
            "Orgs, entities, ownership verification, audit-as-signal jobs (Phase 0), "
            "and the AI Perception Probe (Phase 1)."
        ),
    )
    app.include_router(health.router)
    app.include_router(orgs.router)
    app.include_router(entities.router)
    app.include_router(audits.router)
    app.include_router(probe.router)
    return app


app = create_app()
