# JSON Contract v1 — GEO Optimizer Web API

## Overview

The `POST /api/audit` and `GET /api/audit` endpoints return a stable JSON contract versioned via `schema_version`.

**Current version:** `1`

Consumers must handle `schema_version` being absent (pre-v1 responses) by treating it as `0`.

## Top-level keys

| Key | Type | Notes |
|-----|------|-------|
| `schema_version` | `int` | `1` — added in v4.11 |
| `url` | `string` | Audited URL |
| `timestamp` | `string` | ISO 8601 UTC |
| `score` | `int` | 0–100 |
| `score_version` | `int` | Scoring rubric version; `2` by default, `1` for legacy audits |
| `score_max` | `object` | Per-category maxima for the selected score version |
| `band` | `string` | `critical` \| `foundation` \| `good` \| `excellent` |
| `score_breakdown` | `object` | Per-category scores (see below) |
| `recommendations` | `array` | Ordered improvement suggestions |
| `recommendations_by_category` | `object` | Same strings as `recommendations`, grouped by category (additive, see below) |
| `http_status` | `int \| null` | HTTP status of the audited URL |
| `page_size` | `int` | Response body size in bytes |
| `error` | `string \| null` | Error message if audit failed |
| `robots` | `object` | `RobotsResult` serialized |
| `llms` | `object` | `LlmsTxtResult` serialized |
| `schema` | `object` | `SchemaResult` serialized |
| `meta` | `object` | `MetaResult` serialized |
| `content` | `object` | `ContentResult` serialized |
| `signals` | `object` | `SignalsResult` serialized |
| `ai_discovery` | `object` | `AiDiscoveryResult` serialized |
| `brand_entity` | `object` | `BrandEntityResult` serialized |
| `google_ai` | `object` | Google AI readiness result with G-* checks |
| `checks` | `object` | Flat + nested alias map (see below) |

## `score_breakdown` keys

Always present with 9 categories in v2 (value `0` if audit not run):

| Key | Max score |
|-----|-----------|
| `google_ai` | 20 |
| `robots` | 14 |
| `schema` | 14 |
| `content` | 14 |
| `brand_entity` | 12 |
| `meta` | 11 |
| `llms` | 6 |
| `signals` | 6 |
| `ai_discovery` | 3 |

The `google_ai` object contains `points`, `max_points`, and `checks`. Each check has `id`, `status` (`pass`, `warn`, `fail`, or `manual`), `points`, `max_points`, `evidence`, `source_url`, and `evidence_level`.

## `recommendations_by_category`

Additive field under the same `schema_version` (`1`). It carries the strings of `recommendations`, grouped by the category that produced them, so a consumer does not have to infer the category from the wording.

`geo audit --format json` emits the same field with the same semantics.

```json
{
  "recommendations": ["Create robots.txt with Allow rules for AI bots (...)", "Add a <title> tag (...)", "..."],
  "recommendations_by_category": {
    "robots": ["Create robots.txt with Allow rules for AI bots (...)"],
    "meta": ["Add a <title> tag (...)"],
    "other": ["..."]
  }
}
```

Rules:

1. Keys are the `score_breakdown` keys of the result's rubric (`score_max` lists them: nine in rubric v2, eight without `google_ai` in v1), plus two non-scored keys, `blockers` and `other`. Only keys with at least one recommendation are present.
2. Every string of `recommendations` appears in exactly one list. Taken together as a multiset, the lists equal `recommendations`.
3. Inside each list the order is the order of `recommendations`. The flat list itself is unchanged.
4. A critical or high-priority recommendation is filed under the category that produced it, not under a priority bucket.
5. An empty object with a non-empty `recommendations` means the category is unknown (a result restored from a cache written before this field existed). Treat such strings as uncategorised.

Mapping:

| Key | Recommendations |
|-----|-----------------|
| `google_ai` | Failing or warning `[G-*]` checks (rubric v2 only) |
| `robots` | Create or update robots.txt, aggressive `Crawl-delay` |
| `llms` | Create `/llms.txt`, sections, links and validation warnings of an existing file |
| `meta` | `<title>`, canonical, Open Graph, meta description, plus the two critical page-level blocks: `X-Robots-Tag: noindex` and the `noai` meta robots directive |
| `schema` | JSON-LD parse errors, missing WebSite, Organization, FAQPage, incomplete types, incomplete Product |
| `content` | H1, word count, heading hierarchy, front-loading, numbers, external links |
| `brand_entity` | Brand name consistency, `sameAs` links, about link, contact info |
| `signals` | `lang` attribute, RSS/Atom feed |
| `ai_discovery` | `/.well-known/ai.txt`, `/ai/summary.json`, `/ai/faq.json`, `/ai/service.json` |
| `blockers` | Not scored. Issues that keep AI crawlers from reading or trusting the page: the CDN/WAF "blocks AI crawlers" warning, the "Content requires JavaScript to render" warning, the critical prompt-injection items (LLM instructions, HTML comment injection, hidden text) and the critical variant of the user-generated-content injection surface |
| `other` | Not scored. The non-critical user-generated-content advisory, negative signals, WebMCP, multimodal, and the message of an error result |

Error results from `geo audit` and the web API (`error` is set because the site was unreachable or answered with an HTTP status other than 200/203) have a single recommendation, and `recommendations_by_category` is `{"other": [<that recommendation>]}`, because no category was audited. Results that `core/batch_audit.py` builds for a per-URL timeout or an unexpected exception have both `recommendations` and `recommendations_by_category` empty.

## `checks` structure

The `checks` object contains both nested sub-dicts and flat alias keys.

### Nested sub-dicts

| Key | Sub-fields |
|-----|-----------|
| `robots_txt` | `found`, `citation_bots_ok`, `citation_bots_explicit`, `bots_allowed`, `bots_blocked`, `bots_missing`, `bots_partial` |
| `llms_txt` | `found`, `has_h1`, `has_description`, `has_sections`, `has_links`, `has_full`, `word_count` |
| `schema_jsonld` | `found_types`, `has_website`, `has_faq`, `has_webapp`, `has_article`, `has_organization`, `has_sameas`, `any_schema_found`, `schema_richness_score`, `raw_schemas` |
| `meta_tags` | `has_title`, `has_description`, `has_canonical`, `has_og_title`, `has_og_description`, `has_og_image`, `title_text`, `description_text`, `description_length`, `title_length`, `canonical_url` |
| `content` | `has_h1`, `heading_count`, `has_numbers`, `has_links`, `word_count`, `h1_text`, `numbers_count`, `external_links_count`, `has_heading_hierarchy`, `has_lists_or_tables`, `has_front_loading` |
| `signals` | `has_lang`, `has_rss`, `has_freshness` |
| `ai_discovery` | `has_well_known_ai`, `has_summary`, `has_faq`, `endpoints_found` |
| `brand_entity` | `brand_name_consistent`, `kg_pillar_count` |

### Flat alias keys

Added in v1 for platform consumers (analytics dashboard, gate service):

| Alias key | Source field | Type |
|-----------|-------------|------|
| `robots_citation_ok` | `robots.citation_bots_ok` | `bool` |
| `llms_found` | `llms.found` | `bool` |
| `llms_full` | `llms.has_full` | `bool` |

## Backward compatibility rules

1. New top-level keys are always optional (consumers use `.get(key, default)`)
2. `schema_version` missing → treat as version `0`
3. `checks` alias keys absent → treat as `False`
4. `score_breakdown` keys absent → treat as `0`
5. The `checks` nested sub-dict structure is stable within a major version

## Frozen fixture

`tests/fixtures/audit_result_v1.json` freezes the required keys for regression testing. Do not modify without bumping `_contract_version`.

## Platform consumers

- **analytics_dashboard** — reads `checks.robots_citation_ok`, `checks.llms_found`, `checks.llms_full` for percentage metrics
- **gate_service** — reads `checks` sub-keys via `CATEGORY_KEY_MAP` to filter locked categories
- **geoready-platform** — reads all top-level keys via `json.loads(result_json).get(key, default)`
