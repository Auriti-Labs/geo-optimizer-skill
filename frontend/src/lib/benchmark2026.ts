/**
 * Benchmark data from State of GEO June 2026 report (288 domains).
 * Used to contextualise individual audit scores against the broader dataset.
 */
export interface BenchmarkData {
  totalDomains: number;
  avgScore: number;
  medianScore: number;
  topQuarterThreshold: number;
  bottomQuarterThreshold: number;
  maxScore: number;
  minScore: number;
  bands: {
    excellent: { range: string; domains: number; share: number };
    good: { range: string; domains: number; share: number };
    foundation: { range: string; domains: number; share: number };
    critical: { range: string; domains: number; share: number };
  };
  categories: {
    slug: string;
    name: string;
    avg: number;
    max: number;
    efficiency: number;
  }[];
}

export const benchmark2026: BenchmarkData = {
  totalDomains: 288,
  avgScore: 53.6,
  medianScore: 57,
  topQuarterThreshold: 66,
  bottomQuarterThreshold: 44,
  maxScore: 90,
  minScore: 7,
  bands: {
    excellent: { range: '86–100', domains: 4, share: 1.4 },
    good: { range: '68–85', domains: 56, share: 19.4 },
    foundation: { range: '36–67', domains: 186, share: 64.6 },
    critical: { range: '0–35', domains: 42, share: 14.6 },
  },
  categories: [
    { slug: 'meta', name: 'Meta tags', avg: 12.4, max: 14, efficiency: 88.6 },
    { slug: 'content', name: 'Content quality', avg: 9.6, max: 12, efficiency: 80.0 },
    { slug: 'robots', name: 'Robots & crawler access', avg: 13.6, max: 18, efficiency: 75.6 },
    { slug: 'signals', name: 'Technical signals', avg: 3.7, max: 6, efficiency: 61.7 },
    { slug: 'llms', name: 'LLMs.txt', avg: 7.0, max: 18, efficiency: 38.9 },
    { slug: 'schema', name: 'Schema markup', avg: 6.1, max: 16, efficiency: 38.1 },
    { slug: 'brand_entity', name: 'Brand & entity', avg: 3.8, max: 10, efficiency: 38.0 },
    { slug: 'ai_discovery', name: 'AI discovery', avg: 0.5, max: 6, efficiency: 8.3 },
  ],
};