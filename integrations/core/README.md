# @auriti-labs/geo-core

Dependency-free build checks for AI search visibility. Five rules, each backed by vendor or Google documentation:

| Rule | What it reports |
|------|-----------------|
| `robots-ai-bots` | robots.txt blocks `OAI-SearchBot`, `Claude-SearchBot` or `PerplexityBot` on a built page |
| `sitemap-indexable` | the sitemap lists a page that answers 4xx/5xx or is marked `noindex` |
| `canonical` | no canonical, conflicting canonicals, a relative one, or one pointing elsewhere |
| `jsonld-valid` | a JSON-LD block that is empty or not valid JSON |
| `sitemap-lastmod` | sitemap URLs without `lastmod`, or with a value that is not a W3C datetime |

```js
import { checkSite } from '@auriti-labs/geo-core';

const { findings, summary } = checkSite({
  robotsTxt, // string, or null when the site has none (no file = no restriction)
  sitemapXml, // string, or null
  pages: [{ url: 'https://example.com/', status: 200, html }],
});
```

It scores nothing and judges nothing beyond these five verifiable defects. `llms.txt` is not checked.

## Limits

- HTML is read with regular expressions, on well-formed pages. The Python engine uses a real parser.
- JSON-LD is checked for syntax only; schema.org semantics stay with the Python engine.
- A sitemap index is recognised, not followed.
- `noindex` is read from `<meta name=robots|googlebot|bingbot>` only (`none` counts); `X-Robots-Tag` headers are not seen. Python ignores `bingbot`, JS counts it.
- URL comparison uses the WHATWG parser: `:443`, `/a/../b` and non-ASCII paths compare equal here, while the Python engine reports a warning.
- Duplicate `User-agent` groups that differ only in case are merged (RFC 9309); the Python engine reads the first one.
- Pages answering 4xx/5xx are reported by `sitemap-indexable` only; their canonical and JSON-LD are not judged.
- Not published: the package is `private` until the API settles (0.x, Node >= 20).

## Conformance

The cases in [`../../conformance`](../../conformance) are shared with the Python engine. `npm test` runs them.
