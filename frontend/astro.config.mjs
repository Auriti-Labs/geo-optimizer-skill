// @ts-check
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { defineConfig } from 'astro/config';
import { loadEnv } from 'vite';

import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';
import sanity from '@sanity/astro';
import sitemap from '@astrojs/sitemap';
import starlight from '@astrojs/starlight';

import geoReady from '../integrations/astro-geoready/index.mjs';
import { aiFaqs, aiService } from './src/data/ai-content.mjs';

// The engine version is owned by pyproject.toml. Reading it here at build time
// keeps the navbar/footer/roadmap badges from drifting away from the package that
// is actually installed in the image — they were pinned at 4.14.0 by hand while
// the container shipped 4.15.0.
const pyprojectPath = fileURLToPath(new URL('../pyproject.toml', import.meta.url));
const versionMatch = readFileSync(pyprojectPath, 'utf8').match(
  /^version\s*=\s*["']([^"']+)["']/m
);

if (!versionMatch) {
  throw new Error(`Could not read version from ${pyprojectPath}`);
}

const engineVersion = versionMatch[1];

const { PUBLIC_SANITY_PROJECT_ID, PUBLIC_SANITY_DATASET } = loadEnv(
  process.env.NODE_ENV ?? 'development',
  process.cwd(),
  ''
);

export default defineConfig({
  site: 'https://geoready.dev',
  trailingSlash: 'always',
  integrations: [
    react(),
    // robots.txt points to the hand-built /sitemap.xml. This second, automatic
    // sitemap-index.xml is still published, so it must not list pages that
    // carry noindex: the mock report, the report shell and the visual lab.
    sitemap({
      filter: (page) => !/\/(report\/(?!demo\/)|visual-lab\/)/.test(page),
    }),
    sanity({
      projectId: PUBLIC_SANITY_PROJECT_ID ?? 'uvzrnk4t',
      dataset: PUBLIC_SANITY_DATASET ?? 'production',
      useCdn: false,
    }),
    geoReady({
      siteName: 'GeoReady',
      description:
        'AI visibility audit, monitoring, and citation tracking — built on the open-source GEO Optimizer engine.',
      faqs: aiFaqs,
      service: aiService,
    }),
    starlight({
      title: 'GeoReady Docs',
      favicon: '/favicon.svg',
      logo: {
        src: './src/assets/geoready-logo.svg',
        replacesTitle: false,
      },
      sidebar: [
        {
          label: 'Getting started',
          items: [
            { label: 'Introduction', link: '/docs/getting-started/' },
            { label: 'Troubleshooting', link: '/docs/troubleshooting/' },
            { label: 'CI/CD', link: '/docs/ci-cd/' },
          ],
        },
        {
          label: 'CLI commands',
          items: [
            { label: 'geo audit', link: '/docs/geo-audit/' },
            { label: 'geo fix', link: '/docs/geo-fix/' },
            { label: 'geo diff', link: '/docs/geo-diff/' },
            { label: 'geo track', link: '/docs/geo-track/' },
            { label: 'geo history', link: '/docs/geo-history/' },
            { label: 'geo monitor', link: '/docs/geo-monitor/' },
            { label: 'geo snapshots', link: '/docs/geo-snapshots/' },
            { label: 'geo logs', link: '/docs/geo-logs/' },
            { label: 'geo coherence', link: '/docs/geo-coherence/' },
            { label: 'GEO methods', link: '/docs/geo-methods/' },
            { label: 'Schema injector', link: '/docs/schema-injector/' },
          ],
        },
        {
          label: 'Scoring',
          items: [{ label: 'Scoring rubric', link: '/docs/scoring-rubric/' }],
        },
        {
          label: 'Content & files',
          items: [
            { label: 'llms.txt', link: '/docs/llms-txt/' },
            { label: 'AI bots reference', link: '/docs/ai-bots-reference/' },
            { label: 'AI context', link: '/docs/ai-context/' },
          ],
        },
        {
          label: 'Infrastructure',
          items: [
            { label: 'JSON contract', link: '/docs/json-contract/' },
            { label: 'LLM providers', link: '/docs/llm-providers/' },
          ],
        },
        {
          label: 'Web, MCP & API',
          items: [{ label: 'MCP server', link: '/docs/mcp-server/' }],
        },
      ],
      customCss: ['./src/styles/docs.css'],
    }),
  ],

  vite: {
    define: {
      __ENGINE_VERSION__: JSON.stringify(engineVersion),
    },
    plugins: [tailwindcss()],
    server: {
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
        '/badge': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
      },
    },
  },
});
