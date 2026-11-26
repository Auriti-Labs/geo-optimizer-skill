// Esegue i casi di conformance/ (condivisi con il motore Python) contro il nucleo JS.
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { canonicalStatus, checkSitemapIndexable, isBlocked, isValidLastmod, jsonLdStatus, parseSitemap } from '../src/index.js';

const dir = fileURLToPath(new URL('../../../conformance/', import.meta.url));

const runners = {
  'robots-ai-bots': (i) => ({ blocked: isBlocked(i.robots, i.bot, i.path) }),
  canonical: (i) => ({ status: canonicalStatus(i.html, i.url).status }),
  'jsonld-valid': (i) => ({ valid: jsonLdStatus(i.block).valid }),
  'sitemap-lastmod': (i) => ({ valid: isValidLastmod(i.value) }),
  'sitemap-indexable': (i) => ({
    flagged: checkSitemapIndexable(parseSitemap(i.xml).entries, i.pages).map((f) => f.url),
  }),
};

const files = readdirSync(dir).filter((f) => f.endsWith('.json'));
test('conformance/ has the five rules', () => {
  const rules = new Set(files.map((f) => JSON.parse(readFileSync(dir + f, 'utf8')).rule));
  assert.deepEqual([...rules].sort(), Object.keys(runners).sort());
});

for (const file of files) {
  const suite = JSON.parse(readFileSync(dir + file, 'utf8'));
  for (const c of suite.cases) {
    if (!c.engines.includes('js')) continue;
    test(`${suite.rule}: ${c.name}`, () => {
      assert.deepEqual(runners[suite.rule](c.input), c.expect);
    });
  }
}
