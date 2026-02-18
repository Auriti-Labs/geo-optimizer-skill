# GEO Optimizer — AI Context Files

Choose the file for your platform:

| Platform | File | How to use |
|----------|------|------------|
| Claude Projects | `ai-context/claude-project.md` | Project → Add as Knowledge |
| ChatGPT Custom GPT | `ai-context/chatgpt-custom-gpt.md` | GPT Builder → System prompt (requires paid plan) |
| ChatGPT Custom Instructions | `ai-context/chatgpt-instructions.md` | Settings → Personalization → Custom Instructions |
| Cursor | `ai-context/cursor.mdc` | Copy to `.cursor/rules/geo-optimizer.mdc` |
| Windsurf | `ai-context/windsurf.md` | Copy to `.windsurf/rules/geo-optimizer.md` |
| Kiro | `ai-context/kiro-steering.md` | Copy to `.kiro/steering/geo-optimizer.md` |

## Why different files?

Each platform has different limits and formats:

- **Claude Projects**: no practical limit — full context with workflow, examples, framework code
- **ChatGPT Custom Instructions**: 1,500 character limit per field — ultra-compressed essentials only
- **ChatGPT Custom GPT**: 8,000 character limit (paid plan required) — compressed but complete
- **Cursor / Windsurf**: YAML frontmatter + imperative rules format (Always/Never style)
- **Kiro**: YAML frontmatter with `inclusion: fileMatch` + `fileMatchPattern` array; file goes in `.kiro/steering/`

## Quick copy commands

```bash
# Claude Projects — upload via web UI (claude.ai → Projects → Add content)
# File: ai-context/claude-project.md

# ChatGPT Custom Instructions — paste content via web UI
# File: ai-context/chatgpt-instructions.md (804 chars — fits in one field)

# ChatGPT Custom GPT — paste in GPT Builder → Configure → Instructions
# File: ai-context/chatgpt-custom-gpt.md (~4,500 chars — well within 8,000 limit)

# Cursor
mkdir -p .cursor/rules
cp ~/geo-optimizer-skill/ai-context/cursor.mdc .cursor/rules/geo-optimizer.mdc

# Windsurf
mkdir -p .windsurf/rules
cp ~/geo-optimizer-skill/ai-context/windsurf.md .windsurf/rules/geo-optimizer.md

# Kiro
mkdir -p .kiro/steering
cp ~/geo-optimizer-skill/ai-context/kiro-steering.md .kiro/steering/geo-optimizer.md
```

## File sizes at a glance

| File | Size | Platform limit | Status |
|------|------|---------------|--------|
| `claude-project.md` | ~11,700 chars | No limit | ✅ Full context |
| `chatgpt-custom-gpt.md` | ~4,500 chars | 8,000 chars | ✅ Safe |
| `chatgpt-instructions.md` | ~800 chars | 1,500 chars/field | ✅ Fits in one field |
| `cursor.mdc` | ~4,200 chars | No limit | ✅ Optimized format |
| `windsurf.md` | ~4,000 chars | No limit | ✅ Optimized format |
| `kiro-steering.md` | ~3,300 chars | No limit | ✅ fileMatch inclusion |

## About GEO Optimizer

GEO Optimizer is a Python toolkit to make websites visible and citable by AI search engines (ChatGPT, Perplexity, Claude, Gemini). It implements the 9 GEO methods from the Princeton KDD 2024 research paper and provides 3 automation scripts:

- `geo_audit.py` — scores your site 0–100, lists what's missing
- `generate_llms_txt.py` — auto-generates `/llms.txt` from your sitemap
- `schema_injector.py` — generates or injects JSON-LD schema into HTML

*GEO Optimizer by Juan Camilo Auriti — https://github.com/auriti-web-design/geo-optimizer-skill*
