# Agent Team Usage Guide
## GeoReady / GEO Optimizer

---

## 1. Agent inventory

| Agent | Role | Writes code? | Worktree isolation | Use before impl? | Use after impl? |
|---|---|---|---|---|---|
| `geoready-orchestrator` | Coordination lead | No | No | Yes (required) | Yes (synthesis) |
| `geo-engine-architect` | Engine/CLI/JSON | Yes | Yes | Yes (design) | Yes (review) |
| `geoready-platform-api` | Backend/API/DB | Yes | Yes | Yes (design) | Yes (review) |
| `geoready-dashboard-ui` | Dashboard/frontend | Yes | Yes | Yes (design) | Yes (review) |
| `geo-qa-verifier` | QA/testing | No* | No | No | Yes (required) |
| `geo-security-privacy-reviewer` | Security/privacy | No | No | Yes | Yes |
| `geo-product-docs-release` | Docs/copy/release | Yes | Yes | No | Yes |
| `geo-roadmap-release-manager` | Versioning/release | No | No | Yes (planning) | Yes (release gate) |
| `geo-wordpress-connector-architect` | WP connector arch | Yes | Yes | Yes (spec only) | Yes (review) |

*`geo-qa-verifier` may apply minimal fixes only if explicitly instructed and fix is directly tied to a QA finding.

---

## 2. Read-only reviewers

These agents should not modify product code:
- `geoready-orchestrator`
- `geo-qa-verifier`
- `geo-security-privacy-reviewer`
- `geo-roadmap-release-manager`

---

## 3. Code-writing implementation agents

These agents may edit/write code (use worktree isolation):
- `geo-engine-architect` — `geo-optimizer-skill/`
- `geoready-platform-api` — `geoready-platform/backend/`
- `geoready-dashboard-ui` — `geoready-platform/frontend/`
- `geo-product-docs-release` — README, CHANGELOG, docs/, copy
- `geo-wordpress-connector-architect` — plugin skeleton (only if approved)

---

## 4. Agents that should run before implementation

1. `geoready-orchestrator` — always first; produces plan and agent assignments
2. `geo-roadmap-release-manager` — confirm SemVer impact and release scope
3. `geo-security-privacy-reviewer` — identify security requirements before building
4. `geo-engine-architect` — design engine API/contract before platform builds against it

---

## 5. Agents that should run after implementation

1. `geo-qa-verifier` — required after every feature implementation
2. `geo-security-privacy-reviewer` — required for any change touching URLs, uploads, auth, or LLM data
3. `geo-product-docs-release` — required before any public release
4. `geo-roadmap-release-manager` — required before any version bump or tag

---

## 6. How to use as a Claude Code agent team

**Required environment variable:**
```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

**Maximum recommended team size:** 5 teammates per session to avoid context fragmentation.

**Example full-feature team instruction:**
```
Create an agent team with:
- geoready-orchestrator as lead
- geo-engine-architect for engine scope
- geoready-platform-api for backend/API
- geoready-dashboard-ui for dashboard
- geo-qa-verifier for validation
Require plan approval from geoready-orchestrator before any teammate edits files.
Do not push, merge, or tag without explicit user approval.
```

**Example release hygiene team:**
```
Create an agent team with:
- geo-roadmap-release-manager as lead
- geo-product-docs-release for README/changelog/docs
- geo-qa-verifier for final test verification
Scope: MVP A release hygiene only — no new feature code.
```

**Example security review team:**
```
Create an agent team with:
- geo-security-privacy-reviewer as lead
- geo-qa-verifier for test verification
Scope: review all MVP A changes for SSRF, privacy, and ownership isolation.
Read-only investigation only — propose fixes but do not apply without approval.
```

---

## 7. Conflict prevention rules

- **One owner per file cluster:** assign each file/directory to exactly one agent per session.
- **No parallel same-file edits:** two agents must never edit the same file simultaneously.
- **Plan approval gate:** `geoready-orchestrator` must approve the task plan before any implementation agent edits files.
- **Engine contract first:** `geo-engine-architect` must define/confirm new dataclass/JSON contract before `geoready-platform-api` builds against it.
- **Backend API contract first:** `geoready-platform-api` must confirm endpoint schema before `geoready-dashboard-ui` wires frontend.

---

## 8. Push / merge / release restrictions

These rules apply to ALL agents, NO EXCEPTIONS:

- **No push** without explicit user approval.
- **No merge** without explicit user approval.
- **No tag** without explicit user approval.
- **No release / publish to PyPI** without explicit user approval.
- **No deploy to production** without explicit user approval.

Agents may commit locally if instructed; they must not push automatically.

---

## 9. Product boundary rules (all agents must respect)

- **GEO Optimizer** = open-source engine, CLI, audit core, JSON contract, foundation.
- **GeoReady** = hosted SaaS platform, dashboard, billing, team workflows.
- **geoready.dev** = public marketing/documentation surface.
- Never move SaaS billing logic into the open-source engine.
- Never make the open-source package depend on the hosted platform.
- Never blur open-source and SaaS boundaries in copy or code.

---

## 10. Claim-safety rules (all agents must respect)

- Access logs prove crawler/user-agent activity — **not real AI answer citations**.
- Real citation tracking requires archived AI answer snapshots.
- `PerceptionSnapshot` is simulated/deterministic extraction — **not a real AI system output**.
- `SemanticDriftDelta` tracks structural/signal changes — **not changes in AI system outputs**.
- Use these terms accurately: "crawler activity", "agent access", "machine-readable readiness", "simulated perception", "citation readiness".
- Never say "ChatGPT cited this site" without actual answer snapshot evidence.
