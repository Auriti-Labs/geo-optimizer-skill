import { mapBackendToFrontend } from './reportMapper';
import type { AuditReport } from './mockData';

const API_BASE = '/api';

export interface FetchAuditResult {
  report: AuditReport | null;
  error: string | null;
}

/**
 * Esegue un audit GEO chiamando il backend FastAPI.
 * Il backend restituisce un oggetto JSON completo che viene
 * mappato nel formato AuditReport atteso dai componenti UI.
 */
export async function fetchAuditReport(url: string): Promise<FetchAuditResult> {
  try {
    const encodedUrl = encodeURIComponent(url);
    const res = await fetch(`${API_BASE}/audit?url=${encodedUrl}`);

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const err = await res.json();
        detail = err.detail || detail;
      } catch {
        // ignore JSON parse error on error response
      }
      return { report: null, error: detail };
    }

    const data = await res.json();
    const report = mapBackendToFrontend(data);
    return { report, error: null };
  } catch (e: any) {
    return {
      report: null,
      error: e.message || 'Network error. Is the backend running?',
    };
  }
}
