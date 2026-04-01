# MCP Server

GEO Optimizer exposes its core functionality as an [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server, making all tools available inside AI coding assistants like Claude Code, Cursor, and Windsurf.

---

## Installation

Install with the `mcp` extra:

```bash
pip install geo-optimizer-skill[mcp]
```

This installs the `geo-mcp` entry point alongside the `mcp` Python SDK.

---

## Setup

### Claude Code

```bash
claude mcp add geo-optimizer -- geo-mcp
```

That's it. The tools are immediately available in your Claude Code session.

### Cursor

Add to your `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "geo-optimizer": {
      "command": "geo-mcp",
      "args": []
    }
  }
}
```

### Windsurf / Generic MCP Client

Any MCP client that supports stdio transport can connect:

```bash
geo-mcp
```

The server runs on stdio transport by default. No port configuration needed.

### Direct Python Invocation

```bash
python -m geo_optimizer.mcp.server
```

---

## Tools (8)

### 1. `geo_audit`

Run a complete GEO audit on a website. Analyzes 7 areas: robots.txt, llms.txt, JSON-LD schema, SEO meta tags, content quality, signals, and AI discovery. Returns a score 0–100 with detailed breakdown and recommendations.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `url` | string | yes | URL of the site to audit |

**Example output (abbreviated):**

```json
{
  "url": "https://example.com",
  "score": 72,
  "band": "good",
  "score_breakdown": {
    "robots": 18,
    "llms": 6,
    "schema": 16,
    "meta": 14,
    "content": 10,
    "signals": 5,
    "ai_discovery": 3
  },
  "recommendations": [
    "Add llms-full.txt for comprehensive AI indexing",
    "Add FAQPage schema for better AI extraction"
  ]
}
```

### 2. `geo_fix`

Generate automatic GEO fixes for a website. Audits the site and produces corrective artifacts: robots.txt patches, llms.txt content, missing JSON-LD schemas, and HTML meta tag snippets.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `url` | string | yes | URL of the site to optimize |
| `only` | string | no | Filter categories (comma-separated): `robots`, `llms`, `schema`, `meta`. Empty = all |

**Example output (abbreviated):**

```json
{
  "fixes": [
    {
      "category": "robots",
      "description": "Create robots.txt with access for all 27 AI bots",
      "file_name": "robots.txt",
      "action": "create"
    },
    {
      "category": "llms",
      "description": "Generate llms.txt from sitemap (42 URLs)",
      "file_name": "llms.txt",
      "action": "create"
    }
  ],
  "score_before": 34,
  "score_estimated_after": 78
}
```

### 3. `geo_llms_generate`

Generate complete llms.txt content for a website. Discovers the sitemap, categorizes URLs by content type, and produces a structured markdown file following the [llmstxt.org](https://llmstxt.org) specification.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `url` | string | yes | Base URL of the site |

**Example output:**

```markdown
# Example Site

> A brief description of the site for AI search engines.

## Documentation

- [Getting Started](https://example.com/docs/getting-started)
- [API Reference](https://example.com/docs/api)

## Blog & Articles

- [How We Built X](https://example.com/blog/how-we-built-x)
```

### 4. `geo_citability`

Analyze content citability using the 11 GEO methods (Princeton KDD 2024 + AutoGEO ICLR 2026). Evaluates the page content and returns a citability score 0–100 with per-method breakdown.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `url` | string | yes | URL of the page to analyze |

**Example output (abbreviated):**

```json
{
  "url": "https://example.com/blog/post",
  "score": 65,
  "methods": {
    "quotation_addition": { "score": 8, "max": 10 },
    "statistics_addition": { "score": 10, "max": 12 },
    "fluency_optimization": { "score": 9, "max": 12 },
    "cite_sources": { "score": 6, "max": 10 },
    "answer_first": { "score": 7, "max": 10 },
    "passage_density": { "score": 5, "max": 10 }
  },
  "suggestions": [
    "Add 2-3 direct quotes from domain experts",
    "Add inline citations to authoritative sources"
  ]
}
```

### 5. `geo_schema_validate`

Validate a JSON-LD schema against schema.org requirements. Checks that all required fields are present for the given schema type.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `json_string` | string | yes | JSON-LD string to validate (max 512 KB) |
| `schema_type` | string | no | Schema type (e.g. `website`, `faqpage`). Auto-detected if empty |

**Example output:**

```json
{
  "valid": true,
  "error": null,
  "schema_type": "website"
}
```

### 6. `geo_compare`

Compare GEO scores across multiple websites (max 5). Returns a ranked comparison with score, band, and per-category breakdown.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `urls` | string | yes | Comma-separated URLs (e.g. `"site1.com, site2.com"`) |

**Example output:**

```json
{
  "comparison": [
    { "url": "https://site1.com", "score": 82, "band": "good" },
    { "url": "https://site2.com", "score": 45, "band": "foundation" }
  ],
  "total_sites": 2
}
```

### 7. `geo_ai_discovery`

Check AI discovery endpoints on a website. Verifies the presence of `/.well-known/ai.txt`, `/ai/summary.json`, `/ai/faq.json`, and `/ai/service.json` based on the [geo-checklist.dev](https://geo-checklist.dev) emerging standard.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `url` | string | yes | URL to check |

**Example output:**

```json
{
  "well_known_ai_txt": true,
  "ai_summary_json": true,
  "ai_faq_json": false,
  "ai_service_json": false,
  "score": 4,
  "max_score": 6
}
```

### 8. `geo_check_bots`

Check which AI bots can access a website via robots.txt. Returns per-bot status (allowed/blocked/missing) with 3-tier classification (training/search/user) and citation bot verification.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `url` | string | yes | URL to check |

**Example output (abbreviated):**

```json
{
  "url": "https://example.com",
  "robots_found": true,
  "citation_bots_ok": true,
  "bots": {
    "OAI-SearchBot": { "description": "OpenAI (ChatGPT search citations)", "status": "allowed", "tier": "search" },
    "ClaudeBot": { "description": "Anthropic (Claude citations)", "status": "allowed", "tier": "search" },
    "GPTBot": { "description": "OpenAI (ChatGPT training)", "status": "blocked", "tier": "training" }
  },
  "summary": { "allowed": 20, "blocked": 2, "missing": 2 }
}
```

---

## Resources (5)

MCP resources provide read-only reference data. Access them via the `geo://` URI scheme.

| URI | Description |
|-----|-------------|
| `geo://ai-bots` | List of all 24 tracked AI bots with 3-tier classification (training/search/user) and citation bot identification |
| `geo://score-bands` | GEO score band definitions (critical, foundation, good, excellent) with ranges |
| `geo://methods` | The 11 citability methods with measured impact data and max scores |
| `geo://changelog` | Latest changes from CHANGELOG.md (first 50 lines) |
| `geo://ai-discovery-spec` | AI discovery endpoint specification (geo-checklist.dev standard) with required fields and JSON schemas |

---

## Usage Examples

### Claude Code — Full Site Audit

```
> Use geo_audit to check https://mysite.com and tell me what to fix first.
```

Claude will call the `geo_audit` tool, parse the results, and give you prioritized recommendations in natural language.

### Claude Code — Generate and Validate Schema

```
> Generate a WebSite JSON-LD schema for mysite.com, then validate it with geo_schema_validate.
```

### Cursor — Compare Competitors

```
> Use geo_compare to compare mysite.com against competitor1.com and competitor2.com.
> Show me where I'm losing points.
```

### Fix Workflow

```
> Run geo_fix on https://mysite.com with only=robots,llms.
> Show me the generated files.
```

---

## Security

All URL inputs are validated against SSRF attacks before making any HTTP requests. Private IPs, localhost, and internal network addresses are rejected. HTTP response size is capped at 10 MB.
