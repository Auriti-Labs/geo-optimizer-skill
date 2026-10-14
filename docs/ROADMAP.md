# Roadmap

> geo-optimizer-skill follows a deliberate release cadence. We ship in focused waves, each one validated, tested, and stable, rather than pushing frequent incremental patches. Quality over velocity.

## Current Direction

The v4.10 to v4.19 cycle is complete. These focus areas carry over to the next cycle:

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
| v4.11.0 | May 2026 (advanced from Jul 2026) | **Static** | Expanded retrieval surface analysis | Shipped: MVP A |
| v4.12.0 | May 2026 (advanced from Sep 2026) | **Ledger** | Scoring model recalibration | Shipped |
| v4.13.0 | Jun 2026 | **Echo** | AI citation visibility (`geo citations`) | Shipped |
| v4.14.0 | Jun 2026 (advanced from Nov 2026) | **Quiet Glass** | Structural pattern recognition (`geo authority`, `geo drift`, multimodal readiness) | Shipped |
| v4.15.0 | Jul 2026 | **Aperture** | AI Perception Snapshot (`geo perception`, MVP C) | Shipped |
| v4.16.0 | Aug 2026 | **Ground Truth** | Bot-roster and access-layer correctness pass | Shipped |
| v4.17.0 | Aug 2026 (advanced from Jan 2027) | **Parallax** | MiniMax/multimodal LLM support, User-Agent override, WebMCP declared-tools credit, JSON-LD parser consolidation | Shipped |
| v4.17.1 | Aug 2026 | n/a (patch) | `geo llms --check-drift`, HowTo/Review/Product schema templates, structured-author E-E-A-T credit, case-insensitive URL normalization, brand-entity extraction fix, leftover-Italian-string cleanup | Shipped |
| v4.18.0 | Sep 2026 | **Quorum** | `geo citations --runs` multi-sample confidence intervals, UGC injection-surface detection, CJK-aware word counts, brand-last entity-disambiguation fix | Shipped |
| v4.18.1 | Sep 2026 | n/a (patch) | Three community-contributed fixes (LocalBusiness/Organization schema subtypes, single-page About-link anchors, third-party form-embed credit), an en-dash title-separator bug fix (#550), and an optional Google SERP + AI Overview citation source via serpbase.dev (#527) | Shipped |
| v4.18.2 | Sep 2026 | n/a (patch) | Security fix: SSRF-via-redirect in sitemap fetching (both functions now revalidate every redirect hop instead of following `requests`' default redirect handling), DNS re-pinning on the async redirect path, raised dependency floors against known CVEs | Shipped |
| v4.18.3 | Sep 2026 | n/a (patch) | CDN/WAF blocking detection for `/llms.txt` (403/406 → `blocked_by_cdn` instead of a false "No llms.txt found"), a browser-like retry wired into the main audit flow to recover a blocked file, a guard against WAF HTML-fallback false positives, and no more empty `llms.txt` written by `geo fix --apply` | Shipped |
| v4.19.0 | Oct 2026 | n/a (minor) | Versioned rubric v2 with a Google AI readiness category (20 pts: G-INDEX, G-SNIPPET, G-CANONICAL, G-DATES, G-BYLINE, G-LINKS, G-VIEWPORT, G-SITEMAP, G-GENAI-CONTROL), `--score-version 1` for legacy comparisons, re-weighted categories (llms.txt 18→6, ai_discovery 6→3), and cross-rubric history/drift/diff comparisons gated to the same score version | Shipped |
| v4.19.1 | Oct 2026 | n/a (patch) | Security hardening of both HTTP paths (DNS pinning on the async client, response size limits enforced while streaming, bounded retries), Organization-subtype and `@id`-author credit in Brand & Entity and G-BYLINE, resilience to malformed JSON-LD, CDN-blocked `llms.txt` detection on the sync path, a 60 s per-URL deadline for batch/sitemap audits, a web report that no longer shows false failures on gated payloads, an optional `score_penalty` field in the web API JSON, and `mcp` pinned below 2.0 | Shipped |
| v4.19.2 | Oct 2026 | n/a (patch) | `recommendations_by_category` in the JSON output (web API and `geo audit --format json`): each recommendation tagged with the scored category that produced it, plus `blockers` (CDN/WAF block, JavaScript-only content, critical injection) and `other`; the flat `recommendations` list is unchanged | Shipped |
| v5.0.0 | May 2027 | **Black Archive** | Next-generation audit framework | Planned |

Release windows are estimates. Dates may shift based on validation outcomes and testing discipline. v4.11.0 and v4.12.0 both advanced ahead of their original windows because their scope was validated and stabilised earlier than planned. v4.13.0 (**Echo**) was inserted ahead of schedule to ship the one-shot AI citation check, and v4.14.0 (**Quiet Glass**) advanced from Nov 2026 once its structural-analysis scope (topic authority, drift, multimodal scaffolding) stabilised early. v4.15.0 (**Aperture**) was inserted ahead of schedule to ship MVP C once the deterministic perception-extraction core (built alongside `geo drift`/`geo access`) stabilised. v4.16.0 (**Ground Truth**) was inserted the same way: an audit against current vendor crawler docs and the manual's own access-layer checklist found the bot roster and `geo access`/`geo authority` had drifted from both, and the fix was small and self-contained enough to ship immediately. v4.17.0 (**Parallax**) then advanced a full validation cycle ahead of its originally planned Jan 2027 window: its own dogfooding sweep (this project audited against its own production site and infrastructure) surfaced a coherent batch of fixes and additions that met the quality bar together, the same pattern that has now pulled every minor release since v4.11.0 forward. Planned codenames for a release window are provisional until that release actually ships: this table has been wrong about a codename before (an earlier revision named this window **Threshold**); trust the "Shipped" rows, not the "Planned" ones.

## Static Cycle, MVP Track

The **Static** codename groups four MVPs covering retrieval-surface visibility. MVPs A–C are shipped; only MVP D remains.

| MVP | Scope | Status |
|-----|-------|--------|
| **MVP A: Crawler Evidence & Access Simulation** | AI Crawler Activity Analytics (`/api/logs/analyze`, `geo logs`) and Agent Access Audit (`geo access`, browser-vs-bot simulation) | Shipped in v4.11.0 |
| **MVP B: Semantic Drift Monitoring** | Cross-snapshot drift detection over content and citation-readiness signals | Shipped: `geo drift` (CLI, one-shot) + continuous regression alerts in the GeoReady platform |
| **MVP C: AI Perception Snapshot** | Deterministic simulated-perception extraction from page signals | Shipped: `geo perception` (CLI, one-shot, deterministic) |
| **MVP D: WordPress Connector** | First-party connector for WordPress sites and headless setups | In progress: open-source plugin v0.1.1 on GitHub (not yet on WordPress.org) |

The [GeoReady WordPress plugin](https://github.com/Auriti-Labs/wordpress-geoready) (v0.1.1) generates `llms.txt`, `/.well-known/ai.txt`, and `/ai/summary.json` from published content, with sitemap detection for WordPress core, Yoast SEO, Rank Math, SEOPress, and All in One SEO, and runs a one-click AI readiness audit of the home page. It is not yet listed on WordPress.org.

In progress: moving the audit to the GeoReady platform, with an opt-in setting (off by default) to contribute pseudonymised results (salted domain hash and scores) to the benchmark dataset. WordPress results are internal-only for now.

Planned for the plugin: WordPress.org submission, headless WordPress support via the REST API, caching, JSON-LD schema output, and a Gutenberg editor panel. A dashboard widget is planned for later and is not built. Scope and exact target releases are not fixed.

## Release Philosophy

Each release is a curated wave, not a deadline. We hold releases until they meet our quality bar:

- Full test coverage for new capabilities
- No regressions in existing audit checks
- Security review for any new network-facing surface
- Documentation updated before the tag is cut

This means some windows may be quiet. That silence is intentional.

## What's Ahead

The v4.10 to v4.19 cycle is shipped. Two items remain on the calendar:

- **MVP D, WordPress Connector:** the open-source plugin (v0.1.1) exists on GitHub; platform-side audit and benchmark opt-in are in progress, and WordPress.org submission and headless support are planned. Target releases are not fixed yet.
- **v5.0.0, Black Archive:** the next-generation audit framework, planned for May 2027.

Rubric v2 (v4.19.0) is the default scoring model.

## What This Roadmap Does Not Cover

- Internal module-level implementation plans
- Exact detector or check lists per release
- Configuration migration specifics
- Experimental features under active research

For the skill system roadmap (internal skill catalog evolution), see [docs/skill-roadmap.md](skill-roadmap.md).

---

*This roadmap reflects current planning as of October 2026. Items may evolve as research and validation continue.*
