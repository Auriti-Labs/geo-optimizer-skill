import { mapBackendToFrontend } from './reportMapper';
import type { AuditReport } from './mockData';

const API_BASE = import.meta.env.PUBLIC_API_BASE || '/api';

/**
 * Costruisce un URL API assoluto combinando il prefisso configurato
 * con il path e i parametri di query.
 *
 * In dev: API_BASE = '/api' → '/api/audit?url=...'
 * In prod: API_BASE = 'https://api.geoready.dev' → 'https://api.geoready.dev/audit?url=...'
 */
export function buildApiUrl(
  path: string,
  params?: Record<string, string | undefined>,
): string {
  const base = API_BASE.endsWith('/') ? API_BASE.slice(0, -1) : API_BASE;
  const cleanPath = path.startsWith('/') ? path : `/${path}`;

  const searchParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.set(key, value);
      }
    });
  }
  const query = searchParams.toString();
  return query ? `${base}${cleanPath}?${query}` : `${base}${cleanPath}`;
}

export interface FetchAuditResult {
  report: AuditReport | null;
  error: string | null;
  claim_token: string | null;
  expires_at: string | null;
}

/**
 * Esegue un audit GEO chiamando il backend FastAPI via POST.
 * Il backend restituisce un oggetto JSON completo che viene
 * mappato nel formato AuditReport atteso dai componenti UI,
 * più claim_token e expires_at per il flusso di claim anonimo.
 */
export async function fetchAuditReport(url: string): Promise<FetchAuditResult> {
  try {
    const res = await fetch(buildApiUrl('/public/audits'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const err = await res.json();
        detail = err.detail || detail;
      } catch {
        // ignore JSON parse error on error response
      }
      return { report: null, error: detail, claim_token: null, expires_at: null };
    }

    const data = await res.json();
    const report = mapBackendToFrontend(data);
    return { report, error: null, claim_token: data.claim_token ?? null, expires_at: data.expires_at ?? null };
  } catch (e: any) {
    return {
      report: null,
      error: e.message || 'Network error. Is the backend running?',
      claim_token: null,
      expires_at: null,
    };
  }
}

// Input per la generazione di un file llms.txt. Solo base_url è obbligatorio.
export interface LlmsGenerateInput {
  base_url: string;
  sitemap_url?: string;
  site_name?: string;
  description?: string;
  max_per_section?: number;
}

// Risultato della generazione: envelope { data, error } come fetchAuditReport.
// data è null in caso di errore; error è null in caso di successo.
export interface LlmsGenerateResult {
  data: {
    base_url: string;
    sitemap_url: string | null;
    found_sitemap: boolean;
    url_count: number;
    content: string;
    line_count: number;
    size_bytes: number;
  } | null;
  error: string | null;
}

/**
 * Genera un file llms.txt chiamando il backend FastAPI via POST.
 * Il backend scopre la sitemap del sito (o usa quella fornita) e
 * costruisce il contenuto llms.txt riusando la pipeline anti-SSRF.
 * Stesso pattern di fetchAuditReport: errori sempre gestiti, mai throw.
 */
export async function generateLlmsTxt(
  input: LlmsGenerateInput,
): Promise<LlmsGenerateResult> {
  try {
    const res = await fetch(buildApiUrl('/llms/generate'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    });

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const err = await res.json();
        detail = err.detail || detail;
      } catch {
        // ignora errore di parsing JSON sulla risposta di errore
      }
      return { data: null, error: detail };
    }

    const data = await res.json();
    return { data, error: null };
  } catch (e: any) {
    return {
      data: null,
      error: e.message || 'Network error. Is the backend running?',
    };
  }
}
