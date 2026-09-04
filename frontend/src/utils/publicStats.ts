// Contatori pubblici (stelle GitHub, download PyPI, audit eseguiti) letti a BUILD TIME
// da GET /api/stats, per la stessa ragione del benchmark in utils/benchmark.ts: i numeri
// che arrivano dopo l'idratazione non entrano nell'HTML che un crawler AI legge.
//
// Il caso era peggiore del benchmark. StatsBar caricava i contatori via JS con un
// fallback statico fermo al 2026-07-15, quindi l'HTML servito a un LLM dichiarava
// 587 stelle e 5.134 download al mese contro i 767 e 71.997 reali: la prova sociale
// del progetto sottodichiarata di 14 volte proprio nel punto in cui viene citata.
//
// I valori restano aggiornati anche lato client: StatsBar continua a fare il suo fetch
// dopo l'idratazione e sovrascrive quelli del build. Questo serve al crawler, non al
// browser.
//
// NON blocca la build: se l'endpoint non risponde si usano i valori di FALLBACK.

const ENDPOINT = 'https://geoready.dev/api/stats';
const TIMEOUT_MS = 5000;

export interface PublicStats {
  github_stars: number;
  pypi_downloads_month: number;
  audits_run: number;
}

// Ultima lettura verificata a mano (2026-09-04, endpoint in produzione). Da aggiornare
// quando si tocca questo file: è ciò che vede un crawler se il fetch fallisce.
export const STATS_FALLBACK: PublicStats = {
  github_stars: 767,
  pypi_downloads_month: 71997,
  audits_run: 1912,
};

export async function getPublicStats(): Promise<{ stats: PublicStats; isLive: boolean }> {
  try {
    const res = await fetch(ENDPOINT, { signal: AbortSignal.timeout(TIMEOUT_MS) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = (await res.json()) as Record<string, unknown>;
    const asCount = (value: unknown): number | null =>
      typeof value === 'number' && Number.isFinite(value) && value > 0 ? Math.trunc(value) : null;

    const github_stars = asCount(data.github_stars);
    const pypi_downloads_month = asCount(data.pypi_downloads_month);
    const audits_run = asCount(data.audits_run);

    // Tutto o niente, come per il benchmark: l'endpoint ritorna 0 sui campi che non ha
    // potuto recuperare (GitHub o PyPI irraggiungibili), e uno zero in pagina sarebbe
    // peggio di un valore di qualche giorno prima.
    if (!github_stars || !pypi_downloads_month || !audits_run) {
      throw new Error('risposta con uno dei contatori a zero o assente');
    }

    console.log(
      `[stats] ${github_stars} stelle · ${pypi_downloads_month} download/mese · ${audits_run} audit`
    );
    return { stats: { github_stars, pypi_downloads_month, audits_run }, isLive: true };
  } catch (err) {
    console.warn(
      `[stats] ATTENZIONE: ${ENDPOINT} non utilizzabile (${(err as Error).message}) — uso i valori di fallback.`
    );
    return { stats: STATS_FALLBACK, isLive: false };
  }
}
