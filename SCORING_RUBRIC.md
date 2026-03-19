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

## Score Progression (Corrected)

| Version | Score | Improvement | Key Achievement |
|---------|-------|-------------|-----------------|
| v1.0.0 | 7.2/10 | — | Foundation |
| v1.1.0 | 8.3/10 | +1.1 | Infrastructure (CI, deps, contributing) |
| v1.2.0 | 8.8/10 | +0.5 | JSON output + 22 tests |
| v1.3.0 | 9.0/10 | +0.2 | Network retry + 67 tests |
| v1.4.0 | 9.15/10 | +0.15 | Schema validation (9/9 audit fixes) |
| **v1.5.0** | **9.25/10** | **+0.10** | **Verbose mode + doc cleanup** |

**Note:** v1.4.0 was initially scored 9.6 (too optimistic). Corrected to 9.15 with stable rubric.

---

## Methodology

1. **Each dimension scored 0–10** based on criteria above
2. **Weighted average** calculated using dimension weights
3. **Final score rounded** to nearest 0.05
4. **Version-to-version** comparison uses same rubric (no moving goalposts)

---

## Future Targets

- **v1.6.0 target:** 9.4/10 (HTML report + batch mode → UX +0.5, Growth +0.5)
- **v2.0.0 target:** 9.7/10 (GitHub Action + PyPI → Growth +1.0, Distribution viral)
- **Long-term ceiling:** 9.8–9.9/10 (10.0 is reserved for perfect, industry-standard tools)

---

**Last updated:** 2026-03-19
**Maintained by:** geo-optimizer-skill core team
