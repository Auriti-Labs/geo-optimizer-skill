// Funzioni condivise per verificare lo stato editoriale Sanity prima di una
// generazione statica. Il dataset pubblico e' sufficiente: gli articoli
// scheduled scaduti sono intenzionalmente interrogabili senza token.

import { createClient } from '@sanity/client';

const DEFAULT_PROJECT_ID = 'uvzrnk4t';
const DEFAULT_DATASET = 'production';

export const DUE_ARTICLES_QUERY = `*[
  _type == "article" &&
  status == "scheduled" &&
  defined(scheduledFor) &&
  dateTime(scheduledFor) <= dateTime(now())
]{_id, title, "slug": slug.current, scheduledFor} | order(scheduledFor asc)`;

export function createSanityPublicationClient(token) {
  return createClient({
    projectId: process.env.PUBLIC_SANITY_PROJECT_ID || DEFAULT_PROJECT_ID,
    dataset: process.env.PUBLIC_SANITY_DATASET || DEFAULT_DATASET,
    apiVersion: '2024-01-01',
    token,
    useCdn: false,
  });
}

export async function fetchDueScheduledArticles(client = createSanityPublicationClient()) {
  return client.fetch(DUE_ARTICLES_QUERY);
}

export async function assertNoDueScheduledArticles() {
  const articles = await fetchDueScheduledArticles();
  if (articles.length === 0) return;

  const slugs = articles.map((article) => article.slug || article._id).join(', ');
  throw new Error(
    `${articles.length} articolo/i programmato/i e gia' scaduto/i: ${slugs}. ` +
      'Eseguire prima la pubblicazione Sanity, poi rigenerare sitemap e sito.'
  );
}
