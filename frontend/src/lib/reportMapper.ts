import type { AuditReport, CategoryScore, Recommendation, TechnicalSignal } from './mockData';

// Massimi per categoria, allineati a CATEGORY_MAX / CATEGORY_MAX_V2 in models/config.py.
// Servono solo quando la risposta non include score_max.
const MAX_SCORES_V1: Record<string, number> = {
  robots: 18,
  llms: 18,
  schema: 16,
  meta: 14,
  content: 12,
  signals: 6,
  ai_discovery: 6,
  brand_entity: 10,
};

const MAX_SCORES_V2: Record<string, number> = {
  google_ai: 20,
  robots: 14,
  schema: 14,
  content: 14,
  brand_entity: 12,
  meta: 11,
  llms: 6,
  signals: 6,
  ai_discovery: 3,
};

// Prima versione dell'engine con la rubrica v2 come default (CHANGELOG 4.19.0)
const FIRST_V2_ENGINE: [number, number, number] = [4, 19, 0];

const CATEGORY_NAMES: Record<string, string> = {
  google_ai: 'Google AI Search',
  robots: 'Robots.txt',
  llms: 'llms.txt',
  schema: 'Schema JSON-LD',
  meta: 'Meta Tags',
  content: 'Content',
  signals: 'Signals',
  ai_discovery: 'AI Discovery',
  brand_entity: 'Brand & Entity',
};

function computeGrade(score: number, max: number): CategoryScore['grade'] {
  const pct = score / max;
  if (pct >= 0.86) return 'excellent';
  if (pct >= 0.68) return 'good';
  if (pct >= 0.36) return 'foundation';
  return 'critical';
}

/** True se la stringa di versione semver è >= min (le versioni non leggibili valgono false). */
function isVersionAtLeast(version: unknown, min: [number, number, number]): boolean {
  if (typeof version !== 'string') return false;
  // Accetta "4.19.0", "v4.19.0", " 4.19" e suffissi pre-release ("4.19.0rc1")
  const match = version.match(/^\s*v?(\d+)\.(\d+)(?:\.(\d+))?/);
  if (!match) return false;
  const parts = [match[1], match[2], match[3] ?? '0'].map(Number);
  for (let i = 0; i < 3; i++) {
    if (parts[i] !== min[i]) return parts[i] > min[i];
  }
  return true;
}

/**
 * Massimi delle categorie per questa risposta.
 *
 * Ordine: score_max del backend, poi score_version, poi gli indizi di una
 * risposta v2 a cui il backend ha tolto i campi di versione (per esempio il
 * payload gated del SaaS): la categoria google_ai nel breakdown o una versione
 * dell'engine >= 4.19.0. Solo in assenza di tutto si usano i massimi v1.
 * Applicare i massimi v1 a punteggi v2 produceva valori come "Content 14/12".
 */
export function resolveScoreMax(data: any): Record<string, number> {
  if (data.score_max && typeof data.score_max === 'object') return data.score_max;
  if (data.score_version === 1) return MAX_SCORES_V1;
  if (typeof data.score_version === 'number' && data.score_version >= 2) return MAX_SCORES_V2;
  if ('google_ai' in (data.score_breakdown || {})) return MAX_SCORES_V2;
  if (isVersionAtLeast(data.version, FIRST_V2_ENGINE)) return MAX_SCORES_V2;
  return MAX_SCORES_V1;
}

/** Slug delle categorie che il backend dichiara bloccate (payload gated). */
function lockedCategoriesOf(data: any): Set<string> {
  return new Set(Array.isArray(data.locked_categories) ? data.locked_categories : []);
}

/** Oggetto di dettaglio di una categoria, se il backend lo ha incluso. */
function detailOf(data: any, key: string): Record<string, any> | null {
  const detail = data[key];
  return detail && typeof detail === 'object' ? detail : null;
}

function extractReportId(reportUrl: string | undefined): string {
  if (!reportUrl) return 'unknown';
  const parts = reportUrl.split('/');
  return parts[parts.length - 1] || 'unknown';
}

/**
 * Trasforma la risposta grezza del backend FastAPI nel formato
 * AuditReport atteso dai componenti React del report.
 *
 * Il backend ha una struttura flat (robots, llms, schema, meta, content, ...)
 * con score_breakdown per i punteggi numerici.
 * Questo mapper normalizza tutto in un array di categorie coeso.
 */
export function mapBackendToFrontend(data: any): AuditReport {
  const scoreBreakdown = data.score_breakdown || {};
  const negativePenalty = scoreBreakdown.negative_penalty || 0;

  const scoreMax = resolveScoreMax(data);
  const locked = lockedCategoriesOf(data);
  // Con score_max del backend si mostrano tutte le sue categorie. Con massimi
  // dedotti si mostrano solo quelle presenti nel breakdown: una categoria che
  // il backend ha omesso (es. google_ai nel payload gated) non è un 0/20.
  const hasBackendMax = Boolean(data.score_max && typeof data.score_max === 'object');
  const entries = Object.entries(scoreMax).filter(
    ([key]) => hasBackendMax || Object.keys(scoreBreakdown).length === 0 || key in scoreBreakdown,
  );
  const categories: CategoryScore[] = entries.map(([key, max]) => {
    const rawScore = scoreBreakdown[key] ?? 0;
    // Applica la penalità solo al totale, non per categoria individuale
    const score = Math.max(0, rawScore);
    const isLocked = locked.has(key);

    return {
      name: CATEGORY_NAMES[key] || key,
      slug: key,
      score,
      maxScore: max,
      grade: computeGrade(score, max),
      // Una categoria bloccata non ha dettagli: nessun segnale, mai controlli "falliti" inventati
      signals: isLocked ? [] : _buildSignalsForCategory(key, data),
      locked: isLocked,
    };
  });

  // Raccomandazioni: il backend restituisce stringhe semplici.
  // Le mappiamo in oggetti generici con priorità inferred.
  const recommendations: Recommendation[] = (data.recommendations || []).map(
    (text: string, i: number) => ({
      id: `rec-${i}`,
      title: text,
      description: '',
      category: 'General',
      priority: _inferPriority(text),
      impact: _extractImpact(text),
    })
  );

  // Segnali tecnici dal backend
  const technicalSignals: TechnicalSignal[] = _buildTechnicalSignals(data);

  return {
    id: extractReportId(data.report_url),
    url: data.url || '',
    geoScore: data.score ?? 0,
    // null quando il backend non include la citabilità: la UI mostra "—", non 0/100
    citabilityScore: typeof data.citability?.total_score === 'number' ? data.citability.total_score : null,
    grade: data.band || 'critical',
    timestamp: data.timestamp || new Date().toISOString(),
    version: data.version || __ENGINE_VERSION__,
    categories,
    recommendations,
    technicalSignals,
  };
}

/**
 * Estrae segnali leggibili per ogni categoria dai dati grezzi.
 *
 * Senza l'oggetto di dettaglio (categoria bloccata o campo omesso dal backend)
 * non c'è nulla da dire: un oggetto mancante non è un controllo fallito.
 */
function _buildSignalsForCategory(key: string, data: any): string[] {
  const out: string[] = [];
  if (!detailOf(data, key)) return out;
  switch (key) {
    case 'robots': {
      const r = data.robots || {};
      if (!r.found) out.push('No robots.txt found');
      if (!r.citation_bots_ok) out.push('AI bots not explicitly allowed');
      if (r.crawl_delay == null) out.push('Crawl-delay not configured');
      if (r.found && out.length === 0) out.push('robots.txt present');
      break;
    }
    case 'llms': {
      const l = data.llms || {};
      if (!l.found) out.push('No llms.txt found');
      if (!l.has_h1) out.push('Missing H1 header');
      if (!l.has_sections) out.push('No sections defined');
      if (l.found && out.length === 0) out.push('llms.txt present');
      break;
    }
    case 'schema': {
      const s = data.schema || {};
      if (!s.any_schema_found) out.push('No valid JSON-LD');
      if (!s.has_organization) out.push('Missing Organization schema');
      if (!s.has_website) out.push('Missing WebSite schema');
      if (s.any_schema_found && out.length === 0) out.push('Schema markup present');
      break;
    }
    case 'meta': {
      const m = data.meta || {};
      if (m.has_title) out.push('Title present');
      else out.push('Missing title');
      if (!m.has_canonical) out.push('Missing canonical');
      if (!m.has_og_title) out.push('OG tags incomplete');
      break;
    }
    case 'content': {
      const c = data.content || {};
      if (c.has_h1) out.push('H1 present');
      if ((c.word_count || 0) < 300) out.push('Low word count');
      if (!c.has_lists_or_tables) out.push('No structured lists');
      break;
    }
    case 'signals': {
      const sig = data.signals || {};
      if (sig.has_lang) out.push(`Lang: ${sig.lang_value || 'set'}`);
      else out.push('Missing lang attribute');
      if (!sig.has_rss) out.push('No RSS feed');
      if (!sig.has_freshness) out.push('Low freshness score');
      break;
    }
    case 'ai_discovery': {
      const ai = data.ai_discovery || {};
      if (!ai.has_well_known_ai) out.push('No well-known AI file');
      if (!ai.has_summary) out.push('Missing summary.json');
      if (ai.faq_count === 0) out.push('No FAQ structured data');
      break;
    }
    case 'brand_entity': {
      const b = data.brand_entity || {};
      if (b.brand_name_consistent) out.push('Brand name consistent');
      else out.push('Brand name inconsistent');
      if (!b.has_about_link) out.push('Missing about page');
      if (!b.has_contact_info) out.push('No contact info');
      break;
    }
    case 'google_ai': {
      for (const c of data.google_ai?.checks || []) {
        if (c.status !== 'pass') out.push(`${c.id}: ${c.status}`);
      }
      break;
    }
  }
  return out;
}

/**
 * Costruisce i segnali tecnici dai dati grezzi del backend.
 *
 * Ogni segnale compare solo se il backend ha incluso i dati da cui dipende
 * e la categoria non è bloccata: altrimenti l'assenza del dato veniva letta
 * come un errore (per esempio "Missing JSON-LD schema" su un report gated).
 */
function _buildTechnicalSignals(data: any): TechnicalSignal[] {
  const out: TechnicalSignal[] = [];
  const locked = lockedCategoriesOf(data);
  const available = (key: string) => !locked.has(key) && detailOf(data, key) !== null;
  const meta = detailOf(data, 'meta') || {};
  const signals = detailOf(data, 'signals') || {};
  const robots = detailOf(data, 'robots') || {};
  const schema = detailOf(data, 'schema') || {};

  if (available('meta')) {
    out.push({
      id: 'ts-1',
      name: 'X-Robots-Tag',
      status: meta.x_robots_noindex ? 'fail' : 'pass',
      description: meta.x_robots_tag || 'No restrictive X-Robots-Tag detected',
    });

    out.push({
      id: 'ts-2',
      name: 'noai / noimageai',
      status: meta.has_noai ? 'fail' : 'pass',
      description: meta.has_noai
        ? `Exclusion directive found: ${meta.noai_value}`
        : 'No AI exclusion meta directives found',
    });
  }

  if (available('robots')) {
    out.push({
      id: 'ts-3',
      name: 'Crawl-delay',
      status: robots.crawl_delay == null ? 'warn' : 'pass',
      description: robots.crawl_delay == null
        ? 'Crawl-delay not configured in robots.txt'
        : `Crawl-delay set to ${robots.crawl_delay}s`,
    });
  }

  if (available('schema')) {
    out.push({
      id: 'ts-4',
      name: 'Schema completeness',
      status: schema.any_schema_found ? 'pass' : 'fail',
      description: schema.any_schema_found ? 'JSON-LD schema found' : 'Missing JSON-LD schema',
    });
  }

  if (available('meta')) {
    out.push({
      id: 'ts-5',
      name: 'Canonical URL',
      status: meta.has_canonical ? 'pass' : 'warn',
      description: meta.has_canonical
        ? 'Canonical tag present'
        : 'Canonical tag missing',
    });
  }

  // 0 è il default dell'engine per "status non rilevato": non è uno status da mostrare
  if (typeof data.http_status === 'number' && data.http_status > 0) {
    out.push({
      id: 'ts-6',
      name: 'HTTPS',
      status: data.http_status === 200 ? 'pass' : 'warn',
      description: `HTTP status ${data.http_status}`,
    });
  }

  if (available('signals')) {
    out.push({
      id: 'ts-7',
      name: 'Language attribute',
      status: signals.has_lang ? 'pass' : 'warn',
      description: signals.has_lang
        ? `Lang set to ${signals.lang_value || 'en'}`
        : 'Missing html lang attribute',
    });
  }

  return out;
}

/** Prova a inferire la priorità dal testo della raccomandazione. */
function _inferPriority(text: string): Recommendation['priority'] {
  const lower = text.toLowerCase();
  if (lower.includes('critical') || lower.includes('must') || lower.includes('required') || lower.includes('essential')) return 'critical';
  if (lower.includes('high') || lower.includes('important') || lower.includes('strongly')) return 'high';
  if (lower.includes('low') || lower.includes('minor') || lower.includes('optional')) return 'low';
  return 'medium';
}

/** Estrae un impatto testuale se presente nel testo della raccomandazione. */
function _extractImpact(text: string): string {
  const match = text.match(/\+\d+%?/);
  return match ? match[0] : '';
}
