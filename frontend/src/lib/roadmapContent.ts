export type RoadmapStatus = 'available' | 'in-progress' | 'planned' | 'exploring';

export interface RoadmapItem {
  id: string;
  title: string;
  description: string;
  status: RoadmapStatus;
}

export interface RoadmapPhase {
  id: string;
  label: string;
  subtitle: string;
  statusColor: string;
  items: RoadmapItem[];
}

export const roadmapPhases: RoadmapPhase[] = [
  {
    id: 'current',
    label: 'Current Foundation',
    subtitle: 'What exists today in v4.14.x',
    statusColor: 'border-accent-success',
    items: [
      {
        id: 'cli-audit',
        title: 'CLI audit',
        description: 'Complete `geo audit` command with 8-category scoring and 4 output formats.',
        status: 'available',
      },
      {
        id: 'scoring-8cat',
        title: '8-category scoring',
        description: 'Robots.txt, llms.txt, Schema, Meta, Content, Signals, AI Discovery, Brand & Entity.',
        status: 'available',
      },
      {
        id: 'citability-score',
        title: 'Citability score',
        description: '47-method citability analysis derived from Princeton KDD 2024 and AutoGEO ICLR 2026.',
        status: 'available',
      },
      {
        id: 'rest-api',
        title: 'REST API',
        description: 'FastAPI endpoints for audit, badge, PDF, and comparison.',
        status: 'available',
      },
      {
        id: 'dynamic-badge',
        title: 'Dynamic badge',
        description: 'SVG badge and Shields.io-compatible endpoint generated from live audit data.',
        status: 'available',
      },
      {
        id: 'mcp-support',
        title: 'MCP support',
        description: 'Model Context Protocol server with 12 tools and 5 resources.',
        status: 'available',
      },
      {
        id: 'ai-discovery',
        title: 'AI discovery checks',
        description: 'Detection of /.well-known/ai.txt, /ai/summary.json, /ai/faq.json, /ai/service.json.',
        status: 'available',
      },
      {
        id: 'negative-signals',
        title: 'Negative signal detection',
        description: 'Excessive CTAs, invasive popups, thin content, broken links, keyword stuffing.',
        status: 'available',
      },
      {
        id: 'prompt-injection',
        title: 'Prompt injection detection',
        description: '8 AI manipulation patterns based on UC Berkeley EMNLP 2024.',
        status: 'available',
      },
      {
        id: 'trust-stack',
        title: 'Trust Stack Score',
        description: '5-layer trust signal aggregation: technical, identity, social, academic, consistency.',
        status: 'available',
      },
      {
        id: 'monitor-history',
        title: 'Monitoring, history & tracking',
        description: 'Scheduled audits, score history, and change tracking for watched URLs.',
        status: 'available',
      },
      {
        id: 'snapshots',
        title: 'Snapshots & citation quality',
        description: 'Point-in-time captures of audit state with citation-quality annotations.',
        status: 'available',
      },
      {
        id: 'output-formats',
        title: 'Output formats',
        description: 'JSON, HTML, SARIF, JUnit XML, and GitHub Annotations for CI integration.',
        status: 'available',
      },
      {
        id: 'astro-frontend-v2',
        title: 'Astro frontend',
        description: 'Static-site frontend in Astro + React + Tailwind (this site), live in production.',
        status: 'available',
      },
      {
        id: 'server-logs',
        title: 'AI Crawler Activity Analytics',
        description: 'Detect AI crawler activity from access logs (OAI-SearchBot, ClaudeBot, PerplexityBot). Available via `geo logs` CLI command and `POST /api/logs/analyze`.',
        status: 'available',
      },
    ],
  },
  {
    id: 'near-term',
    label: 'Near Term',
    subtitle: 'Completing the frontend v2 and production readiness',
    statusColor: 'border-accent-teal',
    items: [
      {
        id: 'static-pages',
        title: 'Strategic static pages',
        description: 'Research, Roadmap, Manifesto, guides, and comparison pages — live.',
        status: 'available',
      },
      {
        id: 'compare-page',
        title: 'Compare page',
        description: 'Side-by-side competitor report linked to the live backend.',
        status: 'available',
      },
      {
        id: 'export-pdf-json',
        title: 'Export PDF/JSON',
        description: 'Export actions in the report UI for PDF and JSON output.',
        status: 'available',
      },
      {
        id: 'gdpr-consent',
        title: 'GDPR cookie consent',
        description: 'Cookie banner, preferences modal, and consent management for analytics.',
        status: 'available',
      },
      {
        id: 'production-deploy',
        title: 'Production deploy',
        description: 'Live on geoready.dev behind a reverse proxy, served from the FastAPI backend.',
        status: 'available',
      },
      {
        id: 'caching',
        title: 'Audit caching',
        description: 'Client-side or server-side caching to reduce redundant backend calls.',
        status: 'in-progress',
      },
      {
        id: 'loading-states',
        title: 'Loading & skeleton states',
        description: 'Polished loading UX for audit and report pages.',
        status: 'in-progress',
      },
      {
        id: 'responsive-a11y',
        title: 'Responsive & accessibility polish',
        description: 'WCAG 2.1 AA pass, keyboard navigation, screen-reader optimization.',
        status: 'in-progress',
      },
    ],
  },
  {
    id: 'mid-term',
    label: 'Mid Term',
    subtitle: 'Product evolution and deeper integrations',
    statusColor: 'border-accent-warning',
    items: [
      {
        id: 'visual-dashboard',
        title: 'Visual dashboard',
        description: 'More comprehensive dashboard with radar charts and category breakdowns.',
        status: 'planned',
      },
      {
        id: 'trend-tracking-ui',
        title: 'Trend tracking & score history',
        description: 'Visual score history and trend graphs directly in the web UI.',
        status: 'planned',
      },
      {
        id: 'competitor-reports',
        title: 'Competitor reports',
        description: 'More readable, shareable competitor comparison reports.',
        status: 'planned',
      },
      {
        id: 'scheduled-monitoring-web',
        title: 'Scheduled monitoring in web app',
        description: 'Configure and view scheduled audits without using the CLI.',
        status: 'planned',
      },
      {
        id: 'batch-audit',
        title: 'Multi-site batch audit',
        description: 'CSV upload, batch processing, and consolidated export.',
        status: 'planned',
      },
      {
        id: 'wordpress-plugin',
        title: 'WordPress plugin',
        description: 'Admin dashboard widget and automated GEO checks for WordPress sites.',
        status: 'exploring',
      },
      {
        id: 'alerts',
        title: 'Slack / Discord / webhook alerts',
        description: 'Notifications when scores drop or critical signals are detected.',
        status: 'planned',
      },
    ],
  },
  {
    id: 'long-term',
    label: 'Long Term',
    subtitle: 'Advanced explorations and architectural evolution',
    statusColor: 'border-text-muted',
    items: [
      {
        id: 'webmcp',
        title: 'WebMCP readiness audit',
        description: 'Measure exposure of machine-readable context for MCP-compatible agents.',
        status: 'exploring',
      },
      {
        id: 'topical-clusters',
        title: 'Topical cluster architecture analysis',
        description: 'Hub-and-spoke content structure analysis for AI citation networks.',
        status: 'exploring',
      },
      {
        id: 'multi-language',
        title: 'Multi-language GEO optimization',
        description: 'Signal weighting and content analysis for non-English languages.',
        status: 'exploring',
      },
      {
        id: 'retrieval-surface',
        title: 'Deeper retrieval surface analysis',
        description: 'Analyze how much of a site is actually retrievable by AI crawlers.',
        status: 'exploring',
      },
      {
        id: 'structural-patterns',
        title: 'Structural pattern recognition',
        description: 'ML-based detection of optimal content patterns for AI citations.',
        status: 'exploring',
      },
      {
        id: 'scoring-recalibration',
        title: 'Scoring recalibration',
        description: 'Periodic re-weighting of the 8 categories based on new research.',
        status: 'exploring',
      },
      {
        id: 'team-workspace',
        title: 'Local / hosted workspace for teams',
        description: 'Multi-user team accounts with shared projects and permissions.',
        status: 'exploring',
      },
      {
        id: 'v5-architecture',
        title: 'v5 architectural evolution',
        description: 'Next-generation core designed for scale, modularity, and real-time analysis.',
        status: 'exploring',
      },
    ],
  },
];

export const releaseCadence = [
  { version: 'v4.10.0', name: 'Veil', status: 'available' as RoadmapStatus },
  { version: 'v4.11.0', name: 'Static', status: 'available' as RoadmapStatus },
  { version: 'v4.12.0', name: 'Ledger', status: 'available' as RoadmapStatus },
  { version: 'v4.13.0', name: 'Echo', status: 'available' as RoadmapStatus },
  { version: 'v4.14.0', name: 'Quiet Glass', status: 'available' as RoadmapStatus },
  { version: 'v4.15.0', name: 'Threshold / Pale Signal', status: 'planned' as RoadmapStatus },
  { version: 'v5.0.0', name: 'Black Archive', status: 'exploring' as RoadmapStatus },
];
