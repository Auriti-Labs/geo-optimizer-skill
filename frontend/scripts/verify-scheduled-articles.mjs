#!/usr/bin/env node
// Blocca le build statiche che altrimenti escluderebbero articoli gia' dovuti ma
// ancora in stato "scheduled". Non modifica Sanity e non richiede un token.

import { assertNoDueScheduledArticles } from './sanity-publication-state.mjs';

async function main() {
  await assertNoDueScheduledArticles();
  console.log("Sanity: nessun articolo programmato scaduto. La build puo' proseguire.");
}

main().catch((error) => {
  console.error(`Controllo pubblicazione Sanity fallito: ${error.message}`);
  process.exitCode = 1;
});
