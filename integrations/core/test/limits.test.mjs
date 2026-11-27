// Tetti sull'input: robots.txt in byte UTF-8 (come Python) e HTML di pagina configurabile (solo JS).
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { DEFAULT_MAX_HTML_BYTES, MAX_ROBOTS_BYTES, checkSite, parseRobots } from '../src/index.js';

const okPage = (url, html) => ({ url, status: 200, html });
const healthy = (url, pad = '') =>
  okPage(url, `<html><head><link rel="canonical" href="${url}"></head><body>${pad}</body></html>`);

test('the default limits match the Python engine', () => {
  assert.equal(MAX_ROBOTS_BYTES, 500 * 1024);
  assert.equal(DEFAULT_MAX_HTML_BYTES, 10 * 1024 * 1024);
});

test('robots.txt is truncated by UTF-8 bytes, not by UTF-16 units', () => {
  // 450000 unità UTF-16, 600000 byte: sotto il tetto contando le unità, sopra contando i byte.
  const text = `User-agent: *\n${'#é\n'.repeat(150000)}Disallow: /late\n`;
  assert.ok(text.length < MAX_ROBOTS_BYTES);
  assert.deepEqual(parseRobots(text).get('*').disallow, []);
});

test('robots.txt under the byte limit keeps its late rule', () => {
  const text = `User-agent: *\n${'#a\n'.repeat(1000)}Disallow: /late\n`;
  assert.deepEqual(parseRobots(text).get('*').disallow, ['/late']);
});

test('a multibyte character cut by the limit becomes U+FFFD and is not dropped', () => {
  // La riga con il tetto in mezzo al secondo "é" (byte 511999-512000 di 512000): resta "/é" + U+FFFD.
  const filler = `${'#' + 'a'.repeat(99)}\n`.repeat(5069) + '#a\n';
  const text = `User-agent: *\n${filler}Disallow: /éé\n`;
  assert.deepEqual(parseRobots(text).get('*').disallow, ['/é�']);
});

test('an HTML page over the limit is reported, not read and not truncated', () => {
  const url = 'https://example.com/big';
  const big = healthy(url, 'x'.repeat(200));
  const r = checkSite({ pages: [big], maxHtmlBytes: 100 });
  assert.deepEqual(r.findings.map((f) => [f.rule, f.severity, f.url]), [['input-limit', 'error', url]]);
  assert.deepEqual(r.summary, { errors: 1, warnings: 0, pages: 1 });
});

test('the HTML limit counts UTF-8 bytes', () => {
  const url = 'https://example.com/';
  const page = healthy(url, 'é'.repeat(100)); // 100 caratteri in più, 200 byte
  const bytes = new TextEncoder().encode(page.html).length;
  assert.deepEqual(checkSite({ pages: [page], maxHtmlBytes: bytes }).findings, []);
  assert.equal(checkSite({ pages: [page], maxHtmlBytes: bytes - 1 }).findings[0].rule, 'input-limit');
  // Contando le unità UTF-16 la pagina starebbe nel tetto di `bytes - 1`.
  assert.ok(page.html.length < bytes - 1);
});

test('an oversized page does not hide the findings of the other pages', () => {
  const r = checkSite({
    pages: [healthy('https://example.com/big', 'x'.repeat(200)), okPage('https://example.com/', '<html></html>')],
    maxHtmlBytes: 100,
  });
  assert.deepEqual(r.findings.map((f) => [f.rule, f.url]), [
    ['input-limit', 'https://example.com/big'],
    ['canonical', 'https://example.com/'],
  ]);
});

test('an oversized page is not judged for noindex in the sitemap', () => {
  const url = 'https://example.com/big';
  const html = `<meta name="robots" content="noindex">${'x'.repeat(200)}`;
  const r = checkSite({
    sitemapXml: `<urlset><url><loc>${url}</loc><lastmod>2026-11-26</lastmod></url></urlset>`,
    pages: [okPage(url, html)],
    maxHtmlBytes: 100,
  });
  assert.deepEqual(r.findings.map((f) => f.rule), ['input-limit']);
});

test('an error page is not read, so its size is not reported', () => {
  const r = checkSite({ pages: [{ url: 'https://example.com/gone', status: 404, html: 'x'.repeat(200) }], maxHtmlBytes: 100 });
  assert.deepEqual(r.findings, []);
});

test('the default limit is 10 MiB and Infinity removes it', () => {
  const page = healthy('https://example.com/', ' '.repeat(DEFAULT_MAX_HTML_BYTES));
  assert.equal(checkSite({ pages: [page] }).findings[0].rule, 'input-limit');
  assert.deepEqual(checkSite({ pages: [page], maxHtmlBytes: Infinity }).findings, []);
});

test('an invalid maxHtmlBytes is rejected instead of silently ignored', () => {
  for (const bad of [0, -1, NaN, '100', null]) {
    assert.throws(() => checkSite({ pages: [], maxHtmlBytes: bad }), RangeError);
  }
});
