# Generating llms.txt

`geo llms` auto-generates an `/llms.txt` file from your sitemap so AI crawlers can understand your site's structure.

---

## What is llms.txt?

`llms.txt` is a plain-text Markdown file placed at the root of your website (`https://yoursite.com/llms.txt`). It works like `robots.txt` but for AI language models: instead of telling crawlers what to block, it tells them what to read and how to understand your site.

Spec: [llmstxt.org](https://llmstxt.org)

A well-structured `llms.txt` helps AI crawlers:
- Understand what your site is about before crawling individual pages
- Discover your most important pages quickly
- Categorize your content into logical sections
- Extract a concise site summary for use in AI-generated answers

---

## Why It Matters

AI crawlers (Perplexity, Claude, ChatGPT Search) use `llms.txt` as a trust and structure signal. Sites without it are treated as generic; sites with it are indexed more accurately. When a user asks an AI a question your site answers, having a well-structured `llms.txt` increases the probability of being cited.

---

## Usage

```bash
# Minimal — auto-detects sitemap from robots.txt
geo llms --base-url https://yoursite.com

# Full options
geo llms \
  --base-url https://yoursite.com \
  --site-name "MySite" \
  --description "Free online calculators for finance and math" \
  --output ./public/llms.txt \
  --sitemap https://yoursite.com/sitemap.xml \
  --max-per-section 10 \
  --fetch-titles
```

### All Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--base-url` | *(required)* | Root URL of the site (e.g. `https://yoursite.com`) |
| `--output` | `./llms.txt` | Output file path |
| `--sitemap` | auto-detected | Direct URL to the sitemap XML; skips auto-detection |
| `--site-name` | derived from URL | Human-readable name for the site |
| `--description` | none | Short description of the site (1–2 sentences) |
| `--max-per-section` | `20` | Max URLs per content section |
| `--fetch-titles` | false | Fetch each URL to extract its `<title>` tag (slower but richer output) |

---

## Sitemap Auto-Detection

When `--sitemap` is not specified, the script:

1. Fetches `https://yoursite.com/robots.txt`
2. Looks for a `Sitemap:` directive
3. If found, uses that URL as the sitemap
4. If not found, tries `https://yoursite.com/sitemap.xml` as a fallback
5. If the sitemap is a sitemap index (contains multiple sitemaps), it fetches and merges all of them

If your sitemap is in a non-standard location, always pass `--sitemap` explicitly.

---

## Structure of the Generated File

The script generates a structured Markdown file. Example output:

```markdown
# MySite

> Free online calculators for finance, math, and health. Accurate, fast, no signup required.

## Finance Tools

- [Mortgage Calculator](https://yoursite.com/finance/mortgage): Calculate monthly payments for fixed and adjustable-rate mortgages
- [Compound Interest Calculator](https://yoursite.com/finance/compound-interest): Compute growth over time with compound interest
- [Loan Amortization](https://yoursite.com/finance/amortization): Full amortization schedule for any loan

## Math

- [Percentage Calculator](https://yoursite.com/math/percentage): Calculate percentages, increases, and decreases
- [Fraction Simplifier](https://yoursite.com/math/fractions): Reduce fractions to their simplest form

## Blog & Articles

- [What is GEO?](https://yoursite.com/blog/what-is-geo): Introduction to Generative Engine Optimization
- [robots.txt for AI Bots](https://yoursite.com/blog/robots-txt-ai): Complete guide to configuring AI crawlers

## Optional

- [About](https://yoursite.com/about)
- [Contact](https://yoursite.com/contact)
- [Privacy Policy](https://yoursite.com/privacy)
```

**Structure breakdown:**
- `# H1` — your site name
- `> blockquote` — your site description (parsed by AI as the summary)
- `## H2 sections` — content categories (auto-detected from URL patterns)
- `- [Title](URL): description` — links with optional descriptions
- Links without descriptions go under `## Optional`

---

## Where to Put the File

Place `llms.txt` at the root of your web server so it's accessible at `https://yoursite.com/llms.txt`.

### Static Sites (Astro, Next.js, plain HTML)

```bash
# Astro
geo llms --base-url https://yoursite.com --output ./public/llms.txt

# Next.js (app router)
geo llms --base-url https://yoursite.com --output ./public/llms.txt

# Plain HTML
geo llms --base-url https://yoursite.com --output ./llms.txt
```

After running: deploy as you normally would. The file will be served at `/llms.txt`.

### WordPress

```bash
# Generate the file locally
geo llms \
  --base-url https://yoursite.com \
  --sitemap https://yoursite.com/sitemap.xml \
  --output llms.txt

# Upload to WordPress root (where wp-config.php lives)
scp llms.txt user@yourserver.com:/var/www/html/llms.txt
```

Or use a plugin like "WP Robots Txt" to serve a custom `llms.txt` via code.

### Generic Site (any server)

```bash
# Generate
geo llms --base-url https://yoursite.com --output llms.txt

# Upload via FTP/SCP to the web root
scp llms.txt user@yourserver.com:/var/www/yoursite.com/llms.txt
```

---

## Verify It's Live

```bash
curl https://yoursite.com/llms.txt
```

Expected: Markdown content starting with `# YourSiteName`.

If you get a 404, the file is not in the right location. Check your web root directory.

---

## Example for Specific Frameworks

### Astro — with custom sitemap

```bash
geo llms \
  --base-url https://yoursite.com \
  --site-name "MySite" \
  --description "Free tools and calculators" \
  --sitemap https://yoursite.com/sitemap-index.xml \
  --output ./public/llms.txt \
  --max-per-section 15 \
  --fetch-titles
```

### Next.js — standard setup

```bash
geo llms \
  --base-url https://yoursite.com \
  --site-name "MySite" \
  --output ./public/llms.txt
```

### WordPress — with Yoast SEO sitemap

```bash
geo llms \
  --base-url https://yoursite.com \
  --sitemap https://yoursite.com/sitemap_index.xml \
  --site-name "MySite" \
  --description "Your WordPress site description" \
  --output llms.txt
```

### Generic site — no sitemap

If you have no sitemap, create a simple `llms.txt` manually following the structure above, or generate a sitemap first (many free tools exist online), then pass it with `--sitemap`.
