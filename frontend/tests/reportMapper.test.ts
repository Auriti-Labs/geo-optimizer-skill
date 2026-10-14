/**
 * Test del mapper del report web (src/lib/reportMapper.ts).
 *
 * Eseguiti con il test runner di Node, senza dipendenze aggiuntive:
 *   npm test   (node --experimental-strip-types --test)
 *
 * I payload riproducono le tre forme che il mapper riceve: risposta completa
 * con rubrica v2, risposta legacy v1 e payload "gated" del SaaS, a cui mancano
 * score_max, score_version, google_ai e i dettagli delle categorie bloccate.
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';

// Costante iniettata da Vite in build (astro.config.mjs): qui va definita a mano.
(globalThis as any).__ENGINE_VERSION__ = '0.0.0-test';

const { mapBackendToFrontend, resolveScoreMax } = await import('../src/lib/reportMapper.ts');

const V2_MAX = {
  google_ai: 20,
  robots: 14,
  schema: 14,
  content: 14,
  brand_entity: 12,
  meta: 11,
  llms: 6,
  signals: 6,
  ai_discovery: 3,
};

/** Payload gated: forma descritta nell'audit di produzione del 13/10 (punteggio 94, google_ai nascosto). */
function gatedPayload(): Record<string, any> {
  return {
    url: 'https://example.com',
    score: 94,
    band: 'excellent',
    version: '4.19.0',
    gated: true,
    locked_categories: ['llms', 'schema', 'content', 'brand_entity'],
    score_breakdown: {
      robots: 14,
      llms: 6,
      schema: 14,
      meta: 9,
      content: 14,
      signals: 5,
      ai_discovery: 3,
      brand_entity: 9,
    },
    robots: { found: true, citation_bots_ok: true, crawl_delay: null },
    meta: { has_title: true, has_canonical: true, has_og_title: true },
    signals: { has_lang: true, lang_value: 'en', has_rss: true, has_freshness: true },
    ai_discovery: { has_well_known_ai: true, has_summary: true, faq_count: 3 },
    recommendations: [],
  };
}

/** Payload completo come lo restituisce l'API dell'engine con rubrica v2. */
function fullV2Payload(): Record<string, any> {
  return {
    url: 'https://example.com',
    score: 94,
    band: 'excellent',
    version: '4.19.0',
    score_version: 2,
    score_max: { ...V2_MAX },
    score_breakdown: { ...gatedPayload().score_breakdown, google_ai: 20 },
    robots: { found: true, citation_bots_ok: true, crawl_delay: 5 },
    llms: { found: false, has_h1: false, has_sections: false },
    schema: { any_schema_found: true, has_organization: true, has_website: true },
    meta: { has_title: true, has_canonical: false, has_og_title: true },
    content: { has_h1: true, word_count: 900, has_lists_or_tables: true },
    signals: { has_lang: true, lang_value: 'en', has_rss: false, has_freshness: true },
    ai_discovery: { has_well_known_ai: true, has_summary: true, faq_count: 2 },
    brand_entity: { brand_name_consistent: true, has_about_link: true, has_contact_info: true },
    google_ai: { checks: [{ id: 'G-BYLINE', status: 'warn' }] },
    citability: { total_score: 71 },
    http_status: 200,
    recommendations: ['Add an llms.txt file (critical)'],
  };
}

const FALSE_NEGATIVES = [
  'No llms.txt found',
  'No valid JSON-LD',
  'Missing Organization schema',
  'Missing WebSite schema',
  'Low word count',
  'Brand name inconsistent',
];

test('gated payload: v2 maxima, so no category scores above its maximum', () => {
  const report = mapBackendToFrontend(gatedPayload());
  const content = report.categories.find((c) => c.slug === 'content')!;
  const llms = report.categories.find((c) => c.slug === 'llms')!;

  assert.equal(content.maxScore, 14); // con i massimi v1 era 14/12
  assert.equal(llms.maxScore, 6); // con i massimi v1 era 6/18 "Critical"
  for (const c of report.categories) assert.ok(c.score <= c.maxScore, `${c.slug} ${c.score}/${c.maxScore}`);
});

test('gated payload: locked categories are flagged and have no invented failures', () => {
  const report = mapBackendToFrontend(gatedPayload());
  const locked = report.categories.filter((c) => c.locked).map((c) => c.slug).sort();

  assert.deepEqual(locked, ['brand_entity', 'content', 'llms', 'schema']);
  const allSignals = report.categories.flatMap((c) => c.signals);
  for (const text of FALSE_NEGATIVES) assert.ok(!allSignals.includes(text), `unexpected signal: ${text}`);
});

test('gated payload: a category missing from the breakdown is not shown as 0', () => {
  const report = mapBackendToFrontend(gatedPayload());

  assert.equal(report.categories.find((c) => c.slug === 'google_ai'), undefined);
  assert.equal(report.categories.length, 8);
});

test('gated payload: technical signals without data are omitted, citability is null', () => {
  const report = mapBackendToFrontend(gatedPayload());
  const ids = report.technicalSignals.map((s) => s.id);

  assert.ok(!ids.includes('ts-4'), 'schema signal from a locked category'); // era "Missing JSON-LD schema"
  assert.ok(!ids.includes('ts-6'), 'HTTP status signal without http_status'); // era "HTTP status unknown"
  assert.ok(ids.includes('ts-1') && ids.includes('ts-3') && ids.includes('ts-7'));
  assert.equal(report.citabilityScore, null); // era 0/100
});

test('full v2 payload: unchanged behaviour', () => {
  const report = mapBackendToFrontend(fullV2Payload());
  const llms = report.categories.find((c) => c.slug === 'llms')!;
  const googleAi = report.categories.find((c) => c.slug === 'google_ai')!;

  assert.equal(report.categories.length, 9);
  assert.ok(report.categories.every((c) => !c.locked));
  assert.ok(llms.signals.includes('No llms.txt found')); // il file manca davvero: il segnale resta
  assert.equal(googleAi.maxScore, 20);
  assert.deepEqual(googleAi.signals, ['G-BYLINE: warn']);
  assert.equal(report.technicalSignals.length, 7);
  assert.equal(report.citabilityScore, 71);
});

test('legacy v1 payload keeps v1 maxima', () => {
  const report = mapBackendToFrontend({
    score: 60,
    version: '4.18.3',
    score_breakdown: { robots: 18, llms: 9, schema: 8, meta: 10, content: 6, signals: 3, ai_discovery: 3, brand_entity: 3 },
  });

  assert.equal(report.categories.find((c) => c.slug === 'robots')!.maxScore, 18);
  assert.equal(report.categories.find((c) => c.slug === 'brand_entity')!.maxScore, 10);
});

test('missing detail object outside a gated payload produces no signals', () => {
  const payload = fullV2Payload();
  delete payload.llms;

  const llms = mapBackendToFrontend(payload).categories.find((c) => c.slug === 'llms')!;

  assert.deepEqual(llms.signals, []);
});

test('resolveScoreMax: precedence of the version hints', () => {
  assert.deepEqual(resolveScoreMax({ score_max: { robots: 99 } }), { robots: 99 });
  assert.equal(resolveScoreMax({ score_version: 2 }).google_ai, 20);
  assert.equal(resolveScoreMax({ score_version: 1, version: '4.19.0' }).robots, 18);
  assert.equal(resolveScoreMax({ score_breakdown: { google_ai: 12 } }).google_ai, 20);
  assert.equal(resolveScoreMax({ version: '4.20.1' }).google_ai, 20);
  // confronto numerico, non tra stringhe: "4.9.0" < "4.19.0"
  assert.equal(resolveScoreMax({ version: '4.9.0' }).robots, 18);
  assert.equal(resolveScoreMax({ version: 'v4.19.0' }).google_ai, 20);
  assert.equal(resolveScoreMax({ version: '4.19' }).google_ai, 20);
  assert.equal(resolveScoreMax({ version: '4.18' }).robots, 18);
  assert.equal(resolveScoreMax({}).robots, 18);
});

test('http_status 0 means unknown and produces no technical signal', () => {
  const payload = fullV2Payload();
  payload.http_status = 0;

  const ids = mapBackendToFrontend(payload).technicalSignals.map((s) => s.id);

  assert.ok(!ids.includes('ts-6'));
});
