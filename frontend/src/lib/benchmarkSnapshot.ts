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
  measuredOn: '21 September 2026',
  sampleLabel: '1200+ audited sites',
  average: '55.1',
  median: '57',
  llmsTxtAdoption: '58%',
  schemaAdoption: '75%',
  biggestGap: 'AI discovery files',
} as const;
