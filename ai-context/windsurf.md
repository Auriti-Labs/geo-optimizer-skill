# GEO Optimizer — Windsurf Rules

## robots.txt

Always include these user-agents with `Allow: /`:
- Critical citation bots: `OAI-SearchBot`, `PerplexityBot`, `ClaudeBot`, `Google-Extended`
- Also include: `GPTBot`, `ChatGPT-User`, `anthropic-ai`, `claude-web`, `Googlebot`, `Bingbot`, `Applebot`, `Applebot-Extended`, `FacebookBot`, `Bytespider`, `cohere-ai`, `DuckAssistBot`

Never block critical citation bots even if blocking training bots.
Use `Disallow: /` for `GPTBot` and `anthropic-ai` to block training while keeping citations.
Always keep `OAI-SearchBot`, `ClaudeBot`, `PerplexityBot` at `Allow: /` for citation access.

## llms.txt

Always include these elements in `/llms.txt`:
- H1: site name (required)
- Blockquote immediately after H1: one-sentence site description (required)
- Sections matching site structure: `## Tools`, `## Articles`, `## Docs`, etc.
- Every link must have a colon + brief description: `- [Title](URL): Description`

Never create an llms.txt without the H1 + blockquote pair.
Never list URLs without descriptions.
Always place `llms.txt` at the site root (`/llms.txt`), not in a subdirectory.
Keep llms.txt under 200 lines — AI crawlers prefer concise files.

Generate llms.txt with: `./geo scripts/generate_llms_txt.py --base-url URL --site-name NAME --description DESC --output ./public/llms.txt`

## JSON-LD Schema

Always add `WebSite` schema to every page's `<head>`.
Always add `WebApplication` schema to tool and calculator pages.
Always add `FAQPage` schema to any page with Q&A content.
Never omit the `"url"` field in any schema type.
Never use schema without the `"@context": "https://schema.org"` field.

Use `WebSite` for: all pages (global schema).
Use `WebApplication` for: tools, calculators, apps, generators.
Use `FAQPage` for: FAQ sections, how-to pages, question-based content.
Use `Article` for: blog posts, guides, news.
Use `HowTo` for: step-by-step tutorials.

Inject schema automatically: `./geo scripts/schema_injector.py --type TYPE --url URL`
Types available: `website`, `webapp`, `faq`, `article`, `organization`, `breadcrumb`, `howto`, `product`

## Content (Princeton GEO Methods)

Always add at least 5 concrete statistics (%, numbers, dates, measurements) per page.
Always include at least 3 external links to authoritative sources.
Always use expert quotes with attribution: `"Text" — Name, Role, Organization, Year`
Never use vague claims without data ("many users", "often", "sometimes").
Never keyword-stuff — Princeton KDD 2024 shows ~0% impact, possible negative effect.

Priority order for content optimization:
1. Cite Sources (+30–115% AI visibility)
2. Add Statistics (+40%)
3. Quotation Addition (+30–40%)
4. Fluency Optimization (+15–30%)
5. Authoritative Tone (+6–12%)

## Audit

Always run the GEO audit before making optimization recommendations.
Always interpret the GEO Score: 0–40 = critical, 41–70 = foundation, 71–90 = good, 91–100 = excellent.
Never skip the audit step — score determines priority.

Run audit: `./geo scripts/geo_audit.py --url https://yoursite.com`

The audit checks: robots.txt, llms.txt, JSON-LD schema, meta tags, content quality signals.

## Scripts

```bash
# Full GEO audit — returns score 0-100 + prioritized action list
./geo scripts/geo_audit.py --url https://yoursite.com

# Generate /llms.txt from sitemap
./geo scripts/generate_llms_txt.py \
  --base-url https://yoursite.com \
  --site-name "Site Name" \
  --description "One-sentence description." \
  --output ./public/llms.txt

# Inject JSON-LD schema (types: website, webapp, faq, article, organization, howto)
./geo scripts/schema_injector.py --type faq --url https://yoursite.com/page
./geo scripts/schema_injector.py --type webapp --url https://yoursite.com/tool
```

Always use the exact `./geo` prefix — it is the toolkit entry point.
Never call scripts with `python3` directly — use the `./geo` wrapper.

---

*Save as `.windsurf/rules/geo-optimizer.md` in your project root*
