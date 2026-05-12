import type { AuditReport, CategoryScore, Recommendation, TechnicalSignal } from './mockData';

const MAX_SCORES: Record<string, number> = {
  robots: 18,
  llms: 18,
  schema: 16,
  meta: 14,
  content: 12,
  signals: 6,
  ai_discovery: 6,
  brand_entity: 10,
};

const CATEGORY_NAMES: Record<string, string> = {
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

  // Costruisci le 8 categorie dal backend
  const categories: CategoryScore[] = [
    'robots',
    'llms',
    'schema',
    'meta',
    'content',
    'signals',
    'ai_discovery',
    'brand_entity',
  ].map((key) => {
    const rawScore = scoreBreakdown[key] ?? 0;
    const max = MAX_SCORES[key] ?? 0;
    // Applica la penalità solo al totale, non per categoria individuale
    const score = Math.max(0, rawScore);

    return {
      name: CATEGORY_NAMES[key] || key,
      slug: key,
      score,
      maxScore: max,
      grade: computeGrade(score, max),
      signals: _buildSignalsForCategory(key, data),
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
    citabilityScore: data.citability?.total_score ?? 0,
    grade: data.band || 'critical',
    timestamp: data.timestamp || new Date().toISOString(),
    version: '4.10.4',
    categories,
    recommendations,
    technicalSignals,
  };
}

/** Estrae segnali leggibili per ogni categoria dai dati grezzi. */
function _buildSignalsForCategory(key: string, data: any): string[] {
  const out: string[] = [];
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
  }
  return out;
}

/** Costruisce i segnali tecnici dai dati grezzi del backend. */
function _buildTechnicalSignals(data: any): TechnicalSignal[] {
  const out: TechnicalSignal[] = [];
  const meta = data.meta || {};
  const signals = data.signals || {};
  const robots = data.robots || {};

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

  out.push({
    id: 'ts-3',
    name: 'Crawl-delay',
    status: robots.crawl_delay == null ? 'warn' : 'pass',
    description: robots.crawl_delay == null
      ? 'Crawl-delay not configured in robots.txt'
      : `Crawl-delay set to ${robots.crawl_delay}s`,
  });

  out.push({
    id: 'ts-4',
    name: 'Schema completeness',
    status: (data.schema || {}).any_schema_found ? 'pass' : 'fail',
    description: (data.schema || {}).any_schema_found
      ? 'JSON-LD schema found'
      : 'Missing JSON-LD schema',
  });

  out.push({
    id: 'ts-5',
    name: 'Canonical URL',
    status: meta.has_canonical ? 'pass' : 'warn',
    description: meta.has_canonical
      ? 'Canonical tag present'
      : 'Canonical tag missing',
  });

  out.push({
    id: 'ts-6',
    name: 'HTTPS',
    status: (data.http_status || 0) === 200 ? 'pass' : 'warn',
    description: `HTTP status ${data.http_status || 'unknown'}`,
  });

  out.push({
    id: 'ts-7',
    name: 'Language attribute',
    status: signals.has_lang ? 'pass' : 'warn',
    description: signals.has_lang
      ? `Lang set to ${signals.lang_value || 'en'}`
      : 'Missing html lang attribute',
  });

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
