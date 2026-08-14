#!/usr/bin/env node
// Riporta se esiste un articolo Sanity live che il sito pubblicato non serve ancora.
//
// Esiste perché la catena "promuovi su Sanity → ridistribuisci il sito" è push-based e
// quindi può rompersi in silenzio: il 2026-08-13 il workflow di pubblicazione ha promosso
// un articolo, ha riportato `success` su tutti gli step, e la pagina è restata 404 per
// mezz'ora — il secret del webhook di deploy puntava a un URL placeholder, e un endpoint
// che risponde 200 a qualunque POST non fa fallire `curl --fail`. Con 28 articoli in coda
// a cadenza di 4 giorni, un fallimento silenzioso per articolo non è accettabile.
//
// Questo script non deploya e non può deployare: decide soltanto, e comunica la decisione
// con l'exit code. Il wrapper che agisce sta sul server, dove vive lo script di rebuild.
// La separazione è deliberata: il codice versionato resta testabile e senza privilegi.
//
// Non richiede token: interroga il dataset pubblico e la sitemap pubblica.
//
// Uso:
//   node scripts/check-live-drift.mjs            # exit 10 se serve un rebuild
//   node scripts/check-live-drift.mjs --json     # output leggibile da uno script
//
// Exit code:
//   0  allineato, nessuna azione
//   10 disallineato, serve un rebuild        <- il wrapper agisce solo su questo
//   1  errore (rete, Sanity, sitemap non parsabile) — NON deployare in caso di dubbio

import { createSanityPublicationClient } from './sanity-publication-state.mjs';

const SITE = 'https://geoready.dev';
const SITEMAP_URL = `${SITE}/sitemap.xml`;
const FETCH_TIMEOUT_MS = 20_000;

// Deve restare allineato a CATEGORY_TO_PATH in generate-sitemap.mjs: una categoria
// assente lì non produce URL, quindi non è un disallineamento da correggere.
const CATEGORY_TO_PATH = {
  guides: '/guides/',
  resources: '/resources/',
};

// Stesso filtro "live" di generate-sitemap.mjs, che è più restrittivo di quello del sito:
// solo `published` conta. Un articolo scheduled-e-scaduto genera la pagina ma resta fuori
// dalla sitemap, ed è il job di pubblicazione a doverlo promuovere — non un rebuild.
const LIVE_ARTICLES_QUERY = `*[
  _type == "article" &&
  defined(slug.current) &&
  (!defined(status) || status == "published")
]{"slug": slug.current, category, _updatedAt}`;

function parseArgs(argv) {
  const flags = { json: false };
  for (const arg of argv) {
    if (arg === '--json') flags.json = true;
    else throw new Error(`Argomento non riconosciuto: ${arg}`);
  }
  return flags;
}

/** Scarica la sitemap pubblica e ne estrae i path, senza dipendenze XML. */
async function fetchLiveSitemapPaths() {
  const res = await fetch(SITEMAP_URL, {
    signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
    headers: { 'User-Agent': 'geoready-live-drift-check' },
  });
  if (!res.ok) throw new Error(`sitemap HTTP ${res.status}`);

  const xml = await res.text();
  const locs = [...xml.matchAll(/<loc>\s*([^<\s]+)\s*<\/loc>/g)].map((m) => m[1]);
  if (locs.length === 0) {
    // Una sitemap vuota o servita come pagina d'errore non è una prova di
    // disallineamento: trattarla come tale farebbe partire un rebuild a ogni glitch.
    throw new Error('la sitemap pubblica non contiene alcun <loc>');
  }

  return new Set(
    locs.map((loc) => {
      try {
        return new URL(loc).pathname.replace(/\/+$/, '') || '/';
      } catch {
        return loc;
      }
    }),
  );
}

function expectedPathFor(article) {
  const prefix = CATEGORY_TO_PATH[article.category];
  if (!prefix) return null;
  return `${prefix}${article.slug}`.replace(/\/+$/, '');
}

async function main() {
  const { json } = parseArgs(process.argv.slice(2));

  const client = createSanityPublicationClient();
  const [articles, livePaths] = await Promise.all([
    client.fetch(LIVE_ARTICLES_QUERY),
    fetchLiveSitemapPaths(),
  ]);

  const missing = [];
  const skipped = [];
  for (const article of articles) {
    const path = expectedPathFor(article);
    if (!path) {
      skipped.push({ slug: article.slug, category: article.category ?? null });
      continue;
    }
    if (!livePaths.has(path)) missing.push({ slug: article.slug, path, updatedAt: article._updatedAt });
  }

  missing.sort((a, b) => String(a.updatedAt).localeCompare(String(b.updatedAt)));

  const result = {
    liveArticles: articles.length,
    sitemapUrls: livePaths.size,
    missingCount: missing.length,
    missing,
    skipped,
    rebuildNeeded: missing.length > 0,
  };

  if (json) {
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } else {
    console.log(`Sanity live: ${result.liveArticles} · sitemap pubblica: ${result.sitemapUrls} URL`);
    if (missing.length === 0) {
      console.log('Allineato — nessun rebuild necessario.');
    } else {
      console.log(`${missing.length} articolo/i live assente/i dalla sitemap pubblica:`);
      for (const m of missing) console.log(`  • ${m.path}  (Sanity: ${m.updatedAt})`);
    }
    for (const s of skipped) {
      console.log(`  ⏭️  ${s.slug}: categoria "${s.category}" non ha una route dinamica — ignorato`);
    }
  }

  process.exitCode = result.rebuildNeeded ? 10 : 0;
}

main().catch((error) => {
  // Exit 1, non 10: un errore di rete non è una prova di disallineamento, e il wrapper
  // deve poter distinguere "serve un rebuild" da "non lo so".
  console.error(`Controllo drift fallito: ${error.message}`);
  process.exitCode = 1;
});
