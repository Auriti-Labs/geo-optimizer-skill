# Schema JSON-LD Templates — Pronti all'uso

> Per GEO (Generative Engine Optimization): gli schema JSON-LD aiutano gli AI engines a capire il contenuto e citarlo correttamente.  
> Spec: https://schema.org | Validator: https://validator.schema.org

## Come usare questi template

1. Copia il template appropriato
2. Sostituisci i valori tra `<< >>`
3. Incolla nell'`<head>` della pagina HTML
4. Valida su https://validator.schema.org

---

## 1. WebSite — Template Globale

Va nell'`<head>` di **tutte le pagine** del sito (tipicamente nel layout principale).

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "<<Nome Sito>>",
  "url": "https://<<dominio.com>>",
  "description": "<<Descrizione breve del sito, cosa offre, a chi serve>>",
  "inLanguage": "it",
  "potentialAction": {
    "@type": "SearchAction",
    "target": {
      "@type": "EntryPoint",
      "urlTemplate": "https://<<dominio.com>>/search?q={search_term_string}"
    },
    "query-input": "required name=search_term_string"
  },
  "publisher": {
    "@type": "Organization",
    "name": "<<Nome Organizzazione>>",
    "url": "https://<<dominio.com>>"
  }
}
</script>
```

**Esempio CalcFast:**
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "CalcFast",
  "url": "https://calcfast.online",
  "description": "Calcolatori online gratuiti per finanza, matematica e salute. Calcola mutui, interessi, BMI e molto altro in pochi secondi.",
  "inLanguage": "it",
  "potentialAction": {
    "@type": "SearchAction",
    "target": "https://calcfast.online/search?q={search_term_string}",
    "query-input": "required name=search_term_string"
  }
}
</script>
```

---

## 2. WebApplication — Calcolatori e Tool

Da aggiungere su ogni pagina che è un **tool/calcolatore/app**.

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "<<Nome Calcolatore/Tool>>",
  "url": "https://<<dominio.com>>/<<pagina>>",
  "description": "<<Cosa calcola, come usarlo, per chi è utile>>",
  "applicationCategory": "UtilityApplication",
  "applicationSubCategory": "<<Finance|Health|Math|Science>>",
  "operatingSystem": "Web",
  "browserRequirements": "Requires JavaScript",
  "inLanguage": "it",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "EUR"
  },
  "featureList": [
    "<<Feature 1>>",
    "<<Feature 2>>",
    "<<Feature 3>>"
  ],
  "author": {
    "@type": "Organization",
    "name": "<<Nome Organizzazione>>"
  }
}
</script>
```

**Esempio Calcolatore Mutuo:**
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "Calcolatore Mutuo",
  "url": "https://calcfast.online/finance/mutuo",
  "description": "Calcola la rata mensile del tuo mutuo inserendo importo, durata e tasso di interesse. Confronta mutuo a tasso fisso e variabile.",
  "applicationCategory": "UtilityApplication",
  "applicationSubCategory": "Finance",
  "operatingSystem": "Web",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "EUR"
  },
  "featureList": [
    "Calcolo rata mutuo tasso fisso",
    "Calcolo rata mutuo tasso variabile",
    "Piano di ammortamento completo",
    "Confronto tra opzioni"
  ]
}
</script>
```

---

## 3. FAQPage — Domande e Risposte

**Impatto GEO: alto** — gli AI engines usano questi schema per rispondere a domande.

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "<<Domanda 1?>>",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "<<Risposta completa e dettagliata alla domanda 1. Includi dati numerici se possibile.>>"
      }
    },
    {
      "@type": "Question",
      "name": "<<Domanda 2?>>",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "<<Risposta 2>>"
      }
    },
    {
      "@type": "Question",
      "name": "<<Domanda 3?>>",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "<<Risposta 3>>"
      }
    }
  ]
}
</script>
```

**Esempio Calcolatore Mutuo FAQ:**
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Come si calcola la rata del mutuo?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "La rata del mutuo si calcola con la formula dell'ammortamento alla francese: R = C × (i × (1+i)^n) / ((1+i)^n - 1), dove C è il capitale, i il tasso mensile, n il numero di rate. Per un mutuo da 200.000€ a 20 anni al 3%, la rata è circa 1.109€/mese."
      }
    },
    {
      "@type": "Question",
      "name": "Qual è la differenza tra tasso fisso e variabile?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Il tasso fisso rimane invariato per tutta la durata del mutuo, garantendo rate costanti e prevedibili. Il tasso variabile è collegato all'Euribor e può aumentare o diminuire nel tempo. Nel 2024, i tassi fissi si aggirano intorno al 3-4%, mentre i variabili dipendono dall'Euribor più lo spread bancario."
      }
    },
    {
      "@type": "Question",
      "name": "Quanto posso richiedere di mutuo?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Le banche tipicamente finanziano fino all'80% del valore dell'immobile (LTV 80%). Per un immobile da 250.000€, il mutuo massimo è solitamente 200.000€. La rata non dovrebbe superare il 30-35% del reddito netto mensile per essere sostenibile."
      }
    }
  ]
}
</script>
```

---

## 4. Article / BlogPosting

Per articoli del blog e contenuti informativi.

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "<<Titolo articolo (max 110 chars)>>",
  "description": "<<Descrizione breve (150-160 chars)>>",
  "url": "https://<<dominio.com>>/blog/<<slug>>",
  "datePublished": "<<YYYY-MM-DD>>",
  "dateModified": "<<YYYY-MM-DD>>",
  "inLanguage": "it",
  "author": {
    "@type": "Person",
    "name": "<<Nome Autore>>",
    "url": "https://<<dominio.com>>/author/<<slug>>"
  },
  "publisher": {
    "@type": "Organization",
    "name": "<<Nome Sito>>",
    "url": "https://<<dominio.com>>",
    "logo": {
      "@type": "ImageObject",
      "url": "https://<<dominio.com>>/logo.png"
    }
  },
  "image": {
    "@type": "ImageObject",
    "url": "https://<<dominio.com>>/images/<<articolo.jpg>>",
    "width": 1200,
    "height": 630
  },
  "mainEntityOfPage": {
    "@type": "WebPage",
    "@id": "https://<<dominio.com>>/blog/<<slug>>"
  }
}
</script>
```

---

## 5. HowTo — Guide Pratiche

Per guide passo-passo. **Molto citato dagli AI engines** per query "come fare".

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "HowTo",
  "name": "Come <<fare qualcosa>>",
  "description": "<<Descrizione della guida>>",
  "totalTime": "PT<<N>>M",
  "tool": [
    {
      "@type": "HowToTool",
      "name": "<<Tool necessario>>"
    }
  ],
  "step": [
    {
      "@type": "HowToStep",
      "position": 1,
      "name": "<<Nome Step 1>>",
      "text": "<<Descrizione dettagliata del passo 1>>",
      "url": "https://<<dominio.com>>/guida#step1"
    },
    {
      "@type": "HowToStep",
      "position": 2,
      "name": "<<Nome Step 2>>",
      "text": "<<Descrizione dettagliata del passo 2>>"
    }
  ]
}
</script>
```

---

## 6. Organization — Chi Siamo

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "<<Nome Organizzazione>>",
  "url": "https://<<dominio.com>>",
  "description": "<<Descrizione organizzazione>>",
  "logo": {
    "@type": "ImageObject",
    "url": "https://<<dominio.com>>/logo.png"
  },
  "contactPoint": {
    "@type": "ContactPoint",
    "email": "<<email@dominio.com>>",
    "contactType": "customer support"
  },
  "sameAs": [
    "https://twitter.com/<<handle>>",
    "https://linkedin.com/company/<<company>>",
    "https://github.com/<<org>>"
  ]
}
</script>
```

---

## 7. BreadcrumbList — Navigazione

Aiuta gli AI a capire la struttura del sito.

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {
      "@type": "ListItem",
      "position": 1,
      "name": "Home",
      "item": "https://<<dominio.com>>"
    },
    {
      "@type": "ListItem",
      "position": 2,
      "name": "<<Categoria>>",
      "item": "https://<<dominio.com>>/<<categoria>>"
    },
    {
      "@type": "ListItem",
      "position": 3,
      "name": "<<Pagina corrente>>",
      "item": "https://<<dominio.com>>/<<categoria>>/<<pagina>>"
    }
  ]
}
</script>
```

---

## 8. Product — Prodotti/Servizi

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "<<Nome Prodotto/Servizio>>",
  "description": "<<Descrizione>>",
  "url": "https://<<dominio.com>>/prodotti/<<slug>>",
  "offers": {
    "@type": "Offer",
    "price": "<<prezzo>>",
    "priceCurrency": "EUR",
    "availability": "https://schema.org/InStock",
    "url": "https://<<dominio.com>>/prodotti/<<slug>>"
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.8",
    "reviewCount": "<<numero_recensioni>>"
  }
}
</script>
```

---

## Multi-Schema — Combinare più tipi

**Best practice**: puoi mettere più schema JSON-LD nella stessa pagina.

```html
<!-- Schema 1: WebSite globale -->
<script type="application/ld+json">
{ "@context": "https://schema.org", "@type": "WebSite", ... }
</script>

<!-- Schema 2: WebApplication per questa pagina -->
<script type="application/ld+json">
{ "@context": "https://schema.org", "@type": "WebApplication", ... }
</script>

<!-- Schema 3: FAQPage con domande frequenti -->
<script type="application/ld+json">
{ "@context": "https://schema.org", "@type": "FAQPage", ... }
</script>

<!-- Schema 4: BreadcrumbList per navigazione -->
<script type="application/ld+json">
{ "@context": "https://schema.org", "@type": "BreadcrumbList", ... }
</script>
```

---

## Implementazione Astro (TypeScript)

```astro
---
// types per schema
interface FAQItem {
  question: string;
  answer: string;
}

interface LayoutProps {
  title: string;
  description: string;
  url?: string;
  isCalculator?: boolean;
  faqItems?: FAQItem[];
  articleDate?: string;
}

const { title, description, url = Astro.url.href, isCalculator, faqItems = [], articleDate } = Astro.props;
---

<head>
  <!-- WebSite (sempre) -->
  <script type="application/ld+json" set:html={JSON.stringify({
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "CalcFast",
    "url": "https://calcfast.online",
    "description": "Calcolatori online gratuiti"
  })} />

  <!-- WebApplication (solo calcolatori) -->
  {isCalculator && (
    <script type="application/ld+json" set:html={JSON.stringify({
      "@context": "https://schema.org",
      "@type": "WebApplication",
      "name": title,
      "url": url,
      "description": description,
      "applicationCategory": "UtilityApplication",
      "offers": { "@type": "Offer", "price": "0", "priceCurrency": "EUR" }
    })} />
  )}

  <!-- FAQPage (se ci sono FAQ) -->
  {faqItems.length > 0 && (
    <script type="application/ld+json" set:html={JSON.stringify({
      "@context": "https://schema.org",
      "@type": "FAQPage",
      "mainEntity": faqItems.map(item => ({
        "@type": "Question",
        "name": item.question,
        "acceptedAnswer": { "@type": "Answer", "text": item.answer }
      }))
    })} />
  )}

  <!-- BreadcrumbList (sempre) -->
  <script type="application/ld+json" set:html={JSON.stringify({
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      { "@type": "ListItem", "position": 1, "name": "Home", "item": "https://calcfast.online" },
      { "@type": "ListItem", "position": 2, "name": title, "item": url }
    ]
  })} />
</head>
```

---

## Validator e Tool Utili

| Tool | URL | Scopo |
|------|-----|-------|
| Schema Validator | https://validator.schema.org | Valida JSON-LD |
| Rich Results Test | https://search.google.com/test/rich-results | Test Google |
| Structured Data Testing | https://developers.google.com/search/docs/appearance/structured-data | Docs |
| JSON-LD Playground | https://json-ld.org/playground/ | Test interattivo |

---

## Priorità per GEO

1. **FAQPage** — massima probabilità di essere estratto per domande AI
2. **WebApplication** — identifica chiaramente i tool
3. **WebSite** — fondamentale per entity understanding
4. **Article** — per contenuti blog
5. **HowTo** — per guide pratiche
