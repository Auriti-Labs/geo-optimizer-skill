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
- Not published: the package is `private` until the API settles (0.x, Node >= 22).

## Conformance

The cases in [`../../conformance`](../../conformance) are shared with the Python engine. `npm test` runs them.

## Public contract

Read from `src/` as it is today (0.0.1, `private`). It is what callers may rely on until the API settles; anything not
listed here is internal.

### Finding

```js
{ rule, severity, message, url? }
```

- `rule`: one of the five stable IDs below.
- `severity`: `'error'` or `'warn'`. There is no other level.
- `message`: English text for people. Its wording is not part of the contract; match on `rule` and `severity`.
- `url`: present only when the finding is about one URL, and only when that URL is a non-empty string. It is the
  page URL as given in `pages[].url` (`canonical`, `jsonld-valid`) or the sitemap `<loc>` as written
  (`sitemap-indexable`, invalid `sitemap-lastmod`). It is not normalised.

| Rule ID | Severity | `url` |
|---------|----------|-------|
| `robots-ai-bots` | `error`, one finding per blocked bot | never |
| `sitemap-indexable` | `error` (4xx/5xx or `noindex`) | always (the `<loc>`) |
| `canonical` | `error` when missing or conflicting (status `fail`); `warn` when relative, with `noindex`, not a valid URL, or pointing to another URL (status `warn`) | always (the page URL) |
| `jsonld-valid` | `error`, one finding per invalid or empty block | always (the page URL) |
| `sitemap-lastmod` | `warn`: one finding for all entries without `lastmod`, one per invalid value | missing: never; invalid: the `<loc>` |

### Summary

`checkSite` returns `{ findings, summary }` with `summary = { errors, warnings, pages }`: `errors` counts findings
with severity `error`, `warnings` counts every other finding, `pages` is `pages.length` as passed in (error pages
included).

### Exports of `src/index.js`

| Export | Returns |
|--------|---------|
| `checkSite({ robotsTxt?, sitemapXml?, pages })` | `{ findings, summary }`. robots is checked on the path of every page (`/` when there are none); canonical and JSON-LD only on pages whose `status` is not >= 400; `lastmod` only for a `urlset`, not a sitemap index |
| `checkRobotsAiBots(robotsTxt, paths = ['/'])` | findings; `[]` when `robotsTxt` is `null` or `undefined` |
| `checkSitemapIndexable(entries, pages)` | findings for entries matching a page (after `normUrl`) with `status >= 400` or `noindex` |
| `checkCanonical(page)` | `[]` on pass, otherwise one finding |
| `canonicalStatus(html, finalUrl)` | `{ status: 'pass' \| 'warn' \| 'fail', message }`, the same outcomes as `G-CANONICAL` in the Python engine |
| `checkJsonLd(page)` | one finding per invalid block |
| `jsonLdStatus(block)` | `{ valid: true }` or `{ valid: false, message }` |
| `checkSitemapLastmod(entries)` | findings as in the table above |
| `AI_SEARCH_BOTS` | `['OAI-SearchBot', 'Claude-SearchBot', 'PerplexityBot']` |
| `normUrl(url)` | lower-case scheme and host, no trailing slash except on the root path, query kept, fragment dropped; throws on an invalid URL |
| `isBlocked(robotsTxt, bot, path)` | `true` when the bot's group (else `*`) disallows `path` (RFC 9309, longest match, Allow wins a tie) |
| `parseRobots(content)` | `Map` from lower-case agent to `{ allow: string[], disallow: string[] }` |
| `parseSitemap(xml)` | `{ index: boolean, entries: { loc, lastmod? }[] }`; entries without `<loc>` are dropped |
| `isValidLastmod(value)` | `true` for a W3C datetime with a real calendar date and time; `false` otherwise, non-strings included |
| `canonicals(html)` | every `rel=canonical` href in the `<head>`, trimmed, duplicates kept |
| `robotsDirectives(html)` | `Set` of lower-case directives from `meta` robots, googlebot and bingbot (`none` adds `noindex` and `nofollow`) |
| `jsonLdBlocks(html)` | body of every `<script type="application/ld+json">`, parameters and case ignored in the type; HTML comments are removed first, inside script bodies too (divergence D4 in `conformance/README.md`) |

### Missing versus not observable

The core does not distinguish "absent" from "not observed" today. There is no status for "not checked" in a finding
or in the summary, so a clean result can mean either. Concretely:

- `robotsTxt: null` means "no file, no restriction": no finding, the same result as a permissive file.
- `sitemapXml: null` gives no sitemap finding, the same result as a clean sitemap.
- A sitemap URL with no matching page in `pages` is skipped, not reported.
- A sitemap index is recognised and its children are not read; nothing is reported for them.
- A page without `status` is treated as live; a page without `html` is read as an empty document, so it gets a
  `canonical` `error` ("No rel=canonical in the head") even if the page could not be read.
- `noindex` sent as an `X-Robots-Tag` header is not seen; such a page is not reported by `sitemap-indexable`.
- A missing `lastmod` is the one case reported as missing (`sitemap-lastmod` `warn`).

A caller that wants to tell the two apart has to do it before calling the core, by what it passes in.

## Canonical pointing to another URL

A canonical that points to another URL is reported as `canonical` with severity `warn`, never `error`. It is counted
in `summary.warnings`, not in `summary.errors`, so a caller that fails a build on errors does not fail on it.

There is no per-page exception mechanism: `checkSite` takes `robotsTxt`, `sitemapXml` and `pages` and nothing else,
so a page cannot be marked as "canonical elsewhere on purpose". The reason is that pointing elsewhere is often
deliberate (a paginated or filtered view, a syndicated copy, a print version), so the core cannot tell a mistake
from a choice. Making it a `warn` keeps such pages from breaking a build without an exception list, and the API is
not settled enough (0.x, `private`) to add a configuration input. Today a caller can filter on `rule === 'canonical'`
and `url`, since the finding always carries the page URL.

What would close it: a decision on where exceptions live, either an input to `checkSite` (for example a list of
page URLs or patterns per rule, which becomes part of this contract) or a documented rule that callers filter
findings themselves. Either way the decision should come with conformance cases for the excepted page.
