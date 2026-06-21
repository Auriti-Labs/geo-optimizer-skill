# Roadmap

> ⚠️ **Target-vision document.** This roadmap describes where the **AI Visibility Platform** is going, not what exists today. Many modules, services, data models, and integrations referenced below — the entity spine, perception probe, execution connectors, attribution loop — are **aspirational and not yet implemented**. The open-source audit engine (`geo` CLI, core modules, MCP, integrations) is real and shipped; treat everything in the platform sections as planned work pending the Phase 0 execution plan. When in doubt, the codebase is the source of truth for current state; this file is the source of truth for direction.

> This roadmap covers two surfaces: the **open-source engine** (`geo` CLI, MCP, integrations) and the **AI Visibility Platform** built on top of it. The open-source engine is the funnel and the credibility layer; the platform is the business. They ship on different cadences and are planned separately below.

---

## 1. What We Are Building

This is **not** a GEO dashboard, an SEO tool, or a scorecard.

This is an **AI Visibility / AI Recommendation Readiness Platform**. Its purpose is to help businesses become **accurately understood, trusted, cited, and recommended** by AI systems — ChatGPT, Claude, Gemini, Perplexity, and the models that follow.

**The score is not the product. The outcome is the product.** We measure and improve discoverability, recommendation likelihood, citation quality, factual accuracy, and trust — and we prove the business impact.

### The core operating loop

```
Audit → Explain → Fix → Implement → Verify → Monitor → Prove Business Impact
```

Two of these stages are where most competitors stop and where we must not: **Implement** (we do the work, not just recommend it) and **Prove Business Impact** (we connect the work to citations, traffic, and revenue). These are mandatory, not optional.

### The one-line strategy

Everyone can build a Score. Almost no one will build the robotic arm (execution) and the proof loop (attribution), and no one can backfill the historical dataset we start accumulating on day one. **We win on execution + proof + compounding data — not on audit depth.**

---

## 2. Non-Negotiable Principles

1. **Lead with perception, not the audit.** The first thing a user sees is *what AI actually says about their business*, never a 100-point score.
2. **Demote the single-site audit to a signal source.** The 47-method engine is a component that feeds the entity's perception picture — it is not the headline.
3. **Surface the few issues that move recommendation**, not all 47. Compute everything server-side; show what matters.
4. **Never claim we can make an AI rank or recommend a business.** We improve the *inputs* AI systems consume and we *measure* what changes. Claims are measured (citation lift) or clearly labeled correlational/attributed (traffic, revenue). Overclaiming causation forfeits the research-authority moat.
5. **Execution requires verified ownership.** No scheduled crawling or auto-fixing of a domain/profile the org has not proven it controls. This is both an abuse guard and a trust signal.
6. **Reuse the engine; do not rewrite it.** The platform wraps existing core modules as workers. Rewrites are the enemy of shipping.

---

## 3. The Wedge (How We Get In The Door)

Two entry points, both visceral, both fear/curiosity-driven, both sellable in a 5-minute demo:

- **AI Perception Probe** — show a business exactly what ChatGPT / Perplexity / Gemini say (and get wrong) when a real buyer asks for a recommendation. Free, public, alarming.
- **Hallucination & Misinformation Defense** — "AI is telling your customers something false about you" (wrong hours, "permanently closed," wrong price, a competitor's product attributed to you). Premium, urgent, high willingness to pay.

The buyer is the **agency first** — they onboard dozens of client entities, market the free Probe to win their own pitches, need a monthly deliverable, and create switching costs and data density. Agencies are the channel *and* the moat, not just a tier.

---

## 4. Platform Roadmap (Phased, Ruthless)

> Phases are sequenced by *value-to-defensibility*, not by feature count. Each phase must be independently demoable and saleable. Dates are directional; gates are firm.

### Phase 0 — Foundation & Entity Spine *(internal, no UI)*

**Goal:** Stand up the platform spine with the **business entity** — not the audit — as the core object.

- Entity-centric data model: `business_entity` is the root; `entity_signal`, `perception`, `intervention`, `impact` hang off it. Audits write *signals onto an entity*.
- Platform API (extend existing FastAPI `web/app.py`), auth (JWT + org-scoped API keys), Postgres, Redis + Celery worker pool.
- Wrap `run_full_audit_async()` as a signal-producing worker — **no engine rewrite**.
- Refactor `core/fixer.py` to emit **structured fix proposals** (no disk writes) — prerequisite for execution.
- Domain/profile ownership verification (DNS TXT / file) — gates execution, prevents competitor abuse.

**Exit gate:** Create an entity by URL → it accumulates website signals + a baseline. No dashboard yet.

### Phase 1 — The Wedge: Perception Probe + One Real Fix `[MVP]`

**Goal:** A non-technical user sees something alarming in 5 minutes, and we fix one thing automatically. This is the minimum viable *category-defining* product.

1. **AI Perception Probe** — buyer-intent prompt set generated from entity category + geo; multi-engine runner (Perplexity Sonar already integrated; add ChatGPT, Gemini). Capture: mentioned? recommended? what's said? accurate? competitors named? Every probe stored timestamped — **history accrues from day one.**
2. **Share-of-Model v1** — % of buyer-intent prompts where the entity is recommended vs. competitors.
3. **Hallucination detection v1** — flag factual conflicts between what AI says and the entity's verified truth (reuse `factual_accuracy.py`, `hallucination_bait.py`).
4. **Gap-linked diagnosis** — surface only the 3–5 issues plausibly driving the perception gap (reuse engine, suppress the other 42). AI explanation layer (Claude) ties each issue to a perception consequence.
5. **One-click auto-execution for ONE fix type** — llms.txt + schema/JSON-LD + robots.txt via **one connector** (WordPress plugin *or* JS snippet/edge proxy). Validation gate: every generated fix must pass its own check + parse-validity before being offered.
6. **Verify by re-probe** — approve once → implement → re-probe → show perception delta + alert.
7. **Minimal UI (Next.js)** — the home screen is the Probe result, not a gauge. Reuse `ScoreGauge`/`CategoryBreakdown` only to *explain the gap*.

**Exit gate (the demo test):** An agency adds a client by URL, sees "ChatGPT recommends 3 competitors and says you're closed," clicks once, we fix it, and re-probe shows movement. If the demo lands, scale. If you're showing a score, stop and re-frame.

### Phase 2 — Proof v1 + Verification Loop

**Goal:** Make improvement *measured*, not asserted. This is the first half of the proof moat.

- **Measured citation/recommendation lift** (Attribution Stage 1): baseline → re-probe → Share-of-Model and citation-frequency delta over time, across engines. This is measured, not modeled — the strongest honest claim.
- **Verification workflow** — before/after diff tied to specific interventions; explain when a fix didn't move the needle and why.
- **Continuous monitoring** — scheduled re-probes (daily/weekly/monthly) on verified entities; alerts on score drop, lost recommendation, new hallucination, bot blocked. *Every alert includes previous value, current value, what changed, and a one-click fix.*
- **Historical trend analysis** — perception + coherence over time. The retention hook.

**Exit gate:** A user can show "before: recommended in 1/20 prompts, 3 misinformation incidents; after: 8/20, 0 incidents" — measured, dated, repeatable.

### Phase 3 — Agency Workflows + Entity Coherence

**Goal:** Turn the wedge into a defensible recurring business via the agency channel and the hardest-to-copy diagnosis.

- **Multi-entity management, team roles, white-label reports, client portal** (read-only client view).
- **Proof-of-improvement report** as the monthly deliverable — shareable branded link (`/r/{slug}`), headlined by Share-of-Model trend and citation lift, *not* a score.
- **Cross-web entity coherence (v1, deliberately scoped)** — reconcile core attributes (name, address, phone, hours, category) across owned + authoritative sources (website, GBP, Wikidata, LinkedIn). Detect conflicts, link them to perception failures, rank by impact × fixability. **Resist premature graph complexity** — start with the handful of attributes that demonstrably drive recommendation; do not build a general knowledge-graph engine yet.
- **Competitor comparison** — Share-of-Model vs. named competitors for the same buyer prompts.
- **More connectors / execution surfaces** — GBP fields via API; additional CMS push paths.

**Exit gate:** 10–20 agencies running real client entities, with at least one auto-executed fix per entity and a monthly proof report. KPI: **# of entities under continuous monitoring with ≥1 executed fix** (the moat accruing), not raw MRR.

### Phase 4 — Proof v2: The Bridge to Revenue

**Goal:** Move proof from "AI cites you more" to "AI is sending you customers."

- **AI-referred traffic (Attribution Stage 2)** — detect AI-source visits (referrers, assistant user-agents, UTM); GA4 / Search Console connectors; correlate against intervention dates. Labeled correlational.
- **Benchmarking (network effect)** — with enough entities, tell any business its percentile for AI recommendation in its category/geo. Only possible with scale; impossible for a new entrant to match.
- **Deeper coherence** — distributed sources (reviews, directories) via official APIs/partners. *Integrate, don't rebuild Yext/BrightLocal.*
- **Public API v1 + webhooks** — agency integration surface; CLI becomes an API client.

### Phase 5 — Proof v3 + Enterprise

**Goal:** CFO-grade proof and the brand-risk buyer.

- **CRM & revenue attribution (Attribution Stage 3)** — call-tracking, form/booking, e-commerce; attribute AI-referred conversions to interventions. Always labeled attributed/estimated.
- **Multi-location / franchise coherence & hallucination defense** — board-level brand-risk product priced to the risk.
- **Custom rubrics, dedicated crawl workers, SLAs.** SSO *only when an enterprise contract requires it* — not before.

---

## 5. What We Will NOT Build (Initially)

Ruthless cuts. Each of these is a trap that turns a category-defining company into a feature-rich tool.

- **No dashboard-first thinking.** The Probe and execution are the product; charts come after.
- **No engine rewrite.** Wrap and reuse. The 47-method engine and 1,720 tests stay intact.
- **No enterprise SSO** until a paying enterprise contract demands it (Phase 5+).
- **No PDF report factory.** One shareable branded link in Phase 3; defer heavy PDF/format work.
- **No premature entity-graph complexity.** Phase 3 reconciles a handful of high-impact attributes across a few authoritative sources — not a general knowledge graph.
- **No new investment in OSS CLI features, the 7 output formats, or SARIF/JUnit.** OSS stays frozen as the free funnel.
- **No surfacing of all 47 methods in the UI.** Compute server-side; show the few that move recommendation.
- **No claim that we make AI rank or recommend a business.** Ever.
- **No scheduled crawling / auto-fixing of unverified domains.**
- **No building of a reviews/citations/directory product.** Integrate with the incumbents that already own it.

---

## 6. The Moat (How This Stays Defensible)

If Semrush, Ahrefs, or Moz ships an "AI Visibility Score" tomorrow, we still win — because the score was never the moat. Ranked by durability:

| Moat | Why it compounds / can't be copied |
|------|------------------------------------|
| **Execution automation** | Measurement companies won't aggressively auto-modify customer sites/profiles — it's off-strategy and a support burden for them. We own the robotic arm. |
| **Historical entity + perception dataset** | Starts accruing on day one for every entity, including free-tier. Incumbents structurally cannot backfill "how AI's opinion evolved over years." |
| **Proof-of-improvement (measured → attributed)** | The Stage 1→3 attribution loop makes ROI unarguable. Hard to build, deadly once built. |
| **Benchmarking / network effect** | Percentile-by-category requires scale; improves with every entity; impossible for a new entrant to match. |
| **Agency adoption & workflow lock-in** | White-label + client portals + history wired into agency delivery make switching organizational surgery. Agencies are distribution + data density. |
| **Recommendation / "Share of Model" tracking** | We define and popularize the category metric; when incumbents enter, they play on our field with our terminology. |
| **Research authority** | Keep publishing (KDD/ICLR-grade). Be the team that *defines* how AI visibility is measured. Incumbent entry validates the category instead of killing it. |

**Not a moat (stop treating these as crown jewels):** the score, the rubric, the UI, "AI-powered fixes" as a phrase. Everyone has Claude's API. Depth of audit loses to distribution.

---

## 7. Pricing Direction (Value, Not Features)

Anchored to the value of *one additional customer acquired through AI*, not to feature count.

- **Free public Probe** — the hook and demand-gen engine. CAC we eat on purpose.
- **Pro (~$99–199/mo)** — continuous monitoring, alerts, hallucination detection, auto-execution for one entity. Priced to signal "protects my revenue," not "another tool."
- **Agency (~$500–1,500/mo, tiered by client entities)** — the revenue engine. White-label, bulk execution, client portal, proof reports.
- **Enterprise / multi-location ($2k–10k+/mo)** — hallucination defense + coherence across many locations as brand-risk insurance.

Principle: the more we *do for them* and the more we *prove*, the further we move from per-seat SaaS toward outcome/managed-service economics — the fattest margins and the worst comparison surface for incumbents.

---

## 8. Open-Source Engine Track (The Funnel)

The OSS engine continues on its quality-over-velocity cadence, but receives **no new feature investment** beyond what keeps it credible and current:

- **Maintain:** the 27-bot database (new AI models launch monthly — staleness makes the audit wrong), security hardening, scoring accuracy.
- **Keep frozen as funnel:** CLI, MCP server, Astro integration, GitHub Action.
- The OSS tool's job is developer-led top-of-funnel and research credibility, not revenue.

(Prior CLI release calendar — Veil through Black Archive — is retained for continuity in the changelog; new energy goes to the platform.)

---

## 9. The Three Things That Decide Everything

1. **Ship execution before incumbents commoditize the score.** Speed on the *unglamorous* parts (execution, attribution) is the whole game.
2. **Start accumulating perception history now**, for every entity, free or paid. The dataset is the only moat that grows while you sleep.
3. **Win agencies, not businesses.** They are customer, channel, and data-density engine at once.

---

*This roadmap supersedes the prior CLI-centric direction. It reflects strategy as of June 2026. Phases are sequenced by defensibility; dates are directional and gates are firm. The score is not the product — the outcome is.*

---

## Appendix A — Phase 0 Execution Plan (Implementation Checklist)

> This is a build checklist, not strategy. It defines the exact folders, modules, services, data models, APIs, and infrastructure to stand up **before** any feature work, in dependency order. The governing constraint: **wrap and reuse the existing audit engine — do not rewrite it.** Phase 0 is "done" when an entity can be created by URL, its ownership verified, an audit run as a background job, and the results stored as signals on that entity — with zero UI.

### Guiding rules for Phase 0

- The existing Python package `src/geo_optimizer/` is **frozen** except for the two surgical refactors listed in Step 4. No changes to `core/audit*.py`, `core/scoring.py`, `models/results.py`, `utils/`, or `tests/`.
- Everything new lives under a **new top-level `platform/` tree**, isolated from the OSS package so the CLI/PyPI build stays clean.
- Reuse `utils/http.py`, `utils/validators.py`, `utils/robots_parser.py` as-is for all crawling — do not write new HTTP code.
- No feature work (probe, fixes, dashboard) until every box below is checked.

### Step 0 — Repo & environment scaffolding *(no app logic)*

- [ ] Create `platform/` top-level tree:
  ```
  platform/
    api/            # FastAPI app (the platform API; separate from src/.../web)
    workers/        # Celery tasks (audit/signal workers)
    db/             # SQLAlchemy models + Alembic migrations
    services/       # business logic (entities, ownership, audits-as-signals)
    schemas/        # Pydantic request/response models
    core_bridge/    # thin adapters that call src/geo_optimizer (no rewrite)
    tests/          # platform tests (separate from OSS tests/)
  ```
- [ ] Add `platform/` deps to a separate dependency group (`pyproject.toml` `[project.optional-dependencies] platform`) — do **not** pollute core install. Pins: FastAPI, Uvicorn, SQLAlchemy 2.x, Alembic, Pydantic v2, Celery, redis, psycopg, python-jose (JWT), httpx (already a dep).
- [ ] `docker-compose.yml` for local dev: Postgres 16, Redis 7, API, one Celery worker. Reuse existing `Dockerfile` patterns.
- [ ] `.env.example` for platform config (DB URL, Redis URL, JWT secret, AI provider keys — keys unused until later phases but slotted now).

### Step 1 — Database & the entity spine *(the foundation everything hangs off)*

- [ ] Alembic baseline migration. Tables, minimal but final-shaped:
  - `orgs (id, name, plan, created_at)`
  - `users (id, email, name, created_at)` + `org_members (org_id, user_id, role)`
  - `business_entity (id, org_id, canonical_name, category, geo, website_url, verified_at, created_at, archived_at)`
  - `entity_signal (id, entity_id, source, signal_type, value_jsonb, ai_reachable, fetched_at)` — the audit writes rows here
  - `audit_jobs (id, entity_id, org_id, status, triggered_by, score, score_breakdown_jsonb, full_result_jsonb, started_at, completed_at, error, created_at)`
  - **Stub-only (create empty, no logic yet):** `perception`, `intervention`, `impact` — shape them now to avoid future migrations, populate in later phases.
- [ ] Enforce `org_id` on every tenant table; add `(entity_id, created_at)` and `(org_id, status)` indexes on `audit_jobs`.
- [ ] Enable PostgreSQL **row-level security** scaffolding (policies keyed on `org_id`) — even if app-level checks come first, wire RLS now.

### Step 2 — Auth & tenancy *(gate before any endpoint does work)*

- [ ] JWT session auth + **org-scoped API keys** (store hashed; never retrievable). Choose managed (Supabase Auth) or self-hosted `python-jose` — pick one, document it, move on.
- [ ] Middleware that resolves `org_id` from token/key on every request and injects it into the DB session (drives RLS).
- [ ] Roles enum: `owner | admin | editor | viewer` (client/agency roles deferred to Phase 3).
- [ ] Per-key rate limiting (Redis token bucket) — Free tier quota enforced here.

### Step 3 — Domain ownership verification *(hard prerequisite for execution & monitoring)*

- [ ] `services/ownership.py`: issue a verification token per entity; verify via **DNS TXT record** or **/.well-known file**.
- [ ] `business_entity.verified_at` set only on success. **No background crawl or auto-fix may run on an unverified entity** — assert this in the worker, not just the UI.
- [ ] Reuse `utils/validators.py` for all URL/IP safety (anti-SSRF) — no new validation code.

### Step 4 — Two surgical engine refactors *(the ONLY changes to `src/geo_optimizer/`)*

- [ ] **Refactor `core/fixer.py`** to return structured `FixProposal` objects (content + instructions + target check) instead of writing files to disk. Preserve the existing file-writing path behind a flag so the CLI keeps working. Add tests in OSS `tests/`.
- [ ] **Make `core/scoring.py` purely re-scorable** if not already — `score(result) -> breakdown`, no side effects — so historical `full_result_jsonb` can be re-scored when the rubric changes. Likely a no-op verification; confirm and document.
- [ ] Everything else in `src/geo_optimizer/` stays untouched.

### Step 5 — Core bridge & audit-as-signal worker *(wrap, don't rewrite)*

- [ ] `core_bridge/audit_adapter.py`: thin async function that calls existing `run_full_audit_async(url)`, serializes `AuditResult` (from `models/results.py`) to JSON-safe dict, and maps category outputs → `entity_signal` rows.
- [ ] `workers/audit_task.py` (Celery): consume `{audit_job_id}`, set status `running`, call the adapter, write `audit_jobs.full_result_jsonb` + `score` + `score_breakdown_jsonb` + `entity_signal` rows, set status `complete`/`failed`. Enforce: ownership-verified, 60s hard timeout, bounded HTTP fetches (reuse engine limits).
- [ ] Redis as broker + result backend. One worker in compose; concurrency bounded (I/O-bound, ~10–20 async audits/worker).

### Step 6 — Platform API (minimal surface) *(no UI; verifiable via curl/tests)*

- [ ] `api/main.py` FastAPI app, mounted separately from `src/.../web/app.py`.
- [ ] Endpoints (Phase 0 scope only):
  ```
  POST   /v1/orgs                         create org
  POST   /v1/entities                     create entity (url, name, category, geo)
  POST   /v1/entities/{id}/verify         start/confirm ownership verification
  POST   /v1/entities/{id}/audits         enqueue audit  -> returns audit_job_id
  GET    /v1/audits/{job_id}              poll status + result
  GET    /v1/entities/{id}/signals        list signals for entity
  GET    /healthz                         liveness/readiness
  ```
- [ ] Pydantic schemas in `platform/schemas/`. OpenAPI auto-doc on.
- [ ] All endpoints org-scoped and ownership-aware; audit enqueue refuses unverified entities.

### Step 7 — Observability & safety floor *(non-negotiable before real users)*

- [ ] Structured logging (request id, org id, entity id) — never log API keys or raw crawled HTML.
- [ ] Sentry (or equivalent) on API + workers.
- [ ] Worker dead-letter handling: failed jobs land in `audit_jobs.error`, not silent loss.
- [ ] Basic CI for `platform/`: lint (ruff, reuse config) + `platform/tests/` on PR. Keep OSS CI untouched.
- [ ] Data hygiene: confirm no raw HTML persisted (only derived signals/results); deletion of an entity cascades to its signals + audit_jobs.

### Phase 0 Definition of Done (exit gate)

All true, verifiable without a UI:

1. `docker-compose up` brings up API + worker + Postgres + Redis.
2. Create org → create entity → verify ownership (DNS or file) → `verified_at` set.
3. `POST /v1/entities/{id}/audits` on a verified entity enqueues a job; the **existing engine** runs unchanged inside the worker.
4. Result is stored as `audit_jobs.full_result_jsonb` + score + `entity_signal` rows; `GET /v1/audits/{job_id}` returns it.
5. Unverified entity → audit enqueue is **refused**.
6. Tenant isolation holds: org A cannot read org B's entities/audits (RLS + app check).
7. OSS CLI, MCP, and `tests/` are **green and unchanged** (the freeze held).

### Explicitly OUT of Phase 0 (do not build yet)

- ❌ Any dashboard / Next.js UI — Phase 1.
- ❌ AI Perception Probe, Share-of-Model, hallucination detection — Phase 1.
- ❌ AI-generated fixes or one-click execution — Phase 1 (the `FixProposal` *shape* exists; the engine that fills it does not).
- ❌ `perception` / `intervention` / `impact` table logic — stub schema only.
- ❌ Monitoring scheduler, alerts, attribution, connectors, white-label, billing — later phases.

**The Phase 0 trap to avoid:** building anything a user can *see* before the entity spine + ownership + audit-as-signal worker are solid. Phase 0 produces no demo. That is correct. The demo is Phase 1, and it is only possible — and only safe — on top of a spine that already isolates tenants, verifies ownership, and reuses the engine without forking it.
