/**
 * astro-geoready — make an Astro site GEO-ready at build time.
 *
 * Generates the text scaffolding AI engines use to discover and understand a
 * site, straight from the route list Astro already knows — no HTTP, no crawl:
 *
 *   /llms.txt                 Markdown index of your pages, grouped by section
 *   /.well-known/ai.txt       AI crawler welcome file
 *   /ai/summary.json          machine-readable site summary
 *   /ai/faq.json              curated FAQ (when `faqs` is provided)
 *   /ai/service.json          service/offer descriptor (when `service` is provided)
 *
 * Existing files are never overwritten (your hand-curated llms.txt wins);
 * pass `overwrite: true` to regenerate on every build.
 *
 * Companion to the GEO Optimizer audit engine — the same files this
 * integration emits are the ones `geo audit` scores under llms.txt (18 pts)
 * and AI Discovery (6 pts). https://github.com/Auriti-Labs/geo-optimizer-skill
 */

import { existsSync } from 'node:fs';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

/** Title-case a slug segment: "getting-started" → "Getting Started". */
function humanize(segment) {
  if (!segment) return '';
  return segment
    .split(/[-_]/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

/** Group page pathnames by their first path segment. */
function groupPages(pages, maxPerSection) {
  const sections = new Map();
  for (const { pathname } of pages) {
    const clean = pathname.replace(/^\/+|\/+$/g, '');
    if (clean.startsWith('404') || clean.startsWith('500')) continue;
    const segments = clean.split('/').filter(Boolean);
    const section = segments.length > 1 ? humanize(segments[0]) : 'Pages';
    const title = humanize(segments[segments.length - 1] || 'Home') || 'Home';
    if (!sections.has(section)) sections.set(section, []);
    const entries = sections.get(section);
    if (entries.length < maxPerSection) entries.push({ title, pathname: clean });
  }
  // "Pages" (root-level) first, then alphabetical.
  return [...sections.entries()].sort(([a], [b]) =>
    a === 'Pages' ? -1 : b === 'Pages' ? 1 : a.localeCompare(b),
  );
}

function buildLlmsTxt({ siteName, description, siteUrl, pages, maxPerSection }) {
  const lines = [`# ${siteName}`, ''];
  if (description) lines.push(`> ${description}`, '');
  for (const [section, entries] of groupPages(pages, maxPerSection)) {
    lines.push(`## ${section}`, '');
    for (const { title, pathname } of entries) {
      const url = pathname ? `${siteUrl}/${pathname}/` : `${siteUrl}/`;
      lines.push(`- [${title}](${url})`);
    }
    lines.push('');
  }
  lines.push(`Generated at build time by astro-geoready. Audit this site: https://geoready.dev`);
  return lines.join('\n') + '\n';
}

function buildAiTxt({ siteName, siteUrl }) {
  return [
    `# ai.txt — AI crawler guidance for ${siteName}`,
    `# Spec: https://site.spawning.ai/spawning-ai-txt`,
    '',
    'User-Agent: *',
    'Allow: /',
    '',
    `Sitemap: ${siteUrl}/sitemap.xml`,
    `LLMs: ${siteUrl}/llms.txt`,
    '',
  ].join('\n');
}

function buildSummaryJson({ siteName, description, siteUrl, pages }) {
  return JSON.stringify(
    {
      name: siteName,
      description: description || undefined,
      url: siteUrl,
      pages_count: pages.length,
      llms_txt: `${siteUrl}/llms.txt`,
      generated_by: 'astro-geoready',
      generated_at: new Date().toISOString(),
    },
    null,
    2,
  ) + '\n';
}

/** Machine-readable FAQ for AI answer engines, from the curated `faqs` option. */
function buildFaqJson({ siteName, siteUrl, faqs }) {
  return JSON.stringify(
    {
      name: `${siteName} — FAQ`,
      url: siteUrl,
      questions: faqs.map(({ q, a }) => ({ question: q, answer: a })),
      generated_by: 'astro-geoready',
      generated_at: new Date().toISOString(),
    },
    null,
    2,
  ) + '\n';
}

/** Machine-readable service/offer descriptor for AI answer engines. */
function buildServiceJson({ siteName, description, siteUrl, service }) {
  return JSON.stringify(
    {
      name: siteName,
      description: description || undefined,
      url: siteUrl,
      service_type: service.type || undefined,
      provider: service.provider || undefined,
      offers: service.offers || undefined,
      features: service.features || undefined,
      generated_by: 'astro-geoready',
      generated_at: new Date().toISOString(),
    },
    null,
    2,
  ) + '\n';
}

/**
 * @param {object} [options]
 * @param {string} [options.siteName]      Site name for headers (default: site hostname).
 * @param {string} [options.description]   One-line description for llms.txt and summary.json.
 * @param {boolean} [options.llmsTxt]      Generate /llms.txt (default true).
 * @param {boolean} [options.aiDiscovery]  Generate /.well-known/ai.txt and /ai/summary.json (default true).
 * @param {boolean} [options.overwrite]    Overwrite files that already exist (default false).
 * @param {number}  [options.maxPerSection] Max links per llms.txt section (default 20).
 * @param {Array<{q: string, a: string}>} [options.faqs] Curated FAQ — emits /ai/faq.json when non-empty.
 * @param {object} [options.service] Service/offer descriptor — emits /ai/service.json when set.
 * @returns {import('astro').AstroIntegration}
 */
export default function geoReady(options = {}) {
  const {
    siteName,
    description = '',
    llmsTxt = true,
    aiDiscovery = true,
    overwrite = false,
    maxPerSection = 20,
    faqs = [],
    service = null,
  } = options;

  let siteUrl = '';

  async function emit(dirPath, relative, content, logger) {
    const target = path.join(dirPath, relative);
    if (!overwrite && existsSync(target)) {
      logger.info(`${relative} already exists — skipped (set overwrite: true to regenerate)`);
      return;
    }
    await mkdir(path.dirname(target), { recursive: true });
    await writeFile(target, content, 'utf-8');
    logger.info(`generated ${relative}`);
  }

  return {
    name: 'astro-geoready',
    hooks: {
      'astro:config:done': ({ config }) => {
        siteUrl = (config.site || '').replace(/\/+$/, '');
      },
      'astro:build:done': async ({ pages, dir, logger }) => {
        if (!siteUrl) {
          logger.warn('`site` is not set in astro.config — skipping (absolute URLs are required)');
          return;
        }
        const dirPath = fileURLToPath(dir);
        const name = siteName || new URL(siteUrl).hostname;
        const ctx = { siteName: name, description, siteUrl, pages, maxPerSection, faqs, service };

        if (llmsTxt) await emit(dirPath, 'llms.txt', buildLlmsTxt(ctx), logger);
        if (aiDiscovery) {
          await emit(dirPath, path.join('.well-known', 'ai.txt'), buildAiTxt(ctx), logger);
          await emit(dirPath, path.join('ai', 'summary.json'), buildSummaryJson(ctx), logger);
          if (faqs.length) await emit(dirPath, path.join('ai', 'faq.json'), buildFaqJson(ctx), logger);
          if (service) await emit(dirPath, path.join('ai', 'service.json'), buildServiceJson(ctx), logger);
        }
      },
    },
  };
}
