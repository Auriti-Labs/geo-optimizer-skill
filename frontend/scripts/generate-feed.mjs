#!/usr/bin/env node
// Genera frontend/public/feed.xml (Atom 1.0) dalle guide in src/pages/guides/**.
// Stesso spirito di generate-sitemap.mjs: deriva tutto dai file sorgente, zero deps.
//
// Le guide sono file .astro con metadati come const inline:
//   const title = '...'; const description = '...';
//   const datePublished = 'YYYY-MM-DD'; const dateModified = 'YYYY-MM-DD';
// Lo script li estrae con regex semplici (non un parser Astro completo: i const
// sono dichiarati nel frontmatter `---` in cima, formato stabile e curato a mano).
//
// Un feed nativo è un segnale di freshness che il motore GEO stesso premia
// (Technical Signals). NON tocca robots/sitemap/canonical.
//
// Uso: npm run generate:feed   (manuale, come generate:sitemap)

import { readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const SITE = 'https://geoready.dev';
const __dirname = dirname(fileURLToPath(import.meta.url));
const FRONTEND_ROOT = join(__dirname, '..');
const GUIDES_DIR = join(FRONTEND_ROOT, 'src', 'pages', 'guides');
const OUTPUT = join(FRONTEND_ROOT, 'public', 'feed.xml');
const FEED_URL = `${SITE}/feed.xml`;

/** Estrae il valore di un const stringa dal frontmatter: const NAME = '...' | "..." */
function extractConst(source, name) {
  const re = new RegExp(`const\\s+${name}\\s*=\\s*['"\`]([^'"\`]*)['"\`]`);
  const m = source.match(re);
  return m ? m[1] : null;
}

/** Escape minimo per contenuti XML. */
function xmlEscape(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

/** RFC-3339 da una data YYYY-MM-DD (Atom richiede timestamp completo). */
function toRfc3339(dateStr) {
  return `${dateStr}T00:00:00Z`;
}

function collectGuides() {
  const guides = [];
  for (const entry of readdirSync(GUIDES_DIR, { withFileTypes: true })) {
    if (!entry.isFile() || !entry.name.endsWith('.astro')) continue;
    if (entry.name === 'index.astro') continue; // l'indice non è una guida
    const abs = join(GUIDES_DIR, entry.name);
    const source = readFileSync(abs, 'utf8');
    const title = extractConst(source, 'title');
    const description = extractConst(source, 'description');
    const datePublished = extractConst(source, 'datePublished');
    const dateModified = extractConst(source, 'dateModified') || datePublished;
    if (!title || !datePublished) {
      console.log(`  ⚠️  ${entry.name}: manca title o datePublished — escluso dal feed.`);
      continue;
    }
    const slug = entry.name.replace(/\.astro$/, '');
    guides.push({
      url: `${SITE}/guides/${slug}/`,
      title,
      description: description || '',
      datePublished,
      dateModified,
    });
  }
  // Più recenti (per dateModified) in cima.
  guides.sort((a, b) => b.dateModified.localeCompare(a.dateModified));
  return guides;
}

function renderAtom(guides) {
  const updated = guides.length ? toRfc3339(guides[0].dateModified) : toRfc3339('2026-01-01');
  const entries = guides
    .map((g) =>
      [
        '  <entry>',
        `    <title>${xmlEscape(g.title)}</title>`,
        `    <link href="${xmlEscape(g.url)}"/>`,
        `    <id>${xmlEscape(g.url)}</id>`,
        `    <published>${toRfc3339(g.datePublished)}</published>`,
        `    <updated>${toRfc3339(g.dateModified)}</updated>`,
        `    <summary>${xmlEscape(g.description)}</summary>`,
        '  </entry>',
      ].join('\n'),
    )
    .join('\n');
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<feed xmlns="http://www.w3.org/2005/Atom">',
    '  <title>GeoReady — Guides</title>',
    `  <subtitle>Guides on AI visibility, GEO, and getting cited by AI answer engines.</subtitle>`,
    `  <link href="${SITE}/guides/"/>`,
    `  <link rel="self" href="${FEED_URL}"/>`,
    `  <id>${FEED_URL}</id>`,
    `  <updated>${updated}</updated>`,
    '  <author><name>Auriti Labs</name></author>',
    entries,
    '</feed>',
    '',
  ].join('\n');
}

// --- main ---
const guides = collectGuides();
const xml = renderAtom(guides);
writeFileSync(OUTPUT, xml, 'utf8');

console.log(`feed.xml generato: ${guides.length} guide → public/feed.xml`);
for (const g of guides) console.log(`  ${g.dateModified}  ${g.url}`);
