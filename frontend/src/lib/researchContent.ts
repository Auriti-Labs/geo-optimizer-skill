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
    authors: 'Aggarwal et al. — Princeton, Georgia Tech, Allen Institute for AI, IIT Delhi',
    finding:
      'Coined the term GEO and introduced GEO-bench (10,000 queries across 9 domains). Tested 9 content strategies and showed that adding quotations, statistics, and cited sources measurably raises how much of an answer a source contributes. The headline gains are a relative maximum on one metric (position-adjusted word count) and are measured with the source already present in the model’s context.',
    howWeUseIt:
      'The 8-category scoring engine (robots.txt, llms.txt, schema, meta, content, signals, AI discovery, brand entity) and the citability suite are derived from this signal taxonomy. Direct quotations and concrete statistics carry the most weight in the content checks.',
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
    id: 'geo-critical-survey-2026',
    type: 'paper',
    title: 'A Critical Survey of Generative Engine Optimization (2023–2026)',
    venue: 'arXiv',
    year: '2026',
    authors: 'O. Martinez',
    finding:
      'Reviews 45 GEO studies across a Nov 2023 – Jul 2026 window and grades the evidence. Strong support: query–document topical relevance and position within the retrieved context are the dominant citation levers, and generative engines differ substantially in their source ecosystems. Weak or unproven: no reviewed technique shows a stable, cross-platform causal effect on organic discoverability or on downstream clicks and conversions. The "+40% visibility" figure is reframed as a conditional relative maximum, not a universal rank gain.',
    howWeUseIt:
      'Confirms the design choice to score machine-readable infrastructure and passage-level structure rather than promise ranking gains. The survey’s "competition erodes individual gains" finding is why GEO Optimizer reports a readiness score, not a projected traffic number.',
    link: 'https://arxiv.org/abs/2607.14035',
    linkLabel: 'Read survey',
  },
  {
    id: 'verifiability-emnlp-2023',
    type: 'paper',
    title: 'Evaluating Verifiability in Generative Search Engines',
    venue: 'EMNLP 2023 (Findings)',
    year: '2023',
    authors: 'Liu, Zhang, Liang — Stanford',
    finding:
      'Human audit of four generative search engines. On average only 51.5% of generated sentences are fully supported by their citations, and only 74.5% of citations actually support the statement they are attached to. Fluent answers routinely contain unsupported claims.',
    howWeUseIt:
      'Motivates the citability checks that reward self-contained, quotable statements with inline evidence — the passages an engine can attribute cleanly — and the negative-signal checks that flag thin or unsourced content.',
    link: 'https://arxiv.org/abs/2304.09848',
    linkLabel: 'Read paper',
  },
  {
    id: 'ai-search-disrupts-2026',
    type: 'paper',
    title: 'How Generative AI Disrupts Search: An Empirical Study of Google Search, Gemini, and AI Overviews',
    venue: 'arXiv',
    year: '2026',
    finding:
      'Large-scale audit of Google Search, AI Overviews, and Gemini. AI Overviews surface a markedly different set of sources than the organic results on the same query, cross-surface overlap is low, and answers change on repeated runs for the same query.',
    howWeUseIt:
      'Underpins the "audit recurring, not once" guidance and the State of GEO methodology: each monthly cohort is treated as an independent sample, and re-audits are expected to move as engines update.',
    link: 'https://arxiv.org/abs/2604.27790',
    linkLabel: 'Read paper',
  },
  {
    id: 'dont-measure-once-2026',
    type: 'paper',
    title: 'Don’t Measure Once: Measuring Visibility in AI Search (GEO)',
    venue: 'arXiv',
    year: '2026',
    authors: 'Schulte, Bleeker, Kaufmann',
    finding:
      'AI-search visibility is a distribution, not a single value. Across four engines over 45 days, Jaccard similarity between runs sits at 0.34–0.42, and 57.8% of ChatGPT repetitions did not trigger a web search at all. A one-shot check is an unreliable estimate.',
    howWeUseIt:
      'Directly shapes the State of GEO benchmark (aggregate distributions, medians and percentiles rather than point claims) and the monitoring product, which runs scheduled repeat checks and tracks score history.',
    link: 'https://arxiv.org/abs/2604.07585',
    linkLabel: 'Read paper',
  },
  {
    id: 'ai-visibility-uncertainty-2026',
    type: 'paper',
    title: 'Quantifying Uncertainty in AI Visibility: A Statistical Framework for Generative Search Measurement',
    venue: 'arXiv',
    year: '2026',
    finding:
      'Proposes treating citation-visibility metrics as sample estimators of an underlying response distribution, with confidence intervals and a minimum number of runs needed before a visibility claim is statistically meaningful.',
    howWeUseIt:
      'Informs how the score-stability figure on the methodology page is reported (measured over thousands of back-to-back audit pairs) and why single-audit deltas are described as directional.',
    link: 'https://arxiv.org/abs/2603.08924',
    linkLabel: 'Read paper',
  },
  {
    id: 'autogeo-iclr-2026',
    type: 'paper',
    title: 'What Generative Search Engines Like and How to Optimize Web Content Cooperatively (AutoGEO)',
    venue: 'ICLR 2026',
    year: '2026',
    authors: 'Carnegie Mellon University',
    finding:
      'Learns generative-engine preferences automatically and rewrites content to match them, reporting up to +50.99% visibility over baseline while preserving answer utility. Cooperative, semantically explicit content earns a 35–60% higher citation rate than adversarial or terse equivalents.',
    howWeUseIt:
      'Validates the "cooperative, explicit, machine-readable" direction of the fixer layer (llms.txt, schema, meta, AI discovery generation) over adversarial rewriting, and the choice to generate structure rather than manipulate phrasing.',
    link: 'https://arxiv.org/abs/2510.11438',
    linkLabel: 'Read paper',
  },
  {
    id: 'e-geo-2025',
    type: 'benchmark',
    title: 'E-GEO: A Testbed for Generative Engine Optimization in E-Commerce',
    venue: 'arXiv',
    year: '2025',
    authors: 'Bagga et al.',
    finding:
      'Of 15 common GEO heuristics tested on e-commerce content, 10 were neutral or negative. Systematic optimization converges on domain-agnostic structural improvements rather than any single copy trick.',
    howWeUseIt:
      'Reinforces scoring structure (headings, lists, answer-first blocks, schema) over tactic-of-the-month advice, and the e-commerce checks that focus on machine-readable product and offer data.',
    link: 'https://arxiv.org/abs/2511.20867',
    linkLabel: 'Read paper',
  },
  {
    id: 'cseo-bench-2025',
    type: 'benchmark',
    title: 'C-SEO Bench: Does Conversational SEO Work?',
    venue: 'arXiv',
    year: '2025',
    authors: 'Puerto, Gubri, Green, Oh, Yun — Parameter Lab / Tübingen',
    finding:
      'First benchmark to test conversational-SEO methods across multiple tasks, domains, and competing actors. Most current C-SEO methods are ineffective or actively hurt document ranking, and the few positive effects erode as more documents adopt the same method.',
    howWeUseIt:
      'Used to validate the citability score and to keep the engine focused on durable structural signals. The "gains erode under adoption" result is why GEO Optimizer scores readiness rather than a competitive edge.',
    link: 'https://arxiv.org/abs/2506.11097',
    linkLabel: 'Read paper',
  },
  {
    id: 'ranking-manipulation-emnlp-2024',
    type: 'paper',
    title: 'Ranking Manipulation for Conversational Search Engines',
    venue: 'EMNLP 2024',
    year: '2024',
    authors: 'Pfrommer et al. — UC Berkeley',
    finding:
      'Prompt injection hidden in a document can move a target source up roughly 3 ranks in a conversational search engine (tested on Perplexity Sonar). Retrieved content is an attack surface: what a page says can influence the ranking of the answer it appears in.',
    howWeUseIt:
      'Drives the prompt-injection pattern detection in the audit (instructions aimed at AI crawlers, hidden directives) and the negative-signal checks that flag manipulative content.',
    link: 'https://arxiv.org/abs/2406.03589',
    linkLabel: 'Read paper',
  },
  {
    id: 'adversarial-seo-llm-2024',
    type: 'paper',
    title: 'Adversarial Search Engine Optimization for Large Language Models',
    venue: 'arXiv',
    year: '2024',
    authors: 'Nestaas, Debenedetti, Tramèr — ETH Zürich',
    finding:
      'Preference Manipulation Attacks: crafted website or plugin content tricks an LLM into promoting the attacker and discrediting competitors. Demonstrated on production Bing and Perplexity and on GPT-4 / Claude plugins. Everyone is incentivised to attack, which degrades answers for all users.',
    howWeUseIt:
      'Sets the boundary GEO Optimizer stays inside: it audits and fixes infrastructure and structure, and explicitly does not generate injection payloads or manipulative copy. Detects these patterns as negative signals instead.',
    link: 'https://arxiv.org/abs/2406.18382',
    linkLabel: 'Read paper',
  },
  {
    id: 'schema-ai-citations',
    type: 'analysis',
    title: 'Schema Markup & AI Citations',
    venue: 'GEO Optimizer analysis',
    year: '2026',
    finding:
      'Across audited sites, valid JSON-LD (Organization, WebSite, Article) correlates with a ~28-point higher average GEO score than sites with none — consistent with structural signals mattering more than copy tactics in the published benchmarks.',
    howWeUseIt:
      'Drives the Schema JSON-LD scoring category (max 16 points) and the structured-data fixer that generates complete @context + @type + sameAs blocks.',
    link: 'https://geoready.dev/state-of-geo/',
    linkLabel: 'See the benchmark data',
  },
  {
    id: 'ai-citations-report-2026',
    type: 'benchmark',
    title: 'State of GEO — Monthly AI Search Readiness Benchmark',
    venue: 'GeoReady',
    year: '2026',
    finding:
      'GeoReady’s own monthly benchmark of audited domains: average and median GEO score, llms.txt and schema adoption, band distribution, and the biggest readiness gaps, tracked month over month.',
    howWeUseIt:
      'Provides the empirical baseline for the readiness bands, the negative-signal thresholds, and the "what to fix first" ordering in every audit.',
    link: 'https://geoready.dev/state-of-geo/',
    linkLabel: 'Read the latest edition',
  },
  {
    id: 'ai-mode-citation-factors',
    type: 'analysis',
    title: 'AI Mode Citation Factors',
    venue: 'GEO Optimizer analysis',
    year: '2026',
    finding:
      'On-page and technical factors that influence whether an AI system selects a source: crawlability, passage-level structure, entity resolution, and freshness — the same levers the factorial and audit studies identify as reproducible.',
    howWeUseIt:
      'Mapped into the 8 scoring categories and the technical-signal checks (X-Robots-Tag, noai directives, crawl-delay, canonical, HTTPS).',
    linkLabel: 'Internal analysis',
  },
];

export const researchClosing = {
  statement:
    'GEO Optimizer focuses on infrastructure optimization — crawlability, structured data, meta signals, and content architecture — not on content manipulation, keyword stuffing, or prompt injection. The published benchmarks (C-SEO Bench, E-GEO) and the 2026 GEO survey all point the same way: durable gains come from structure and relevance, and copy tricks erode as everyone adopts them.',
};
