# Schema JSON-LD Templates — Ready to Use

> For GEO (Generative Engine Optimization): JSON-LD schema helps AI engines understand your content and cite it correctly.  
> Spec: https://schema.org | Validator: https://validator.schema.org

## How to use these templates

1. Copy the appropriate template
2. Replace values marked with `YOUR_VALUE`
3. For `YOUR_LANGUAGE_CODE` use an [ISO 639-1 code](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes): `"en"`, `"it"`, `"fr"`, `"de"`, `"es"`, etc.
4. Paste into the `<head>` of your HTML page
4. Validate at https://validator.schema.org

---

## 1. WebSite — Global Template

Goes in the `<head>` of **all pages** on the site (typically in the main layout).

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "YOUR_SITE_NAME",
  "url": "https://YOUR_DOMAIN",
  "description": "YOUR_SITE_DESCRIPTION",
  "inLanguage": "YOUR_LANGUAGE_CODE",
  "potentialAction": {
    "@type": "SearchAction",
    "target": {
      "@type": "EntryPoint",
      "urlTemplate": "https://YOUR_DOMAIN/search?q={search_term_string}"
    },
    "query-input": "required name=search_term_string"
  },
  "publisher": {
    "@type": "Organization",
    "name": "YOUR_ORGANIZATION_NAME",
    "url": "https://YOUR_DOMAIN"
  }
}
</script>
```

**Example:**
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "MySite",
  "url": "https://example.com",
  "description": "Free online calculators for finance, math, and health. Calculate mortgages, interest, BMI, and much more in seconds.",
  "inLanguage": "YOUR_LANGUAGE_CODE",
  "potentialAction": {
    "@type": "SearchAction",
    "target": "https://example.com/search?q={search_term_string}",
    "query-input": "required name=search_term_string"
  }
}
</script>
```

---

## 2. WebApplication — Calculators and Tools

Add this to every page that is a **tool/calculator/app**.

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "YOUR_TOOL_NAME",
  "url": "https://YOUR_DOMAIN/YOUR_PAGE",
  "description": "YOUR_TOOL_DESCRIPTION",
  "applicationCategory": "UtilityApplication",
  "applicationSubCategory": "YOUR_SUBCATEGORY",
  "operatingSystem": "Web",
  "browserRequirements": "Requires JavaScript",
  "inLanguage": "YOUR_LANGUAGE_CODE",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "USD"
  },
  "featureList": [
    "YOUR_FEATURE_1",
    "YOUR_FEATURE_2",
    "YOUR_FEATURE_3"
  ],
  "author": {
    "@type": "Organization",
    "name": "YOUR_ORGANIZATION_NAME"
  }
}
</script>
```

**Example — Mortgage Calculator:**
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "Mortgage Calculator",
  "url": "https://example.com/finance/mortgage",
  "description": "Calculate your monthly mortgage payment by entering the amount, term, and interest rate. Compare fixed-rate and adjustable-rate mortgages.",
  "applicationCategory": "UtilityApplication",
  "applicationSubCategory": "Finance",
  "operatingSystem": "Web",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "USD"
  },
  "featureList": [
    "Fixed-rate mortgage calculation",
    "Adjustable-rate mortgage calculation",
    "Full amortization schedule",
    "Comparison between options"
  ]
}
</script>
```

---

## 3. FAQPage — Questions and Answers

**GEO impact: high** — AI engines use these schemas to answer questions.

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "YOUR_QUESTION_1",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "YOUR_ANSWER_1"
      }
    },
    {
      "@type": "Question",
      "name": "YOUR_QUESTION_2",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "YOUR_ANSWER_2"
      }
    },
    {
      "@type": "Question",
      "name": "YOUR_QUESTION_3",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "YOUR_ANSWER_3"
      }
    }
  ]
}
</script>
```

**Example — Mortgage Calculator FAQ:**
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "How is the mortgage payment calculated?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "The mortgage payment is calculated using the standard amortization formula: M = P × (r × (1+r)^n) / ((1+r)^n - 1), where P is the principal, r is the monthly rate, and n is the number of payments. For a $200,000 mortgage over 20 years at 3%, the monthly payment is approximately $1,109."
      }
    },
    {
      "@type": "Question",
      "name": "What is the difference between a fixed-rate and adjustable-rate mortgage?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "A fixed rate stays the same for the entire loan term, guaranteeing stable and predictable payments. An adjustable rate is tied to a market index (such as SOFR) and can increase or decrease over time. In 2024, fixed rates are around 6–7%, while adjustable rates depend on the index plus a bank spread."
      }
    },
    {
      "@type": "Question",
      "name": "How much mortgage can I qualify for?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Lenders typically finance up to 80% of the property value (LTV 80%). For a $300,000 home, the maximum mortgage is usually $240,000. The monthly payment should not exceed 28–36% of gross monthly income to remain affordable."
      }
    }
  ]
}
</script>
```

---

## 4. Article / BlogPosting

For blog articles and informational content.

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "YOUR_ARTICLE_TITLE",
  "description": "YOUR_ARTICLE_DESCRIPTION",
  "url": "https://YOUR_DOMAIN/blog/YOUR_SLUG",
  "datePublished": "YYYY-MM-DD",
  "dateModified": "YYYY-MM-DD",
  "inLanguage": "YOUR_LANGUAGE_CODE",
  "author": {
    "@type": "Person",
    "name": "YOUR_AUTHOR_NAME",
    "url": "https://YOUR_DOMAIN/author/YOUR_AUTHOR_SLUG"
  },
  "publisher": {
    "@type": "Organization",
    "name": "YOUR_SITE_NAME",
    "url": "https://YOUR_DOMAIN",
    "logo": {
      "@type": "ImageObject",
      "url": "https://YOUR_DOMAIN/logo.png"
    }
  },
  "image": {
    "@type": "ImageObject",
    "url": "https://YOUR_DOMAIN/images/YOUR_IMAGE.jpg",
    "width": 1200,
    "height": 630
  },
  "mainEntityOfPage": {
    "@type": "WebPage",
    "@id": "https://YOUR_DOMAIN/blog/YOUR_SLUG"
  }
}
</script>
```

---

## 5. HowTo — Step-by-Step Guides

For step-by-step guides. **Frequently cited by AI engines** for "how to" queries.

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "HowTo",
  "name": "How to YOUR_TASK",
  "description": "YOUR_GUIDE_DESCRIPTION",
  "totalTime": "PTXM",
  "tool": [
    {
      "@type": "HowToTool",
      "name": "YOUR_REQUIRED_TOOL"
    }
  ],
  "step": [
    {
      "@type": "HowToStep",
      "position": 1,
      "name": "YOUR_STEP_1_NAME",
      "text": "YOUR_STEP_1_DESCRIPTION",
      "url": "https://YOUR_DOMAIN/guide#step1"
    },
    {
      "@type": "HowToStep",
      "position": 2,
      "name": "YOUR_STEP_2_NAME",
      "text": "YOUR_STEP_2_DESCRIPTION"
    }
  ]
}
</script>
```

---

## 6. Organization — About Us

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "YOUR_ORGANIZATION_NAME",
  "url": "https://YOUR_DOMAIN",
  "description": "YOUR_ORGANIZATION_DESCRIPTION",
  "logo": {
    "@type": "ImageObject",
    "url": "https://YOUR_DOMAIN/logo.png"
  },
  "contactPoint": {
    "@type": "ContactPoint",
    "email": "YOUR_EMAIL@YOUR_DOMAIN",
    "contactType": "customer support"
  },
  "sameAs": [
    "https://twitter.com/YOUR_HANDLE",
    "https://linkedin.com/company/YOUR_COMPANY",
    "https://github.com/YOUR_ORG"
  ]
}
</script>
```

---

## 7. BreadcrumbList — Navigation

Helps AI understand the site structure.

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
      "item": "https://YOUR_DOMAIN"
    },
    {
      "@type": "ListItem",
      "position": 2,
      "name": "YOUR_CATEGORY",
      "item": "https://YOUR_DOMAIN/YOUR_CATEGORY"
    },
    {
      "@type": "ListItem",
      "position": 3,
      "name": "YOUR_CURRENT_PAGE",
      "item": "https://YOUR_DOMAIN/YOUR_CATEGORY/YOUR_PAGE"
    }
  ]
}
</script>
```

---

## 8. Product — Products/Services

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "YOUR_PRODUCT_NAME",
  "description": "YOUR_PRODUCT_DESCRIPTION",
  "url": "https://YOUR_DOMAIN/products/YOUR_SLUG",
  "offers": {
    "@type": "Offer",
    "price": "YOUR_PRICE",
    "priceCurrency": "USD",
    "availability": "https://schema.org/InStock",
    "url": "https://YOUR_DOMAIN/products/YOUR_SLUG"
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.8",
    "reviewCount": "YOUR_REVIEW_COUNT"
  }
}
</script>
```

---

## Multi-Schema — Combining Multiple Types

**Best practice**: you can include multiple JSON-LD schemas on the same page.

```html
<!-- Schema 1: Global WebSite -->
<script type="application/ld+json">
{ "@context": "https://schema.org", "@type": "WebSite", ... }
</script>

<!-- Schema 2: WebApplication for this page -->
<script type="application/ld+json">
{ "@context": "https://schema.org", "@type": "WebApplication", ... }
</script>

<!-- Schema 3: FAQPage with frequently asked questions -->
<script type="application/ld+json">
{ "@context": "https://schema.org", "@type": "FAQPage", ... }
</script>

<!-- Schema 4: BreadcrumbList for navigation -->
<script type="application/ld+json">
{ "@context": "https://schema.org", "@type": "BreadcrumbList", ... }
</script>
```

---

## Astro Implementation (TypeScript)

```astro
---
// Types for schema
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

const SITE_NAME = "MySite";
const SITE_URL = "https://example.com";
---

<head>
  <!-- WebSite (always) -->
  <script type="application/ld+json" set:html={JSON.stringify({
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": SITE_NAME,
    "url": SITE_URL,
    "description": "Free online tools and calculators"
  })} />

  <!-- WebApplication (calculators only) -->
  {isCalculator && (
    <script type="application/ld+json" set:html={JSON.stringify({
      "@context": "https://schema.org",
      "@type": "WebApplication",
      "name": title,
      "url": url,
      "description": description,
      "applicationCategory": "UtilityApplication",
      "offers": { "@type": "Offer", "price": "0", "priceCurrency": "USD" }
    })} />
  )}

  <!-- FAQPage (if FAQs are present) -->
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

  <!-- BreadcrumbList (always) -->
  <script type="application/ld+json" set:html={JSON.stringify({
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      { "@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL },
      { "@type": "ListItem", "position": 2, "name": title, "item": url }
    ]
  })} />
</head>
```

---

## Validators and Useful Tools

| Tool | URL | Purpose |
|------|-----|---------|
| Schema Validator | https://validator.schema.org | Validate JSON-LD |
| Rich Results Test | https://search.google.com/test/rich-results | Google test |
| Structured Data Testing | https://developers.google.com/search/docs/appearance/structured-data | Docs |
| JSON-LD Playground | https://json-ld.org/playground/ | Interactive test |

---

## GEO Priority

1. **FAQPage** — highest probability of being extracted for AI questions
2. **WebApplication** — clearly identifies tools
3. **WebSite** — fundamental for entity understanding
4. **Article** — for blog content
5. **HowTo** — for step-by-step guides
