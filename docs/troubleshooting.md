# Troubleshooting

Solutions to common installation and runtime problems.

---

## 1. `./geo: No such file or directory`

**Cause:** `install.sh` did not complete successfully, or you're running from the wrong directory.

**Fix:**

```bash
# Check you're in the right directory
cd ~/geo-optimizer-skill
ls -la geo

# If ./geo doesn't exist, re-run the installer
bash install.sh

# If install.sh fails, create the wrapper manually
cat > geo << 'EOF'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/.venv/bin/activate"
python3 "$@"
EOF
chmod +x geo
```

Then verify:

```bash
./geo --version
```

---

## 2. `ModuleNotFoundError: requests`

**Cause:** You ran a script directly with `python3` instead of using the `./geo` wrapper. The venv with dependencies is not activated.

**Fix:** Always use `./geo` instead of `python3`:

```diff
- python3 scripts/geo_audit.py --url https://yoursite.com
+ ./geo scripts/geo_audit.py --url https://yoursite.com
```

If you need to use the venv directly:

```bash
source ~/geo-optimizer-skill/.venv/bin/activate
python3 scripts/geo_audit.py --url https://yoursite.com
```

Or reinstall dependencies into the venv:

```bash
cd ~/geo-optimizer-skill
.venv/bin/pip install -r requirements.txt
```

---

## 3. `--help shows a dependency error`

**Cause:** You're running a version older than 1.3.0. Earlier versions imported dependencies at the top of the file, causing `--help` to fail if the venv wasn't active.

**Fix:**

```bash
bash ~/geo-optimizer-skill/update.sh
```

After updating, `--help` will always work regardless of venv state:

```bash
./geo scripts/geo_audit.py --help
./geo scripts/generate_llms_txt.py --help
./geo scripts/schema_injector.py --help
```

---

## 4. `llms.txt generated but 0 links`

**Cause:** The script couldn't find your sitemap. Auto-detection looks for a `Sitemap:` line in `robots.txt` and falls back to `/sitemap.xml`. If neither exists or both return 404, the output file will have no links.

**Fix:** Pass the sitemap URL explicitly:

```bash
./geo scripts/generate_llms_txt.py \
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

**Cause:** WebSite schema is the baseline (worth ~8 points). The biggest GEO impact comes from FAQPage schema, which is worth another ~8 points and directly feeds into AI-generated answers.

**Fix:** Add FAQPage schema to pages with Q&A content:

```bash
# Option 1: generate from a JSON file
./geo scripts/schema_injector.py --type faq --faq-file faqs.json --file page.html --inject

# Option 2: generate and print to copy manually
./geo scripts/schema_injector.py --type faq --faq-file faqs.json
```

FAQPage schema alone can increase your score by 8 points. Combined with adding external citations (5 points) and a few more statistics (5 points), you can move from 70 to 85.

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
./geo scripts/generate_llms_txt.py \
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

If the site consistently times out, wait a few minutes and retry. The audit script does not cache results.

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
./geo scripts/schema_injector.py --type faq --faq-file faqs.json
```

Copy the output and paste it manually into your file.

**Alternative:** If your file is a template (Jinja2, Twig, PHP), add the schema to the base layout where the `</head>` tag lives.

---

## 10. Install on Windows

**Issue:** `install.sh` is a bash script and does not run natively on Windows.

**Solution: Use WSL2 (Windows Subsystem for Linux)**

```powershell
# Run in PowerShell as Administrator
wsl --install
```

After WSL2 installs and you restart:

```bash
# Inside the WSL terminal (Ubuntu by default)
curl -sSL https://raw.githubusercontent.com/auriti-labs/geo-optimizer-skill/main/install.sh | bash
cd ~/geo-optimizer-skill
./geo scripts/geo_audit.py --url https://yoursite.com
```

WSL2 gives you a full Linux environment. Python 3.8+ is included by default in Ubuntu 20.04+.

If you prefer not to use WSL2, you can run the Python scripts directly in a Windows environment:

```powershell
git clone https://github.com/auriti-labs/geo-optimizer-skill.git
cd geo-optimizer-skill
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts\geo_audit.py --url https://yoursite.com
```

Note: the `./geo` wrapper does not work on Windows. Use `python scripts\<script>.py` directly with the venv activated.
