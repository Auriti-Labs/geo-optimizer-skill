# Getting Started

Get the toolkit installed and run your first GEO audit in under 10 minutes.

---

## 1. What You Need

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.8+ | [python.org](https://python.org) |
| git | any | [git-scm.com](https://git-scm.com) |
| Website | — | Must be publicly accessible via HTTPS |

Check your Python version:

```bash
python3 --version
```

---

## 2. Install

**One-liner (recommended):**

```bash
curl -sSL https://raw.githubusercontent.com/auriti-web-design/geo-optimizer-skill/main/install.sh | bash
```

This script:
1. Clones the repo to `~/geo-optimizer-skill`
2. Creates a Python virtual environment at `~/geo-optimizer-skill/.venv`
3. Installs dependencies (`requests`, `beautifulsoup4`, `lxml`) into the venv
4. Creates a `./geo` wrapper script that activates the venv automatically before running any script

You never need to activate the venv manually — `./geo` handles it.

> **Custom install path?** The `--dir` flag cannot be used with `curl | bash` (the flag is intercepted by `bash`, not the script). Download first, then pass the flag:
> ```bash
> curl -sSL https://raw.githubusercontent.com/auriti-web-design/geo-optimizer-skill/main/install.sh -o install.sh
> bash install.sh --dir /custom/path
> ```

**Manual alternative** (if you prefer to inspect first):

```bash
git clone https://github.com/auriti-web-design/geo-optimizer-skill.git ~/geo-optimizer-skill
cd ~/geo-optimizer-skill
bash install.sh
```

**Update anytime:**

```bash
bash ~/geo-optimizer-skill/update.sh
```

---

## 3. Your First Audit

```bash
cd ~/geo-optimizer-skill
./geo scripts/geo_audit.py --url https://yoursite.com
```

That's it. The script fetches your homepage, `robots.txt`, and checks for `/llms.txt`, JSON-LD schema, meta tags, and content signals.

---

## 4. Reading the Output

The audit output is divided into 5 sections plus a final score.

**Section 1 — ROBOTS.TXT**

Shows which AI bots are explicitly configured in your `robots.txt`. Each bot is shown as allowed or missing.

```
▸ ROBOTS.TXT ─────────────────────────────────────────────
  ✅ GPTBot          allowed  (OpenAI — ChatGPT training)
  ✅ OAI-SearchBot   allowed  (OpenAI — ChatGPT citations)  ← critical
  ❌ ClaudeBot        MISSING                               ← critical
  ❌ PerplexityBot    MISSING                               ← critical
```

**Section 2 — LLMS.TXT**

Checks whether `/llms.txt` exists at the root of your site and whether it has content.

```
▸ LLMS.TXT ───────────────────────────────────────────────
  ❌ Not found at https://yoursite.com/llms.txt
```

**Section 3 — SCHEMA JSON-LD**

Lists which schema types were found in the page's `<head>`.

```
▸ SCHEMA JSON-LD ─────────────────────────────────────────
  ✅ WebSite schema
  ❌ FAQPage schema missing
  ❌ WebApplication schema missing
```

**Section 4 — META TAGS**

Checks for title, meta description, canonical URL, and Open Graph tags.

```
▸ META TAGS ──────────────────────────────────────────────
  ✅ Title · Meta description · Canonical · OG tags
```

**Section 5 — CONTENT QUALITY**

Counts headings, statistics (numbers/percentages), and external citation links.

```
▸ CONTENT QUALITY ────────────────────────────────────────
  ✅ 12 headings  ·  3 statistics  ·  0 external citations
```

**GEO Score:**

```
──────────────────────────────────────────────────────────
  GEO SCORE   [████████░░░░░░░░░░░░]   55 / 100   ⚠️  NEEDS WORK
──────────────────────────────────────────────────────────
```

Score ranges: `0–49` Poor · `50–69` Needs Work · `70–84` Good · `85–100` Excellent

---

## 5. What to Fix First

Follow this priority order — each step has the highest ROI before moving to the next:

1. **robots.txt** — Add all AI bots. Takes 5 minutes. Affects whether bots can crawl you at all. → [AI Bots Reference](ai-bots-reference.md)
2. **llms.txt** — Generate it from your sitemap. Takes 2 minutes. → [Generating llms.txt](llms-txt.md)
3. **Schema** — Add WebSite, FAQPage, WebApplication. → [Schema Injector](schema-injector.md)
4. **Content** — Add statistics, external citations, expert quotes. → [The 9 Princeton GEO Methods](geo-methods.md)

---

## 6. Update

```bash
bash ~/geo-optimizer-skill/update.sh
```

Pulls the latest commits, updates dependencies, and keeps your `./geo` wrapper intact.
