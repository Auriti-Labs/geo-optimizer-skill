// Aggregati della coorte per le pagine statiche, letti a BUILD TIME da
// GET /api/public/benchmark — la stessa fonte che /state-of-geo/ carica via JS.
//
// Perché a build time e non via JS: i numeri che arrivano dopo l'idratazione non entrano
// nell'HTML che un crawler AI legge, ed è proprio la citabilità di quel passaggio il
// motivo per cui il dato sta in pagina.
//
// Perché non più hardcoded: i valori scritti a mano invecchiano in silenzio. Al
// 2026-09-04 la homepage dichiarava «750+ audited sites, average 54.3, measured 13
// August» mentre la coorte reale era a 900+ siti con media 54.6, e il pillar GEO citava
// ancora i 288 domini della sola edizione di giugno — un terzo del dataset. Un dato
// proprietario sottodichiarato è autorità regalata ai competitor.
//
// L'endpoint è pubblico su internet, quindi la build lo raggiunge come già fa con Sanity
// (lo stage Node del Dockerfile gira prima che l'app locale sia in piedi: per questo si
// interroga l'URL pubblico e non localhost).
//
// NON blocca la build: se l'endpoint non risponde restano i valori di FALLBACK, con un
// avviso su stdout. A differenza di sitemap e llms.txt — dove un dato mancante
// significherebbe pagine non indicizzabili — qui il peggio che succede è un numero
// vecchio di qualche giorno, che non è un motivo per non deployare il sito.

const ENDPOINT = 'https://geoready.dev/api/public/benchmark';
const TIMEOUT_MS = 5000;

export interface BenchmarkFacts {
  average: string;
  median: string;
  llmsTxtAdoption: string;
  schemaAdoption: string;
  sampleLabel: string;
  /** Data leggibile della lettura, es. "4 September 2026". */
  asOf: string;
  /** false = si stanno mostrando i valori di FALLBACK. */
  isLive: boolean;
}

// Ultima lettura verificata a mano (2026-09-04, endpoint in produzione). Serve solo se
// il fetch fallisce: va aggiornata quando si tocca questo file, non a ogni pubblicazione.
const FALLBACK: BenchmarkFacts = {
  average: '54.6',
  median: '57',
  llmsTxtAdoption: '58%',
  schemaAdoption: '75%',
  sampleLabel: '900+ audited sites',
  asOf: '4 September 2026',
  isLive: false,
};

const asPercent = (value: unknown): string | null =>
  typeof value === 'number' && value >= 0 && value <= 1 ? `${Math.round(value * 100)}%` : null;

const asReadableDate = (iso: unknown): string | null => {
  if (typeof iso !== 'string') return null;
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  });
};

export async function getBenchmark(): Promise<BenchmarkFacts> {
  try {
    const res = await fetch(ENDPOINT, { signal: AbortSignal.timeout(TIMEOUT_MS) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = (await res.json()) as Record<string, any>;

    const average = typeof data?.score?.average === 'number' ? data.score.average.toFixed(1) : null;
    const median = typeof data?.score?.median === 'number' ? String(Math.round(data.score.median)) : null;
    const llmsTxtAdoption = asPercent(data?.adoption?.llms_txt);
    const schemaAdoption = asPercent(data?.adoption?.schema_jsonld);
    const sampleLabel = typeof data?.sample_size_label === 'string' ? data.sample_size_label : null;
    const asOf = asReadableDate(data?.updated_at);

    // Tutto o niente: mescolare valori live e di fallback produrrebbe un passaggio
    // internamente incoerente (media di oggi con campione di tre settimane fa), che è
    // peggio di uno coerente e vecchio di un giorno.
    if (!average || !median || !llmsTxtAdoption || !schemaAdoption || !sampleLabel || !asOf) {
      throw new Error('risposta priva di uno dei campi richiesti');
    }

    console.log(
      `[benchmark] ${sampleLabel} · media ${average} · mediana ${median} · llms.txt ${llmsTxtAdoption} · schema ${schemaAdoption} (as of ${asOf})`
    );
    return { average, median, llmsTxtAdoption, schemaAdoption, sampleLabel, asOf, isLive: true };
  } catch (err) {
    console.warn(
      `[benchmark] ATTENZIONE: ${ENDPOINT} non utilizzabile (${(err as Error).message}) — uso i valori di fallback del ${FALLBACK.asOf}.`
    );
    return FALLBACK;
  }
}
