# GEO Scoring Rubric

How the GEO Score (0–100) is computed. Based on the Princeton KDD 2024 research on Generative Engine Optimization, extended with AutoGEO ICLR 2026 and geo-checklist.dev signals.

---

## Score Bands

| Band | Range | Meaning |
|------|-------|---------|
| **Excellent** | 86–100 | Fully optimized for AI citation engines |
| **Good** | 68–85 | Well-optimized, minor gaps remain |
| **Foundation** | 36–67 | Partially visible — key signals missing |
| **Critical** | 0–35 | AI engines cannot reliably discover or cite you |

---

## Categories and Weights (v4.0.0)

The total score is the sum of all points earned across **8 categories**, capped at 100.

### 1. robots.txt — max 18 pts

| Signal | Points | Condition |
|--------|--------|-----------|
| `robots_found` | 5 | File exists and is reachable |
| `robots_citation_ok` | 13 | All 4 citation bots allowed (OAI-SearchBot, ClaudeBot, Claude-SearchBot, PerplexityBot) |
| `robots_some_allowed` | 10 | At least some AI bots allowed (partial credit — **not cumulative** with `citation_ok`) |

> **Citation bots** are the most critical: OAI-SearchBot, ClaudeBot, Claude-SearchBot, and PerplexityBot drive real-time citations in ChatGPT, Claude, and Perplexity. The `robots_some_allowed` score is awarded only when citation bots are not fully covered — it acts as partial credit for sites that allow some AI bots via wildcard rules.

### 2. llms.txt — max 18 pts

| Signal | Points | Condition |
|--------|--------|-----------|
| `llms_found` | 5 | `/llms.txt` exists at site root |
| `llms_h1` | 2 | File has a top-level H1 heading |
| `llms_blockquote` | 1 | File contains a blockquote (site description) |
| `llms_sections` | 2 | File has H2 content sections |
| `llms_links` | 2 | File contains at least one URL link |
| `llms_depth` | 2 | Word count ≥ 1,000 (substantial index) |
| `llms_depth_high` | 2 | Word count ≥ 5,000 (comprehensive index) |
| `llms_full` | 2 | `llms-full.txt` also exists at site root |

> Quality is graduated: a minimal llms.txt scores 5 pts, but a deep, well-structured file with a blockquote description and companion `llms-full.txt` can earn all 18.

### 3. Schema JSON-LD — max 16 pts effective (declared 22)

| Signal | Points | Condition |
|--------|--------|-----------|
| `schema_any_valid` | 2 | Any valid JSON-LD schema found in the page |
| `schema_richness` | 3 | Schema contains 5+ relevant attributes (Growth Marshal 2026) |
| `schema_faq` | 3 | `FAQPage` schema present |
| `schema_article` | 3 | `Article` or `BlogPosting` schema present |
| `schema_organization` | 3 | `Organization` schema present |
| `schema_website` | 2 | `WebSite` schema present |
| `schema_sameas` | 0 | *(migrated to `brand_kg_readiness` in v3.18.2 — retained for backwards compatibility, always 0)* |

> **Note:** The `sameAs` knowledge graph signal has been moved to the **Brand & Entity Signals** category as `brand_kg_readiness` (3 pts). The `schema_sameas` key is kept for compatibility but contributes 0 points. The effective maximum for this category is **16 pts**, not 22.

### 4. Meta Tags — max 14 pts

| Signal | Points | Condition |
|--------|--------|-----------|
| `meta_title` | 5 | `<title>` tag present and non-empty |
| `meta_description` | 2 | `<meta name="description">` present |
| `meta_canonical` | 3 | `<link rel="canonical">` present |
| `meta_og` | 4 | Open Graph tags present (`og:title`, `og:description`) |

### 5. Content Quality — max 12 pts

| Signal | Points | Condition |
|--------|--------|-----------|
| `content_h1` | 2 | Page has at least one `<h1>` heading |
| `content_numbers` | 1 | Page contains statistics (numbers, percentages) |
| `content_links` | 1 | Page contains external citation links |
| `content_word_count` | 2 | Page has ≥ 300 words of substantive content |
| `content_heading_hierarchy` | 2 | Has H2 + H3 headings in correct hierarchy |
| `content_lists_or_tables` | 2 | Contains `<ul>`, `<ol>`, or `<table>` elements |
| `content_front_loading` | 2 | Key information appears in the first 30% of the content |

> **Note:** The declared category maximum was 14 pts in v3.14, but the real sum of weights has always been 12 pts. The rubric now reflects the actual values from `config.py`.

### 6. Signals — max 6 pts

| Signal | Points | Condition |
|--------|--------|-----------|
| `signals_lang` | 3 | `<html lang="...">` attribute is set |
| `signals_rss` | 2 | RSS or Atom feed is discoverable |
| `signals_freshness` | 1 | `dateModified` in schema or `Last-Modified` HTTP header present |

> Reduced from 8 pts in v3.14. `signals_rss` reduced from 3 to 2, `signals_freshness` reduced from 2 to 1, reflecting their relatively lower impact on AI citability.

### 7. AI Discovery — max 6 pts

Based on the [geo-checklist.dev](https://geo-checklist.dev) emerging standard.

| Signal | Points | Condition |
|--------|--------|-----------|
| `ai_discovery_well_known` | 2 | `/.well-known/ai.txt` is present |
| `ai_discovery_summary` | 2 | `/ai/summary.json` is present and valid |
| `ai_discovery_faq` | 1 | `/ai/faq.json` is present |
| `ai_discovery_service` | 1 | `/ai/service.json` is present |

### 8. Brand & Entity Signals — max 10 pts *(new in v3.18.2)*

Rewards sites that establish a clear, machine-readable brand identity — a key factor in knowledge graph inclusion and AI attribution accuracy.

| Signal | Points | Condition |
|--------|--------|-----------|
| `brand_entity_coherence` | 3 | Brand name is consistent across title, schema, and OG tags |
| `brand_kg_readiness` | 3 | `sameAs` links to authoritative KG domains (Wikipedia, Wikidata, LinkedIn, etc.) |
| `brand_about_contact` | 2 | `/about` and `/contact` (or equivalents) are discoverable |
| `brand_geo_identity` | 1 | Geographic identity signal present (LocalBusiness schema or address) |
| `brand_topic_authority` | 1 | Consistent topical focus across headings, schema, and meta tags |

> Authoritative `sameAs` domains include: wikipedia.org, wikidata.org, linkedin.com, crunchbase.com, github.com, twitter.com / x.com, facebook.com.

---

## Total Points Reference

| Category | Max Points | Notes |
|----------|-----------|-------|
| robots.txt | 18 | |
| llms.txt | 18 | |
| Schema JSON-LD | 16 | 22 declared; `schema_sameas` migrated (0 pts) |
| Meta Tags | 14 | |
| Content Quality | 12 | 14 declared in v3.14; actual sum was always 12 |
| Signals | 6 | Reduced from 8 in v3.14 |
| AI Discovery | 6 | |
| Brand & Entity Signals | 10 | New in v3.18.2 |
| **Total** | **100** | |

---

## WebMCP Readiness *(v3.18.3, #233)*

**WebMCP Readiness** measures how well a site exposes machine-readable context for MCP-compatible AI agents. This signal does **not** contribute to the GEO score but is included in the audit report and JSON output as a standalone indicator.

| Level | Value | Meaning |
|-------|-------|---------|
| `none` | No MCP signals detected | Site has no machine-readable AI context endpoints |
| `basic` | Minimal signals present | `/.well-known/ai.txt` or `/ai/summary.json` found, but incomplete |
| `ready` | MCP-compatible | Full AI Discovery suite present and valid (`ai.txt` + `summary.json` + `faq.json`) |
| `advanced` | Full MCP + structured data | All AI Discovery endpoints present plus rich schema and llms.txt with depth |

> WebMCP Readiness is surfaced in the CLI output, HTML report, and JSON API. It helps site owners understand their exposure to next-generation AI agents that consume structured context (not just crawled content) before generating responses.

---

## Changelog

| Version | Change |
|---------|--------|
| v3.18.3 | WebMCP Readiness Check (#233): 4-level indicator (none/basic/ready/advanced), exposed in report but excluded from GEO score |
| v3.18.2 | Brand & Entity Signals category added (10 pts, 5 checks); `schema_sameas` migrated to `brand_kg_readiness` (Schema effective max 22→16); Content max corrected 14→12; Signals max reduced 8→6 |
| v3.18.0 | Rich formatter v2 (ASCII art, stacked dashboard), centralized URL validation across 4 endpoints |
| v3.17.x | Mass bugfix series: citability score accuracy, formatter max scores, security hardening (SSRF, XSS, rate limiting), `@graph` JSON-LD parser (Yoast/RankMath), CI fixes |
| v3.14 | 7 categories (added Signals + AI Discovery), `schema_richness` + `schema_sameas`, graduated llms.txt scoring, content structure checks, bands adjusted |
| v3.0.0 | 5 categories, `schema_website` 10 pts, `meta_description` 8 pts |
| v1.5.0 | Original weights |
