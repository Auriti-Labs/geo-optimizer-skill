=== GeoReady — AI Visibility & AEO ===
Contributors: auritilabs
Tags: aeo, generative engine optimization, ai seo, llms.txt, ai search
Requires at least: 5.8
Tested up to: 6.7
Requires PHP: 7.4
Stable tag: 0.1.0
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

Make your WordPress site visible to AI answer engines. Generate llms.txt and AI discovery files, and score your AI search readiness (GEO/AEO).

== Description ==

AI answer engines — ChatGPT, Perplexity, Google AI Overviews, Gemini — give one synthesized answer and cite a handful of sources. If your site isn't one of them, you're invisible, even if you rank on Google. This is **Answer Engine Optimization (AEO)**, also called **Generative Engine Optimization (GEO)** or **AI SEO**.

GeoReady makes your WordPress site ready to be found, understood, and cited by AI:

* **Generates `llms.txt`** at your site root from your published pages and posts — the orientation file AI systems read first.
* **Generates AI discovery files** — `/.well-known/ai.txt` and `/ai/summary.json`.
* **Scores your AI visibility** — one click runs a GEO audit and shows your 0–100 score, band, and the top fixes, powered by the open-source [GEO Optimizer](https://github.com/Auriti-Labs/geo-optimizer-skill) engine.

Everything is generated from content you already have. Existing files are never overwritten. No account required.

For continuous monitoring, score history, and AI citation tracking across ChatGPT and Perplexity, see the hosted [GeoReady](https://geoready.dev) platform.

== Installation ==

1. Upload the plugin to `/wp-content/plugins/geoready` or install it from the Plugins screen.
2. Activate it.
3. Go to **Settings → GeoReady**, choose which files to generate and which post types to include.
4. Click **Check my AI visibility now** to score your site.
5. Visit `https://yoursite.com/llms.txt` to confirm the file is served.

== Frequently Asked Questions ==

= What is llms.txt? =
A plain-text Markdown file at your site root that indexes your most important pages so AI systems can orient themselves. It is an orientation signal, not a guaranteed ranking factor.

= Will it overwrite a file I already have? =
No. The files are served as virtual routes only when no real file exists at that path, so a hand-curated `llms.txt` always wins.

= Does it send my content anywhere? =
The generated files are built locally from your published content. The "Check my AI visibility" button sends only your site URL to the public GeoReady audit API to compute a score.

= Which AI engines does this help with? =
ChatGPT, Perplexity, Google AI Overviews, Gemini, and Claude — the audit covers 27 AI crawlers and 8 scoring categories.

== Changelog ==

= 0.1.0 =
* Initial release: llms.txt + AI discovery file generation, one-click AI visibility audit.
