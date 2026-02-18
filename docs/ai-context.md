# AI Context Files — Platform Guide

GEO Optimizer provides platform-specific context files in the `ai-context/` folder. Each file is optimized for its platform's format and character limits.

> **TL;DR:** See `SKILL.md` for the quick-reference table. This doc has step-by-step setup for each platform.

---

## Claude Projects

**File:** `ai-context/claude-project.md`  
**Limit:** No practical limit — full context loaded  
**What you get:** Full workflow, 9 Princeton methods with impact %, all scripts with flags, framework examples (Astro, Next.js, WordPress), GEO checklist, robots.txt block, llms.txt templates, JSON-LD schema examples

### Setup

1. Go to [claude.ai](https://claude.ai) → click **Projects** in the sidebar
2. Click **+ New Project** (e.g. "GEO Optimizer")
3. Click **Add content** → **Upload file** → select `ai-context/claude-project.md`
4. Start a new conversation inside the Project

Claude will have persistent GEO context across every conversation in that Project.

### What to expect

- Immediate, specific advice without needing to re-explain what GEO is
- Ready-to-paste robots.txt blocks, llms.txt, and schema JSON
- The AI will start every site analysis with the audit command
- Framework-specific schema code (Astro, Next.js, WordPress, PHP)

---

## ChatGPT Custom GPT (GPT Builder)

**File:** `ai-context/chatgpt-custom-gpt.md`  
**Limit:** 8,000 characters for system prompt  
**File size:** ~4,500 characters — well within limit  
**Requires:** ChatGPT Plus, Team, or Enterprise (paid plan)

### Setup

1. Go to [chat.openai.com](https://chat.openai.com) → click your avatar → **My GPTs**
2. Click **Create a GPT** → go to the **Configure** tab
3. In the **Instructions** field, paste the full contents of `ai-context/chatgpt-custom-gpt.md`
4. Give the GPT a name (e.g. "GEO Optimizer") and save

### What to expect

- Compressed but complete GEO knowledge: workflow, all 9 methods, schema templates
- Starts every site query with the audit command
- Generates ready-to-paste code blocks
- Slightly less verbose than Claude Projects version (due to space constraints)

> **Note:** Custom GPTs require a paid ChatGPT plan. If you're on the free plan, use Custom Instructions instead.

---

## ChatGPT Custom Instructions

**File:** `ai-context/chatgpt-instructions.md`  
**Limit:** 1,500 characters per field (2 fields = 3,000 max)  
**File size:** ~800 characters — fits in a single field  
**Requires:** Free or paid ChatGPT account

> ⚠️ **Honest limitation:** Custom Instructions have a 1,500 character limit per field. The file covers only the essentials: role, workflow steps, script commands, and top 3 methods. For full context (all 9 methods, schema templates, framework examples), use the Custom GPT file (requires paid plan) or Claude Projects (free with account).

### Setup

1. Go to [chat.openai.com](https://chat.openai.com) → click your avatar → **Customize ChatGPT**
2. Under **"What would you like ChatGPT to know about you?"** paste the contents of `ai-context/chatgpt-instructions.md`
3. Save. Active for all new conversations.

### What to expect

- ChatGPT will understand GEO context without re-explaining every time
- Knows the 3 script commands and top 3 Princeton methods
- Does NOT have the full 9-method table, schema templates, or framework examples
- For complex tasks, paste relevant sections from `ai-context/claude-project.md` directly into the chat

---

## Cursor

**File:** `ai-context/cursor.mdc`  
**Format:** `.mdc` with YAML frontmatter  
**Limit:** No character limit  
**Activation:** Rules load when files match the `globs` pattern

### Setup

```bash
mkdir -p .cursor/rules
cp ~/geo-optimizer-skill/ai-context/cursor.mdc .cursor/rules/geo-optimizer.mdc
```

Or copy manually:
1. In your project root, create `.cursor/rules/` directory
2. Copy `ai-context/cursor.mdc` → `.cursor/rules/geo-optimizer.mdc`
3. Cursor loads the rule automatically when you open matching files

The `globs` pattern activates the rule for: `*.html`, `*.astro`, `*.tsx`, `*.jsx`, `*.php`, `robots.txt`, `llms.txt`, `*.json`

### What to expect

- Cursor AI (Cmd+K, Cmd+L, inline chat) will follow GEO rules when editing matching files
- Imperative "Always/Never" format integrates well with Cursor's rule system
- Suggests correct schema types for each page type automatically
- Reminds you to run the audit command before making recommendations

### Frontmatter reference

```yaml
description: "GEO Optimizer — make websites cited by AI search engines..."
globs: "**/*.html,**/*.astro,**/*.tsx,..."
alwaysApply: false  # Only applies when matching files are open
```

Change `alwaysApply: true` to load the rule in every Cursor session regardless of file type.

---

## Windsurf

**File:** `ai-context/windsurf.md`  
**Format:** Plain Markdown (no YAML frontmatter)  
**Limit:** No character limit  
**Activation:** Cascade AI loads rules from `.windsurf/rules/`

### Setup

```bash
mkdir -p .windsurf/rules
cp ~/geo-optimizer-skill/ai-context/windsurf.md .windsurf/rules/geo-optimizer.md
```

Or copy manually:
1. In your project root, create `.windsurf/rules/` directory
2. Copy `ai-context/windsurf.md` → `.windsurf/rules/geo-optimizer.md`
3. Windsurf's Cascade AI will load the rule for this project

### What to expect

- Identical rules to the Cursor file (same content, different format)
- Windsurf Cascade will follow GEO "Always/Never" rules when editing project files
- No YAML frontmatter — Windsurf uses plain Markdown in rules files

---

## Platform Comparison

| Platform | Context quality | Setup effort | Cost | Persistence |
|----------|----------------|--------------|------|-------------|
| Claude Projects | ⭐⭐⭐⭐⭐ Full | Upload file | Free account | Project-scoped |
| ChatGPT Custom GPT | ⭐⭐⭐⭐ Compressed | Paste in builder | Paid plan | GPT-scoped |
| ChatGPT Custom Instructions | ⭐⭐ Essentials only | Paste in settings | Free account | Account-wide |
| Cursor | ⭐⭐⭐⭐ Rules format | Copy file | Free | Project-scoped |
| Windsurf | ⭐⭐⭐⭐ Rules format | Copy file | Free | Project-scoped |

## Updating context files

When the GEO Optimizer toolkit is updated, re-copy the relevant files:

```bash
# Update all IDE rule files
cp ~/geo-optimizer-skill/ai-context/cursor.mdc .cursor/rules/geo-optimizer.mdc
cp ~/geo-optimizer-skill/ai-context/windsurf.md .windsurf/rules/geo-optimizer.md

# For Claude/ChatGPT: re-upload/re-paste the updated file manually
```

---

*GEO Optimizer by Juan Camilo Auriti — https://github.com/auriti-web-design/geo-optimizer-skill*
