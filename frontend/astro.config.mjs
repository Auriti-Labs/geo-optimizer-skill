// @ts-check
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { defineConfig } from 'astro/config';
import { loadEnv } from 'vite';

import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';
import sanity from '@sanity/astro';

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
