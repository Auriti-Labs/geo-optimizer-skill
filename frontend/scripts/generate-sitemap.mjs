#!/usr/bin/env node
// Genera frontend/public/sitemap.xml derivando le route da src/pages/**.
// lastmod onesto: data dell'ultimo commit git che tocca il file sorgente.
// Mantiene l'URL /sitemap.xml (continuità GSC) e NON tocca robots/canonical.
//
// Strategia lastmod (priorità decrescente, ogni scelta non-git è segnalata a stdout):
//   1. file tracciato e MODIFICATO nel working tree → data ODIERNA (marcato DIRTY).
//      Motivo: workflow reale = modifico pagina → genero sitemap → commit. La
//      modifica è il vero "ultimo aggiornamento", anche se non ancora committata.
//   2. file tracciato e PULITO → git log -1 --format=%cs -- <file>  (data ultimo commit).
//   3. git non disponibile o file non tracciato → mtime del file     (fallback segnalato).
//   4. mtime illeggibile → data odierna                              (fallback finale segnalato).
//
// Uso: npm run generate:sitemap   (manuale — vedi nota churn in fondo)

import { execFileSync } from 'node:child_process';
import { readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { join, relative, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const SITE = 'https://geoready.dev';
const __dirname = dirname(fileURLToPath(import.meta.url));
const FRONTEND_ROOT = join(__dirname, '..');
const PAGES_DIR = join(FRONTEND_ROOT, 'src', 'pages');
const OUTPUT = join(FRONTEND_ROOT, 'public', 'sitemap.xml');

// Estensioni che producono una route.
const ROUTE_EXTENSIONS = ['.astro', '.md', '.mdx'];

// Route da escludere dal walk (path file relativo a src/pages, senza estensione).
// Motivi: noindex o non indicizzabili.
const EXCLUDE_ROUTES = new Set([
  '404', // noindex, nofollow
  'report/audit', // noindex, nofollow
  // 'report/[id]' è dinamica → esclusa automaticamente (vedi isDynamic)
]);

// Route generate NON da un file proprio (es. demo prodotta da report/[id].astro).
// Sono aggiunte a mano con il file sorgente da cui derivare il lastmod.
const EXTRA_ROUTES = [
  { url: '/report/demo/', sourceFile: 'report/[id].astro' },
];

// changefreq/priority curati per pagina (preserva i valori storici della sitemap).
// Le route non elencate ricevono i default DEFAULT_META.
const META_BY_PATH = {
  '/': { changefreq: 'weekly', priority: '1.0' },
  '/pricing/': { changefreq: 'weekly', priority: '0.9' },
  '/early-access/': { changefreq: 'weekly', priority: '0.8' },
  '/compare/': { changefreq: 'weekly', priority: '0.8' },
  '/analyze-competitors/': { changefreq: 'weekly', priority: '0.8' },
  '/research/': { changefreq: 'monthly', priority: '0.7' },
  '/roadmap/': { changefreq: 'monthly', priority: '0.7' },
  '/about/': { changefreq: 'monthly', priority: '0.8' },
  '/guides/': { changefreq: 'weekly', priority: '0.8' },
  '/tools/llms-txt-generator/': { changefreq: 'monthly', priority: '0.8' },
  '/ai-seo/': { changefreq: 'weekly', priority: '0.9' },
  '/guides/generative-engine-optimization/': { changefreq: 'monthly', priority: '0.8' },
  '/guides/what-is-llms-txt/': { changefreq: 'monthly', priority: '0.7' },
  '/guides/appear-in-chatgpt-perplexity/': { changefreq: 'monthly', priority: '0.7' },
  '/guides/geo-vs-seo/': { changefreq: 'monthly', priority: '0.7' },
  '/guides/llms-txt-wordpress/': { changefreq: 'monthly', priority: '0.7' },
  '/guides/ai-visibility-checklist/': { changefreq: 'monthly', priority: '0.7' },
  '/guides/ai-citations-check/': { changefreq: 'monthly', priority: '0.7' },
  '/guides/entity-authority/': { changefreq: 'monthly', priority: '0.7' },
  '/guides/multimodal-geo/': { changefreq: 'monthly', priority: '0.7' },
  '/report/demo/': { changefreq: 'monthly', priority: '0.5' },
  '/manifesto/': { changefreq: 'monthly', priority: '0.7' },
  '/privacy/': { changefreq: 'monthly', priority: '0.5' },
  '/cookie-policy/': { changefreq: 'monthly', priority: '0.5' },
  '/tools/ai-citation-checker/': { changefreq: 'monthly', priority: '0.8' },
};
const DEFAULT_META = { changefreq: 'monthly', priority: '0.6' };

// Immagini principali indicizzabili. Le stesse pagine mantengono alt text e caption
// in HTML; questa mappa espone i visual anche nella sitemap.
const IMAGE_BY_PATH = {
  '/': [
    {
      loc: '/assets/geoready-visuals/ai-visibility-command-center.png',
      title: 'GeoReady AI visibility audit dashboard',
      caption: 'GEO score, crawler access, citation graph, recommendations, and score trend in one report.',
    },
    {
      loc: '/assets/geoready-visuals/ai-discovery-stack.png',
      title: 'AI visibility signal stack',
      caption: 'Crawler access, llms.txt, schema, content structure, entity clarity, and citation output.',
    },
    {
      loc: '/assets/geoready-visuals/monitoring-alerts-dashboard.png',
      title: 'GeoReady monitoring and alerts dashboard',
      caption: 'Score history, portfolio checks, regression alerts, and AI answer snapshots.',
    },
    {
      loc: '/assets/geoready-visuals/client-report-export.png',
      title: 'GeoReady report export package',
      caption: 'Score breakdown, recommendations, and PDF export for audit deliverables.',
    },
  ],
  '/pricing/': [
    {
      loc: '/assets/geoready-visuals/client-report-export.png',
      title: 'GeoReady report export package',
      caption: 'Client-ready reporting for paid GeoReady plans.',
    },
  ],
  '/ai-seo/': [
    {
      loc: '/assets/geoready-visuals/ai-discovery-stack.png',
      title: 'AI SEO discovery stack',
      caption: 'How crawler access, llms.txt, schema, entity clarity, and citation output fit into AI SEO.',
    },
  ],
  '/guides/': [
    {
      loc: '/assets/geoready-visuals/ai-discovery-stack.png',
      title: 'AI visibility guide visual',
      caption: 'Technical signal layers behind AI visibility and GEO guides.',
    },
  ],
  '/research/': [
    {
      loc: '/assets/geoready-visuals/ai-discovery-stack.png',
      title: 'Research-backed AI visibility signals',
      caption: 'Visual model of the signals that inform GEO Optimizer scoring.',
    },
  ],
  '/compare/': [
    {
      loc: '/assets/geoready-visuals/ai-visibility-command-center.png',
      title: 'AI visibility comparison dashboard',
      caption: 'Audit dashboard used to compare GEO score, crawler access, citations, and recommendations.',
    },
  ],
  '/analyze-competitors/': [
    {
      loc: '/assets/geoready-visuals/ai-visibility-command-center.png',
      title: 'Competitor AI visibility analysis dashboard',
      caption: 'Dashboard for comparing AI visibility signals across competitor domains.',
    },
  ],
  '/tools/llms-txt-generator/': [
    {
      loc: '/assets/geoready-visuals/ai-discovery-stack.png',
      title: 'llms.txt in the AI discovery stack',
      caption: 'Where llms.txt fits alongside crawler access, schema, and citation output.',
    },
  ],
  '/tools/ai-citation-checker/': [
    {
      loc: '/assets/geoready-visuals/ai-citation-checker.png',
      title: 'AI citation checker interface',
      caption: 'Domain input, AI answer snapshots, citation chips, and citation rate metric.',
    },
  ],
};

// Avvisi (fallback non-git) accumulati durante la generazione, stampati alla fine.
const warnings = [];
// Note informative (es. file dirty → data odierna): comportamento atteso, non errore.
const notes = [];

/** Data odierna in formato YYYY-MM-DD. */
function today() {
  return new Date().toISOString().slice(0, 10);
}

/** True se il file è tracciato da git E ha modifiche non committate nel working tree. */
function isDirty(absPath) {
  try {
    const out = execFileSync('git', ['status', '--porcelain', '--', absPath], {
      cwd: FRONTEND_ROOT,
      stdio: ['ignore', 'pipe', 'ignore'],
      encoding: 'utf8',
    });
    // Output non vuoto = file modificato/staged/untracked. Distinguo untracked ('??').
    const line = out.split('\n').find((l) => l.trim().length > 0);
    if (!line) return false; // pulito
    if (line.startsWith('??')) return false; // non tracciato → gestito dal fallback mtime
    return true; // tracciato e modificato (M, A, R, ...)
  } catch {
    return false; // git non disponibile → la logica chiamante userà il fallback mtime
  }
}

/** Restituisce true se il path file rappresenta una route dinamica ([param]). */
function isDynamicRoute(relPath) {
  return relPath.includes('[') || relPath.includes(']');
}

/** Restituisce true se il file dichiara robots noindex tramite la prop robots. */
function hasNoindex(absPath, source) {
  // Match solo su assegnazione della prop/const robots, non sul testo del body.
  // Es: robots="noindex, nofollow"  oppure  const robots = 'noindex...'
  const robotsAssign = /\brobots\s*[=:]\s*['"][^'"]*noindex/i;
  if (robotsAssign.test(source)) return true;
  return false;
}

/** Converte un path file (relativo a src/pages, senza estensione) in URL con trailing slash. */
function fileToUrl(routePath) {
  // routePath è già senza estensione, separatori '/'.
  if (routePath === 'index') return '/';
  let url = routePath.endsWith('/index')
    ? routePath.slice(0, -'/index'.length)
    : routePath;
  url = '/' + url;
  if (!url.endsWith('/')) url += '/';
  return url;
}

/** Escape minimo per contenuti XML testuali e attributi. */
function xmlEscape(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

/** Walk ricorsivo della cartella pages, ritorna i path file relativi. */
function walkPages(dir) {
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const abs = join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...walkPages(abs));
    } else if (ROUTE_EXTENSIONS.some((ext) => entry.name.endsWith(ext))) {
      out.push(abs);
    }
  }
  return out;
}

/** lastmod del file secondo la gerarchia: dirty→oggi, pulito→git, fallback mtime→oggi. */
function lastmodFor(absPath, relForMsg) {
  // Livello 1: file tracciato e modificato → data odierna (la modifica è il vero update).
  if (isDirty(absPath)) {
    const d = today();
    notes.push(`DIRTY → ${d}: ${relForMsg} ha modifiche non committate — lastmod = oggi (non l'ultimo commit).`);
    return d;
  }

  // Livello 2: file tracciato e pulito → data dell'ultimo commit.
  try {
    const out = execFileSync('git', ['log', '-1', '--format=%cs', '--', absPath], {
      cwd: FRONTEND_ROOT,
      stdio: ['ignore', 'pipe', 'ignore'],
      encoding: 'utf8',
    }).trim();
    if (out) return out;
    // git presente ma nessun commit per il file (file nuovo non committato e non dirty: raro).
    warnings.push(`FALLBACK mtime: ${relForMsg} non ha cronologia git (file nuovo non committato?).`);
  } catch {
    warnings.push(`FALLBACK mtime: git non disponibile per ${relForMsg} (atteso dentro Docker; lancia lo script in locale).`);
  }

  // Livello 3: mtime del file.
  try {
    return statSync(absPath).mtime.toISOString().slice(0, 10);
  } catch {
    /* fallthrough */
  }

  // Livello 4: oggi (fallback finale, segnalato).
  warnings.push(`FALLBACK today: impossibile leggere mtime di ${relForMsg} — uso la data odierna.`);
  return today();
}

function buildEntries() {
  const entries = [];
  /** @type {Set<string>} */
  const seenUrls = new Set();

  // 1. Route derivate dai file.
  for (const absPath of walkPages(PAGES_DIR)) {
    const rel = relative(PAGES_DIR, absPath).replace(/\\/g, '/');
    const routePath = rel.replace(/\.(astro|md|mdx)$/, '');

    if (isDynamicRoute(rel)) continue; // route dinamiche: no URL canonico statico noto
    if (EXCLUDE_ROUTES.has(routePath)) continue;

    let source = '';
    try {
      source = readFileSync(absPath, 'utf8');
    } catch {
      warnings.push(`SKIP: impossibile leggere ${rel} — escluso per sicurezza.`);
      continue;
    }
    if (hasNoindex(absPath, source)) continue;

    const url = fileToUrl(routePath);
    if (seenUrls.has(url)) continue;
    seenUrls.add(url);

    entries.push({ url, lastmod: lastmodFor(absPath, rel) });
  }

  // 2. Route extra (generate, non da file proprio).
  for (const extra of EXTRA_ROUTES) {
    if (seenUrls.has(extra.url)) continue;
    const absSrc = join(PAGES_DIR, extra.sourceFile);
    seenUrls.add(extra.url);
    entries.push({ url: extra.url, lastmod: lastmodFor(absSrc, extra.sourceFile) });
  }

  // Ordine stabile: home prima, poi alfabetico.
  entries.sort((a, b) => (a.url === '/' ? -1 : b.url === '/' ? 1 : a.url.localeCompare(b.url)));
  return entries;
}

function renderXml(entries) {
  const urls = entries
    .map((e) => {
      const meta = META_BY_PATH[e.url] || DEFAULT_META;
      const images = IMAGE_BY_PATH[e.url] || [];
      const imageXml = images
        .map((img) => [
          '    <image:image>',
          `      <image:loc>${xmlEscape(SITE + img.loc)}</image:loc>`,
          `      <image:title>${xmlEscape(img.title)}</image:title>`,
          `      <image:caption>${xmlEscape(img.caption)}</image:caption>`,
          '    </image:image>',
        ].join('\n'))
        .join('\n');
      return [
        '  <url>',
        `    <loc>${SITE}${e.url}</loc>`,
        `    <lastmod>${e.lastmod}</lastmod>`,
        `    <changefreq>${meta.changefreq}</changefreq>`,
        `    <priority>${meta.priority}</priority>`,
        imageXml,
        '  </url>',
      ].filter(Boolean).join('\n');
    })
    .join('\n');
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n${urls}\n</urlset>\n`;
}

// --- main ---
const entries = buildEntries();
const xml = renderXml(entries);
writeFileSync(OUTPUT, xml, 'utf8');

console.log(`sitemap.xml generata: ${entries.length} URL → ${relative(FRONTEND_ROOT, OUTPUT)}`);
for (const e of entries) console.log(`  ${e.lastmod}  ${SITE}${e.url}`);
if (notes.length) {
  console.log(`\n${notes.length} nota/e (comportamento atteso):`);
  for (const n of notes) console.log(`  • ${n}`);
}
if (warnings.length) {
  console.log(`\n${warnings.length} avviso/i (fallback non-git):`);
  for (const w of warnings) console.log(`  ⚠️  ${w}`);
}
if (!notes.length && !warnings.length) {
  console.log('\nTutti i lastmod derivano da commit git puliti (nessun file dirty, nessun fallback).');
}
