#!/usr/bin/env node
// Notifica IndexNow (Bing/Yandex/...) dei nuovi URL o di quelli aggiornati.
// Nessun servizio terzo: POST diretto all'endpoint IndexNow con la key ospitata su geoready.dev.
//
// Sorgente URL (priorità):
//   1. URL passati da CLI (posizionali o --url=...) → submit mirato.
//   2. altrimenti tutti gli URL canonici da frontend/public/sitemap.xml.
//
// Filtri:
//   --since=YYYY-MM-DD  → solo URL con <lastmod> >= data (submit dei soli aggiornati).
//   --all               → forza il batch completo (default se non c'è --since né URL CLI).
//
// Sicurezza:
//   - DRY-RUN di default: stampa il payload, NON invia. Serve --submit per inviare davvero.
//   - mai in build/prebuild (anti-spam): si lancia a mano dopo il deploy.
//   - rifiuta URL di host diverso da geoready.dev (IndexNow richiede stesso host della key).
//
// Uso:
//   npm run indexnow:dry-run                      # batch completo, solo anteprima
//   npm run indexnow:submit                       # batch completo, invio reale
//   node scripts/indexnow-submit.mjs --since=2026-06-10 --submit
//   node scripts/indexnow-submit.mjs https://geoready.dev/pricing/ --submit

import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HOST = 'geoready.dev';
const SITE = `https://${HOST}`;
const KEY = '96179a58f47cb3810b563e9d98f4ad6b';
const KEY_LOCATION = `${SITE}/${KEY}.txt`;
const ENDPOINT = 'https://api.indexnow.org/indexnow';

const __dirname = dirname(fileURLToPath(import.meta.url));
const FRONTEND_ROOT = join(__dirname, '..');
const SITEMAP = join(FRONTEND_ROOT, 'public', 'sitemap.xml');

/** Parsing argomenti CLI in { flags, urls }. */
function parseArgs(argv) {
  const flags = { submit: false, all: false, since: null };
  const urls = [];
  for (const arg of argv) {
    if (arg === '--submit') flags.submit = true;
    else if (arg === '--all') flags.all = true;
    else if (arg === '--dry-run') flags.submit = false;
    else if (arg.startsWith('--since=')) flags.since = arg.slice('--since='.length).trim();
    else if (arg.startsWith('--url=')) urls.push(arg.slice('--url='.length).trim());
    else if (arg.startsWith('http://') || arg.startsWith('https://')) urls.push(arg.trim());
    else throw new Error(`Argomento non riconosciuto: ${arg}`);
  }
  return { flags, urls };
}

/** Estrae [{ loc, lastmod }] dagli <url> della sitemap (parsing semplice e controllato). */
function readSitemapEntries() {
  const xml = readFileSync(SITEMAP, 'utf8');
  const entries = [];
  const blockRe = /<url>([\s\S]*?)<\/url>/g;
  let m;
  while ((m = blockRe.exec(xml)) !== null) {
    const block = m[1];
    const loc = (block.match(/<loc>([^<]+)<\/loc>/) || [])[1];
    const lastmod = (block.match(/<lastmod>([^<]+)<\/lastmod>/) || [])[1] || null;
    if (loc) entries.push({ loc: loc.trim(), lastmod: lastmod && lastmod.trim() });
  }
  return entries;
}

/** Tiene solo gli URL dello stesso host della key; scarta gli altri con avviso. */
function keepSameHost(urls) {
  const kept = [];
  for (const u of urls) {
    let host;
    try {
      host = new URL(u).host;
    } catch {
      console.warn(`  ⚠️  SCARTATO (URL non valido): ${u}`);
      continue;
    }
    if (host !== HOST) {
      console.warn(`  ⚠️  SCARTATO (host ${host} ≠ ${HOST}): ${u}`);
      continue;
    }
    kept.push(u);
  }
  return kept;
}

/** Seleziona gli URL da inviare in base a CLI/filtri. */
function selectUrls({ flags, urls }) {
  // 1. URL espliciti da CLI → submit mirato.
  if (urls.length > 0) {
    return { list: keepSameHost(urls), source: 'CLI (URL espliciti)' };
  }
  // 2. dalla sitemap.
  const entries = readSitemapEntries();
  let selected = entries;
  let source = `sitemap.xml (batch completo, ${entries.length} URL)`;
  if (flags.since && !flags.all) {
    selected = entries.filter((e) => e.lastmod && e.lastmod >= flags.since);
    source = `sitemap.xml con lastmod ≥ ${flags.since} (${selected.length}/${entries.length} URL)`;
  }
  return { list: keepSameHost(selected.map((e) => e.loc)), source };
}

/** Costruisce il payload batch IndexNow. */
function buildPayload(urlList) {
  return { host: HOST, key: KEY, keyLocation: KEY_LOCATION, urlList };
}

/** Mappa lo status HTTP di IndexNow in messaggio leggibile. */
function explainStatus(status) {
  const map = {
    200: 'OK — URL accettati.',
    202: 'Accettato — URL ricevuti, key in fase di validazione.',
    400: 'Bad request — formato non valido.',
    403: 'Forbidden — key non valida (file non trovato o contenuto diverso).',
    422: 'Unprocessable — URL non appartengono all\'host o key/keyLocation non corrispondono.',
    429: 'Too many requests — rallenta gli invii.',
  };
  return map[status] || `Status ${status} inatteso.`;
}

async function submit(payload) {
  const res = await fetch(ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
    body: JSON.stringify(payload),
  });
  return { status: res.status, ok: res.ok, body: await res.text().catch(() => '') };
}

async function main() {
  const parsed = parseArgs(process.argv.slice(2));
  const { list, source } = selectUrls(parsed);

  console.log(`IndexNow — host: ${HOST}`);
  console.log(`keyLocation: ${KEY_LOCATION}`);
  console.log(`Sorgente URL: ${source}`);

  if (list.length === 0) {
    console.log('\nNessun URL da inviare (filtro vuoto o sitemap senza match). Niente da fare.');
    return;
  }

  console.log(`\n${list.length} URL selezionati:`);
  for (const u of list) console.log(`  • ${u}`);

  const payload = buildPayload(list);

  if (!parsed.flags.submit) {
    console.log('\n[DRY-RUN] Nessun invio. Payload che verrebbe spedito:');
    console.log(JSON.stringify(payload, null, 2));
    console.log('\nPer inviare davvero: aggiungi --submit (o usa `npm run indexnow:submit`).');
    console.log('Ricorda: invia SOLO dopo che il deploy è live (sitemap + key file raggiungibili).');
    return;
  }

  console.log(`\n[SUBMIT] POST ${ENDPOINT} …`);
  try {
    const { status, ok, body } = await submit(payload);
    console.log(`HTTP ${status} — ${explainStatus(status)}`);
    if (body) console.log(`Risposta: ${body.slice(0, 500)}`);
    if (!ok) process.exitCode = 1;
  } catch (err) {
    console.error(`Invio fallito: ${err.message}`);
    process.exitCode = 1;
  }
}

main();
