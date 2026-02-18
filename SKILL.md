---
name: geo-optimizer
description: >
  Ottimizza siti web per essere citati dai motori di ricerca AI (ChatGPT, Perplexity, Claude, Gemini).
  Implementa GEO (Generative Engine Optimization) con i 9 metodi Princeton: audit automatico,
  generazione llms.txt, schema JSON-LD, robots.txt per AI bots. Aumenta visibilità AI fino al 40%.
  Trigger: "ottimizza per AI search", "GEO", "llms.txt", "visibilità AI", "citazioni AI",
  "generative engine optimization", "ChatGPT mi cita", "Perplexity ottimizzazione".
---

# GEO Optimizer — Generative Engine Optimization

> Basato sulla ricerca Princeton KDD 2024 "GEO: Generative Engine Optimization"  
> Autore skill: Juan Auriti (juancamilo.auriti@gmail.com)

## Cos'è il GEO?

GEO = ottimizzare contenuti web per **essere citati da AI search engines** (ChatGPT, Perplexity, Claude, Gemini) invece che solo rankare su Google tradizionale.

**Dati chiave (Princeton 2024):**
- Aggiungere statistiche e citazioni → **+40% visibilità** nelle risposte AI
- Cite Sources (citare fonti nel testo) → **fino a +115%** per certi rank positions  
- Ottimizzazione fluency → **+15-30%** visibilità media
- Testato su Perplexity.ai reale → **+37% visibilità** confermata

---

## Workflow in 4 Step

### STEP 1 — AUDIT 🔍

Esegui l'audit completo del sito:

```bash
cd /path/to/project
source /home/openclaw/.openclaw/workspace/.env/bin/activate
python /home/openclaw/.openclaw/workspace/skills/geo-optimizer/scripts/geo_audit.py --url https://tuosito.com
```

L'audit verifica:
- ✅/❌ robots.txt con tutti gli AI bots (GPTBot, ClaudeBot, PerplexityBot, ecc.)
- ✅/❌ Presenza di `/llms.txt`
- ✅/❌ Schema JSON-LD (WebSite, FAQPage, WebApplication)
- ✅/❌ Meta description, canonical URL, Open Graph tags
- ⚠️ Warning per configurazioni parziali

> Ref: [`references/ai-bots-list.md`](references/ai-bots-list.md) per tutti i bot AI

---

### STEP 2 — robots.txt 🤖

Aggiungi questi blocchi al `robots.txt` del sito (permetti tutti i bot AI search):

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
User-agent: PerplexityBot
Allow: /
User-agent: Bytespider
Allow: /
```

> Se vuoi **bloccare** il training (ma permettere citazioni), usa `Disallow: /` per `anthropic-ai` e `GPTBot`  
> ma `Allow: /` per `ClaudeBot`, `OAI-SearchBot` e `PerplexityBot`

---

### STEP 3 — llms.txt 📋

**Genera automaticamente da sitemap:**

```bash
python /home/openclaw/.openclaw/workspace/skills/geo-optimizer/scripts/generate_llms_txt.py \
  --base-url https://tuosito.com \
  --output ./public/llms.txt
```

**Oppure crea manualmente** il file `/llms.txt` seguendo questo template:

```markdown
# Nome Sito

> Breve descrizione del sito in 1-2 frasi. Cosa offre, a chi serve.

Dettagli aggiuntivi facoltativi sul progetto.

## Strumenti / Tools

- [Nome Tool](https://tuosito.com/tool): Descrizione breve

## Documentazione

- [Guida](https://tuosito.com/docs): Documentazione principale

## Blog / Articoli

- [Articolo 1](https://tuosito.com/blog/articolo): Descrizione

## Optional

- [Pagina secondaria](https://tuosito.com/about): Info opzionali
```

> Spec completa: https://llmstxt.org  
> Il file va a `/llms.txt` (root del sito, accanto a `robots.txt`)

---

### STEP 4 — Schema JSON-LD 🏗️

Aggiungi schema strutturato per aiutare gli AI a capire il contenuto.

**Template base (WebSite)** — va nell'`<head>` di tutte le pagine:

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "Nome Sito",
  "url": "https://tuosito.com",
  "description": "Descrizione del sito",
  "potentialAction": {
    "@type": "SearchAction",
    "target": "https://tuosito.com/search?q={search_term_string}",
    "query-input": "required name=search_term_string"
  }
}
</script>
```

**Per calcolatori/tool (WebApplication):**

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "Nome Calculator",
  "url": "https://tuosito.com/calculator",
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

**Per FAQ (FAQPage):**

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Domanda 1?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Risposta completa..."
      }
    }
  ]
}
</script>
```

> Template completi: [`references/schema-templates.md`](references/schema-templates.md)  
> Script automatico: `scripts/schema_injector.py`

---

## Metodi GEO Princeton (Priorità)

Implementa in ordine di impatto:

| # | Metodo | Impatto | Come |
|---|--------|---------|------|
| 1 | **Cite Sources** | +40% | Aggiungi link a fonti autorevoli nel testo |
| 2 | **Statistics** | +40% | Inserisci dati numerici concreti (%, €, date) |
| 3 | **Quotation Addition** | +30% | Cita esperti con virgolette |
| 4 | **Authoritative** | +15% | Tono da esperto, non generico |
| 5 | **Fluency Opt.** | +15-30% | Testo scorrevole, ben strutturato |
| 6 | **Easy-to-Understand** | +10% | Semplifica linguaggio complesso |
| 7 | **Technical Terms** | +8% | Usa terminologia settoriale corretta |
| 8 | **Unique Words** | +5% | Arricchisci vocabolario |
| 9 | **Keyword Stuffing** | ⚠️ | Non efficace, spesso negativo |

> Dettaglio completo: [`references/princeton-geo-methods.md`](references/princeton-geo-methods.md)

---

## Implementazione Astro (esempio CalcFast)

Per siti Astro, aggiungi nel `BaseLayout.astro`:

```astro
---
interface Props {
  title: string;
  description: string;
  isCalculator?: boolean;
  faqItems?: Array<{ question: string; answer: string }>;
}
const { title, description, isCalculator = false, faqItems = [] } = Astro.props;
---

<head>
  <!-- WebSite Schema (sempre) -->
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "CalcFast",
    "url": "https://calcfast.online"
  }
  </script>

  <!-- WebApplication Schema (solo calcolatori) -->
  {isCalculator && (
    <script type="application/ld+json">
    {JSON.stringify({
      "@context": "https://schema.org",
      "@type": "WebApplication",
      "name": title,
      "url": Astro.url.href
    })}
    </script>
  )}

  <!-- FAQPage Schema (se ci sono FAQ) -->
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

---

## Checklist GEO Completa

- [ ] robots.txt: tutti gli AI bots con `Allow: /`
- [ ] `/llms.txt` presente e strutturato
- [ ] Schema WebSite nell'`<head>` globale
- [ ] Schema WebApplication su pagine tool/calcolatori
- [ ] Schema FAQPage su pagine con domande/risposte
- [ ] Contenuti con statistiche numeriche concrete
- [ ] Citazioni di fonti autorevoli nel testo
- [ ] Meta description accurata e descrittiva
- [ ] Canonical URL su ogni pagina
- [ ] Open Graph tags (og:title, og:description, og:image)
- [ ] Testo fluente e ben strutturato con heading H1/H2/H3

---

## Script Disponibili

| Script | Uso |
|--------|-----|
| `scripts/geo_audit.py` | Audit completo con report ✅/❌/⚠️ |
| `scripts/generate_llms_txt.py` | Genera llms.txt da sitemap XML |
| `scripts/schema_injector.py` | Inietta schema JSON-LD in HTML/Astro |

## Riferimenti

| File | Contenuto |
|------|-----------|
| `references/princeton-geo-methods.md` | 9 metodi GEO con impatto e implementazione |
| `references/ai-bots-list.md` | Tutti i bot AI con user-agent e robots.txt snippet |
| `references/schema-templates.md` | Template JSON-LD pronti all'uso |
