---
name: geo-optimizer
version: "1.2.0"
description: >
  Optimizes websites to be cited by AI search engines (ChatGPT, Perplexity, Claude, Gemini).
  Implements GEO (Generative Engine Optimization) with the 9 Princeton methods: automated audit,
  llms.txt generation, JSON-LD schema, robots.txt for AI bots. Increases AI visibility by up to 40%.
  Trigger: "optimize for AI search", "GEO", "llms.txt", "AI visibility", "AI citations",
  "generative engine optimization", "ChatGPT cites me", "Perplexity optimization".
---

# GEO Optimizer — Generative Engine Optimization

> Based on Princeton KDD 2024 research "GEO: Generative Engine Optimization"  
> Skill author: Juan Camilo Auriti (juancamilo.auriti@gmail.com)

## What is GEO?

GEO = optimizing web content to **be cited by AI search engines** (ChatGPT, Perplexity, Claude, Gemini) instead of just ranking on traditional Google.

**Key data (Princeton 2024):**
- Adding statistics and citations → **+40% visibility** in AI responses
- Cite Sources (citing sources in the text) → **up to +115%** for certain rank positions  
- Fluency optimization → **+15-30%** average visibility
- Tested on real Perplexity.ai → **+37% visibility** confirmed

---

## How to Use This Skill with AI

For each workflow step, use the **"expert role + specific deliverables" pattern**:

```
You are a [expert role at a leading company in the field].
I need [specific deliverable] for my site [URL].

Provide:
- [output 1]
- [output 2]
- [output 3]
```

**Ready-to-use examples:**

```
You are a Senior SEO Engineer at Google.
I need a robots.txt optimized for AI search engines
for my site example.com (a financial tools website).
Provide: full AI bots list 2026, Allow/Disallow rules,
explanatory comments, Crawl-delay handling.
```

```
You are a Schema.org Architect at Bing.
I need complete JSON-LD schema for an IRPEF calculator page
(Italian taxes). Provide: WebApplication, FAQPage with 5 real questions,
BreadcrumbList, code ready for Astro/React/HTML.
```

```
You are an AI Search Optimization Lead at Perplexity.
Analyze this page [URL] and tell me what's missing to be
cited in AI responses. Provide: gap analysis, priorities,
llms.txt template adapted to my site.
```

> **Principle:** the more specific the role and deliverables, the better the output.
> Always replace values between `[...]` with real data.

---

## 4-Step Workflow

### STEP 1 — AUDIT 🔍

Run the full site audit:

```bash
# From the skill directory
cd /path/to/skills/geo-optimizer
pip install requests beautifulsoup4 -q
python scripts/geo_audit.py --url https://yoursite.com
```

The audit checks:
- ✅/❌ robots.txt with all AI bots (GPTBot, ClaudeBot, PerplexityBot, etc.)
- ✅/❌ Presence of `/llms.txt`
- ✅/❌ JSON-LD Schema (WebSite, FAQPage, WebApplication)
- ✅/❌ Meta description, canonical URL, Open Graph tags
- ⚠️ Warnings for partial configurations

> Ref: [`references/ai-bots-list.md`](references/ai-bots-list.md) for all AI bots

---

### STEP 2 — robots.txt 🤖

Add these blocks to the site's `robots.txt` (allow all AI search bots):

```
# ——— OpenAI ———
User-agent: GPTBot
Allow: /
User-agent: OAI-SearchBot
Allow: /
User-agent: ChatGPT-User
Allow: /

# ——— Anthropic (Claude) ———
User-agent: anthropic-ai
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: claude-web
Allow: /

# ——— Perplexity ———
User-agent: PerplexityBot
Allow: /
User-agent: Perplexity-User
Allow: /

# ——— Google (Gemini) ———
User-agent: Google-Extended
Allow: /
User-agent: Googlebot
Allow: /

# ——— Microsoft (Copilot) ———
User-agent: Bingbot
Allow: /

# ——— Apple (Siri) ———
User-agent: Applebot
Allow: /
User-agent: Applebot-Extended
Allow: /

# ——— Others ———
User-agent: cohere-ai
Allow: /
User-agent: DuckAssistBot
Allow: /
User-agent: Bytespider
Allow: /
```

> If you want to **block** training (but still allow citations), use `Disallow: /` for `anthropic-ai` and `GPTBot`  
> but `Allow: /` for `ClaudeBot`, `OAI-SearchBot` and `PerplexityBot`

---

### STEP 3 — llms.txt 📋

**Auto-generate from sitemap:**

```bash
# From the skill directory
python scripts/generate_llms_txt.py \
  --base-url https://yoursite.com \
  --output ./public/llms.txt
```

**Or create manually** the `/llms.txt` file following this template:

```markdown
# Site Name

> Brief site description in 1-2 sentences. What it offers, who it serves.

Optional additional details about the project.

## Tools

- [Tool Name](https://yoursite.com/tool): Brief description

## Documentation

- [Guide](https://yoursite.com/docs): Main documentation

## Blog / Articles

- [Article 1](https://yoursite.com/blog/article): Description

## Optional

- [Secondary page](https://yoursite.com/about): Optional info
```

> Full spec: https://llmstxt.org  
> The file goes at `/llms.txt` (site root, next to `robots.txt`)

---

### STEP 4 — Schema JSON-LD 🏗️

Add structured schema to help AI understand the content.

**Base template (WebSite)** — goes in the `<head>` of all pages:

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "Site Name",
  "url": "https://yoursite.com",
  "description": "Site description",
  "potentialAction": {
    "@type": "SearchAction",
    "target": "https://yoursite.com/search?q={search_term_string}",
    "query-input": "required name=search_term_string"
  }
}
</script>
```

**For calculators/tools (WebApplication):**

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "Calculator Name",
  "url": "https://yoursite.com/calculator",
  "applicationCategory": "UtilityApplication",
  "operatingSystem": "Web",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "USD"
  }
}
</script>
```

**For FAQ (FAQPage):**

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Question 1?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Complete answer..."
      }
    }
  ]
}
</script>
```

> Full templates: [`references/schema-templates.md`](references/schema-templates.md)  
> Automated script: `scripts/schema_injector.py`

---

## Princeton GEO Methods (Priority Order)

Implement in order of impact:

| # | Method | Impact | How |
|---|--------|--------|-----|
| 1 | **Cite Sources** | +40% | Add links to authoritative sources in the text |
| 2 | **Statistics** | +40% | Include concrete numerical data (%, $, dates) |
| 3 | **Quotation Addition** | +30% | Quote experts with quotation marks |
| 4 | **Authoritative** | +15% | Expert tone, not generic |
| 5 | **Fluency Opt.** | +15-30% | Flowing, well-structured text |
| 6 | **Easy-to-Understand** | +10% | Simplify complex language |
| 7 | **Technical Terms** | +8% | Use correct industry terminology |
| 8 | **Unique Words** | +5% | Enrich vocabulary |
| 9 | **Keyword Stuffing** | ⚠️ | Not effective, often negative |

> Full detail: [`references/princeton-geo-methods.md`](references/princeton-geo-methods.md)

---

## Astro Implementation

For Astro sites, add to your main layout (e.g. `BaseLayout.astro`):

```astro
---
interface Props {
  title: string;
  description: string;
  siteUrl: string;
  siteName: string;
  isTool?: boolean;    // true for calculators/apps
  faqItems?: Array<{ question: string; answer: string }>;
}
const { title, description, siteUrl, siteName, isTool = false, faqItems = [] } = Astro.props;
---

<head>
  <!-- WebSite Schema (always present) -->
  <script type="application/ld+json">
  {JSON.stringify({
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": siteName,
    "url": siteUrl
  })}
  </script>

  <!-- WebApplication Schema (only on tools/calculators) -->
  {isTool && (
    <script type="application/ld+json">
    {JSON.stringify({
      "@context": "https://schema.org",
      "@type": "WebApplication",
      "name": title,
      "url": Astro.url.href,
      "applicationCategory": "UtilityApplication",
      "operatingSystem": "Web",
      "offers": { "@type": "Offer", "price": "0", "priceCurrency": "EUR" }
    })}
    </script>
  )}

  <!-- FAQPage Schema (when there are frequently asked questions) -->
  {faqItems.length > 0 && (
    <script type="application/ld+json">
    {JSON.stringify({
      "@context": "https://schema.org",
      "@type": "FAQPage",
      "mainEntity": faqItems.map(item => ({
        "@type": "Question",
        "name": item.question,
        "acceptedAnswer": { "@type": "Answer", "text": item.answer }
      }))
    })}
    </script>
  )}
</head>
```

**Usage in pages:**

```astro
<BaseLayout
  title="Tool Name"
  description="Brief description"
  siteUrl="https://yoursite.com"
  siteName="Site Name"
  isTool={true}
  faqItems={[
    { question: "How does it work?", answer: "..." },
    { question: "Is it free?", answer: "Yes, completely free." }
  ]}
/>
```

---

## Complete GEO Checklist

- [ ] robots.txt: all AI bots with `Allow: /`
- [ ] `/llms.txt` present and structured
- [ ] WebSite schema in the global `<head>`
- [ ] WebApplication schema on tool/calculator pages
- [ ] FAQPage schema on pages with questions/answers
- [ ] Content with concrete numerical statistics
- [ ] Citations of authoritative sources in the text
- [ ] Accurate and descriptive meta description
- [ ] Canonical URL on every page
- [ ] Open Graph tags (og:title, og:description, og:image)
- [ ] Fluent and well-structured text with H1/H2/H3 headings

---

## Available Scripts

| Script | Usage |
|--------|-------|
| `scripts/geo_audit.py` | Full audit with ✅/❌/⚠️ report |
| `scripts/generate_llms_txt.py` | Generates llms.txt from XML sitemap |
| `scripts/schema_injector.py` | Injects JSON-LD schema into HTML/Astro |

## Iterative Learning

After each completed optimization, ask the AI:

```
What did we learn from this GEO optimization?
What could we do faster next time?
Are there common patterns to apply to other similar sites?
```

This approach improves efficiency by 30-52% iteration after iteration
(technique validated by Dane Gregory with Claude).

Save the responses in a `memory/geo-learnings.md` file in your workspace.

---

## References

| File | Content |
|------|---------|
| `references/princeton-geo-methods.md` | 9 GEO methods with impact and implementation |
| `references/ai-bots-list.md` | All AI bots with user-agent and robots.txt snippet |
| `references/schema-templates.md` | Ready-to-use JSON-LD templates |
