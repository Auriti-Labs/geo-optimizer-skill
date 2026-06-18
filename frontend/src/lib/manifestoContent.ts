export interface ManifestoSection {
  id: string;
  number: string;
  title: string;
  intro?: string;
  paragraphs?: string[];
  items?: { title: string; description: string; points?: string[] }[];
  quote?: string;
  references?: { label: string; href: string }[];
}

export const manifestoSections: ManifestoSection[] = [
  {
    id: 'the-web-changed',
    number: '01',
    title: 'The web changed. Most websites do not know it yet.',
    paragraphs: [
      'The historic cycle of search — publish, index, click — is shifting. Generative systems like ChatGPT, Perplexity, and Claude synthesize answers instead of showing links.',
      'AI search engines are already changing how users discover and evaluate information. Most of the web remains invisible to these engines.',
    ],
  },
  {
    id: 'visibility-gap',
    number: '02',
    title: 'The visibility gap is a tooling problem.',
    paragraphs: [
      'Academic studies have quantified the factors that increase citations: source citations, inclusion of quotations, statistical claims, and authoritative prose.',
      'Yet these findings are trapped inside expensive, opaque enterprise platforms. Every piece of data analyzed is public and inspectable. The visibility gap is not a data problem. It is an access problem. It is a tooling problem.',
    ],
    quote: 'The visibility gap is not a data problem. It is an access problem. It is a tooling problem.',
    references: [
      {
        label: 'GEO: Generative Engine Optimization — KDD 2024',
        href: 'https://arxiv.org/abs/2311.09735',
      },
    ],
  },
  {
    id: 'values',
    number: '03',
    title: 'What GEO Optimizer stands for.',
    intro: 'Six guiding principles that define every design, architecture, and communication decision.',
    items: [
      {
        title: 'Auditability over opacity',
        description: 'Every calculation is documented and inspectable. No score originates from a black box.',
      },
      {
        title: 'Scientific foundation over marketing claims',
        description: 'Every signal derives from published peer-reviewed research, not marketing intuition.',
      },
      {
        title: 'Universality over platform bias',
        description: 'Compatible with any public URL. We neither reward nor penalize specific CMS or stacks.',
      },
      {
        title: 'Open source over gatekeeping',
        description: 'Algorithms, weights, and change history are public. Anyone can audit them.',
      },
      {
        title: 'Precision over noise',
        description: 'Every suggestion is concrete, actionable, and quantifiable in points. No generic lists.',
      },
      {
        title: 'Developer experience as a first-class concern',
        description: 'CLI before dashboard. JSON before PDF. API before widget. The tool must disappear into your workflow.',
      },
    ],
  },
  {
    id: 'eight-signals',
    number: '04',
    title: 'The eight signals that determine AI visibility.',
    intro: 'The maximum score is 100, distributed across eight documented signal categories.',
    items: [
      {
        title: 'robots.txt',
        description: 'Authorize AI crawlers such as OAI-SearchBot, ClaudeBot, Claude-SearchBot, and PerplexityBot.',
        points: ['Max 18 points'],
      },
      {
        title: 'llms.txt',
        description: 'Machine-readable standard proposed by Answer.AI; full score with a comprehensive document and llms-full.txt version.',
        points: ['Max 18 points'],
      },
      {
        title: 'Schema JSON-LD',
        description: 'Structured data for FAQ, Article, Organization, and WebSite schemas, with sameAs links.',
        points: ['Max 16 points'],
      },
      {
        title: 'Meta Tags',
        description: 'Descriptive title, accurate summary, canonical URL, and social sharing tags.',
        points: ['Max 14 points'],
      },
      {
        title: 'Content Quality',
        description: 'Concrete numbers, H2/H3 heading hierarchy, information in the first parts of the text, lists and tables, sufficient minimum length.',
        points: ['Max 12 points'],
      },
      {
        title: 'Technical Signals',
        description: 'Language declaration in the html element, RSS/Atom feeds, freshness indicators in headers or schema.',
        points: ['Max 6 points'],
      },
      {
        title: 'AI Discovery',
        description: 'Paths such as /.well-known/ai.txt, /ai/summary.json, /ai/faq.json, /ai/service.json.',
        points: ['Max 6 points'],
      },
      {
        title: 'Brand & Entity Signals',
        description: 'Brand name consistency, links to external knowledge graphs, contact pages, and geographic information.',
        points: ['Max 10 points'],
      },
    ],
  },
  {
    id: 'beyond-score',
    number: '04b',
    title: 'Beyond the score: what no competitor tells you.',
    intro: 'Six additional checks that do not affect the numeric score but determine real-world citability.',
    items: [
      {
        title: 'Prompt Injection Detection',
        description: 'Eight AI manipulation patterns (hidden text, invisible Unicode characters, direct LLM instructions, cloaking, micro-font, data attribute abuse, aria-hidden). Based on UC Berkeley EMNLP 2024.',
      },
      {
        title: 'Trust Stack Score',
        description: 'Composite evaluation across technical, identity, social, academic, and consistency dimensions. Grade A to F.',
      },
      {
        title: 'Negative Signals',
        description: 'Excessive CTAs, invasive popups, thin content, broken links, keyword stuffing, missing author, high boilerplate ratio, title-content mismatches.',
      },
      {
        title: 'CDN Crawler Access',
        description: 'Tests whether Cloudflare, Akamai, or Vercel protections silently block AI spiders despite a permissive robots.txt.',
      },
      {
        title: 'JS Rendering',
        description: 'Detects whether essential content requires JavaScript execution (React, Vue, Angular frameworks).',
      },
      {
        title: 'WebMCP Readiness',
        description: 'Measures exposure of machine-readable context for MCP-compatible agents, verifying patterns such as registerTool() and potentialAction schema.',
      },
    ],
  },
  {
    id: 'who-for',
    number: '05',
    title: 'Who this is for.',
    intro: 'GEO Optimizer is built for people who build the web, not just those who buy it.',
    items: [
      {
        title: 'Developers',
        description: 'Seeking visibility for their own projects without relying on opaque tools.',
      },
      {
        title: 'Agencies',
        description: 'With clients to position and reports to justify with data, not opinions.',
      },
      {
        title: 'Independent founders',
        description: 'Without enterprise budgets but with the need to be found by AI engines.',
      },
      {
        title: 'Technical writers and open source maintainers',
        description: 'Who must ensure documentation is citable and discoverable.',
      },
      {
        title: 'DevOps engineers',
        description: 'Who want automated checks in CI pipelines, not manual audits.',
      },
      {
        title: 'Researchers',
        description: 'Studying AI citation dynamics empirically and needing reproducible data.',
      },
    ],
  },
  {
    id: 'commitments',
    number: '06',
    title: 'What we commit to.',
    intro: 'Four promises that constrain every future release.',
    items: [
      {
        title: 'The core will always remain open source',
        description: 'No essential feature will ever be behind a paywall. The source code is and will remain MIT.',
      },
      {
        title: 'Built for developers first',
        description: 'CLI before dashboard. JSON before PDF. API before widget.',
      },
      {
        title: 'Honesty about the evolution of the field',
        description: 'We do not sell certainty where uncertainty exists. We document what we know and what we do not.',
      },
      {
        title: 'The score you see is the real score',
        description: 'No hidden rounding, no secret thresholds, no undocumented factors.',
      },
    ],
    quote: 'The score you see is the real score.',
  },
  {
    id: 'bottom-line',
    number: '07',
    title: 'The bottom line.',
    paragraphs: [
      'Generative search represents the next dominant paradigm for discovering information. Sites that structure content for citability and make themselves discoverable to intelligent agents will build a lasting advantage.',
      'You should not need a subscription to know whether your site is being seen. This is the reason GEO Optimizer exists.',
    ],
    quote: 'You should not need a subscription to know if your site is being seen.',
  },
];
