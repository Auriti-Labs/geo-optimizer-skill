// Esegue i casi di conformance/ (condivisi con il motore Python) contro il nucleo JS.
// La suite si sorveglia da sola: file mancanti, file senza casi, `engines` assente/vuoto/sconosciuto
// e casi dichiarati ma non eseguiti fanno fallire il run invece di essere saltati in silenzio.
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { canonicalStatus, checkJsonLd, checkSitemapIndexable, isBlocked, isValidLastmod, jsonLdStatus, parseSitemap } from '../src/index.js';

const dir = fileURLToPath(new URL('../../../conformance/', import.meta.url));

const EXPECTED_FILES = {
  'canonical.json': 'canonical',
  'jsonld.json': 'jsonld-valid',
  'robots.json': 'robots-ai-bots',
  'sitemap-indexable.json': 'sitemap-indexable',
  'sitemap.json': 'sitemap-lastmod',
};
const ENGINES = new Set(['python', 'js']);

const runners = {
  'robots-ai-bots': (i) => ({ blocked: isBlocked(i.robots, i.bot, i.path) }),
  canonical: (i) => ({ status: canonicalStatus(i.html, i.url).status }),
  // Con `html` il caso passa per il percorso reale (jsonLdBlocks + jsonLdStatus via checkJsonLd).
  'jsonld-valid': (i) =>
    'html' in i ? { invalid: checkJsonLd({ url: i.url ?? 'https://example.com/', html: i.html }).length } : { valid: jsonLdStatus(i.block).valid },
  'sitemap-lastmod': (i) => ({ valid: isValidLastmod(i.value) }),
  'sitemap-indexable': (i) => ({
    flagged: checkSitemapIndexable(parseSitemap(i.xml).entries, i.pages).map((f) => f.url),
  }),
};

const files = readdirSync(dir).filter((f) => f.endsWith('.json')).sort();
const suites = files.map((file) => ({ file, suite: JSON.parse(readFileSync(dir + file, 'utf8')) }));
const casesOf = (suite) => (Array.isArray(suite.cases) ? suite.cases : []);
const declaresJs = (c) => Array.isArray(c.engines) && c.engines.includes('js');
const declared = suites.reduce((n, { suite }) => n + casesOf(suite).filter(declaresJs).length, 0);
const executed = [];

test('conformance/ has the five expected rule files', () => {
  const found = Object.fromEntries(suites.map(({ file, suite }) => [file, suite.rule]));
  const missing = Object.keys(EXPECTED_FILES).filter((f) => !(f in found));
  assert.deepEqual(missing, [], `conformance files missing: ${missing}`);
  assert.deepEqual(found, EXPECTED_FILES);
  assert.deepEqual(Object.values(EXPECTED_FILES).sort(), Object.keys(runners).sort());
});

test('every conformance file has cases', () => {
  const empty = suites.filter(({ suite }) => casesOf(suite).length === 0).map(({ file }) => file);
  assert.deepEqual(empty, [], `conformance files with no cases: ${empty}`);
});

test('every case declares known engines and is run by at least one', () => {
  const bad = [];
  for (const { file, suite } of suites) {
    casesOf(suite).forEach((c, i) => {
      const where = `${file}#${i} ${JSON.stringify(c.name)}`;
      if (!('name' in c && 'input' in c && 'expect' in c)) bad.push(`${where}: missing name/input/expect`);
      if (!Array.isArray(c.engines) || c.engines.length === 0) return void bad.push(`${where}: engines missing or empty`);
      const unknown = c.engines.filter((e) => !ENGINES.has(e));
      if (unknown.length) bad.push(`${where}: unknown engines ${unknown}`);
      if (new Set(c.engines).size !== c.engines.length) bad.push(`${where}: duplicate engines`);
      if (!c.engines.some((e) => ENGINES.has(e))) bad.push(`${where}: run by no engine`);
      if (declaresJs(c) && !(suite.rule in runners)) bad.push(`${where}: declares js but JS has no runner for ${suite.rule}`);
    });
  }
  assert.deepEqual(bad, []);
});

for (const { suite } of suites) {
  for (const c of casesOf(suite)) {
    if (!declaresJs(c)) continue;
    test(`${suite.rule}: ${c.name}`, () => {
      assert.deepEqual(runners[suite.rule](c.input), c.expect);
      executed.push(`${suite.rule}: ${c.name}`);
    });
  }
}

// I test di primo livello di un file girano in ordine: questo arriva dopo tutti i casi.
test('executed JS cases equal declared', () => {
  assert.ok(declared > 0, 'no case declares js');
  assert.equal(executed.length, declared, `executed ${executed.length} of ${declared} declared JS cases`);
});
