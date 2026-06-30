// @ts-check
import { defineConfig } from 'astro/config';

import react from '@astrojs/react';

import tailwindcss from '@tailwindcss/vite';

// Dogfooding: the same integration we ship on npm (astro-geoready).
// Skips the hand-curated public/llms.txt; generates the AI discovery files.
import geoReady from '../integrations/astro-geoready/index.mjs';
import { aiFaqs, aiService } from './src/data/ai-content.mjs';

// https://astro.build/config
export default defineConfig({
  site: 'https://geoready.dev',
  trailingSlash: 'always',
  integrations: [
    react(),
    geoReady({
      siteName: 'GeoReady',
      description:
        'AI visibility audit, monitoring, and citation tracking — built on the open-source GEO Optimizer engine.',
      faqs: aiFaqs,
      service: aiService,
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
