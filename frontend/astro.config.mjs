// @ts-check
import { defineConfig } from 'astro/config';
import { loadEnv } from 'vite';

import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';
import sanity from '@sanity/astro';

import geoReady from '../integrations/astro-geoready/index.mjs';

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
    }),
  ],

  vite: {
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
