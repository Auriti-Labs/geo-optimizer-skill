#!/usr/bin/env node
// Rigenera il blocco "## Guides" di frontend/public/llms.txt dai contenuti Sanity
// live, sullo stesso modello di generate-sitemap.mjs: interroga il dataset con lo
// stesso LIVE_FILTER, sostituisce solo la sezione meccanica e lascia intatto tutto
// il resto del file (identità prodotto, tool, sezioni curate a mano).
//
// BOZZA — non ancora agganciata a Dockerfile.web né a `prebuild`. Prima di farlo,
// va rivista la scelta editoriale qui sotto: la lista attuale in llms.txt è ordinata
// a mano per cluster tematico (llms.txt/visibility → AI Overviews → robots.txt →
// schema → SaaS/e-commerce…), non alfabeticamente né per data. Questo script ordina
// invece per datePublished decrescente (i più recenti prima), che garantisce
// freschezza automatica ma perde il raggruppamento tematico curato a mano — è il
// trade-off da discutere prima di collegarlo alla build.
//
// Perché esiste: llms.txt non ha oggi nessuna generazione automatica (a differenza
// di sitemap.xml), quindi ogni riscrittura di titolo/descrizione su Sanity lascia
// l'entry corrispondente disallineata finché qualcuno non la corregge a mano —
// esattamente il tipo di disallineamento silenzioso trovato il 2026-09-03 su
// track-google-ai-overviews-visibility (titolo riscritto su Sanity, mai sincronizzato
// qui). Vedi commit "content(llms): sync stale llms.txt entries..." su questo branch.
//
// Uso: npm run generate:llms            # sovrascrive frontend/public/llms.txt
//      npm run generate:llms -- --dry-run   # stampa il diff, non scrive nulla

import { readFileSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createClient } from '@sanity/client';

const SITE = 'https://geoready.dev';
const __dirname = dirname(fileURLToPath(import.meta.url));
const FRONTEND_ROOT = join(__dirname, '..');
const LLMS_TXT_PATH = join(FRONTEND_ROOT, 'public', 'llms.txt');

const SECTION_HEADING = '## Guides';
const NEXT_HEADING_PREFIX = '## '; // qualunque heading di pari livello chiude la sezione

const SANITY_PROJECT_ID = process.env.PUBLIC_SANITY_PROJECT_ID || 'uvzrnk4t';
const SANITY_DATASET = process.env.PUBLIC_SANITY_DATASET || 'production';

// Stesso filtro "live" di generate-sitemap.mjs (frontend/src/utils/sanity.ts):
// i documenti legacy senza `status` restano visibili; gli scheduled diventano
// visibili solo dopo la promozione esplicita a "published".
const LIVE_FILTER = `(!defined(status) || status == "published")`;

const dryRun = process.argv.includes('--dry-run');
const warnings = [];

async function fetchGuideEntries() {
  const client = createClient({
    projectId: SANITY_PROJECT_ID,
    dataset: SANITY_DATASET,
    apiVersion: '2024-01-01',
    useCdn: false,
  });

  const articles = await client.fetch(
    `*[_type == "article" && category == "guides" && defined(slug.current) && ${LIVE_FILTER}]{
      title, "slug": slug.current, description, llmsContext, datePublished
    } | order(datePublished desc)`
  );

  return articles.map((article) => {
    // Campo dedicato per llms.txt/AI discovery (vedi schema: "One-paragraph
    // description for llms.txt and AI discovery files"). In sua assenza, fallback
    // sulla meta description standard — meno mirata ma sempre presente (required).
    let summary = article.llmsContext?.trim() || article.description?.trim();
    if (!summary) {
      warnings.push(`${article.slug}: nessun llmsContext né description, entry saltata.`);
      return null;
    }
    if (!article.llmsContext) {
      warnings.push(`${article.slug}: llmsContext assente, uso description come fallback.`);
    }
    // Solo la prima frase: llmsContext è pensato come paragrafo pieno, ma lo stile
    // esistente in llms.txt è una riga sola per entry.
    const firstSentence = summary.split(/(?<=[.!?])\s+/)[0];
    // Il titolo pagina spesso porta un punto finale (H1 in stile frase); come link
    // text in una riga "- [Title](url): desc." risulterebbe ridondante col ":" che
    // segue, quindi lo togliamo.
    const linkText = article.title.replace(/\.$/, '');

    return `- [${linkText}](${SITE}/guides/${article.slug}/): ${firstSentence}`;
  }).filter(Boolean);
}

function replaceSection(fileContent, newLines) {
  const lines = fileContent.split('\n');
  const startIdx = lines.findIndex((l) => l.trim() === SECTION_HEADING);
  if (startIdx === -1) {
    throw new Error(`Sezione "${SECTION_HEADING}" non trovata in ${LLMS_TXT_PATH}`);
  }
  let endIdx = lines.findIndex(
    (l, i) => i > startIdx && l.startsWith(NEXT_HEADING_PREFIX)
  );
  if (endIdx === -1) endIdx = lines.length;

  // Preserva heading + eventuale riga vuota subito dopo, sostituisce solo le entry.
  const before = lines.slice(0, startIdx + 1);
  const after = lines.slice(endIdx);
  return [...before, '', ...newLines, ...after].join('\n');
}

async function main() {
  const entries = await fetchGuideEntries();
  if (entries.length === 0) {
    throw new Error('Nessuna guida live trovata su Sanity — mi rifiuto di svuotare la sezione Guides.');
  }

  const current = readFileSync(LLMS_TXT_PATH, 'utf-8');
  const updated = replaceSection(current, entries);

  for (const w of warnings) console.warn(`WARN  ${w}`);
  console.log(`${entries.length} guide live trovate su Sanity.`);

  if (dryRun) {
    console.log(updated === current ? 'Nessuna differenza.' : 'Differenze trovate (--dry-run, nessuna scrittura).');
    process.exit(0);
  }

  writeFileSync(LLMS_TXT_PATH, updated, 'utf-8');
  console.log(`Scritto ${LLMS_TXT_PATH}`);
}

main().catch((err) => {
  console.error(`ERRORE: ${err.message}`);
  process.exit(1);
});
