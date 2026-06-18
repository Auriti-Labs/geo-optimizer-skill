export interface ResearchSource {
  id: string;
  type: 'paper' | 'benchmark' | 'report' | 'analysis';
  title: string;
  venue?: string;
  year?: string;
  authors?: string;
  finding: string;
  howWeUseIt: string;
  link?: string;
  linkLabel?: string;
  metrics?: { label: string; value: string }[];
}

export const researchSources: ResearchSource[] = [
  {
    id: 'geo-kdd-2024',
    type: 'paper',
    title: 'GEO: Generative Engine Optimization',
    venue: 'KDD 2024',
    year: '2024',
    authors: 'Princeton, Georgia Tech, AI2, IIT Delhi',
    finding:
      'Tested 9 optimization strategies across 10,000 queries on GEO-bench. Demonstrated that structural and authoritative signals significantly increase LLM citation rates.',
    howWeUseIt:
      'The 8-category scoring engine (robots.txt, llms.txt, schema, meta, content, signals, AI discovery, brand entity) is directly derived from the signal taxonomy validated in this paper.',
    link: 'https://arxiv.org/abs/2311.09735',
    linkLabel: 'Read paper',
    metrics: [
      { label: 'Cite Sources', value: '+27–115%' },
      { label: 'Quotations', value: '+41%' },
      { label: 'Statistics', value: '+33%' },
      { label: 'Fluency', value: '+29%' },
      { label: 'Technical Terms', value: '+18%' },
      { label: 'Authority', value: '+16%' },
      { label: 'Readability', value: '+14%' },
      { label: 'Unique Words', value: '+7%' },
      { label: 'Keyword Stuffing', value: '~0%' },
    ],
  },
  {
    id: 'autogeo-iclr-2026',
    type: 'paper',
    title: 'AutoGEO: Automatic Generative Engine Optimization',
    venue: 'ICLR 2026',
    year: '2026',
    authors: 'AutoGEO Research Group',
    finding:
      'Introduces automated pipelines that optimize content for generative engines without human intervention, using reinforcement learning from LLM feedback. Reports a +50.99% improvement over the Princeton KDD 2024 baseline by optimizing content automatically.',
    howWeUseIt:
      'Informs the design of the `geo fix` command and the auto-fix generation layer: robots.txt, llms.txt, schema, and meta tag suggestions are generated using the same structural principles.',
    link: 'https://arxiv.org/abs/2510.11438',
    linkLabel: 'Read paper',
  },
  {
    id: 'cseo-bench',
    type: 'benchmark',
    title: 'C-SEO Bench: Conversational SEO Methods',
    venue: 'Industry benchmark',
    year: '2025',
    finding:
      'Benchmark for evaluating how well web content is retrieved and cited in conversational search systems. Covers passage retrieval, answer grounding, and source attribution.',
    howWeUseIt:
      'Used to validate the citability score (47-method suite) and to weight signals such as front-loaded information, heading hierarchy, and structured lists.',
    linkLabel: 'Internal benchmark',
  },
  {
    id: 'schema-ai-citations',
    type: 'analysis',
    title: 'Schema Markup & AI Citations',
    venue: 'GEO Optimizer analysis',
    year: '2025',
    finding:
      'JSON-LD Schema.org markup (FAQ, Article, Organization, WebSite) directly improves the probability of being cited as a source in AI-generated answers.',
    howWeUseIt:
      'Drives the Schema JSON-LD scoring category (max 16 points) and the structured-data fixer that generates complete @context + @type + sameAs blocks.',
    linkLabel: 'Internal analysis',
  },
  {
    id: 'ai-citations-report-2026',
    type: 'report',
    title: 'AI Citations Report 2026',
    venue: 'Industry report',
    year: '2026',
    finding:
      'Aggregated data from major AI search platforms showing citation patterns, domain diversity, and the rise of generative answer engines over traditional link lists.',
    howWeUseIt:
      'Provides the empirical baseline for the trust stack score and negative-signal detection (excessive CTAs, thin content, broken links, keyword stuffing).',
    linkLabel: 'Industry report',
  },
  {
    id: 'ai-mode-citation-factors',
    type: 'analysis',
    title: 'AI Mode Citation Factors',
    venue: 'GEO Optimizer analysis',
    year: '2025',
    finding:
      'Identification of the specific on-page and technical factors that influence whether an AI system selects a source for citation: crawlability, content structure, entity resolution, and freshness.',
    howWeUseIt:
      'Mapped directly into the 8 scoring categories and the technical-signal checks (X-Robots-Tag, noai directives, crawl-delay, canonical, HTTPS).',
    linkLabel: 'Internal analysis',
  },
];

export const researchClosing = {
  statement:
    'GEO Optimizer focuses on infrastructure optimization — crawlability, structured data, meta signals, and content architecture — not on content manipulation, keyword stuffing, or prompt injection.',
};
