---
title: "AI Crawler User-Agent List & robots.txt Rules"
description: "Complete user-agent reference for AI search and training bots in 2026, plus robots.txt allow/block rules for OpenAI, Anthropic, Google and Perplexity."
order: 7
---

Complete reference for AI crawler user-agents and `robots.txt` configuration strategies.

---

## Search Bots vs Training Bots

This is the most important distinction in GEO robot configuration.

| Type | What they do | GEO impact | Example |
|------|-------------|-----------|---------|
| **Search bots** | Crawl and index your content for use in AI-generated answers | 🔴 Keep allowed — blocking them removes eligibility; allowing them does not guarantee citation | `OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`, `Googlebot`, `Applebot` |
| **Training bots** | Collect data to train AI models (offline process) | ⚠️ Policy choice — vendors treat training and search settings as independent | `GPTBot`, `ClaudeBot`, `Google-Extended`, `CCBot` |

**Key insight:** You can block training bots (if you have IP concerns) while still allowing search bots. A third tier, user-triggered fetch (`ChatGPT-User`, `Claude-User`, `Perplexity-User`), fetches a page when a user asks for it. Blocking `GPTBot` does not prevent ChatGPT from citing you — `OAI-SearchBot` is the relevant bot for citations. Likewise `ClaudeBot` is Anthropic's training crawler, not the one Claude cites through — `Claude-SearchBot` (index) and `Claude-User` (on-demand, when a user asks Claude to visit a URL) are.

---

## Complete Bot Table

### 🔴 Critical Citation Bots

These five bots build the indexes AI search engines answer from. Blocking them removes the site from those answers; allowing them makes it eligible, it does not guarantee citation. **Never block them.**

| Bot | Vendor | Type | Purpose | Crawl Frequency |
|-----|--------|------|---------|----------------|
| `OAI-SearchBot` | OpenAI | **Citation** | ChatGPT Search index — determines citation eligibility | Daily |
| `Claude-SearchBot` | Anthropic | **Citation** | Claude search-specific crawler | On-demand |
| `PerplexityBot` | Perplexity | **Citation** | Perplexity AI citation index | Several times per week |
| `Googlebot` | Google | **Citation** | Same crawler/index that feeds AI Overviews — see note below | Very frequent |
| `Applebot` | Apple | **Citation** | Siri, Spotlight Search, Safari Suggestions | Periodic |

### OpenAI (ChatGPT)

| Bot | Type | Purpose | Crawl Frequency |
|-----|------|---------|----------------|
| `GPTBot` | Training | ChatGPT model training data | Frequent |
| `OAI-SearchBot` | **Citation** | ChatGPT Search citations | Daily |
| `ChatGPT-User` | On-demand | Fetched when a ChatGPT user requests a page | As needed |

### Anthropic (Claude)

Anthropic's current published crawler docs (support.claude.com) name exactly
these three bots — `anthropic-ai` and `claude-web` are no longer listed and
have been removed from this reference.

| Bot | Type | Purpose | Crawl Frequency |
|-----|------|---------|----------------|
| `ClaudeBot` | Training | Claude model training | Periodic |
| `Claude-SearchBot` | **Citation** | Claude search-specific crawler | On-demand |
| `Claude-User` | On-demand | Fetched when a Claude user asks it to visit a URL | As needed |

### Perplexity AI

| Bot | Type | Purpose | Crawl Frequency |
|-----|------|---------|----------------|
| `PerplexityBot` | **Citation** | Perplexity index and citation source | Several times/week |
| `Perplexity-User` | On-demand | Fetched when a user clicks a Perplexity citation | As needed |

### Google AI (Gemini)

| Bot | Type | Purpose | Crawl Frequency |
|-----|------|---------|----------------|
| `Google-Extended` | Training only | Gemini Apps and Vertex AI generative model training/grounding | Frequent |
| `Googlebot` | Search + Citation | Traditional Google Search and AI Overviews (same crawler, same index) | Very frequent |

Note: `Google-Extended` is a `robots.txt` token, not a separate user-agent. Per Google's own documentation, it controls only whether content is used to improve Gemini Apps and Vertex AI generative models — it has no effect on Search inclusion or AI Overviews eligibility, which are governed entirely by standard Googlebot access. AI Overviews and AI Mode follow Googlebot access and snippet controls (`nosnippet`, `max-snippet`); the audit's manual check `G-GENAI-CONTROL` asks you to review the Search Console generative-AI opt-out ([Google's AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide)). Blocking Google-Extended alone does not opt a site out of AI Overviews.

### Microsoft (Copilot)

| Bot | Type | Purpose | Crawl Frequency |
|-----|------|---------|----------------|
| `Bingbot` | Search + Citation | Bing Search index; Copilot uses this index | Frequent |

There is no separate `CopilotBot` — Copilot reads the Bing index, so allowing `Bingbot` = allowing Copilot.

### Apple (Siri)

| Bot | Type | Purpose | Crawl Frequency |
|-----|------|---------|----------------|
| `Applebot` | Search | Siri, Spotlight Search, Safari Suggestions | Periodic |
| `Applebot-Extended` | Training | Apple Intelligence training data | Periodic |

### Meta (Facebook AI)

| Bot | Type | Purpose | Crawl Frequency |
|-----|------|---------|----------------|
| `meta-externalagent` | AI | Meta AI (Facebook/Instagram AI features) | Periodic |
| `Meta-ExternalFetcher` | On-demand | Meta content fetch on-demand | As needed |
| `facebookexternalhit` | Preview | Meta social preview and AI features | On-demand |

### Amazon (Alexa AI)

| Bot | Type | Purpose | Crawl Frequency |
|-----|------|---------|----------------|
| `Amazonbot` | Search AI | Amazon Alexa and search AI features | Periodic |

### Other AI Bots

| Bot | Vendor | Type | Purpose |
|-----|--------|------|---------|
| `Bytespider` | ByteDance/TikTok | AI + Rec | TikTok recommendations and AI features |
| `DuckAssistBot` | DuckDuckGo | Citation | DuckAssist AI answers |
| `cohere-ai` | Cohere | Training | Cohere language model training |
| `AI2Bot` | Allen Institute | Academic | Semantic Scholar, research AI |
| `AI2Bot-Dolma` | Allen Institute | Training | Allen Institute Dolma dataset collection |
| `xAI-Bot` | xAI | Citation | Grok search citations |
| `PetalBot` | Huawei | Search AI | Huawei PetalSearch AI (EU/Asia markets) |
| `YouBot` | You.com | Citation | You.com AI search index |
| `CCBot` | Common Crawl | Training | Open dataset used by many models |

---

## robots.txt — Ready to Copy

Full GEO-optimized `robots.txt` block. Replace `https://yoursite.com/sitemap.xml` with your actual sitemap URL.

```
# ═══════════════════════════════════════════════
#   AI BOTS — Allow All (search, training, user fetch)
#   GEO-Optimized robots.txt
#   Updated: 2026-11
# ═══════════════════════════════════════════════

# ——— OpenAI ———
User-agent: GPTBot
Allow: /
User-agent: OAI-SearchBot
Allow: /
User-agent: ChatGPT-User
Allow: /

# ——— Anthropic (Claude) ———
User-agent: ClaudeBot
Allow: /
User-agent: Claude-SearchBot
Allow: /
User-agent: Claude-User
Allow: /

# ——— Perplexity ———
User-agent: PerplexityBot
Allow: /
User-agent: Perplexity-User
Allow: /

# ——— Google AI (Gemini training/grounding only — does not affect Search or AI Overviews) ———
User-agent: Google-Extended
Allow: /

# ——— Microsoft (Copilot via Bing) ———
User-agent: Bingbot
Allow: /

# ——— Apple (Siri / Apple Intelligence) ———
User-agent: Applebot
Allow: /
User-agent: Applebot-Extended
Allow: /

# ——— Meta (AI) ———
User-agent: meta-externalagent
Allow: /

# ——— ByteDance/TikTok ———
User-agent: Bytespider
Allow: /

# ——— DuckDuckGo AI ———
User-agent: DuckAssistBot
Allow: /

# ——— Cohere ———
User-agent: cohere-ai
Allow: /

# ——— Academic / Open ———
User-agent: AI2Bot
Allow: /
User-agent: CCBot
Allow: /

# ——— Traditional Search (always keep) ———
User-agent: Googlebot
Allow: /
User-agent: *
Allow: /

Sitemap: https://yoursite.com/sitemap.xml
```

---

## Strategy: Allow AI Search, Block Training

If you want to stay eligible for AI answers but prevent your content from being used as training data (a policy choice):

```
# ─── Training bots — blocked ──────────────────
User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: Applebot-Extended
Disallow: /

# ─── Search bots — allowed ────────────────────
User-agent: OAI-SearchBot
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Bingbot
Allow: /

User-agent: Googlebot
Allow: /

User-agent: *
Allow: /

Sitemap: https://yoursite.com/sitemap.xml
```

Note: `robots.txt` is an honor system. Well-behaved bots respect it; scraper bots may not. For actual training data protection, consider additional legal or technical measures.

---

## Verify Bot Access

Simulate a bot's HTTP request to check what your server returns:

```bash
# Simulate OAI-SearchBot (ChatGPT citations)
curl -A "OAI-SearchBot/1.0 (+https://openai.com/searchbot)" https://yoursite.com/robots.txt

# Simulate Claude-SearchBot (Claude citations)
curl -A "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Claude-SearchBot/1.0; +https://www.anthropic.com/claude-searchbot)" https://yoursite.com

# Simulate PerplexityBot
curl -A "PerplexityBot/1.0 (+https://perplexity.ai/bot)" https://yoursite.com

# Simulate GPTBot (training only — does not affect ChatGPT citations)
curl -A "GPTBot/1.2 (+https://openai.com/gptbot)" https://yoursite.com/robots.txt
```

If you get a 403 or 401 for citation bots, they can't index your site.

---

## Monitor Bots in Server Logs

Check if AI bots are actively crawling your site:

```bash
# Search nginx access logs for all major AI bots
grep -E "GPTBot|OAI-SearchBot|ClaudeBot|Claude-SearchBot|PerplexityBot|Googlebot|Applebot" \
  /var/log/nginx/access.log

# Count hits per bot (last 7 days)
grep -oE "GPTBot|OAI-SearchBot|ClaudeBot|Claude-SearchBot|PerplexityBot" \
  /var/log/nginx/access.log | sort | uniq -c | sort -rn

# Apache equivalent
grep -E "GPTBot|OAI-SearchBot|ClaudeBot|Claude-SearchBot|PerplexityBot" \
  /var/log/apache2/access.log | awk '{print $1, $7}' | head -50
```

For managed hosting without log access, check **Google Search Console → Settings → Crawl Stats** — it shows `Googlebot` activity (`Google-Extended` is a robots.txt token, not a crawler, so it never shows up as separate traffic). For other bots, there is no equivalent dashboard; server logs are the only reliable source.

---

## Resources

- OpenAI bot docs: [openai.com/gptbot](https://openai.com/gptbot)
- Anthropic bot docs: [anthropic.com/legal/aup](https://www.anthropic.com/legal/aup)
- Perplexity bot docs: [docs.perplexity.ai/docs/resources/perplexity-crawlers](https://docs.perplexity.ai/docs/resources/perplexity-crawlers)
- Google crawlers: [developers.google.com/search/docs/crawling-indexing/google-common-crawlers](https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers)
