/**
 * Curated AI-discovery content — single source for the machine-readable files
 * the astro-geoready integration emits at build time (/ai/faq.json,
 * /ai/service.json). Kept as plain .mjs so both astro.config.mjs and the
 * integration can import it without a TypeScript build step.
 *
 * Keep these answer-shaped and factual: AI answer engines lift them verbatim.
 */

/** Product-level FAQ. `q`/`a` shape matches the on-page FAQPage schema arrays. */
export const aiFaqs = [
  {
    q: 'What is GeoReady?',
    a: 'GeoReady is an AI visibility audit and monitoring platform. It scores any website 0-100 across 8 categories for how discoverable, readable, and citable it is to AI answer engines like ChatGPT, Perplexity, Claude, and Gemini, and tells you exactly what to fix. It is built on the open-source GEO Optimizer engine.',
  },
  {
    q: 'Is the free audit really free?',
    a: 'Yes. The web audit requires no account, no credit card, and no signup. You get a full GEO score and three category breakdowns immediately. The CLI is MIT-licensed and free to use without limits.',
  },
  {
    q: 'What does the free plan include for monitoring?',
    a: 'The free plan monitors one domain on a weekly schedule and emails you when its GEO score drifts significantly. Paid plans add more monitored domains, daily checks, the full 8-category report, and granular per-signal regression alerts.',
  },
  {
    q: 'What does Pro add that Free does not?',
    a: 'Pro adds depth and breadth: up to 10 monitored domains, daily checks, the full 8-category report, granular regression alerts on every signal (not just overall drift), PDF export, and API access.',
  },
  {
    q: 'How does GeoReady check if AI engines cite my site?',
    a: 'GeoReady runs a citation check that asks an AI answer engine the questions your customers ask, then reports whether your brand is mentioned and your domain is cited as a source, plus which competitor domains get cited instead. It uses Perplexity Sonar for real web-grounded citations.',
  },
  {
    q: 'Are paid plans available right now?',
    a: 'Yes. Pick a plan, create an account, and pay — your subscription is active immediately. No sales call, no waitlist. Payments are processed securely by Stripe.',
  },
  {
    q: 'Will the CLI remain open source?',
    a: 'Yes. The CLI (geo-optimizer-skill on PyPI) is MIT-licensed and will remain free forever. SaaS plans add server-side continuity features the CLI cannot provide on its own.',
  },
  {
    q: 'Can I cancel at any time?',
    a: 'Yes. You can cancel from your account settings at any time, with no lock-in or penalties.',
  },
];

/** Service/offer descriptor. Mirrors the public pricing tiers. */
export const aiService = {
  type: 'AI visibility audit, monitoring, and citation tracking',
  provider: 'Auriti Labs',
  features: [
    'GEO score 0-100 across 8 research-backed categories',
    'Free one-shot web audit, no account required',
    'Free weekly monitoring for one domain with drift email',
    'Full 8-category report and fix recommendations (Pro+)',
    'AI citation tracking via Perplexity Sonar',
    'Open-source CLI engine (geo-optimizer-skill, MIT)',
  ],
  offers: [
    { plan: 'Free', price: '0', priceCurrency: 'EUR', description: '1 monitored domain, weekly drift email, 3-of-8 report' },
    { plan: 'Pro', price: '19', priceCurrency: 'EUR', billingPeriod: 'month', description: '10 domains, daily checks, full report, alerts, API' },
    { plan: 'Studio', price: '49', priceCurrency: 'EUR', billingPeriod: 'month', description: '15 domains, AI snapshots, batch audit, history' },
    { plan: 'Agency', price: '89', priceCurrency: 'EUR', billingPeriod: 'month', description: '50 domains, team workspace, multi-client' },
  ],
};
