/**
 * Snapshot of the GeoReady cohort benchmark (GET /api/public/benchmark).
 *
 * Hardcoded on purpose: the Docker build runs before the app is up, so a fetch
 * in page frontmatter would fail, and numbers loaded by client script never reach
 * the HTML an AI crawler reads. The cost is staleness, so `measuredOn` makes the
 * age visible to the reader. Single source for best-geo-tools and state-of-geo:
 * update it here, once, when the endpoint moves.
 */
export const BENCHMARK = {
  // Figures as published in the engine README on 17 October 2026 (latest audit per
  // domain, self-selected sample). Keep README, this file and the monthly editions in step.
  measuredOn: '17 October 2026',
  sampleLabel: '1,800+ audited sites',
  average: '56.5',
  median: '59',
  llmsTxtAdoption: '58%',
  schemaAdoption: '76%',
  biggestGap: 'AI discovery files',
} as const;
