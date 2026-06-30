import assert from 'node:assert/strict';
import { mkdtemp, readFile, writeFile, mkdir } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { test } from 'node:test';

import geoReady from '../index.mjs';

const silentLogger = { info: () => {}, warn: () => {} };

const PAGES = [
  { pathname: '' },
  { pathname: 'pricing/' },
  { pathname: 'guides/what-is-llms-txt/' },
  { pathname: 'guides/geo-vs-seo/' },
  { pathname: 'tools/llms-txt-generator/' },
  { pathname: '404/' },
];

async function runBuild(options, { existingLlms = null } = {}) {
  const dir = await mkdtemp(path.join(os.tmpdir(), 'astro-geoready-'));
  if (existingLlms !== null) {
    await writeFile(path.join(dir, 'llms.txt'), existingLlms, 'utf-8');
  }
  const integration = geoReady(options);
  integration.hooks['astro:config:done']({ config: { site: 'https://example.com/' } });
  await integration.hooks['astro:build:done']({
    pages: PAGES,
    dir: pathToFileURL(dir + path.sep),
    logger: silentLogger,
  });
  return dir;
}

test('generates llms.txt grouped by section with absolute URLs', async () => {
  const dir = await runBuild({ siteName: 'Example', description: 'A test site.' });
  const content = await readFile(path.join(dir, 'llms.txt'), 'utf-8');

  assert.match(content, /^# Example/m);
  assert.match(content, /^> A test site\./m);
  assert.match(content, /^## Pages/m);
  assert.match(content, /^## Guides/m);
  assert.match(content, /\[What Is Llms Txt\]\(https:\/\/example\.com\/guides\/what-is-llms-txt\/\)/);
  assert.doesNotMatch(content, /404/);
});

test('generates ai discovery files', async () => {
  const dir = await runBuild({ siteName: 'Example' });
  const aiTxt = await readFile(path.join(dir, '.well-known', 'ai.txt'), 'utf-8');
  assert.match(aiTxt, /LLMs: https:\/\/example\.com\/llms\.txt/);

  const summary = JSON.parse(await readFile(path.join(dir, 'ai', 'summary.json'), 'utf-8'));
  assert.equal(summary.name, 'Example');
  assert.equal(summary.url, 'https://example.com');
  assert.equal(summary.pages_count, PAGES.length);
});

test('generates ai/faq.json from the faqs option', async () => {
  const faqs = [
    { q: 'What is it?', a: 'A test.' },
    { q: 'Is it free?', a: 'Yes.' },
  ];
  const dir = await runBuild({ siteName: 'Example', faqs });
  const faq = JSON.parse(await readFile(path.join(dir, 'ai', 'faq.json'), 'utf-8'));
  assert.equal(faq.name, 'Example — FAQ');
  assert.equal(faq.url, 'https://example.com');
  assert.equal(faq.questions.length, 2);
  assert.deepEqual(faq.questions[0], { question: 'What is it?', answer: 'A test.' });
});

test('generates ai/service.json from the service option', async () => {
  const service = {
    type: 'Audit tool',
    provider: 'Acme',
    offers: [{ plan: 'Free', price: '0', priceCurrency: 'EUR' }],
    features: ['One', 'Two'],
  };
  const dir = await runBuild({ siteName: 'Example', description: 'Desc.', service });
  const svc = JSON.parse(await readFile(path.join(dir, 'ai', 'service.json'), 'utf-8'));
  assert.equal(svc.name, 'Example');
  assert.equal(svc.service_type, 'Audit tool');
  assert.equal(svc.provider, 'Acme');
  assert.equal(svc.offers.length, 1);
  assert.deepEqual(svc.features, ['One', 'Two']);
});

test('skips faq.json and service.json when options are absent', async () => {
  const dir = await runBuild({ siteName: 'Example' });
  // summary.json still generated; faq/service must NOT exist without their options.
  await readFile(path.join(dir, 'ai', 'summary.json'), 'utf-8');
  await assert.rejects(readFile(path.join(dir, 'ai', 'faq.json'), 'utf-8'));
  await assert.rejects(readFile(path.join(dir, 'ai', 'service.json'), 'utf-8'));
});

test('never overwrites an existing llms.txt by default', async () => {
  const dir = await runBuild({ siteName: 'Example' }, { existingLlms: 'HAND CURATED\n' });
  const content = await readFile(path.join(dir, 'llms.txt'), 'utf-8');
  assert.equal(content, 'HAND CURATED\n');
});

test('overwrite: true regenerates existing files', async () => {
  const dir = await runBuild({ siteName: 'Example', overwrite: true }, { existingLlms: 'HAND CURATED\n' });
  const content = await readFile(path.join(dir, 'llms.txt'), 'utf-8');
  assert.match(content, /^# Example/m);
});

test('skips everything without config.site', async () => {
  const dir = await mkdtemp(path.join(os.tmpdir(), 'astro-geoready-'));
  let warned = false;
  const integration = geoReady({});
  integration.hooks['astro:config:done']({ config: {} });
  await integration.hooks['astro:build:done']({
    pages: PAGES,
    dir: pathToFileURL(dir + path.sep),
    logger: { info: () => {}, warn: () => { warned = true; } },
  });
  assert.equal(warned, true);
});

test('respects maxPerSection and aiDiscovery flag', async () => {
  const dir = await runBuild({ siteName: 'Example', maxPerSection: 1, aiDiscovery: false });
  const content = await readFile(path.join(dir, 'llms.txt'), 'utf-8');
  const guidesLinks = content.split('## Guides')[1].split('##')[0].match(/^- \[/gm) || [];
  assert.equal(guidesLinks.length, 1);
  await assert.rejects(readFile(path.join(dir, 'ai', 'summary.json'), 'utf-8'));
  await mkdir(dir, { recursive: true }); // keep tmp dir valid for cleanup tools
});
