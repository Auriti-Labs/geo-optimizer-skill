# 🤖 GEO Optimizer Skill — Generative Engine Optimization

[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-blue)](https://github.com/auriti-web-design)
[![GEO](https://img.shields.io/badge/GEO-Optimization-green)](https://arxiv.org/abs/2311.09735)
[![Princeton Research](https://img.shields.io/badge/Based_on-Princeton_KDD_2024-orange)](https://arxiv.org/abs/2311.09735)
[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://python.org)

> Ottimizza siti web per essere **citati** dai motori di ricerca AI: ChatGPT, Perplexity, Claude, Gemini.  
> Basato sulla ricerca Princeton "GEO: Generative Engine Optimization" (KDD 2024, +40% visibilità AI).

---

## 🎯 Cos'è il GEO?

**GEO (Generative Engine Optimization)** è l'evoluzione del SEO per l'era delle AI. Invece di ottimizzare per rankare su Google, si ottimizza per essere **citati e referenziati** dai motori di ricerca AI:

- 💬 **ChatGPT Search** (OAI-SearchBot)
- 🔍 **Perplexity AI** (PerplexityBot)
- 🤖 **Claude** (ClaudeBot)
- ✨ **Google AI Overviews / Gemini** (Google-Extended)
- 🔵 **Microsoft Copilot** (Bingbot)

**Risultati comprovati (Princeton KDD 2024):**
- +40% visibilità media nei motori AI con statistiche e citazioni
- +115% per alcuni rank positions con Cite Sources method
- +37% su Perplexity.ai reale nei test

---

## 📦 Struttura

```
geo-optimizer/
├── SKILL.md                          # Skill OpenClaw principale
├── scripts/
│   ├── geo_audit.py                  # Audit completo con report ✅/❌/⚠️
│   ├── generate_llms_txt.py          # Genera llms.txt da sitemap XML
│   └── schema_injector.py            # Aggiunge schema JSON-LD a HTML/Astro
└── references/
    ├── princeton-geo-methods.md      # I 9 metodi Princeton con impatto stimato
    ├── ai-bots-list.md               # 25+ bot AI con user-agent e robots.txt snippet
    └── schema-templates.md           # Template JSON-LD pronti (8 tipi)
```

---

## 🚀 Quick Start

### 1. Installa dipendenze
```bash
pip install requests beautifulsoup4
```

### 2. Audit del tuo sito
```bash
python scripts/geo_audit.py --url https://tuosito.com
```

**Output:**
```
🔍 GEO AUDIT — https://tuosito.com

1. ROBOTS.TXT — AI Bot Access
  ✅ robots.txt trovato (200)
  ❌ OAI-SearchBot NON configurato — CRITICO per citazioni AI!
  ✅ ClaudeBot consentito ✓
  ✅ PerplexityBot consentito ✓
  ...

📊 GEO SCORE FINALE
  [███████████░░░░░░░░░] 55/100
  ⚠️  SUFFICIENTE — Implementa le ottimizzazioni mancanti
```

### 3. Genera llms.txt
```bash
python scripts/generate_llms_txt.py \
  --base-url https://tuosito.com \
  --output ./public/llms.txt
```

### 4. Genera schema JSON-LD
```bash
# Analizza file HTML esistente
python scripts/schema_injector.py --file index.html --analyze

# Genera snippet WebSite
python scripts/schema_injector.py --type website --name "MioSito" --url https://tuosito.com

# Genera snippet Astro
python scripts/schema_injector.py --type website --url https://tuosito.com --astro
```

---

## 📋 Workflow GEO in 4 Step

### Step 1 — Audit 🔍
Esegui `geo_audit.py` per scoprire cosa manca.

### Step 2 — robots.txt 🤖
Aggiungi tutti i bot AI search al robots.txt:
```
User-agent: OAI-SearchBot
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: Google-Extended
Allow: /
```
> Lista completa in [`references/ai-bots-list.md`](references/ai-bots-list.md)

### Step 3 — llms.txt 📋
Crea `/llms.txt` alla root del sito (come robots.txt ma per AI):
```markdown
# Nome Sito

> Descrizione breve per LLM

## Strumenti

- [Tool 1](https://tuosito.com/tool): Descrizione

## Optional

- [About](https://tuosito.com/about)
```
> Spec: https://llmstxt.org

### Step 4 — Schema JSON-LD 🏗️
Aggiungi schema strutturato nell'`<head>`:
- **WebSite** — globale su tutte le pagine
- **WebApplication** — su ogni tool/calcolatore
- **FAQPage** — con domande frequenti → massima probabilità di citazione AI
> Template in [`references/schema-templates.md`](references/schema-templates.md)

---

## 🔬 I 9 Metodi Princeton GEO

| # | Metodo | Impatto AI | Priorità |
|---|--------|-----------|----------|
| 1 | **Cite Sources** | +30-115% | 🔴 Alta |
| 2 | **Statistics** | +40% | 🔴 Alta |
| 3 | **Quotation Addition** | +30-40% | 🟠 Media |
| 4 | **Authoritative** | +6-12% | 🟠 Media |
| 5 | **Fluency Optimization** | +15-30% | 🟡 Media |
| 6 | **Easy-to-Understand** | +8-15% | 🟡 Bassa |
| 7 | **Technical Terms** | +5-10% | 🟢 Bassa |
| 8 | **Unique Words** | +5-8% | 🟢 Bassa |
| 9 | **Keyword Stuffing** | ≈0% ⚠️ | ❌ Evitare |

> Dettaglio completo in [`references/princeton-geo-methods.md`](references/princeton-geo-methods.md)

---

## 🤖 Bot AI Supportati

| Bot | Vendor | Scopo |
|-----|--------|-------|
| `OAI-SearchBot` | OpenAI | ChatGPT Search — citazioni |
| `GPTBot` | OpenAI | Training modelli |
| `ClaudeBot` | Anthropic | Claude — citazioni |
| `anthropic-ai` | Anthropic | Training Claude |
| `PerplexityBot` | Perplexity | Index AI search |
| `Google-Extended` | Google | Gemini + AI Overviews |
| `Bingbot` | Microsoft | Copilot |
| `Applebot-Extended` | Apple | Apple Intelligence |
| `cohere-ai` | Cohere | Modelli Cohere |
| `DuckAssistBot` | DuckDuckGo | DuckAssist AI |
| + 15 altri... | | |

> Lista completa in [`references/ai-bots-list.md`](references/ai-bots-list.md)

---

## 🛠️ Script Reference

### `geo_audit.py`
```
usage: geo_audit.py [--url URL] [--verbose]

Controlla:
  - robots.txt: 13 AI bots
  - llms.txt: presenza e qualità
  - Schema JSON-LD: WebSite, WebApp, FAQPage
  - Meta tags: description, canonical, OG
  - Content: headings, numeri, link esterni

Output: Report con ✅/❌/⚠️ + GEO Score /100
```

### `generate_llms_txt.py`
```
usage: generate_llms_txt.py --base-url URL [--output FILE]
                             [--sitemap URL] [--site-name NAME]
                             [--description TEXT] [--max-per-section N]

Features:
  - Auto-detect sitemap da robots.txt
  - Supporta sitemap index (multi-sitemap)
  - Raggruppa URL per categoria automaticamente
  - Genera sezioni markdown strutturate
  - Gestisce "Optional" section per contenuti secondari
```

### `schema_injector.py`
```
usage: schema_injector.py [--file HTML] [--type TYPE]
                           [--name NAME] [--url URL]
                           [--description TEXT] [--astro]
                           [--inject] [--analyze]

Types: website, webapp, faq, article, organization, breadcrumb
```

---

## 📊 Caso Reale: CalcFast

Audit su [calcfast.online](https://calcfast.online) (Feb 2026):

```
GEO Score: 78/100 ✅ BUONO

✅ robots.txt con GPTBot, ClaudeBot, PerplexityBot, Google-Extended
✅ llms.txt presente (46 link, 6 sezioni)
✅ Schema WebSite + Organization + BreadcrumbList
✅ Meta description ottimizzata
✅ OG tags completi
❌ OAI-SearchBot mancante (critico per ChatGPT Search!)
⚠️ FAQPage schema mancante
```

---

## 📚 Risorse

- **Paper Princeton**: https://arxiv.org/abs/2311.09735
- **GEO-bench**: https://generative-engines.com/GEO/
- **llms.txt spec**: https://llmstxt.org
- **Schema.org**: https://schema.org
- **Schema Validator**: https://validator.schema.org

---

## 👤 Autore

**Juan Auriti**  
Web Developer | GEO Specialist  
📧 juancamilo.auriti@gmail.com  
🐙 [@auriti-web-design](https://github.com/auriti-web-design)

---

## 📄 Licenza

MIT License — libero uso, modifica e distribuzione.
