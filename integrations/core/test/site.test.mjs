import assert from 'node:assert/strict';
import { test } from 'node:test';

import { checkSite } from '../src/index.js';

const page = (url, extra = '', status = 200) => ({
  url,
  status,
  html: `<html><head><link rel="canonical" href="${url}">${extra}</head><body></body></html>`,
});

test('a healthy site has no findings', () => {
  const r = checkSite({
    robotsTxt: 'User-agent: *\nAllow: /\n',
    sitemapXml: '<urlset><url><loc>https://example.com/</loc><lastmod>2026-11-26</lastmod></url></urlset>',
    pages: [page('https://example.com/', '<script type="application/ld+json">{"@type":"Thing"}</script>')],
  });
  assert.deepEqual(r.findings, []);
  assert.deepEqual(r.summary, { errors: 0, warnings: 0, pages: 1 });
});

test('a site without robots.txt and sitemap is not penalised', () => {
  const r = checkSite({ pages: [page('https://example.com/')] });
  assert.equal(r.summary.errors + r.summary.warnings, 0);
});

test('each broken thing is reported once, under its own rule', () => {
  const r = checkSite({
    robotsTxt: 'User-agent: PerplexityBot\nDisallow: /\n',
    sitemapXml: '<urlset><url><loc>https://example.com/a</loc></url><url><loc>https://example.com/b</loc></url></urlset>',
    pages: [
      { url: 'https://example.com/a', status: 200, html: '<html><head><script type="application/ld+json">{bad}</script></head></html>' },
      page('https://example.com/b', '', 404),
    ],
  });
  const rules = r.findings.map((f) => f.rule).sort();
  assert.deepEqual(rules, ['canonical', 'jsonld-valid', 'robots-ai-bots', 'sitemap-indexable', 'sitemap-lastmod']);
  assert.equal(r.summary.errors, 4);
  assert.equal(r.summary.warnings, 1);
});

test('a sitemap index is recognised and not mistaken for pages', () => {
  const r = checkSite({
    sitemapXml: '<sitemapindex><sitemap><loc>https://example.com/s1.xml</loc></sitemap></sitemapindex>',
    pages: [page('https://example.com/')],
  });
  assert.equal(r.findings.filter((f) => f.rule === 'sitemap-indexable').length, 0);
});

test('a malformed canonical href is a finding, not a crash', () => {
  const r = checkSite({
    pages: [{ url: 'https://example.com/', status: 200, html: '<head><link rel="canonical" href="https://"></head>' }],
  });
  assert.deepEqual(r.findings.map((f) => f.rule), ['canonical']);
});

test('an error page is reported by the sitemap rule only, not for its missing canonical', () => {
  const r = checkSite({
    sitemapXml: '<urlset><url><loc>https://example.com/gone</loc><lastmod>2026-11-26</lastmod></url></urlset>',
    pages: [{ url: 'https://example.com/gone', status: 404, html: '<html></html>' }],
  });
  assert.deepEqual(r.findings.map((f) => f.rule), ['sitemap-indexable']);
});

test('robots=none counts as noindex', () => {
  const r = checkSite({
    sitemapXml: '<urlset><url><loc>https://example.com/</loc><lastmod>2026-11-26</lastmod></url></urlset>',
    pages: [page('https://example.com/', '<meta name="robots" content="none">')],
  });
  assert.ok(r.findings.some((f) => f.rule === 'sitemap-indexable'));
});

test('a sitemap with a namespace prefix is read', () => {
  const r = checkSite({
    sitemapXml: '<sm:urlset><sm:url><sm:loc>https://example.com/</sm:loc></sm:url></sm:urlset>',
    pages: [page('https://example.com/')],
  });
  assert.deepEqual(r.findings.map((f) => f.rule), ['sitemap-lastmod']);
});

test('a robots rule on a query string is checked against the page URL with its query', () => {
  const r = checkSite({
    robotsTxt: 'User-agent: PerplexityBot\nDisallow: /search?private=1\n',
    pages: [page('https://example.com/search?private=1')],
  });
  assert.deepEqual(r.findings.map((f) => f.rule), ['robots-ai-bots']);
  const clean = checkSite({
    robotsTxt: 'User-agent: PerplexityBot\nDisallow: /search?private=1\n',
    pages: [page('https://example.com/search')],
  });
  assert.equal(clean.findings.length, 0);
});
