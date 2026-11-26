# astro-geoready

Make your Astro site **GEO-ready at build time**. Generates the text
text files that describe your site to AI tools and agents, straight from
the route list Astro already knows — no crawling, no HTTP:

| File | Purpose |
|---|---|
| `/llms.txt` | Markdown index of your pages, grouped by section — the orientation file AI systems read first |
| `/.well-known/ai.txt` | AI crawler guidance file (sitemap + llms.txt pointers) |
| `/ai/summary.json` | Machine-readable site summary |

These are files the open-source
[GEO Optimizer](https://github.com/Auriti-Labs/geo-optimizer-skill) audit
checks for (llms.txt and AI discovery). Generate them here, verify them with
`geo audit`.

## Install

```bash
npm install astro-geoready
```

```js
// astro.config.mjs
import { defineConfig } from 'astro/config';
import geoReady from 'astro-geoready';

export default defineConfig({
  site: 'https://yoursite.com',   // required — absolute URLs need it
  integrations: [
    geoReady({
      siteName: 'Your Site',
      description: 'One line about what your site is.',
    }),
  ],
});
```

Run `astro build` — the files land in `dist/` and deploy with everything else.

## Options

| Option | Default | Notes |
|---|---|---|
| `siteName` | site hostname | H1 of llms.txt |
| `description` | `''` | Blockquote line in llms.txt + summary.json |
| `llmsTxt` | `true` | Generate `/llms.txt` |
| `aiDiscovery` | `true` | Generate `/.well-known/ai.txt` + `/ai/summary.json` |
| `overwrite` | `false` | **Never overwrites existing files by default** — your hand-curated `public/llms.txt` always wins |
| `maxPerSection` | `20` | Max links per llms.txt section |

## Notes

- An llms.txt is an optional, informal proposal, not a standard. Google states
  that Google Search and AI Overviews do not use it, and no major AI vendor has
  said its crawlers read it; server-log studies find such requests are rare. It
  is low-cost to publish, but nothing shows that it increases citations or
  visibility. What the vendors do document is robots.txt: make sure it does not
  block the AI search bots you want to be found by.
- The generated file is a solid starting point; a hand-curated one (better
  titles, descriptions per link) is still stronger. Generate, then refine.
- Verify the result: `uvx --from geo-optimizer-skill geo audit --url https://yoursite.com`
  or the free audit at [geoready.dev](https://geoready.dev).

MIT © [Auriti Labs](https://github.com/Auriti-Labs)
