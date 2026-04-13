# geo fix Command

`geo fix` audits a URL and generates all missing files in one shot: robots.txt patches, llms.txt, JSON-LD schemas, meta tag recommendations, AI discovery templates, and deterministic content rewrite guidance.

---

## Usage

```bash
# Preview what would be generated (dry-run, default)
geo fix --url https://yoursite.com

# Write fix files to disk
geo fix --url https://yoursite.com --apply

# Target only specific categories
geo fix --url https://yoursite.com --only robots,llms
geo fix --url https://yoursite.com --only schema,meta
geo fix --url https://yoursite.com --only content
```

---

## What It Generates

| Category | File | Description |
|----------|------|-------------|
| **robots** | `robots.txt` | Patch adding missing AI bot entries |
| **llms** | `llms.txt` | Structured AI index from sitemap |
| **schema** | `schema-*.json` | WebSite, Organization, FAQPage as needed |
| **meta** | `meta-tags.html` | Description, canonical, Open Graph snippets |
| **ai-discovery** | `ai/summary.json` | Site summary for AI systems |
| **ai-discovery** | `ai/faq.json` | Structured FAQ for AI |
| **content** | `content-rewrite.md` | Deterministic rewrite checklist for weak content signals |

---

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--url` | (required) | URL of the site to fix |
| `--apply` | `false` | Write files to disk (default is dry-run preview) |
| `--only` | all | Comma-separated categories: `robots,llms,schema,meta,ai_discovery,content` |
| `--output-dir` | `.` | Directory to write fix files |

---

## Example Output (Dry-Run)

```
🛠️ GEO Fix Plan — https://yoursite.com
Score before: 52/100

📄 robots.txt patch (append to existing):
   User-agent: GPTBot
   Allow: /
   User-agent: ClaudeBot
   Allow: /
   User-agent: PerplexityBot
   Allow: /

📄 llms.txt (new file):
   # Your Site Name
   > Brief description of your site
   ## Main Pages
   - [Home](https://yoursite.com): Main page
   - [Blog](https://yoursite.com/blog): Articles
   ...

📄 schema-website.json:
   {"@context": "https://schema.org", "@type": "WebSite", ...}

📄 meta-tags.html:
   <meta name="description" content="...">
   <link rel="canonical" href="...">

📄 ai/summary.json:
   {"name": "Your Site", "description": "...", "url": "..."}

📄 content-rewrite.md:
   # Content Rewrite Plan
   - Rewrite the opening 150 characters to answer the main question directly
   - Add 2-3 authoritative citations near factual claims
   - Split the page into H2/H3 sections with one takeaway each

Estimated score after fixes: 85/100 (+33 points)

Use --apply to write these files to disk.
```

---

## Using with MCP

The `geo_fix` MCP tool provides the same functionality:

```
"Fix my site's GEO issues" → calls geo_fix tool
```

Returns the complete fix plan as JSON, which AI assistants can then help you implement.

---

## Tips

- **Always preview first** — run without `--apply` to review what will be generated
- **Combine with audit** — run `geo audit` first to understand the full picture
- **Iterate** — fix one category at a time with `--only` if you prefer incremental changes
- **Version control** — commit existing files before running `--apply`
