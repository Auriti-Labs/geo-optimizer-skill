export const articleVisualAssets = {
  aiDiscovery: {
    src: '/images/article-visuals/A1HeroAIDiscovery.png',
    alt: 'Diagram showing a website moving through crawlability, structured signals, AI engines, and citation output.',
    height: 452,
  },
  techFoundations: {
    src: '/images/article-visuals/A2TechFoundations.png',
    alt: 'Diagram of technical foundations: crawler access, clean HTML, canonical URLs, and structured data.',
    height: 377,
  },
  failureModes: {
    src: '/images/article-visuals/A3FailureModes.png',
    alt: 'Diagram showing common AI citation failure modes across access, parsing, structure, and quotability.',
    height: 424,
  },
  seoVsGeo: {
    src: '/images/article-visuals/B1HeroSEOvsGEO.png',
    alt: 'Diagram comparing traditional SEO ranking surfaces with GEO citation surfaces.',
    height: 452,
  },
  rankingVsCitation: {
    src: '/images/article-visuals/B2RankingVsCitation.png',
    alt: 'Side-by-side diagram comparing traditional search ranking with AI answer citation.',
    height: 377,
  },
  llmsTxt: {
    src: '/images/article-visuals/C1HeroLlmsTxt.png',
    alt: 'Diagram showing llms.txt as an AI discovery layer that orients tools toward important pages.',
    height: 411,
  },
  checklist: {
    src: '/images/article-visuals/D1HeroChecklist.png',
    alt: 'Checklist diagram of AI visibility signals across access, structure, content, entity, and monitoring.',
    height: 411,
  },
  monitorLoop: {
    src: '/images/article-visuals/D4MonitorLoop.png',
    alt: 'Loop diagram showing audit snapshots, fixes, rechecks, and ongoing monitoring over time.',
    height: 424,
  },
  geoPipeline: {
    src: '/images/article-visuals/E1HeroGEOPipeline.png',
    alt: 'Pipeline diagram showing site foundations, measurable signals, retrieval selection, and AI citation output.',
    height: 452,
  },
  entityAuthority: {
    src: '/images/article-visuals/F1HeroEntityAuthority.png',
    alt: 'Diagram showing connected entity signals across a topic cluster feeding AI source trust.',
    height: 452,
  },
  multimodal: {
    src: '/images/article-visuals/G1HeroMultimodalScaffolding.png',
    alt: 'Diagram showing images, video, and audio becoming retrievable through captions, transcripts, schema, and surrounding text.',
    height: 452,
  },
  llmsOrientation: {
    src: '/images/article-visuals/H1HeroLlmsTxtOrientation.png',
    alt: 'Diagram showing llms.txt as an orientation layer that points AI tools to canonical URLs and summaries.',
    height: 452,
  },
  structuredData: {
    src: '/images/article-visuals/I1HeroStructuredData.png',
    alt: 'Diagram showing structured data labeling article facts before an AI answer engine cites a page.',
    height: 452,
  },
  schemaTypes: {
    src: '/images/article-visuals/P1HeroSchemaTypeStack.png',
    alt: 'Diagram showing schema types for page identity, entity identity, answer formats, and action paths.',
    height: 452,
  },
  schemaValidation: {
    src: '/images/article-visuals/Q1HeroSchemaValidationLoop.png',
    alt: 'Loop diagram showing schema implementation, validation, publishing, monitoring, and rechecking.',
    height: 452,
  },
} as const;

export const guidePrimaryVisuals = {
  'appear-in-chatgpt-perplexity': {
    ...articleVisualAssets.aiDiscovery,
    caption: 'The end-to-end path from a well-optimized website to an AI citation.',
  },
  'check-if-chatgpt-sees-your-website': {
    ...articleVisualAssets.aiDiscovery,
    caption: 'A page must be crawlable, understandable, and quotable before ChatGPT can use it as a source.',
  },
  'robots-txt-ai-bots': {
    ...articleVisualAssets.techFoundations,
    caption: 'AI crawler access is the first technical layer behind retrievability and citation eligibility.',
  },
  'does-robots-txt-block-chatgpt': {
    ...articleVisualAssets.techFoundations,
    caption: 'Crawler permissions decide whether an AI retrieval system can reach the page at all.',
  },
  'signs-your-website-isnt-cited-by-ai': {
    ...articleVisualAssets.failureModes,
    caption: 'Most missing AI citations trace back to access, parsing, structure, or quotability failures.',
  },
  'prompt-injection-ai-crawlers': {
    ...articleVisualAssets.failureModes,
    caption: 'Unsafe or ambiguous page signals can make AI crawlers mistrust, skip, or misread a source.',
  },
  'geo-vs-seo': {
    ...articleVisualAssets.seoVsGeo,
    caption: 'SEO and GEO share technical foundations, but optimize for different answer surfaces.',
  },
  'geo-vs-seo-7-key-differences': {
    ...articleVisualAssets.seoVsGeo,
    caption: 'Traditional search ranks links; AI answer engines retrieve, synthesize, and cite sources.',
  },
  'chatgpt-search-vs-google-search': {
    ...articleVisualAssets.seoVsGeo,
    caption: 'Classic search and AI search expose different visibility mechanics, even when foundations overlap.',
  },
  'ai-citations-check': {
    ...articleVisualAssets.rankingVsCitation,
    caption: 'In classic search you rank. In AI answers, your domain is cited as a source or it is absent.',
  },
  'schema-markup-for-ai-citations': {
    ...articleVisualAssets.structuredData,
    caption: 'Structured data gives AI systems explicit labels for the page, entity, author, dates, and answer structure.',
  },
  'how-perplexity-chooses-sources': {
    ...articleVisualAssets.rankingVsCitation,
    caption: 'Perplexity-style answers make the source-selection step visible through cited URLs.',
  },
  'llms-txt-wordpress': {
    ...articleVisualAssets.llmsTxt,
    caption: 'llms.txt is one discovery layer: useful for orientation, but never a substitute for crawl access.',
  },
  'ai-visibility-checklist': {
    ...articleVisualAssets.checklist,
    caption: 'AI visibility depends on a complete stack of access, structure, content, entity, and monitoring signals.',
  },
  'how-to-improve-ai-visibility': {
    ...articleVisualAssets.checklist,
    caption: 'Improving AI visibility starts by fixing the signal layers a retrieval system can actually observe.',
  },
  'free-ai-search-visibility-tools-2026': {
    ...articleVisualAssets.checklist,
    caption: 'A useful AI visibility tool should measure the full stack, not just one isolated signal.',
  },
  'how-long-to-get-cited-by-chatgpt': {
    ...articleVisualAssets.monitorLoop,
    caption: 'AI visibility is measured over repeated snapshots, not a single answer on one day.',
  },
  'generative-engine-optimization': {
    ...articleVisualAssets.geoPipeline,
    caption: 'The GEO pipeline: site foundations, measurable signals, retrieval selection, and AI citation output.',
  },
  'what-is-generative-engine-optimization': {
    ...articleVisualAssets.geoPipeline,
    caption: 'GEO turns crawlable, understandable, quotable pages into stronger candidates for AI citations.',
  },
  'google-ai-overviews-optimization': {
    ...articleVisualAssets.geoPipeline,
    caption: 'Google AI Overviews still depend on access, understanding, answer fit, and source trust.',
  },
  'entity-authority': {
    ...articleVisualAssets.entityAuthority,
    caption: 'A linked topic cluster gives crawlers a stronger entity signal than a single isolated page.',
  },
  'do-backlinks-matter-for-ai-search': {
    ...articleVisualAssets.entityAuthority,
    caption: 'Authority in AI search comes from the broader entity graph around a topic, not one page alone.',
  },
  'multimodal-geo': {
    ...articleVisualAssets.multimodal,
    caption: 'Images, video, and audio become retrievable when each asset has descriptive text, schema, captions, or transcripts.',
  },
  'is-ai-search-traffic-growing': {
    ...articleVisualAssets.monitorLoop,
    caption: 'AI search growth is easier to reason about when you track snapshots, citations, and changes over time.',
  },
  'what-is-llms-txt': {
    ...articleVisualAssets.llmsOrientation,
    caption: 'llms.txt is a concise orientation layer: it points AI tools to canonical pages and explains what matters.',
  },
  'do-you-need-llms-txt-2026': {
    ...articleVisualAssets.llmsOrientation,
    caption: 'llms.txt is useful orientation for AI tools, not a guaranteed ranking or citation lever.',
  },
  'what-is-an-ai-crawler-bot-list': {
    ...articleVisualAssets.techFoundations,
    caption: 'AI crawler bot lists matter because access is the first step in every retrieval path.',
  },
} as const;

export const guideSupplementalVisuals = {
  'schema-markup-for-ai-citations': [
    {
      ...articleVisualAssets.schemaTypes,
      caption: 'The schema types that matter most for AI citation label the page, entity, answer format, and action path.',
    },
    {
      ...articleVisualAssets.schemaValidation,
      caption: 'Schema only stays useful when validation and re-checking are part of the publishing workflow.',
    },
  ],
} as const;
