# AI Bots List — User-Agents per robots.txt

> Lista aggiornata: Febbraio 2026  
> Fonte: server logs analisi, documentazione ufficiale vendor, Momentic Marketing (Nov 2025)

## robots.txt Completo Raccomandato

Copia questo blocco nel tuo `robots.txt` per ottimizzare l'accesso AI:

```
# ═══════════════════════════════════════════════
#   AI SEARCH & CITATION BOTS — Allow All
#   GEO-Optimized robots.txt
#   Aggiornato: 2026-02
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

# ——— Google AI (Gemini) ———
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

# ——— Accademici / Open ———
User-agent: AI2Bot
Allow: /
User-agent: CCBot
Allow: /

# ——— Tradizionali (mantieni sempre) ———
User-agent: Googlebot
Allow: /
User-agent: *
Allow: /

Sitemap: https://tuosito.com/sitemap.xml
```

---

## Lista Completa per Categoria

### OpenAI (ChatGPT)

| User-Agent | Tipo | Scopo | Priorità GEO |
|-----------|------|-------|--------------|
| `GPTBot` | Training | Crawl per training modelli OpenAI | ⚠️ Training only |
| `OAI-SearchBot` | Search | **Citazioni ChatGPT Search** — critico! | 🔴 CRITICO |
| `ChatGPT-User` | On-demand | Fetch pagine quando utente chiede | ⭐⭐⭐ |

**robots.txt snippet:**
```
User-agent: GPTBot
Allow: /
User-agent: OAI-SearchBot
Allow: /
User-agent: ChatGPT-User
Allow: /
```

**Note:**
- `OAI-SearchBot` = il bot che decide se citarti in ChatGPT Search
- `GPTBot` = training data. Puoi bloccare il training ma permettere citazioni:
  ```
  User-agent: GPTBot
  Disallow: /
  User-agent: OAI-SearchBot
  Allow: /
  ```
- `ChatGPT-User` segue robots.txt ma può essere user-triggered

---

### Anthropic (Claude)

| User-Agent | Tipo | Scopo | Priorità GEO |
|-----------|------|-------|--------------|
| `anthropic-ai` | Training | Training modelli Claude | ⚠️ Training only |
| `ClaudeBot` | Search/Citation | **Citazioni Claude.ai** | 🔴 CRITICO |
| `claude-web` | Crawl | Web crawling generico Claude | ⭐⭐ |

**User-Agent completa ClaudeBot:**
```
Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +claudebot@anthropic.com)
```

**robots.txt snippet:**
```
User-agent: anthropic-ai
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: claude-web
Allow: /
```

**Se vuoi separare training da citazioni:**
```
User-agent: anthropic-ai
Disallow: /
User-agent: ClaudeBot
Allow: /
```

---

### Perplexity AI

| User-Agent | Tipo | Scopo | Priorità GEO |
|-----------|------|-------|--------------|
| `PerplexityBot` | Index | **Costruisce indice Perplexity** | 🔴 CRITICO |
| `Perplexity-User` | On-demand | Fetch quando utente clicca citazione | ⭐⭐⭐ |

**robots.txt snippet:**
```
User-agent: PerplexityBot
Allow: /
User-agent: Perplexity-User
Allow: /
```

**Note:**
- Perplexity è uno dei motori AI che cita di più le fonti web
- `PerplexityBot` è il più importante per la visibilità

---

### Google AI (Gemini)

| User-Agent | Tipo | Scopo | Priorità GEO |
|-----------|------|-------|--------------|
| `Google-Extended` | Training/AI | Gemini training e AI Overviews | ⭐⭐⭐ |
| `Googlebot` | Search | Google Search tradizionale | 🔴 CRITICO |

**robots.txt snippet:**
```
User-agent: Google-Extended
Allow: /
User-agent: Googlebot
Allow: /
```

**Note:**
- `Google-Extended` è un **token robots.txt**, non un user-agent separato
- Controlla sia Gemini training che AI Overviews in Google Search
- Bloccare `Google-Extended` rimuove il sito dagli AI Overviews Google

---

### Microsoft (Copilot/Bing)

| User-Agent | Tipo | Scopo | Priorità GEO |
|-----------|------|-------|--------------|
| `Bingbot` | Search | Bing Search e Copilot | 🔴 CRITICO |

**robots.txt snippet:**
```
User-agent: Bingbot
Allow: /
```

**Note:**
- Copilot usa l'indice Bing: permettere Bingbot = permettere Copilot
- Non esiste un "CopilotBot" separato

---

### Apple (Siri/AI)

| User-Agent | Tipo | Scopo | Priorità GEO |
|-----------|------|-------|--------------|
| `Applebot` | Search | Siri, Spotlight Search | ⭐⭐ |
| `Applebot-Extended` | Training | Apple Intelligence training | ⭐ |

**robots.txt snippet:**
```
User-agent: Applebot
Allow: /
User-agent: Applebot-Extended
Allow: /
```

---

### Meta (Facebook AI)

| User-Agent | Tipo | Scopo | Priorità GEO |
|-----------|------|-------|--------------|
| `FacebookBot` | Preview | Link preview Facebook/Instagram | ⭐ |
| `meta-externalagent` | Backup | Fetcher backup Meta | ⭐ |

**robots.txt snippet:**
```
User-agent: FacebookBot
Allow: /
User-agent: meta-externalagent
Allow: /
```

---

### ByteDance/TikTok

| User-Agent | Tipo | Scopo | Priorità GEO |
|-----------|------|-------|--------------|
| `Bytespider` | AI/Rec | TikTok AI, raccomandazioni | ⭐⭐ |

**robots.txt snippet:**
```
User-agent: Bytespider
Allow: /
```

---

### DuckDuckGo

| User-Agent | Tipo | Scopo | Priorità GEO |
|-----------|------|-------|--------------|
| `DuckAssistBot` | AI | DuckAssist AI answers | ⭐ |

---

### Cohere

| User-Agent | Tipo | Scopo | Priorità GEO |
|-----------|------|-------|--------------|
| `cohere-ai` | Training | Training modelli Cohere | ⭐ |
| `cohere-training-data-crawler` | Training | Data crawler Cohere | ⭐ |

---

### Accademici & Open Source

| User-Agent | Tipo | Scopo |
|-----------|------|-------|
| `AI2Bot` | Academic | Allen Institute for AI, Semantic Scholar |
| `CCBot` | Open | Common Crawl — base per molti modelli |
| `Diffbot` | Data | Structured data extraction |
| `omgili` | Forum | Forum e discussioni |
| `LinkedInBot` | Preview | Anteprima link LinkedIn |
| `Amazonbot` | AI | Alexa, Fire OS AI |

---

## Strategie robots.txt

### Strategia 1: Allow All (Massima Visibilità AI) ✅
```
User-agent: *
Allow: /
```
Semplice, permette tutto. Ideale per siti di contenuto che vogliono massima visibilità.

### Strategia 2: Permetti citazioni, blocca training
```
# Training — blocca (no AI training data)
User-agent: GPTBot
Disallow: /
User-agent: anthropic-ai
Disallow: /
User-agent: Google-Extended
Disallow: /
User-agent: CCBot
Disallow: /

# Citazioni AI — permetti
User-agent: OAI-SearchBot
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: Bingbot
Allow: /
```

### Strategia 3: Blocca tutto tranne Google
```
User-agent: Googlebot
Allow: /
User-agent: Bingbot
Allow: /
User-agent: *
Disallow: /
```
⚠️ Rimuove il sito da tutte le AI search engines.

---

## Verifica con curl

Testa se un bot può accedere al tuo sito:

```bash
# Simula GPTBot
curl -A "GPTBot" https://tuosito.com/robots.txt

# Simula ClaudeBot
curl -A "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +claudebot@anthropic.com)" https://tuosito.com

# Simula PerplexityBot
curl -A "PerplexityBot/1.0 (+https://perplexity.ai/bot)" https://tuosito.com
```

---

## Monitorare i Bot nei Log

Cerca nei server log (nginx/apache):

```bash
# Cerca tutti gli AI bots nei log nginx
grep -E "GPTBot|OAI-SearchBot|ClaudeBot|PerplexityBot|Google-Extended|anthropic-ai|claude-web" /var/log/nginx/access.log

# Conta visite per bot
grep -oE "GPTBot|OAI-SearchBot|ClaudeBot|PerplexityBot" /var/log/nginx/access.log | sort | uniq -c | sort -rn
```

---

## Risorse Ufficiali

- OpenAI: https://openai.com/gptbot
- Anthropic: https://www.anthropic.com/legal/aup
- Perplexity: https://docs.perplexity.ai/guides/perplexity-bot
- Google: https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers
- Momentic Marketing Bot List: https://momenticmarketing.com/blog/ai-search-crawlers-bots
- Search Engine Journal: https://www.searchenginejournal.com/ai-crawler-user-agents-list/
