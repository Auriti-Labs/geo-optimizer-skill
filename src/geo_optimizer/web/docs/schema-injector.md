# Schema Injector

`geo schema` generates and injects JSON-LD structured data into HTML pages. It supports multiple schema types, framework-specific output, and in-place file injection.

---

## What is JSON-LD Schema?

JSON-LD (JavaScript Object Notation for Linked Data) is a format for embedding machine-readable metadata in HTML pages. You add it inside a `<script type="application/ld+json">` tag in your `<head>`.

AI search engines read JSON-LD schema to understand:
- What type of page this is (tool, article, FAQ, organization)
- What the page is about, without parsing the full body text
- How to extract structured answers (especially from FAQPage)

Without schema, AI engines have to guess your content's meaning. With schema, you tell them directly.

---

## The 3 Most Important Schema Types for GEO

| Schema | GEO Priority | Where to use |
|--------|-------------|--------------|
| **FAQPage** | 🔴 Highest | Any page with Q&A, how-to, explainer content |
| **WebApplication** | 🟠 High | Every tool, calculator, or interactive page |
| **WebSite** | 🟡 Baseline | Global layout — all pages |

FAQPage has the highest GEO impact because AI engines directly extract Q&A pairs to answer user questions — and cite your page as the source.

---

## Usage

```bash
# Analyze an HTML file — see what schema is present and what's missing
geo schema --file index.html --analyze

# Generate WebSite schema (print to stdout)
geo schema --type website --name "MySite" --url https://yoursite.com

# Generate FAQPage schema from a JSON file
geo schema --type faq --faq-file faqs.json

# Inject schema directly into an HTML file (creates .bak backup first)
geo schema --file page.html --type website --name "MySite" --url https://yoursite.com --inject

# Generate Astro BaseLayout snippet
geo schema --type website --name "MySite" --url https://yoursite.com --astro
```

---

## All Flags

| Flag | Description |
|------|-------------|
| `--file` | Path to the HTML file to analyze or inject into |
| `--analyze` | Analyze `--file` and print what schema is present / missing |
| `--type` | Schema type to generate: `website`, `webapp`, `faq`, `article`, `organization`, `breadcrumb` |
| `--name` | Site or page name |
| `--url` | Canonical URL |
| `--description` | Short description |
| `--inject` | Inject generated schema directly into `--file` (modifies in place) |
| `--faq-file` | Path to a JSON file with Q&A pairs (for `--type faq`) |
| `--astro` | Output an Astro component snippet instead of raw HTML |

---

## Flag: --analyze

Analyzes an existing HTML file and reports which schema types are present and which are missing.

```bash
geo schema --file index.html --analyze
```

Example output:

```
Analyzing: index.html
─────────────────────────────────
✅ WebSite schema found
❌ FAQPage schema missing      ← high GEO impact
❌ WebApplication schema missing
❌ Article schema missing

Suggestion: Add FAQPage schema — highest impact for AI citation visibility.
Run: geo schema --file index.html --type faq --faq-file faqs.json --inject
```

---

## Flag: --type

Generates a specific schema type. Prints JSON-LD to stdout by default; combine with `--inject` to write directly to the file.

```bash
# WebSite
geo schema --type website --name "MySite" --url https://yoursite.com --description "Free calculators"

# WebApplication
geo schema --type webapp --name "Mortgage Calculator" --url https://yoursite.com/mortgage --description "Calculate monthly payments"

# FAQPage (from --faq-file)
geo schema --type faq --faq-file faqs.json

# Organization
geo schema --type organization --name "MySite" --url https://yoursite.com

# Article
geo schema --type article --name "What is GEO?" --url https://yoursite.com/blog/geo --description "Introduction to GEO"

# BreadcrumbList
geo schema --type breadcrumb --url https://yoursite.com/finance/mortgage
```

---

## Flag: --astro

Generates a ready-to-paste snippet for Astro `BaseLayout.astro`. Supports conditional rendering based on props.

```bash
geo schema --type website --name "MySite" --url https://yoursite.com --astro
```

Output — complete Astro layout snippet:

```astro
---
// Types
interface FAQItem {
  question: string;
  answer: string;
}

interface Props {
  title: string;
  description: string;
  url?: string;
  isCalculator?: boolean;
  faqItems?: FAQItem[];
}

const {
  title,
  description,
  url = Astro.url.href,
  isCalculator = false,
  faqItems = [],
} = Astro.props;

const SITE_NAME = "MySite";
const SITE_URL = "https://yoursite.com";
---

<head>
  <meta charset="UTF-8" />
  <title>{title}</title>
  <meta name="description" content={description} />
  <link rel="canonical" href={url} />

  <!-- WebSite schema (all pages) -->
  <script type="application/ld+json" set:html={JSON.stringify({
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": SITE_NAME,
    "url": SITE_URL,
    "description": description,
  })} />

  <!-- WebApplication schema (calculator pages only) -->
  {isCalculator && (
    <script type="application/ld+json" set:html={JSON.stringify({
      "@context": "https://schema.org",
      "@type": "WebApplication",
      "name": title,
      "url": url,
      "description": description,
      "applicationCategory": "UtilityApplication",
      "operatingSystem": "Web",
      "offers": { "@type": "Offer", "price": "0", "priceCurrency": "USD" },
    })} />
  )}

  <!-- FAQPage schema (pages with FAQ content) -->
  {faqItems.length > 0 && (
    <script type="application/ld+json" set:html={JSON.stringify({
      "@context": "https://schema.org",
      "@type": "FAQPage",
      "mainEntity": faqItems.map(item => ({
        "@type": "Question",
        "name": item.question,
        "acceptedAnswer": { "@type": "Answer", "text": item.answer },
      })),
    })} />
  )}
</head>
```

Use it in a page:

```astro
---
import BaseLayout from '../layouts/BaseLayout.astro';

const faqItems = [
  {
    question: "How is the monthly mortgage payment calculated?",
    answer: "The formula is M = P × (r(1+r)^n) / ((1+r)^n - 1), where P is the principal, r is the monthly rate, and n is the total number of payments.",
  },
  {
    question: "What is the difference between fixed and adjustable rates?",
    answer: "A fixed rate stays constant for the life of the loan. An adjustable rate is tied to a market index and can change periodically, usually after an initial fixed period.",
  },
];
---

<BaseLayout
  title="Mortgage Calculator"
  description="Calculate your monthly mortgage payment instantly."
  isCalculator={true}
  faqItems={faqItems}
/>
```

---

## Flag: --inject

Injects the generated schema directly into the HTML file, inserting it before `</head>`. A backup (`.bak`) is created automatically.

```bash
geo schema \
  --file index.html \
  --type faq \
  --faq-file faqs.json \
  --inject
```

Output:

```
✅ Backup created: index.html.bak
✅ FAQPage schema injected into index.html (before </head>)
```

If the file has no `</head>` tag, injection fails gracefully with an error. See [Troubleshooting](troubleshooting.md#9-inject-failed-no-head-tag) for the fix.

---

## Flag: --faq-file

Reads Q&A pairs from a JSON file to generate FAQPage schema.

Format of `faqs.json`:

```json
[
  {
    "question": "How is the monthly mortgage payment calculated?",
    "answer": "The standard formula is M = P × (r(1+r)^n) / ((1+r)^n - 1). For a $200,000 loan at 6% over 30 years, the monthly payment is $1,199."
  },
  {
    "question": "What is LTV (Loan-to-Value) ratio?",
    "answer": "LTV measures how much of the property value you are financing. An LTV of 80% means you are borrowing 80% and providing 20% as a down payment."
  },
  {
    "question": "Should I choose a fixed or variable rate?",
    "answer": "Fixed rates offer payment stability for the full term. Variable rates may start lower but change with market benchmarks like SOFR. Choose fixed if you expect rates to rise or prefer predictability."
  }
]
```

```bash
geo schema --type faq --faq-file faqs.json
```

---

## Framework Examples

### Astro — Full Integration

See the `--astro` section above. Pass `isCalculator={true}` for tool pages and `faqItems={[...]}` for pages with Q&A.

### Next.js (App Router)

In `app/layout.tsx` (WebSite schema on all pages):

```typescript
export default function RootLayout({ children }: { children: React.ReactNode }) {
  const websiteSchema = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "MySite",
    "url": "https://yoursite.com",
    "description": "Free online tools and calculators",
  };

  return (
    <html lang="en">
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteSchema) }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
```

In a tool page (WebApplication + FAQPage):

```typescript
export default function MortgagePage() {
  const appSchema = {
    "@context": "https://schema.org",
    "@type": "WebApplication",
    "name": "Mortgage Calculator",
    "url": "https://yoursite.com/mortgage",
    "description": "Calculate monthly mortgage payments for fixed and variable rates.",
    "applicationCategory": "UtilityApplication",
    "operatingSystem": "Web",
    "offers": { "@type": "Offer", "price": "0", "priceCurrency": "USD" },
  };

  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
      {
        "@type": "Question",
        "name": "How is a mortgage payment calculated?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "Using the formula M = P × (r(1+r)^n) / ((1+r)^n - 1), where P is the loan amount, r the monthly rate, and n the number of payments.",
        },
      },
    ],
  };

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(appSchema) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }} />
      {/* page content */}
    </>
  );
}
```

### WordPress — functions.php

Add WebSite schema to all pages and FAQPage to pages with an FAQ section:

```php
function add_geo_schema() {
    $schema = [
        '@context' => 'https://schema.org',
        '@type'    => 'WebSite',
        'name'     => get_bloginfo('name'),
        'url'      => home_url('/'),
        'description' => get_bloginfo('description'),
    ];
    echo '<script type="application/ld+json">' . wp_json_encode($schema) . '</script>' . "\n";
}
add_action('wp_head', 'add_geo_schema');
```

For FAQPage on specific pages, use a custom field or ACF repeater to store Q&A pairs and output them similarly.

### HTML Static — Manual

Add directly in the `<head>` of your HTML file:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>My Page</title>

  <!-- WebSite schema -->
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "MySite",
    "url": "https://yoursite.com",
    "description": "Free online calculators"
  }
  </script>

  <!-- FAQPage schema -->
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
      {
        "@type": "Question",
        "name": "Your question here?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "Your answer here, with specific details and numbers."
        }
      }
    ]
  }
  </script>
</head>
```

---

## FAQPage Best Practices

**How many questions?**
- Minimum: 3 questions per page
- Optimal: 5–8 questions
- Maximum: 15 (more than 15 dilutes individual question weight)

**How to write questions for maximum GEO impact:**
- Write them as real user queries: *"How is X calculated?"* not *"X calculation"*
- Be specific: *"What is the LTV ratio and how does it affect my mortgage?"* not *"What is LTV?"*
- Include numbers in answers: *"A typical LTV is 80%, meaning you borrow 80% of the property value"*
- Keep answers 2–5 sentences. Long answers reduce extraction clarity.
- Include at least one statistic or concrete example in each answer

**What makes an answer extractable by AI:**
- Starts with a direct answer to the question (not a preamble)
- Includes a specific number, formula, or comparison
- Self-contained — can be understood without reading the rest of the page

**Validate your schema:**

```bash
# Google's validator
open https://validator.schema.org
# Paste your JSON-LD or enter your URL
```
