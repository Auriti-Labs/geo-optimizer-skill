import imageUrlBuilder from '@sanity/image-url';

// projectId e dataset devono allinearsi con la configurazione Astro Sanity
// (vedi astro.config.mjs — default: uvzrnk4t / production).
const projectId = import.meta.env.PUBLIC_SANITY_PROJECT_ID ?? 'uvzrnk4t';
const dataset = import.meta.env.PUBLIC_SANITY_DATASET ?? 'production';

const builder = imageUrlBuilder({ projectId, dataset });

/**
 * Costruisce l'URL CDN di un'immagine Sanity a partire dal nodo Portable Text.
 * Accetta sia il formato diretto ({ _ref }) sia quello espanso ({ asset: { _ref } }).
 */
export function urlForImage(source: any): string {
  if (!source) return '';
  // Sanity Portable Text: il blocco image ha { asset: { _ref, _type } }
  const ref = source?.asset?._ref ?? source?._ref;
  if (!ref) return '';
  return builder.image(source).auto('format').fit('max').width(1200).url();
}