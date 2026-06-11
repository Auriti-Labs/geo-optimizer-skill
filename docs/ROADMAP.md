# Roadmap

> geo-optimizer-skill follows a deliberate release cadence. We ship in focused waves — each one validated, tested, and stable — rather than pushing frequent incremental patches. Quality over velocity.

## Current Direction

The project is entering its next phase of evolution. Focus areas for the upcoming cycle include:

- Deeper structural analysis of how content surfaces in AI-generated responses
- Expanded signal coverage across emerging retrieval and citation patterns
- Scoring model refinements informed by ongoing research validation
- Tighter integration between audit, remediation, and monitoring workflows
- Continued hardening of the skill system and plugin architecture

Some of these themes will span multiple releases. Specific scope may shift as research findings and community feedback inform priorities.

## Release Calendar

| Version | Window | Codename | Theme | Status |
|---------|--------|----------|-------|--------|
| v4.10.0 | Late May / Early Jun 2026 | **Veil** | Signal architecture refinement | Shipped |
| v4.11.0 | May 2026 (advanced from Jul 2026) | **Static** | Expanded retrieval surface analysis | Shipped — MVP A |
| v4.12.0 | May 2026 (advanced from Sep 2026) | **Ledger** | Scoring model recalibration | Shipped |
| v4.13.0 | Jun 2026 | **Echo** | AI citation visibility (`geo citations`) | Shipped |
| v4.14.0 | Jun 2026 (advanced from Nov 2026) | **Quiet Glass** | Structural pattern recognition (`geo authority`, `geo drift`, multimodal readiness) | Shipped |
| v4.15.0-rc1 | Jan 2027 | **Threshold** | Pre-release validation cycle | Planned |
| v4.15.0-rc2 / v4.16.0 | Mar 2027 | **Pale Signal** | Stabilization and edge resolution | Planned |
| v5.0.0 | May 2027 | **Black Archive** | Next-generation audit framework | Planned |

Release windows are estimates. Dates may shift based on validation outcomes and testing discipline. v4.11.0 and v4.12.0 both advanced ahead of their original windows because their scope was validated and stabilised earlier than planned. v4.13.0 (**Echo**) was inserted ahead of schedule to ship the one-shot AI citation check, and v4.14.0 (**Quiet Glass**) advanced from Nov 2026 once its structural-analysis scope (topic authority, drift, multimodal scaffolding) stabilised early. Later codenames keep their positions.

## Static Cycle — MVP Track

The **Static** codename groups four MVPs covering retrieval-surface visibility. Only MVP A is shipped; the remaining MVPs are sequenced across the v4.11–v4.14 cycle.

| MVP | Scope | Status |
|-----|-------|--------|
| **A — Crawler Evidence & Access Simulation** | AI Crawler Activity Analytics (`/api/logs/analyze`, `geo logs`) and Agent Access Audit (`geo access`, browser-vs-bot simulation) | Shipped in v4.11.0 |
| **B — Semantic Drift Monitoring** | Cross-snapshot drift detection over content and citation-readiness signals | Shipped — `geo drift` (CLI, one-shot) + continuous regression alerts in the GeoReady platform |
| **C — AI Perception Snapshot** | Enriched simulated-perception extraction from page signals | Planned |
| **D — WordPress Connector** | First-party connector for WordPress sites and headless setups | Planned |

MVP B–D scope and exact target releases will be confirmed as MVP A adoption signal and validation feedback come in.

## Release Philosophy

Each release is a curated wave, not a deadline. We hold releases until they meet our quality bar:

- Full test coverage for new capabilities
- No regressions in existing audit checks
- Security review for any new network-facing surface
- Documentation updated before the tag is cut

This means some windows may be quiet. That silence is intentional.

## What's Ahead

The v4.10–v4.13 cycle focuses on deepening the analytical foundation. New signal categories, refined scoring weights, and improved detection heuristics are under active research. Not all of this work will be visible in public commits — some validation happens offline before it reaches the codebase.

The v4.14 release candidates mark the transition toward v5.0, which represents a broader architectural evolution. More details will surface as the earlier releases stabilize.

## What This Roadmap Does Not Cover

- Internal module-level implementation plans
- Exact detector or check lists per release
- Configuration migration specifics
- Experimental features under active research

For the skill system roadmap (internal skill catalog evolution), see [docs/skill-roadmap.md](skill-roadmap.md).

---

*This roadmap reflects current planning as of April 2026. Items may evolve as research and validation continue.*
