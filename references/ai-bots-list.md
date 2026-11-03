# AI Bots List — User-Agents for robots.txt

> Last updated: November 2026 (Anthropic and Google entries; tiers follow `src/geo_optimizer/models/config.py`)  
> Source: server log analysis, official vendor documentation, Momentic Marketing (Feb 2026)

## Recommended Full robots.txt

Copy this block into your `robots.txt` to optimize AI access:

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

# ——— Google AI (Gemini/Vertex training token — does not affect Search or AI Overviews) ———
User-agent: Google-Extended
Allow: /

# ——— Microsoft (Copilot/Bing) ———
User-agent: Bingbot
Allow: /

# ——— Apple (Siri/AI) ———
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

# ——— Academic / Open ———
User-agent: AI2Bot
Allow: /
User-agent: CCBot
Allow: /

# ——— Traditional (always keep) ———
User-agent: Googlebot
Allow: /
User-agent: *
Allow: /

Sitemap: https://yoursite.com/sitemap.xml
```

---

## Full List by Category

### OpenAI (ChatGPT)

| User-Agent | Type | Purpose | GEO Priority |
|-----------|------|---------|--------------|
| `GPTBot` | Training | Crawl for OpenAI model training | ⚠️ Training only |
| `OAI-SearchBot` | Search | **ChatGPT Search citations** — critical! | 🔴 CRITICAL |
| `ChatGPT-User` | On-demand | Fetch pages when user asks | ⭐⭐⭐ |

**robots.txt snippet:**
```
User-agent: GPTBot
Allow: /
User-agent: OAI-SearchBot
Allow: /
User-agent: ChatGPT-User
Allow: /
```

**Notes:**
- `OAI-SearchBot` = the ChatGPT search crawler; allowing it makes the site eligible for ChatGPT search answers, it does not guarantee citation
- `GPTBot` = training data. You can block training and stay open to ChatGPT search:
  ```
  User-agent: GPTBot
  Disallow: /
  User-agent: OAI-SearchBot
  Allow: /
  ```
- `ChatGPT-User` fetches a page when a user asks ChatGPT; OpenAI says robots.txt rules may not apply to these user-initiated visits

---

### Anthropic (Claude)

| User-Agent | Type | Purpose | GEO Priority |
|-----------|------|---------|--------------|
| `ClaudeBot` | Training | Claude model training | ⚠️ Training only |
| `Claude-SearchBot` | Search | **Claude search index** | 🔴 CRITICAL |
| `Claude-User` | On-demand | Fetch pages when a Claude user asks | ⭐⭐⭐ |

Anthropic's published crawler docs name only these three; `anthropic-ai` and `claude-web` are no longer listed.

**Full ClaudeBot User-Agent:**
```
Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +claudebot@anthropic.com)
```

**robots.txt snippet:**
```
User-agent: ClaudeBot
Allow: /
User-agent: Claude-SearchBot
Allow: /
User-agent: Claude-User
Allow: /
```

**If you want to block training and stay open to Claude search:**
```
User-agent: ClaudeBot
Disallow: /
User-agent: Claude-SearchBot
Allow: /
```

---

### Perplexity AI

| User-Agent | Type | Purpose | GEO Priority |
|-----------|------|---------|--------------|
| `PerplexityBot` | Index | **Builds Perplexity index** | 🔴 CRITICAL |
| `Perplexity-User` | On-demand | Fetches a page when a user asks Perplexity a question; generally ignores robots.txt | ⭐⭐⭐ |

**robots.txt snippet:**
```
User-agent: PerplexityBot
Allow: /
User-agent: Perplexity-User
Allow: /
```

**Notes:**
- Perplexity is one of the AI engines that cites web sources the most
- `PerplexityBot` is the most important for visibility

---

### Google AI (Gemini)

| User-Agent | Type | Purpose | GEO Priority |
|-----------|------|---------|--------------|
| `Google-Extended` | Training (token) | Gemini/Vertex training and grounding, not Search or AI Overviews | ⚠️ Training only |
| `Googlebot` | Search | Google Search, which also feeds AI Overviews and AI Mode | 🔴 CRITICAL |

**robots.txt snippet:**
```
User-agent: Google-Extended
Allow: /
User-agent: Googlebot
Allow: /
```

**Notes:**
- `Google-Extended` is a **robots.txt token**, not a separate user-agent
- Controls only whether Google may use content for Gemini/Vertex training and grounding
- It does not affect Search or AI Overviews: those are governed by Googlebot access and snippet controls (`nosnippet`, `max-snippet`)

---

### Microsoft (Copilot/Bing)

| User-Agent | Type | Purpose | GEO Priority |
|-----------|------|---------|--------------|
| `Bingbot` | Search | Bing Search and Copilot | 🔴 CRITICAL |

**robots.txt snippet:**
```
User-agent: Bingbot
Allow: /
```

**Notes:**
- Copilot uses the Bing index: allowing Bingbot = allowing Copilot
- There is no separate "CopilotBot"

---

### Apple (Siri/AI)

| User-Agent | Type | Purpose | GEO Priority |
|-----------|------|---------|--------------|
| `Applebot` | Search | Apple search features in Spotlight, Siri and Safari | ⭐⭐ |
| `Applebot-Extended` | Training (token) | Controls use for Apple Intelligence training; a robots.txt token that does not crawl webpages | ⭐ |

**robots.txt snippet:**
```
User-agent: Applebot
Allow: /
User-agent: Applebot-Extended
Allow: /
```

---

### Meta (Facebook AI)

| User-Agent | Type | Purpose | GEO Priority |
|-----------|------|---------|--------------|
| `meta-externalagent` | Training | AI model training and product indexing | ⭐ |
| `Meta-ExternalFetcher` | On-demand | User-requested link fetches (incl. agentic AI tasks); may bypass robots.txt | ⭐ |

**robots.txt snippet:**
```
User-agent: meta-externalagent
Allow: /
User-agent: Meta-ExternalFetcher
Allow: /
```

---

### ByteDance/TikTok

| User-Agent | Type | Purpose | GEO Priority |
|-----------|------|---------|--------------|
| `Bytespider` | AI/Rec | TikTok AI, recommendations | ⭐⭐ |

**robots.txt snippet:**
```
User-agent: Bytespider
Allow: /
```

---

### DuckDuckGo

| User-Agent | Type | Purpose | GEO Priority |
|-----------|------|---------|--------------|
| `DuckAssistBot` | AI | DuckAssist AI answers | ⭐ |

---

### Academic & Open Source

| User-Agent | Type | Purpose |
|-----------|------|---------|
| `AI2Bot` | Academic | Allen Institute for AI, Semantic Scholar |
| `CCBot` | Open | Common Crawl — base for many models |
| `Amazonbot` | AI | Alexa, Fire OS AI |

---

## robots.txt Strategies

### Strategy 1: Allow All (Maximum AI Visibility) ✅
```
User-agent: *
Allow: /
```
Simple, allows everything. Ideal for content sites that want maximum visibility.

### Strategy 2: Allow AI search, block training (policy choice)
```
# Training — block (no AI training data)
User-agent: GPTBot
Disallow: /
User-agent: ClaudeBot
Disallow: /
User-agent: Google-Extended
Disallow: /
User-agent: CCBot
Disallow: /

# AI search — allow (eligibility, not a citation guarantee)
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
```

### Strategy 3: Block everything except Google
```
User-agent: Googlebot
Allow: /
User-agent: Bingbot
Allow: /
User-agent: *
Disallow: /
```
⚠️ Blocks every AI-specific crawler (OAI-SearchBot, Claude-SearchBot, PerplexityBot…), so the site drops out of those AI search indexes. Google AI Overviews and Copilot still read the Googlebot and Bingbot indexes.

---

## Verify with curl

Test whether a bot can access your site:

```bash
# Simulate GPTBot
curl -A "GPTBot" https://yoursite.com/robots.txt

# Simulate ClaudeBot
curl -A "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +claudebot@anthropic.com)" https://yoursite.com

# Simulate Claude-SearchBot
curl -A "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Claude-SearchBot/1.0; +https://www.anthropic.com/claude-searchbot)" https://yoursite.com

# Simulate PerplexityBot
curl -A "PerplexityBot/1.0 (+https://perplexity.ai/bot)" https://yoursite.com
```

---

## Monitor Bots in Logs

Search server logs (nginx/apache):

```bash
# Search all AI bots in nginx logs
# Google-Extended is a robots.txt token, never a user-agent, so it does not appear in logs
grep -E "GPTBot|OAI-SearchBot|ClaudeBot|Claude-SearchBot|Claude-User|PerplexityBot" /var/log/nginx/access.log

# Count visits per bot
grep -oE "GPTBot|OAI-SearchBot|ClaudeBot|Claude-SearchBot|PerplexityBot" /var/log/nginx/access.log | sort | uniq -c | sort -rn
```

---

## Official Resources

- OpenAI: https://developers.openai.com/api/docs/bots
- Anthropic: https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler
- Perplexity: https://docs.perplexity.ai/guides/bots
- Apple: https://support.apple.com/en-us/119829
- Meta: https://developers.facebook.com/docs/sharing/webmasters/web-crawlers
- Google: https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers
- Momentic Marketing Bot List: https://momenticmarketing.com/blog/ai-search-crawlers-bots
- Search Engine Journal: https://www.searchenginejournal.com/ai-crawler-user-agents-list/
