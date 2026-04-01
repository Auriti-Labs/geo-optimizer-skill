# Getting Started

Get the toolkit installed and run your first GEO audit in under 5 minutes.

---

## 1. What You Need

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.9+ | [python.org](https://python.org) |
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
curl -sSL https://raw.githubusercontent.com/auriti-labs/geo-optimizer-skill/main/install.sh | bash
```

This script:
1. Clones the repo to `~/geo-optimizer-skill`
2. Creates a Python virtual environment at `~/geo-optimizer-skill/.venv`
3. Installs dependencies (`requests`, `beautifulsoup4`, `lxml`) into the venv
4. Creates a `./geo` wrapper script that activates the venv automatically before running any script

You never need to activate the venv manually — `./geo` handles it.

> **Custom install path?** The `--dir` flag cannot be used with `curl | bash` (the flag is intercepted by `bash`, not the script). Download first, then pass the flag:
> ```bash
> curl -sSL https://raw.githubusercontent.com/auriti-labs/geo-optimizer-skill/main/install.sh -o install.sh
> bash install.sh --dir /custom/path
> ```

**Manual alternative** (if you prefer to inspect first):

```bash
git clone https://github.com/auriti-labs/geo-optimizer-skill.git ~/geo-optimizer-skill
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
geo audit --url https://yoursite.com
```

That's it. The script fetches your homepage, `robots.txt`, and checks for `/llms.txt`, JSON-LD schema, meta tags, and content signals.

---

## 4. Reading the Output

The audit output is divided into **8 scored categories** plus bonus checks and a final score.

The 8 categories are: **Robots.txt** (18pt), **llms.txt** (18pt), **Schema JSON-LD** (16pt), **Meta Tags** (14pt), **Content Quality** (12pt), **Brand & Entity** (10pt), **Signals** (6pt), **AI Discovery** (6pt).

Each section shows what passed and what's missing:

```
▸ ROBOTS.TXT ─────────────────────────── 5 / 18
  ✅ robots.txt found
  ❌ OAI-SearchBot   MISSING   ← critical
  ❌ ClaudeBot        MISSING   ← critical

▸ LLMS.TXT ───────────────────────────── 0 / 18
  ❌ Not found at https://yoursite.com/llms.txt

▸ SCHEMA JSON-LD ─────────────────────── 4 / 16
  ✅ WebSite schema
  ❌ FAQPage schema missing
  ❌ Organization schema missing

▸ META TAGS ──────────────────────────── 14 / 14
  ✅ Title · Meta description · Canonical · OG tags

▸ CONTENT QUALITY ────────────────────── 5 / 12
  ✅ 12 headings · H2+H3 hierarchy
  ❌ 1 statistic (target: 5+) · 0 external citations

▸ BRAND & ENTITY ─────────────────────── 3 / 10
  ✅ Brand name coherent
  ❌ No sameAs Knowledge Graph links

▸ SIGNALS ────────────────────────────── 3 / 6
  ✅ <html lang="en">
  ❌ No RSS/Atom feed

▸ AI DISCOVERY ───────────────────────── 0 / 6
  ❌ No AI discovery endpoints

──────────────────────────────────────────────────────────
  GEO SCORE   [████████░░░░░░░░░░░░]   34 / 100   ❌ CRITICAL
──────────────────────────────────────────────────────────
```

**Score bands:** `0–35` Critical · `36–67` Foundation · `68–85` Good · `86–100` Excellent

---

## 5. What to Fix First

Follow this priority order — each step has the highest ROI before moving to the next:

1. **robots.txt** — Add all 27 AI bots. Takes 5 minutes. Affects whether bots can crawl you at all. → [AI Bots Reference](ai-bots-reference.md)
2. **llms.txt** — Generate it from your sitemap. Takes 2 minutes. → [Generating llms.txt](llms-txt.md)
3. **Schema** — Add WebSite, Organization, FAQPage, Article. → [Schema Injector](schema-injector.md)
4. **Brand & Entity** — Add sameAs KG links, about/contact pages. → [Scoring Rubric](scoring-rubric.md#8-brand--entity-signals--max-10-pts-new-in-v3182)
5. **AI Discovery** — Generate ai.txt and /ai/*.json endpoints. Use `geo fix` to auto-generate.
6. **Content** — Add statistics, external citations, expert quotes. → [42 GEO Methods](geo-methods.md)

---

## 6. Update

```bash
bash ~/geo-optimizer-skill/update.sh
```

Pulls the latest commits, updates dependencies, and keeps your `./geo` wrapper intact.
