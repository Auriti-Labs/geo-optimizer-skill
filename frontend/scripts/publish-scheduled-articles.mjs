#!/usr/bin/env node
// Promuove a "published" gli articoli Sanity con scheduledFor gia' trascorso.
//
// Sicurezza e operativita':
// - --dry-run e' sempre consentito e non richiede token: legge solo il dataset pubblico.
// - la modalita' reale richiede SANITY_API_TOKEN con permesso Editor; il token non viene
//   mai stampato o scritto su disco.
// - tutte le patch sono raccolte in una singola transazione, per evitare stati parziali.
// - il workflow GitHub invoca il deploy solo se la transazione ha pubblicato contenuti.
//
// Uso:
//   npm run sanity:publish-due:dry-run
//   SANITY_API_TOKEN=... npm run sanity:publish-due
//   node scripts/publish-scheduled-articles.mjs --json

import { appendFileSync } from 'node:fs';
import { createSanityPublicationClient, fetchDueScheduledArticles } from './sanity-publication-state.mjs';

function parseArgs(argv) {
  const flags = { dryRun: false, json: false };
  for (const arg of argv) {
    if (arg === '--dry-run') flags.dryRun = true;
    else if (arg === '--json') flags.json = true;
    else throw new Error(`Argomento non riconosciuto: ${arg}`);
  }
  return flags;
}

function writeGithubOutput(name, value) {
  if (!process.env.GITHUB_OUTPUT) return;
  appendFileSync(process.env.GITHUB_OUTPUT, `${name}=${value}\n`, 'utf8');
}

function printResult(result, json) {
  if (json) {
    process.stdout.write(`${JSON.stringify(result)}\n`);
    return;
  }

  const mode = result.dryRun ? 'DRY-RUN' : 'PUBBLICATO';
  console.log(`Sanity scheduled publishing — ${mode}`);
  console.log(`${result.dueCount} articolo/i scaduto/i trovato/i.`);
  for (const article of result.articles) {
    console.log(`  • ${article.scheduledFor}  ${article.slug || article._id}`);
  }
  if (result.dryRun) console.log('Nessuna modifica eseguita.');
}

async function main() {
  const { dryRun, json } = parseArgs(process.argv.slice(2));
  const token = process.env.SANITY_API_TOKEN;
  if (!dryRun && !token) {
    throw new Error('SANITY_API_TOKEN e\' obbligatorio per pubblicare gli articoli programmati.');
  }

  const client = createSanityPublicationClient(token);
  const articles = await fetchDueScheduledArticles(client);
  const result = {
    dryRun,
    dueCount: articles.length,
    publishedCount: 0,
    articles,
  };

  if (!dryRun && articles.length > 0) {
    const transaction = client.transaction();
    for (const article of articles) {
      transaction.patch(article._id, { set: { status: 'published' } });
    }
    await transaction.commit();
    result.publishedCount = articles.length;
  }

  writeGithubOutput('due_count', result.dueCount);
  writeGithubOutput('published_count', result.publishedCount);
  writeGithubOutput('published_slugs', articles.map((article) => article.slug).filter(Boolean).join(','));
  printResult(result, json);
}

main().catch((error) => {
  console.error(`Pubblicazione Sanity fallita: ${error.message}`);
  process.exitCode = 1;
});
