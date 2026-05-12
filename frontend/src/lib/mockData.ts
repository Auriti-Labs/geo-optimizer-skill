export interface CategoryScore {
  name: string;
  slug: string;
  score: number;
  maxScore: number;
  grade: 'excellent' | 'good' | 'foundation' | 'critical';
  signals: string[];
}

export interface Recommendation {
  id: string;
  title: string;
  description: string;
  category: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  impact: string;
}

export interface TechnicalSignal {
  id: string;
  name: string;
  status: 'pass' | 'warn' | 'fail';
  description: string;
}

export interface AuditReport {
  id: string;
  url: string;
  geoScore: number;
  citabilityScore: number;
  grade: 'excellent' | 'good' | 'foundation' | 'critical';
  timestamp: string;
  version: string;
  categories: CategoryScore[];
  recommendations: Recommendation[];
  technicalSignals: TechnicalSignal[];
}

export const mockAuditReport: AuditReport = {
  id: '100680ad546ce6a577f42f52df33b4cf',
  url: 'https://example.com',
  geoScore: 12,
  citabilityScore: 47,
  grade: 'critical',
  timestamp: '2026-05-12T14:32:00Z',
  version: '4.10.4',
  categories: [
    {
      name: 'Robots.txt',
      slug: 'robots',
      score: 0,
      maxScore: 18,
      grade: 'critical',
      signals: ['No robots.txt found', 'Missing AI bot directives', 'Crawl-delay not configured'],
    },
    {
      name: 'llms.txt',
      slug: 'llms',
      score: 0,
      maxScore: 18,
      grade: 'critical',
      signals: ['No llms.txt found', 'Missing H1 header', 'No sections defined'],
    },
    {
      name: 'Schema JSON-LD',
      slug: 'schema',
      score: 0,
      maxScore: 16,
      grade: 'critical',
      signals: ['No valid JSON-LD', 'Missing @context', 'Missing @type'],
    },
    {
      name: 'Meta Tags',
      slug: 'meta',
      score: 5,
      maxScore: 14,
      grade: 'foundation',
      signals: ['Title present', 'Missing canonical', 'OG tags incomplete'],
    },
    {
      name: 'Content',
      slug: 'content',
      score: 3,
      maxScore: 12,
      grade: 'critical',
      signals: ['H1 present', 'Low word count', 'No structured lists'],
    },
    {
      name: 'Signals',
      slug: 'signals',
      score: 3,
      maxScore: 6,
      grade: 'foundation',
      signals: ['Lang attribute set', 'No RSS feed', 'Low freshness score'],
    },
    {
      name: 'AI Discovery',
      slug: 'ai_discovery',
      score: 0,
      maxScore: 6,
      grade: 'critical',
      signals: ['No well-known AI file', 'Missing summary.json', 'No FAQ structured data'],
    },
    {
      name: 'Brand & Entity',
      slug: 'brand',
      score: 2,
      maxScore: 10,
      grade: 'critical',
      signals: ['Some brand coherence', 'Missing Organization schema', 'No contact page'],
    },
  ],
  recommendations: [
    {
      id: 'rec-1',
      title: 'Create robots.txt with AI bot directives',
      description:
        'Add a robots.txt file allowing major AI crawlers (ChatGPT-User, ClaudeBot, PerplexityBot, Google-Extended) and set an appropriate Crawl-delay.',
      category: 'Robots.txt',
      priority: 'critical',
      impact: '+13 points',
    },
    {
      id: 'rec-2',
      title: 'Generate llms.txt',
      description:
        'Create an llms.txt file with H1 header, description, and structured markdown links to your most important pages.',
      category: 'llms.txt',
      priority: 'critical',
      impact: '+13 points',
    },
    {
      id: 'rec-3',
      title: 'Add JSON-LD schema markup',
      description:
        'Implement Organization, WebSite, and Article schemas with required fields: @context, @type, url, name.',
      category: 'Schema JSON-LD',
      priority: 'critical',
      impact: '+11 points',
    },
    {
      id: 'rec-4',
      title: 'Complete Open Graph meta tags',
      description:
        'Add og:title, og:description, og:image, and og:url to all pages for better AI citation.',
      category: 'Meta Tags',
      priority: 'high',
      impact: '+4 points',
    },
    {
      id: 'rec-5',
      title: 'Increase content depth',
      description:
        'Add structured lists, numeric data, and front-loaded key information. Target 800+ words on core pages.',
      category: 'Content',
      priority: 'high',
      impact: '+6 points',
    },
    {
      id: 'rec-6',
      title: 'Add AI discovery endpoints',
      description:
        'Create /.well-known/ai.txt, /ai/summary.json, and /ai/faq.json to signal AI-readiness.',
      category: 'AI Discovery',
      priority: 'high',
      impact: '+5 points',
    },
    {
      id: 'rec-7',
      title: 'Add Organization schema with sameAs',
      description:
        'Include links to your Knowledge Graph profiles (LinkedIn, Wikipedia, Crunchbase) for brand entity resolution.',
      category: 'Brand & Entity',
      priority: 'medium',
      impact: '+5 points',
    },
  ],
  technicalSignals: [
    {
      id: 'ts-1',
      name: 'X-Robots-Tag',
      status: 'pass',
      description: 'No restrictive X-Robots-Tag headers detected',
    },
    {
      id: 'ts-2',
      name: 'noai / noimageai',
      status: 'pass',
      description: 'No AI exclusion meta directives found',
    },
    {
      id: 'ts-3',
      name: 'Crawl-delay',
      status: 'warn',
      description: 'Crawl-delay not configured in robots.txt',
    },
    {
      id: 'ts-4',
      name: 'Schema completeness',
      status: 'fail',
      description: 'Missing required properties: @context, @type, url',
    },
    {
      id: 'ts-5',
      name: 'Canonical URL',
      status: 'warn',
      description: 'Canonical tag present but self-referencing',
    },
    {
      id: 'ts-6',
      name: 'HTTPS',
      status: 'pass',
      description: 'Site served over secure connection',
    },
  ],
};
