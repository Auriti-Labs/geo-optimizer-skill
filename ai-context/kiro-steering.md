---
inclusion: fileMatch
fileMatchPattern:
  - "**/*.html"
  - "**/*.astro"
  - "**/*.tsx"
  - "**/*.jsx"
  - "**/*.php"
  - "**/robots.txt"
  - "**/llms.txt"
---

# GEO Optimizer

Make this site citable by AI search engines (ChatGPT, Perplexity, Claude, Gemini).

## robots.txt

Always include these user-agents with `Allow: /`:
- Citation bots (required): `OAI-SearchBot`, `PerplexityBot`, `ClaudeBot`, `Google-Extended`
- Also allow: `GPTBot`, `ChatGPT-User`, `anthropic-ai`, `claude-web`, `Googlebot`, `Bingbot`, `Applebot`, `Applebot-Extended`, `meta-externalagent`, `Bytespider`, `cohere-ai`, `DuckAssistBot`

Never block `OAI-SearchBot`, `ClaudeBot`, or `PerplexityBot` — these are citation bots, not training bots.
Use `Disallow: /` only for training bots (`GPTBot`, `anthropic-ai`) when training opt-out is desired.

## llms.txt

Always include:
- H1: site name
- Blockquote immediately after H1: one-sentence description
- Sections: `## Tools`, `## Articles`, `## Docs` (matching site structure)
- Every link must have a description: `- [Title](URL): Description`

Never omit the H1 + blockquote pair — they are required by the llms.txt spec.
Always place `llms.txt` at the site root (`/llms.txt`).
Keep llms.txt under 200 lines.

Generate: `geo llms --base-url URL --site-name NAME --description DESC --output ./public/llms.txt`

## JSON-LD Schema

Always add `WebSite` schema to every page's `<head>`.
Always add `WebApplication` schema to tool and calculator pages.
Always add `FAQPage` schema to any page with Q&A content.
Never omit `"url"` or `"@context": "https://schema.org"` from any schema.

Schema type guide:
- `WebSite` → all pages (global)
- `WebApplication` → tools, calculators, generators
- `FAQPage` → FAQ sections, question-based content
- `Article` → blog posts, guides, tutorials

Inject: `geo schema --type TYPE --url URL`
Types: `website`, `webapp`, `faq`, `article`, `organization`, `breadcrumb`

## Content (Princeton GEO Methods)

Always add at least 5 concrete statistics per page (%, numbers, dates).
Always include at least 3 external links to authoritative sources.
Always use expert quotes with attribution: `"Text" — Name, Role, Year`
Never use vague claims without data ("many users", "often").
Never keyword-stuff — Princeton KDD 2024 shows ~0% impact or negative effect.

Priority:
1. Cite Sources → +30–115% AI visibility
2. Add Statistics → +40%
3. Expert Quotes → +30–40%
4. Fluency Optimization → +15–30%
5. Authoritative Tone → +6–12%

## Audit

Always run audit before recommending optimizations.
GEO Score: 0–35 = critical | 36–67 = foundation | 68–85 = good | 86–100 = excellent

Run: `geo audit --url https://yoursite.com`

## Quick Reference

```bash
# Audit
geo audit --url https://yoursite.com

# Generate llms.txt
geo llms \
  --base-url https://yoursite.com \
  --site-name "Site Name" \
  --description "One-sentence description." \
  --output ./public/llms.txt

# Inject schema
geo schema --type webapp --url https://yoursite.com/tool
geo schema --type faq   --url https://yoursite.com/page
```

Always use `./geo` — never call scripts with `python3` directly.
