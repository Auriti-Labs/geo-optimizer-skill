# Deployment record — GeoReady CLS & branding follow-up

**Date:** 2026-06-16
**Scope:** `geoready.dev` public site (the hosted GeoReady product surface)
**Result:** Deployed and verified live. No known regressions post-smoke.

> **Positioning note.** *GeoReady* is the public site / product / hosted SaaS.
> *GEO Optimizer* is the open-source engine, CLI, methodology, and repository
> that powers it. This record is about the public **site**; it does not rename
> the engine. When the text below says "GeoReady" it means the site surface,
> not the engine.

---

## What shipped

Two related changes were deployed to the public site:

1. **Mobile CLS fix on the cookie banner** — the consent banner grew in height
   once a medium/semibold web font finished loading on slow connections, which
   shifted the fixed banner and hurt Cumulative Layout Shift on a couple of
   content pages.
2. **Branding / discovery / CSP follow-up** — align the public site naming to
   *GeoReady* across page titles, copy, and AI-discovery metadata, preserve
   discovery metadata in the sitemap, and assert the analytics CSP allowlist.

## Commits deployed

| Commit | Summary |
|--------|---------|
| `fbbfff1` | `perf(fonts)`: self-host Geist 500/600 to fix cookie banner CLS |
| `22c8087` | `fix(web)`: serve woff2 with correct MIME type |
| `290cd68` | `test(web)`: assert Launchpadly CSP allowlist |
| `9fbb188` | `fix(seo)`: preserve discovery metadata in sitemap |
| `a2684bf` | `fix(brand)`: align GeoReady naming across site surfaces |

Live target after deploy: `a2684bf385601e158364ac58446ca3c5bd6471cc`.

## What was corrected

- **Cookie banner CLS (mobile):** the banner used font weights (Geist 500 for
  buttons, Geist 600 for the title) still loaded with `font-display: swap`. On
  slow networks the late swap changed text metrics, grew the fixed banner, and
  pushed it upward — the real cause of the layout shift. Self-hosting those two
  weights with `font-display: optional` (same pattern already used for the body
  and heading weights) means the font arriving no longer changes the banner
  height. The banner markup and the consent logic were not changed.
- **Font MIME type:** woff2 files are now served as `font/woff2` instead of
  `application/octet-stream`, so the `<link rel="preload" as="font">` hint is
  not invalidated.
- **GeoReady branding:** page titles, on-page copy, and structured data on the
  public site now consistently say *GeoReady*.
- **Sitemap metadata:** discovery metadata is preserved and `lastmod` reflects
  the deploy date for the key pages.
- **AI discovery files:** `llms.txt` and `llms-full.txt` headers are realigned
  to the GeoReady site branding.
- **CSP allowlist:** the analytics provider origin is present in the
  Content-Security-Policy header, covered by a regression test.

## Live smoke results

All checks passed. Only non-sensitive status/values are recorded.

| Check | Result |
|-------|--------|
| `/` | 200 |
| `/pricing/` | 200 |
| `/privacy/` | 200 |
| `/cookie-policy/` | 200 |
| `/report/demo/` | 200 |
| `/compare/` | 200 |
| `/analyze-competitors/` | 200 |
| `/guides/` | 200 |
| `sitemap.xml` | valid XML, `lastmod 2026-06-16` for homepage, pricing, guides, report/demo, tools |
| `llms.txt` header | `# GeoReady` |
| `llms-full.txt` header | `# GeoReady — Full LLM Context` |
| `/privacy/` title | `Privacy Policy — GeoReady` |
| `/cookie-policy/` title | `Cookie Policy — GeoReady` |
| `/report/demo/` title | `GeoReady Audit Report Demo` |
| `/pricing/` schema/copy | `GeoReady` |
| CSP header | contains the analytics provider origin `https://launchpadly.co` |
| woff2 `Content-Type` | `font/woff2` |

### Core Web Vitals (mobile, throttled lab measurement)

| Page | CLS before | CLS after | LCP after |
|------|-----------|-----------|-----------|
| `/pricing/` | 0.11 | 0.0005 | ~1264 ms |
| `/best-geo-tools/` | 0.11 | 0.0004 | ~1111 ms |

LCP did not regress; both pages stay well within the "good" threshold.

## Residual risks

- None known after the post-deploy smoke.
- **Rollback:** the previous container image was retained as a tagged rollback
  image before the new build was promoted, so the site can be reverted to the
  prior release without rebuilding. Infrastructure-specific commands are
  intentionally omitted from this public record.

## Verification method (summary)

CLS was confirmed on a cold-cache mobile profile by observing that the cookie
banner height no longer changes when the medium/semibold font finishes loading.
Layout-shift sources were inspected directly to confirm the banner was the sole
contributor before the fix.
