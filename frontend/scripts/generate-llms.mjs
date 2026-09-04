#!/usr/bin/env node
// Rigenera il blocco "## Guides" di frontend/public/llms.txt dai contenuti Sanity
// live, sullo stesso modello di generate-sitemap.mjs: interroga il dataset con lo
// stesso LIVE_FILTER, sostituisce solo la sezione meccanica e lascia intatto tutto
// il resto del file (identità prodotto, tool, sezioni curate a mano).
//
// Perché esiste: llms.txt era l'unico file di discovery senza generazione automatica
// (a differenza di sitemap.xml), quindi ogni articolo pubblicato da Sanity nasceva
// invisibile agli LLM e ogni riscrittura di titolo/descrizione lasciava l'entry
// disallineata finché qualcuno non la correggeva a mano. È già stato rattoppato a
// mano tre volte (386777a, 5c8f01e, 609bb60) e il 2026-09-04 mancavano di nuovo tre
// guide su 45. Questo script chiude la causa, non il sintomo.
//
// ORDINAMENTO — decisione 2026-09-04, che chiude la domanda aperta del primo draft:
// l'ordine delle entry già presenti nel file viene PRESERVATO, le guide nuove sono
// aggiunte in coda per datePublished decrescente. Il draft iniziale riordinava tutto
// per data, il che avrebbe distrutto il raggruppamento per cluster tematico curato a
// mano (llms.txt/visibility → AI Overviews → robots.txt → schema → SaaS/e-commerce).
// Preservare l'ordine ha anche un effetto pratico: il diff a ogni pubblicazione resta
// minimo e leggibile (righe aggiunte in coda) invece di un rimescolamento completo.
//
// Uso: npm run generate:llms                # sovrascrive frontend/public/llms.txt
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

// La sezione non può restringersi sotto questa frazione delle entry già presenti:
// una query parziale, un dataset sbagliato o una rete che risponde a metà non devono
// poter cancellare silenziosamente metà del file. Stessa logica della guardia
// anti-shrink sulla sitemap in rebuild-geo-web.py.
const MIN_KEEP_RATIO = 0.8;

// Oltre questa soglia una riga della sezione non è più una sintesi: si segnala.
const LONG_SUMMARY_CHARS = 300;

const dryRun = process.argv.includes('--dry-run');
const warnings = [];

// Estrae lo slug da una riga "- [Title](https://geoready.dev/guides/<slug>/): desc"
const slugOfLine = (line) => line.match(/\/guides\/([^/)]+)\//)?.[1] ?? null;

// Prima frase di un testo. Spezza SOLO se dopo il punto comincia davvero una frase
// nuova (maiuscola, citazione o parentesi): senza il lookahead, "ranking vs. citation"
// e "extraction vs. multi-source" venivano tagliati su "vs." e finivano in llms.txt
// come tronconi ("Ranking position vs."). Verificato su 4 entry reali il 2026-09-04.
const firstSentence = (text) => text.trim().split(/(?<=[.!?])\s+(?=["'“‘(\[]?[A-Z0-9])/)[0];

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

  const bySlug = new Map();
  for (const article of articles) {
    // FONTE DEL TESTO — misurato sulle 45 guide live il 2026-09-04: la prima frase di
    // `description` ha mediana 104 caratteri (max 242), quella di `llmsContext` 228
    // (max 441). La sezione vuole UNA riga di sintesi per guida, quindi vince la
    // description — è il meta description, già tarato su quella lunghezza e validato
    // dallo Studio. `llmsContext` è nato come paragrafo pieno per i file di AI
    // discovery e in 6 bozze è anche tagliato a 300 caratteri a metà parola dallo
    // script che le genera: come riga singola darebbe entry prolisse o mutilate.
    // Resta come fallback per le guide senza description (oggi nessuna).
    const description = article.description?.trim();
    const context = article.llmsContext?.trim();
    const summary = description || context;
    if (!summary) {
      warnings.push(`${article.slug}: nessuna description né llmsContext, entry saltata.`);
      continue;
    }
    if (!description) {
      warnings.push(`${article.slug}: description assente, uso llmsContext come fallback.`);
    }
    const sentence = firstSentence(summary);
    // Frase non chiusa = testo sorgente troncato a monte: l'entry sarebbe un troncone.
    if (!/[.!?]$/.test(sentence)) {
      warnings.push(`${article.slug}: prima frase non chiusa (sorgente troncata?), entry comunque scritta.`);
    }
    if (sentence.length > LONG_SUMMARY_CHARS) {
      warnings.push(`${article.slug}: sintesi di ${sentence.length} caratteri, da accorciare su Sanity.`);
    }
    // Il titolo pagina spesso porta un punto finale (H1 in stile frase); come link
    // text in una riga "- [Title](url): desc." risulterebbe ridondante col ":" che
    // segue, quindi lo togliamo.
    const linkText = article.title.replace(/\.$/, '');

    bySlug.set(article.slug, `- [${linkText}](${SITE}/guides/${article.slug}/): ${sentence}`);
  }
  // La query è già ordinata per datePublished desc: l'ordine di inserimento nella
  // Map è quello usato per le guide nuove, che vanno in coda alla sezione.
  return bySlug;
}

function readSection(fileContent) {
  const lines = fileContent.split('\n');
  const startIdx = lines.findIndex((l) => l.trim() === SECTION_HEADING);
  if (startIdx === -1) {
    throw new Error(`Sezione "${SECTION_HEADING}" non trovata in ${LLMS_TXT_PATH}`);
  }
  let endIdx = lines.findIndex((l, i) => i > startIdx && l.startsWith(NEXT_HEADING_PREFIX));
  if (endIdx === -1) endIdx = lines.length;
  return { lines, startIdx, endIdx, body: lines.slice(startIdx + 1, endIdx) };
}

// Ordine stabile: prima le entry già nel file, nel loro ordine curato a mano; poi le
// guide nuove in coda (datePublished desc, come arrivano dalla query).
function orderEntries(currentBody, bySlug) {
  const existingSlugs = currentBody.map(slugOfLine).filter(Boolean);
  const ordered = [];
  const seen = new Set();
  const dropped = [];

  for (const slug of existingSlugs) {
    if (bySlug.has(slug)) {
      ordered.push(bySlug.get(slug));
      seen.add(slug);
    } else {
      dropped.push(slug);
    }
  }
  const added = [];
  for (const [slug, line] of bySlug) {
    if (!seen.has(slug)) {
      ordered.push(line);
      added.push(slug);
    }
  }
  return { ordered, added, dropped, existingSlugs };
}

function replaceSection({ lines, startIdx, endIdx }, newLines) {
  // Preserva heading + riga vuota subito dopo, sostituisce solo le entry. La riga
  // vuota di chiusura va reinserita a mano: apparteneva al corpo della sezione, e
  // senza di essa l'ultima entry finirebbe incollata all'heading successivo.
  const closing = endIdx < lines.length ? [''] : [];
  return [...lines.slice(0, startIdx + 1), '', ...newLines, ...closing, ...lines.slice(endIdx)].join('\n');
}

async function main() {
  const current = readFileSync(LLMS_TXT_PATH, 'utf-8');
  const section = readSection(current);
  const bySlug = await fetchGuideEntries();

  if (bySlug.size === 0) {
    throw new Error('Nessuna guida live trovata su Sanity — mi rifiuto di svuotare la sezione Guides.');
  }

  const { ordered, added, dropped, existingSlugs } = orderEntries(section.body, bySlug);
  const floor = Math.floor(existingSlugs.length * MIN_KEEP_RATIO);
  if (existingSlugs.length > 0 && ordered.length < floor) {
    throw new Error(
      `La sezione passerebbe da ${existingSlugs.length} a ${ordered.length} entry (< ${floor}): ` +
        'sospetto di query parziale, nessuna scrittura. Verificare il dataset Sanity.'
    );
  }

  for (const w of warnings) console.warn(`WARN  ${w}`);
  console.log(`${bySlug.size} guide live su Sanity · ${existingSlugs.length} entry già nel file.`);
  for (const slug of added) console.log(`  + ${slug}`);
  for (const slug of dropped) console.log(`  - ${slug} (non più live, entry rimossa)`);

  const updated = replaceSection(section, ordered);
  if (updated === current) {
    console.log('Nessuna differenza: llms.txt è già allineato a Sanity.');
    return;
  }
  if (dryRun) {
    console.log('Differenze trovate (--dry-run, nessuna scrittura).');
    return;
  }

  writeFileSync(LLMS_TXT_PATH, updated, 'utf-8');
  console.log(`Scritto ${LLMS_TXT_PATH}`);
}

main().catch((err) => {
  console.error(`ERRORE: ${err.message}`);
  process.exit(1);
});
