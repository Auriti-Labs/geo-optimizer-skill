# GeoReady AI Visibility Platform — Phase 0 Foundation

This directory is the commercial **AI Visibility Platform**. It is intentionally
isolated from the open-source `geo_optimizer` engine (`../src`): the platform
**wraps and reuses** the engine via `geoready_platform/core_bridge/` and never
modifies it.

> ⚠️ Phase 0 only. This is the foundation (entity spine, auth, ownership, the
> audit-as-signal worker, and a minimal API). There is **no UI, no perception
> probe, no AI fixes, and no attribution** yet — those are later phases. See
> [`../docs/ROADMAP.md`](../docs/ROADMAP.md), Appendix A.

## Why `geoready_platform/` and not `platform/`

Python's standard library owns the `platform` module. Naming our importable
package `platform` would shadow it and break dependencies that `import platform`.
The roadmap's `platform/` **directory** is preserved as the container; the
importable package is `geoready_platform`, and `platform/` is placed on
`sys.path` (see `pytest.ini` and `docker-compose.yml`).

## Architecture (dependency order)

```
config.py            env-driven settings (SQLite default; Postgres in prod)
db/base.py           SQLAlchemy engine, session, Base
db/models.py         entity spine: Org/User/ApiKey, BusinessEntity,
                     EntitySignal, AuditJob  (+ stub: Perception/Intervention/Impact)
services/auth.py     PBKDF2 hashing, API keys, JWT
services/ownership   DNS-TXT / well-known-file domain verification
services/entities    org-scoped entity CRUD + verification
services/audits      enqueue (ownership + quota gated) + execute_audit_job
core_bridge/         the ONLY code that touches the engine (audit + fix adapters)
workers/             Celery app + audit task (delegates to services.audits)
api/                 FastAPI app, deps (auth/org scoping), routers
alembic/             migrations (baseline creates tables; Postgres RLS policies)
```

## Operating loop (target)

`Audit → Explain → Fix → Implement → Verify → Monitor → Prove Business Impact`

Phase 0 implements the **Audit** stage as a queued, ownership-gated,
tenant-isolated job that writes results as *signals on an entity*.

**Phase 1 — AI Perception Probe** adds the user-visible wedge: query AI engines
(Perplexity Sonar by default, via the engine's LLM client) with buyer-intent
prompts, then compute **Share-of-Model v1**, **competitor mentions**, and
**hallucination/factual-mismatch flags**. Every per-prompt response is persisted
with full provenance (provider, model, taxonomy version, prompt, raw response,
timestamp) so historical comparisons stay valid as scoring evolves.

> **Probes require auth + per-org quota only — NOT ownership verification.**
> A probe queries AI engines *about* the business and never crawls the entity's
> site, so the SSRF/ownership rationale does not apply. This also keeps the path
> open for the future free public-probe wedge. (Audits, which DO crawl, remain
> verification-gated.)

The pure layers — `services/probe/{taxonomy,prompt_generator,analysis,share_of_model,hallucination}.py`
— contain no I/O and are fully unit-tested offline; the engine is touched only
through `core_bridge/probe_adapter.py`.

## Local development

```bash
# from repo root
pip install -e ".[platform,async]"

# run migrations (SQLite by default)
cd platform && alembic upgrade head

# API
uvicorn geoready_platform.api.main:app --reload   # http://localhost:8000/docs

# real workers (otherwise set GR_CELERY_EAGER=true to run inline)
celery -A geoready_platform.workers.celery_app worker --loglevel=info
```

Or the full stack (Postgres + Redis + API + worker):

```bash
cd platform && docker compose up
```

## Tests

```bash
pip install -e ".[platform-dev]"
cd platform && pytest
```

Tests run on a throwaway SQLite DB with Celery in eager mode and the engine
stubbed at the bridge boundary — **no network access**. The OSS engine test
suite under `../tests` is untouched and runs independently.

## Phase 0 endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET`  | `/healthz` | liveness + DB check |
| `POST` | `/v1/orgs` | create org; returns API key **once** |
| `POST` | `/v1/entities` | create entity |
| `GET`  | `/v1/entities` | list org entities |
| `GET`  | `/v1/entities/{id}` | get entity |
| `POST` | `/v1/entities/{id}/verify` | start ownership verification |
| `POST` | `/v1/entities/{id}/verify/confirm` | confirm ownership |
| `POST` | `/v1/entities/{id}/audits` | enqueue audit (verified only) |
| `GET`  | `/v1/audits/{job_id}` | poll audit status/result |
| `GET`  | `/v1/entities/{id}/signals` | list entity signals |
| `POST` | `/v1/entities/{id}/probes` | enqueue AI Perception Probe (**auth + quota; NO verification**) |
| `GET`  | `/v1/probes/{run_id}` | poll probe run (Share-of-Model, competitors, flags) |
| `GET`  | `/v1/probes/{run_id}/responses` | per-prompt responses with full provenance |
| `GET`  | `/v1/entities/{id}/probes` | probe history for an entity |

## Hard rules (do not violate)

- The engine (`../src/geo_optimizer`) is frozen; touch it only via `core_bridge`.
- No crawl/audit on an entity whose ownership is not verified.
- Every tenant query is scoped by `org_id` (app layer) and RLS (Postgres).
- Never log API keys or raw crawled HTML; only derived signals are persisted.
