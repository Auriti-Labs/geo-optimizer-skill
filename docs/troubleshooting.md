# Troubleshooting

Solutions to common installation and runtime problems.

---

## 1. `geo: command not found`

**Cause:** The package is not installed, or the Python `bin` directory is not in your `PATH`.

**Fix:**

```bash
# Install from PyPI
pip install geo-optimizer-skill

# Or install with all optional dependencies
pip install "geo-optimizer-skill[all]"

# Verify the command is available
geo --version
```

If `geo` is still not found after installation, your Python scripts directory may not be in `PATH`. On Linux/macOS:

```bash
# Add to PATH (add this line to your ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"

# Reload shell
source ~/.bashrc
```

---

## 2. `ModuleNotFoundError: requests`

**Cause:** You have an incomplete installation, or you are running `python3 geo_optimizer/...` directly instead of using the installed `geo` command.

**Fix:** Always use the `geo` command installed by pip:

```diff
- python3 geo_optimizer/cli/audit_cmd.py --url https://yoursite.com
+ geo audit --url https://yoursite.com
```

If the error persists, reinstall the package:

```bash
pip install --upgrade geo-optimizer-skill
```

Or install with all extras to ensure all optional dependencies are present:

```bash
pip install "geo-optimizer-skill[all]"
```

---

## 3. `--help shows a dependency error`

**Cause:** You are running a version older than 1.3.0. Earlier versions imported dependencies at the top of the file, causing `--help` to fail if the environment was incomplete.

**Fix:** Upgrade to the latest version:

```bash
pip install --upgrade geo-optimizer-skill
```

After upgrading, `--help` will always work:

```bash
geo audit --help
geo llms --help
geo schema --help
```

---

## 4. `llms.txt generated but 0 links`

**Cause:** The script couldn't find your sitemap. Auto-detection looks for a `Sitemap:` line in `robots.txt` and falls back to `/sitemap.xml`. If neither exists or both return 404, the output file will have no links.

**Fix:** Pass the sitemap URL explicitly:

```bash
geo llms \
  --base-url https://yoursite.com \
  --sitemap https://yoursite.com/sitemap_index.xml \
  --output ./llms.txt
```

Common sitemap paths to try:

```bash
curl -I https://yoursite.com/sitemap.xml
curl -I https://yoursite.com/sitemap_index.xml
curl -I https://yoursite.com/sitemap-index.xml
curl -I https://yoursite.com/post-sitemap.xml     # WordPress/Yoast
curl -I https://yoursite.com/page-sitemap.xml     # WordPress/Yoast
```

Use whichever returns `200 OK` as the `--sitemap` value.

---

## 5. `robots.txt bot shows as MISSING despite being there`

**Cause A:** The bot entry has a comment on the same line, which is invalid `robots.txt` syntax.

```diff
- User-agent: ClaudeBot  # Anthropic citation bot
+ User-agent: ClaudeBot
+ Allow: /
```

`robots.txt` does not support inline comments. `#` must be on its own line.

**Cause B:** Extra whitespace or a typo in the user-agent name.

```diff
- User-agent: Claudebot
+ User-agent: ClaudeBot
```

User-agent names are case-sensitive. `ClaudeBot` ≠ `Claudebot`.

**Cause C:** A `Disallow: /` lower in the file overrides the specific Allow.

```
User-agent: ClaudeBot
Allow: /          ← this works

User-agent: *
Disallow: /       ← but this doesn't override the above in most parsers
```

To be safe, place specific bot entries before the catch-all `User-agent: *` block.

---

## 6. `WebSite schema found but score is still low`

**Cause:** WebSite schema is the baseline (worth 2 points in v3.18+). The biggest GEO impact comes from FAQPage schema, which is worth 3 points and directly feeds into AI-generated answers. Brand & Entity Signals (10 pts new in v3.18.2) are also a major opportunity.

**Fix:** Add FAQPage schema to pages with Q&A content:

```bash
# Option 1: generate from a JSON file
geo schema --type faq --faq-file faqs.json --file page.html --inject

# Option 2: generate and print to copy manually
geo schema --type faq --faq-file faqs.json
```

Also ensure your `sameAs` links are in place — they now feed `brand_kg_readiness` (3 pts):

```json
{
  "@type": "Organization",
  "sameAs": [
    "https://www.linkedin.com/company/yourcompany",
    "https://en.wikipedia.org/wiki/YourCompany"
  ]
}
```

See [Schema Injector](schema-injector.md) and [FAQPage best practices](schema-injector.md#faqpage-best-practices).

---

## 7. `sitemap.xml returns 404`

**Cause:** Your sitemap is not at the standard `/sitemap.xml` path, or hasn't been generated.

**Fix — find your sitemap:**

```bash
# Check robots.txt for Sitemap: directive
curl https://yoursite.com/robots.txt | grep -i sitemap

# Try common WordPress paths
curl -I https://yoursite.com/sitemap_index.xml
curl -I https://yoursite.com/wp-sitemap.xml
curl -I https://yoursite.com/post-sitemap.xml

# Try common Next.js / Astro paths
curl -I https://yoursite.com/server-sitemap.xml
curl -I https://yoursite.com/sitemap-0.xml
```

Once found, pass it explicitly:

```bash
geo llms \
  --base-url https://yoursite.com \
  --sitemap https://yoursite.com/wp-sitemap.xml
```

**Fix — generate a sitemap:**

If you have no sitemap at all, generate one first. For Astro, use `@astrojs/sitemap`. For Next.js, use `next-sitemap`. For WordPress, use the Yoast SEO plugin. For generic sites, use an online tool or [xml-sitemaps.com](https://www.xml-sitemaps.com).

---

## 8. `Timeout error on --url`

**Cause:** The target site is slow to respond, or temporarily unreachable.

> ⚠️ Note: `--verbose` is not yet implemented — it currently has no effect.

**Common fixes:**

```bash
# Test if the site is reachable
curl -I https://yoursite.com

# Test from a different network or VPN if you suspect IP blocking
# Check if the site returns 200 or a redirect chain (3xx)
curl -L -I https://yoursite.com
```

If the site consistently times out, wait a few minutes and retry. The audit does not cache results between CLI invocations.

---

## 9. `inject failed: no <head> tag`

**Cause:** The HTML file passed to `--inject` does not have a standard `</head>` closing tag, which the injector uses as the insertion point.

**Fix — manual injection:**

Open your HTML file and add the schema block manually, just before the closing `</head>` tag:

```html
  <!-- GEO Schema -->
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [...]
  }
  </script>
</head>
```

Generate the schema JSON first (without `--inject`):

```bash
geo schema --type faq --faq-file faqs.json
```

Copy the output and paste it manually into your file.

**Alternative:** If your file is a template (Jinja2, Twig, PHP), add the schema to the base layout where the `</head>` tag lives.

---

## 10. Install on Windows

**Issue:** `geo-optimizer-skill` is a standard Python package and installs via pip on any platform, including Windows.

**Solution: Install with pip**

```powershell
pip install geo-optimizer-skill
geo audit --url https://yoursite.com
```

If you need to use a virtual environment (recommended):

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install geo-optimizer-skill
geo audit --url https://yoursite.com
```

**Alternative: WSL2 (Windows Subsystem for Linux)**

If you prefer a Linux environment:

```powershell
# Run in PowerShell as Administrator
wsl --install
```

After WSL2 installs and you restart:

```bash
# Inside the WSL terminal (Ubuntu by default)
pip install geo-optimizer-skill
geo audit --url https://yoursite.com
```

WSL2 gives you a full Linux environment. Python 3.9+ is included by default in Ubuntu 22.04+.
