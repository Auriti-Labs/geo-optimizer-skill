// Le cinque regole del verificatore di build. Ognuna ha evidenza documentata dal vendor o da Google;
// niente punteggi, niente giudizi: solo difetti verificabili su file e pagine.
import { canonicals, jsonLdBlocks, robotsDirectives } from './html.js';
import { isBlocked } from './robots.js';
import { isValidLastmod, parseSitemap } from './sitemap.js';

/** Bot di ricerca con citazione: bloccarli per errore toglie il sito dalle risposte che li usano. */
export const AI_SEARCH_BOTS = ['OAI-SearchBot', 'Claude-SearchBot', 'PerplexityBot'];

/** Stessa normalizzazione di geo_optimizer.core.audit_google_ai._norm: schema e host minuscoli, no slash finale. */
export function normUrl(url) {
  const u = new URL(url);
  const path = u.pathname.replace(/\/+$/, '') || '/';
  return `${u.protocol.toLowerCase()}//${u.host.toLowerCase()}${path}${u.search}`;
}

// null se l'URL non è valido: un href malformato non deve abortire la verifica dell'intero sito.
const safeNorm = (url) => {
  try {
    return normUrl(url);
  } catch {
    return null;
  }
};

const finding = (rule, severity, message, url) => ({ rule, severity, message, ...(url ? { url } : {}) });

// 1) robots.txt non blocca per errore i bot di ricerca AI
export function checkRobotsAiBots(robotsTxt, paths = ['/']) {
  if (robotsTxt == null) return []; // nessun file = nessuna restrizione
  const out = [];
  for (const bot of AI_SEARCH_BOTS) {
    const blocked = paths.filter((p) => isBlocked(robotsTxt, bot, p));
    if (blocked.length) {
      out.push(finding('robots-ai-bots', 'error', `robots.txt blocks ${bot} on ${blocked.length} of ${paths.length} checked path(s), e.g. ${blocked[0]}`));
    }
  }
  return out;
}

// 2) nella sitemap non ci sono pagine noindex né 4xx/5xx
export function checkSitemapIndexable(entries, pages) {
  const byUrl = new Map(pages.map((p) => [safeNorm(p.url), p]));
  const out = [];
  for (const { loc } of entries) {
    const key = safeNorm(loc);
    const page = key === null ? undefined : byUrl.get(key);
    if (!page) continue; // pagina non nel build: non si giudica
    if (page.status >= 400) out.push(finding('sitemap-indexable', 'error', `Sitemap lists a page that answers ${page.status}`, loc));
    else if (robotsDirectives(page.html ?? '').has('noindex')) out.push(finding('sitemap-indexable', 'error', 'Sitemap lists a page marked noindex', loc));
  }
  return out;
}

// 3) canonical presente e coerente (stessi esiti di G-CANONICAL del motore: pass | warn | fail)
export function canonicalStatus(html, finalUrl) {
  const hrefs = [...new Set(canonicals(html))];
  if (hrefs.length === 0) return { status: 'fail', message: 'No rel=canonical in the head' };
  if (hrefs.length > 1) return { status: 'fail', message: `${hrefs.length} conflicting canonical URLs` };
  const href = hrefs[0];
  if (!/^https?:\/\//i.test(href)) return { status: 'warn', message: `Relative canonical '${href}': use an absolute URL` };
  if (robotsDirectives(html).has('noindex')) return { status: 'warn', message: 'canonical together with noindex sends conflicting signals' };
  const target = safeNorm(href);
  if (target === null) return { status: 'warn', message: `Canonical is not a valid URL: '${href}'` };
  if (target !== safeNorm(finalUrl)) return { status: 'warn', message: `Canonical points elsewhere: ${href}` };
  return { status: 'pass', message: 'One absolute canonical matching the page URL' };
}

export function checkCanonical(page) {
  const { status, message } = canonicalStatus(page.html ?? '', page.url);
  if (status === 'pass') return [];
  return [finding('canonical', status === 'fail' ? 'error' : 'warn', message, page.url)];
}

// 4) JSON-LD sintatticamente valido (solo sintassi: la semantica schema.org resta al motore Python)
export function jsonLdStatus(block) {
  if (!block.trim()) return { valid: false, message: 'Empty JSON-LD block' };
  try {
    JSON.parse(block);
    return { valid: true };
  } catch (e) {
    return { valid: false, message: `Invalid JSON-LD: ${e.message}` };
  }
}

export function checkJsonLd(page) {
  const out = [];
  for (const block of jsonLdBlocks(page.html ?? '')) {
    const r = jsonLdStatus(block);
    if (!r.valid) out.push(finding('jsonld-valid', 'error', r.message, page.url));
  }
  return out;
}

// 5) sitemap con lastmod valido
export function checkSitemapLastmod(entries) {
  const out = [];
  const missing = entries.filter((e) => e.lastmod === undefined || e.lastmod === '');
  if (missing.length) out.push(finding('sitemap-lastmod', 'warn', `${missing.length} of ${entries.length} sitemap URLs have no lastmod`));
  for (const e of entries) {
    if (e.lastmod && !isValidLastmod(e.lastmod)) out.push(finding('sitemap-lastmod', 'warn', `Invalid lastmod '${e.lastmod}'`, e.loc));
  }
  return out;
}

/**
 * Verifica un sito già costruito.
 * @param {{robotsTxt?: string|null, sitemapXml?: string|null, pages: {url: string, status?: number, html?: string}[]}} input
 */
export function checkSite({ robotsTxt = null, sitemapXml = null, pages = [] }) {
  const sitemap = sitemapXml == null ? { index: false, entries: [] } : parseSitemap(sitemapXml);
  const paths = pages.map((p) => {
    try {
      return new URL(p.url).pathname || '/';
    } catch {
      return '/';
    }
  });
  // Una pagina che risponde 4xx/5xx non ha un canonical né un JSON-LD da giudicare: la segnala la regola sitemap.
  const live = pages.filter((p) => !(p.status >= 400));
  const findings = [
    ...checkRobotsAiBots(robotsTxt, paths.length ? paths : ['/']),
    ...checkSitemapIndexable(sitemap.entries, pages),
    ...live.flatMap((p) => [...checkCanonical(p), ...checkJsonLd(p)]),
    // Un sitemapindex non si segue: le sue voci sono altre sitemap, non pagine, quindi niente giudizio sul lastmod.
    ...(sitemapXml == null || sitemap.index ? [] : checkSitemapLastmod(sitemap.entries)),
  ];
  const errors = findings.filter((f) => f.severity === 'error').length;
  return { findings, summary: { errors, warnings: findings.length - errors, pages: pages.length } };
}
