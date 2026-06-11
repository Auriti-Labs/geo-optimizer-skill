# GeoReady — WordPress plugin

Make a WordPress site **visible to AI answer engines** (ChatGPT, Perplexity,
Gemini). The WordPress counterpart of [`astro-geoready`](../astro-geoready):

| What | How |
|---|---|
| **`/llms.txt`** | Generated from your published pages/posts, grouped by post type |
| **`/.well-known/ai.txt`** | AI crawler guidance file (sitemap + llms.txt pointers) |
| **`/ai/summary.json`** | Machine-readable site summary |
| **AI visibility score** | One click runs a GEO/AEO audit (0–100) via the public GeoReady API and shows the top fixes |

This is **Answer Engine Optimization (AEO)** / **Generative Engine Optimization
(GEO)** for WordPress, powered by the open-source
[GEO Optimizer](https://github.com/Auriti-Labs/geo-optimizer-skill) engine.

## Install (development)

```bash
# Symlink or copy this folder into your WordPress install
cp -r integrations/wordpress-geoready /path/to/wp-content/plugins/geoready
```

Activate it, then go to **Settings → GeoReady**. After activation the rewrite
rules are flushed automatically so `/llms.txt` resolves.

## How it works

- The three files are served as **virtual routes** via WordPress rewrite rules,
  so a real static file at the same path is never shadowed — your hand-curated
  `llms.txt` always wins.
- The pure builders (`includes/class-geoready-builder.php`) have no WordPress
  dependency, so they're unit-testable with plain PHP:

  ```bash
  php test/test-builder.php   # 20 assertions, no WordPress, no PHPUnit
  ```

- The "Check my AI visibility" button calls `https://geoready.dev/api/audit`
  (the same engine as `geo audit`) and renders score, band, and recommendations.

## Files

```
geoready.php                         plugin bootstrap (WP header, hooks)
includes/class-geoready-builder.php  pure llms.txt / ai.txt / summary.json builders
includes/class-geoready-files.php    virtual-route registration + rendering
includes/class-geoready-admin.php    settings page + AJAX audit
readme.txt                           WordPress.org plugin readme
uninstall.php                        option cleanup
test/test-builder.php                plain-PHP unit tests
```

## Notes

- llms.txt is an orientation file, not a confirmed ranking factor — it helps AI
  systems understand your site; it does not guarantee citations.
- For continuous monitoring, score history, and AI citation tracking, see the
  hosted [GeoReady](https://geoready.dev) platform.

GPL-2.0-or-later © [Auriti Labs](https://github.com/Auriti-Labs)
