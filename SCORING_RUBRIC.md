# Quality Scoring Rubric

This document defines the stable, public criteria used to score `geo-optimizer-skill` quality across versions.

**Purpose:** Provide transparency and consistency in version-to-version quality assessment.

---

## Scoring Dimensions

| Dimension | Weight | Criteria |
|-----------|--------|----------|
| **Idea & Positioning** | 15% | Uniqueness, market fit, problem-solution clarity, competitive differentiation |
| **Code Structure** | 20% | Architecture, modularity, maintainability, adherence to Python best practices |
| **Documentation** | 20% | README clarity, examples, AI context files, inline docs, changelog quality |
| **Robustness & Testing** | 25% | Test coverage, CI/CD, error handling, network resilience, edge case coverage |
| **UX & Usability** | 10% | CLI design, output clarity, debugging features, installation ease |
| **Growth Potential** | 10% | Roadmap clarity, community engagement, extensibility, viral distribution mechanisms |

**Total:** 100% (weighted average)

---

## Scoring Scale

- **9.0–10.0** — Exceptional (reference-quality, industry-leading)
- **8.0–8.9** — Excellent (production-ready, minor improvements possible)
- **7.0–7.9** — Good (functional, some gaps remain)
- **6.0–6.9** — Fair (usable but needs work)
- **< 6.0** — Needs improvement

---

## Version History

### v1.5.0 (2026-02-21)

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Idea & Positioning | 9.0/10 | GEO is a unique, well-defined problem. Princeton paper backing. No direct competitors. |
| Code Structure | 9.5/10 | Modular scripts, lazy imports, clean separation. Pythonic. |
| Documentation | 9.0/10 | (+0.5 from v1.4.0) README clear, `--verbose` implemented (no broken promises), AI context files comprehensive. |
| Robustness & Testing | 9.5/10 | 89 tests (87% business logic coverage), network retry, schema validation, CI/CD. |
| UX & Usability | 9.0/10 | (+0.5 from v1.4.0) CLI intuitive, JSON output, `--verbose` for debugging. |
| Growth Potential | 9.0/10 | Clear roadmap (HTML report, batch mode, GitHub Action, PyPI). Active development. |
| **Weighted Score** | **9.25/10** | Realistic score based on stable criteria. |

### v1.4.0 (2026-02-21)

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Idea & Positioning | 9.0/10 | Same as v1.5.0 |
| Code Structure | 9.5/10 | Same as v1.5.0 |
| Documentation | 8.5/10 | README had "coming soon" broken promise for `--verbose`. |
| Robustness & Testing | 9.5/10 | 89 tests, schema validation (9/9 audit fixes completed). |
| UX & Usability | 8.5/10 | `--verbose` mentioned but not implemented. |
| Growth Potential | 9.0/10 | Same as v1.5.0 |
| **Weighted Score** | **9.15/10** | Previous realistic score (9.6 was too optimistic). |

### v1.0.0 (2026-02-18) — Baseline

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Idea & Positioning | 9.0/10 | Strong foundation |
| Code Structure | 7.5/10 | Basic structure, lazy imports |
| Documentation | 7.0/10 | README + docs, but no tests documented |
| Robustness & Testing | 5.0/10 | Zero tests, no CI/CD |
| UX & Usability | 7.5/10 | CLI functional but basic |
| Growth Potential | 8.0/10 | Clear vision, no roadmap |
| **Weighted Score** | **7.2/10** | Foundation release |

---

## Score Progression

| Version | Score | Improvement | Key Achievement |
|---------|-------|-------------|-----------------|
| v1.0.0 | 7.2/10 | — | Foundation |
| v1.1.0 | 8.3/10 | +1.1 | Infrastructure (CI, deps, contributing) |
| v1.2.0 | 8.8/10 | +0.5 | JSON output + 22 tests |
| v1.3.0 | 9.0/10 | +0.2 | Network retry + 67 tests |
| v1.4.0 | 9.15/10 | +0.15 | Schema validation (9/9 audit fixes) |
| v1.5.0 | 9.25/10 | +0.10 | Verbose mode + doc cleanup |
| v2.0.0 | 9.4/10 | +0.15 | PyPI package, GitHub Action, HTML reports |
| v3.0.0 | 9.5/10 | +0.10 | 5 scoring categories, web demo, badge SVG |
| v3.14.x | 9.6/10 | +0.10 | 7→8 categories (Signals + AI Discovery), graduated llms.txt, content structure checks |
| v3.17.x | 9.65/10 | +0.05 | Security hardening (anti-SSRF, HSTS, rate limiting), @graph JSON-LD parser |
| v3.18.x | 9.7/10 | +0.05 | Brand & Entity category (10pt), MCP server (8 tools), rich formatter v2 |
| v3.19.x | 9.75/10 | +0.05 | Trust Stack Score (5-layer), Prompt Injection Detection, Negative Signals, 1007 tests |
| **v4.0.0-beta.1** | **9.8/10** | **+0.05** | **Architecture split (audit.py → 12 sub-modules), 27 AI bots, 1030 tests, IT→EN conversion** |

---

## Methodology

1. **Each dimension scored 0–10** based on criteria above
2. **Weighted average** calculated using dimension weights
3. **Final score rounded** to nearest 0.05
4. **Version-to-version** comparison uses same rubric (no moving goalposts)

---

## Current Status (v4.6.0)

- **1189 tests** (all mocked, zero network)
- **8 scoring categories**, 100 points total
- **27 AI bots** with 3-tier classification
- **47 citability methods** from Princeton KDD 2024 + AutoGEO ICLR 2026
- **7 output formats** (text, json, rich, html, sarif, junit, github)
- **MCP server** with 12 tools and 5 resources
- **Web demo** on Render, Docker images on GHCR + Docker Hub

## Future Targets

- **Long-term ceiling:** 9.9/10 (10.0 is reserved for perfect, industry-standard tools)

---

**Last updated:** 2026-04-01
**Maintained by:** geo-optimizer-skill core team
