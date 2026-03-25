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

## Categories and Weights (v3.14)

The total score is the sum of all points earned across **7 categories**, capped at 100.

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
| `llms_found` | 6 | `/llms.txt` exists at site root |
| `llms_h1` | 2 | File has a top-level H1 heading |
| `llms_sections` | 2 | File has H2 content sections |
| `llms_links` | 2 | File contains at least one URL link |
| `llms_depth` | 2 | Word count ≥ 1,000 (substantial index) |
| `llms_depth_high` | 2 | Word count ≥ 5,000 (comprehensive index) |
| `llms_full` | 2 | `llms-full.txt` also exists at site root |

> Quality is now graduated: a minimal llms.txt scores 6 pts, but a deep, well-structured file with a companion `llms-full.txt` can earn all 18.

### 3. Schema JSON-LD — max 22 pts

| Signal | Points | Condition |
|--------|--------|-----------|
| `schema_any_valid` | 2 | Any valid JSON-LD schema found in the page |
| `schema_richness` | 3 | Schema contains 5+ relevant attributes (Growth Marshal 2026) |
| `schema_faq` | 5 | `FAQPage` schema present |
| `schema_article` | 3 | `Article` or `BlogPosting` schema present |
| `schema_organization` | 3 | `Organization` schema present |
| `schema_website` | 3 | `WebSite` schema present |
| `schema_sameas` | 3 | `sameAs` links to authoritative domains (Wikipedia, Wikidata, LinkedIn, etc.) |

> The `schema_sameas` signal rewards knowledge graph connections. Authoritative domains: wikipedia.org, wikidata.org, linkedin.com, crunchbase.com, github.com, twitter.com/x.com, facebook.com.

### 4. Meta Tags — max 14 pts

| Signal | Points | Condition |
|--------|--------|-----------|
| `meta_title` | 5 | `<title>` tag present and non-empty |
| `meta_description` | 2 | `<meta name="description">` present |
| `meta_canonical` | 3 | `<link rel="canonical">` present |
| `meta_og` | 4 | Open Graph tags present (`og:title`, `og:description`) |

### 5. Content Quality — max 14 pts

| Signal | Points | Condition |
|--------|--------|-----------|
| `content_h1` | 2 | Page has at least one `<h1>` heading |
| `content_numbers` | 2 | Page contains statistics (numbers, percentages) |
| `content_links` | 2 | Page contains external citation links |
| `content_word_count` | 2 | Page has ≥ 300 words of substantive content |
| `content_heading_hierarchy` | 2 | Has H2 + H3 headings in correct hierarchy |
| `content_lists_or_tables` | 2 | Contains `<ul>`, `<ol>`, or `<table>` elements |
| `content_front_loading` | 2 | Key information appears in the first 30% of the content |

### 6. Signals — max 8 pts (new)

| Signal | Points | Condition |
|--------|--------|-----------|
| `signals_lang` | 3 | `<html lang="...">` attribute is set |
| `signals_rss` | 3 | RSS or Atom feed is discoverable |
| `signals_freshness` | 2 | `dateModified` in schema or `Last-Modified` HTTP header present |

### 7. AI Discovery — max 6 pts (new)

Based on the [geo-checklist.dev](https://geo-checklist.dev) emerging standard.

| Signal | Points | Condition |
|--------|--------|-----------|
| `ai_discovery_well_known` | 2 | `/.well-known/ai.txt` is present |
| `ai_discovery_summary` | 2 | `/ai/summary.json` is present and valid |
| `ai_discovery_faq` | 1 | `/ai/faq.json` is present |
| `ai_discovery_service` | 1 | `/ai/service.json` is present |

---

## Total Points Reference

| Category | Max Points |
|----------|-----------|
| robots.txt | 18 |
| llms.txt | 18 |
| Schema JSON-LD | 22 |
| Meta Tags | 14 |
| Content Quality | 14 |
| Signals | 8 |
| AI Discovery | 6 |
| **Total** | **100** |

---

## Changelog

| Version | Change |
|---------|--------|
| v3.14 | 7 categories (added Signals + AI Discovery), `schema_richness` + `schema_sameas`, graduated llms.txt scoring, content structure checks, bands adjusted |
| v3.0.0 | 5 categories, `schema_website` 10 pts, `meta_description` 8 pts |
| v1.5.0 | Original weights |
