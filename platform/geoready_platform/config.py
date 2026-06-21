"""Platform configuration loaded from environment variables.

Deliberately dependency-light: a plain settings object backed by ``os.environ``
with sane local-dev defaults. No secrets are hard-coded; production must supply
``GR_JWT_SECRET`` and a real ``GR_DATABASE_URL``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the platform API and workers."""

    # ─── Database ────────────────────────────────────────────────────────────
    # Default to a local SQLite file so the foundation is runnable and testable
    # without Postgres. Production sets GR_DATABASE_URL to a postgres+psycopg URL.
    database_url: str = field(
        default_factory=lambda: os.environ.get("GR_DATABASE_URL", "sqlite:///./geoready_platform.db")
    )

    # ─── Cache / broker ──────────────────────────────────────────────────────
    redis_url: str = field(default_factory=lambda: os.environ.get("GR_REDIS_URL", "redis://localhost:6379/0"))

    # ─── Auth ────────────────────────────────────────────────────────────────
    jwt_secret: str = field(default_factory=lambda: os.environ.get("GR_JWT_SECRET", "dev-insecure-change-me"))
    jwt_algorithm: str = field(default_factory=lambda: os.environ.get("GR_JWT_ALG", "HS256"))
    jwt_ttl_seconds: int = field(default_factory=lambda: int(os.environ.get("GR_JWT_TTL_SECONDS", "3600")))

    # ─── AI provider keys (slotted now, unused until later phases) ────────────
    openai_api_key: str | None = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY"))
    anthropic_api_key: str | None = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY"))
    perplexity_api_key: str | None = field(default_factory=lambda: os.environ.get("PERPLEXITY_API_KEY"))

    # ─── Worker execution ────────────────────────────────────────────────────
    # When true, Celery runs tasks inline (no broker needed) — used by tests and
    # by single-process local dev. Production runs real workers (eager=False).
    celery_eager: bool = field(default_factory=lambda: _env_bool("GR_CELERY_EAGER", False))
    audit_timeout_seconds: int = field(default_factory=lambda: int(os.environ.get("GR_AUDIT_TIMEOUT_SECONDS", "60")))

    # ─── Rate limiting (per API key) ─────────────────────────────────────────
    free_audits_per_day: int = field(default_factory=lambda: int(os.environ.get("GR_FREE_AUDITS_PER_DAY", "5")))
    free_probes_per_day: int = field(default_factory=lambda: int(os.environ.get("GR_FREE_PROBES_PER_DAY", "3")))

    # ─── Perception probe ────────────────────────────────────────────────────
    probe_max_prompts: int = field(default_factory=lambda: int(os.environ.get("GR_PROBE_MAX_PROMPTS", "8")))
    probe_provider: str | None = field(default_factory=lambda: os.environ.get("GR_PROBE_PROVIDER"))

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith(("postgres", "postgresql"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance (read once per process)."""
    return Settings()
