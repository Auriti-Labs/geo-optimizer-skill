# AI Bots Reference

Complete reference for AI crawler user-agents and `robots.txt` configuration strategies.

---

## Citation Bots vs Training Bots

This is the most important distinction in GEO robot configuration.

| Type | What they do | GEO impact | Example |
|------|-------------|-----------|---------|
| **Citation bots** | Crawl and index your content for use in AI-generated answers | 🔴 Critical — blocking these = not being cited | `OAI-SearchBot`, `ClaudeBot`, `PerplexityBot` |
| **Training bots** | Collect data to train AI models (offline process) | ⚠️ Optional — blocking doesn't affect citations | `GPTBot`, `anthropic-ai`, `CCBot` |

**Key insight:** You can block training bots (if you have IP concerns) while still allowing citation bots. Blocking `GPTBot` does not prevent ChatGPT from citing you — `OAI-SearchBot` is the relevant bot for citations.

---

## Complete Bot Table

### 🔴 Critical Citation Bots

These three bots directly determine whether AI search engines cite your site. **Never block them.**

| Bot | Vendor | Type | Purpose | Crawl Frequency |
|-----|--------|------|---------|----------------|
| `OAI-SearchBot` | OpenAI | **Citation** | ChatGPT Search index — determines citation eligibility | Daily |
| `ClaudeBot` | Anthropic | **Citation** | Claude.ai real-time web citations | On-demand + regular crawl |
| `PerplexityBot` | Perplexity | **Citation** | Perplexity AI citation index | Several times per week |

### OpenAI (ChatGPT)

| Bot | Type | Purpose | Crawl Frequency |
|-----|------|---------|----------------|
| `GPTBot` | Training | ChatGPT model training data | Frequent |
| `OAI-SearchBot` | **Citation** | ChatGPT Search citations | Daily |
| `ChatGPT-User` | On-demand | Fetched when a ChatGPT user requests a page | As needed |

### Anthropic (Claude)

| Bot | Type | Purpose | Crawl Frequency |
|-----|------|---------|----------------|
| `anthropic-ai` | Training | Claude model training | Periodic |
| `ClaudeBot` | **Citation** | Claude.ai web citations | On-demand + regular |
| `claude-web` | Crawl | General Claude web crawling | Periodic |

### Perplexity AI

| Bot | Type | Purpose | Crawl Frequency |
|-----|------|---------|----------------|
| `PerplexityBot` | **Citation** | Perplexity index and citation source | Several times/week |
| `Perplexity-User` | On-demand | Fetched when a user clicks a Perplexity citation | As needed |

### Google AI (Gemini)

| Bot | Type | Purpose | Crawl Frequency |
|-----|------|---------|----------------|
| `Google-Extended` | Training + AI Overviews | Gemini training and Google AI Overviews | Frequent |
| `Googlebot` | Search + Citation | Traditional Google Search and AI-assisted results | Very frequent |

Note: `Google-Extended` is a `robots.txt` token, not a separate user-agent. Blocking it removes your site from Google AI Overviews.

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
| `FacebookBot` | Preview | Facebook/Instagram link preview | On-demand |
| `meta-externalagent` | Backup | Meta backup fetcher | Periodic |

### Other AI Bots

| Bot | Vendor | Type | Purpose |
|-----|--------|------|---------|
| `Bytespider` | ByteDance/TikTok | AI + Rec | TikTok recommendations and AI features |
| `DuckAssistBot` | DuckDuckGo | Citation | DuckAssist AI answers |
| `cohere-ai` | Cohere | Training | Cohere language model training |
| `AI2Bot` | Allen Institute | Academic | Semantic Scholar, research AI |
| `CCBot` | Common Crawl | Training | Open dataset used by many models |

---

## robots.txt — Ready to Copy

Full GEO-optimized `robots.txt` block. Replace `https://yoursite.com/sitemap.xml` with your actual sitemap URL.

```
# ═══════════════════════════════════════════════
#   AI SEARCH & CITATION BOTS — Allow All
#   GEO-Optimized robots.txt
#   Updated: 2026-02
# ═══════════════════════════════════════════════

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

# ——— Google AI (Gemini + AI Overviews) ———
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
User-agent: FacebookBot
Allow: /
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

## Strategy: Allow Citations, Block Training

If you want to appear in AI answers but prevent your content from being used as training data:

```
# ─── Training bots — blocked ──────────────────
User-agent: GPTBot
Disallow: /

User-agent: anthropic-ai
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: Applebot-Extended
Disallow: /

# ─── Citation bots — allowed ──────────────────
User-agent: OAI-SearchBot
Allow: /

User-agent: ClaudeBot
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

# Simulate ClaudeBot
curl -A "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +claudebot@anthropic.com)" https://yoursite.com

# Simulate PerplexityBot
curl -A "PerplexityBot/1.0 (+https://perplexity.ai/bot)" https://yoursite.com

# Simulate GPTBot
curl -A "GPTBot/1.2 (+https://openai.com/gptbot)" https://yoursite.com/robots.txt
```

If you get a 403 or 401 for citation bots, they can't index your site.

---

## Monitor Bots in Server Logs

Check if AI bots are actively crawling your site:

```bash
# Search nginx access logs for all major AI bots
grep -E "GPTBot|OAI-SearchBot|ClaudeBot|PerplexityBot|Google-Extended|anthropic-ai" \
  /var/log/nginx/access.log

# Count hits per bot (last 7 days)
grep -oE "GPTBot|OAI-SearchBot|ClaudeBot|PerplexityBot|Google-Extended" \
  /var/log/nginx/access.log | sort | uniq -c | sort -rn

# Apache equivalent
grep -E "GPTBot|OAI-SearchBot|ClaudeBot|PerplexityBot" \
  /var/log/apache2/access.log | awk '{print $1, $7}' | head -50
```

For managed hosting without log access, check **Google Search Console → Settings → Crawl Stats** — it shows `Googlebot` and `Google-Extended` activity. For other bots, there is no equivalent dashboard; server logs are the only reliable source.

---

## Resources

- OpenAI bot docs: [openai.com/gptbot](https://openai.com/gptbot)
- Anthropic bot docs: [anthropic.com/legal/aup](https://www.anthropic.com/legal/aup)
- Perplexity bot docs: [docs.perplexity.ai/guides/perplexity-bot](https://docs.perplexity.ai/guides/perplexity-bot)
- Google crawlers: [developers.google.com/search/docs/crawling-indexing/google-common-crawlers](https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers)
