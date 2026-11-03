"""I file ai-context/ e la documentazione sui bot seguono SKILL.md: ClaudeBot e Google-Extended sono training."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTEXT_DIR = ROOT / "ai-context"
# Each docs page ships in two copies here: docs/ and the packaged web docs. The geoready.dev copy
# lives in Auriti-Labs/geoready-site.
DOC_COPIES = [
    path
    for name in ("ai-bots-reference", "scoring-rubric", "troubleshooting", "mcp-server")
    for path in (
        ROOT / f"docs/{name}.md",
        ROOT / f"src/geo_optimizer/web/docs/{name}.md",
    )
]
FILES = [
    *sorted(p for p in CONTEXT_DIR.iterdir() if p.is_file()),
    ROOT / "references/ai-bots-list.md",
    *DOC_COPIES,
    ROOT / "site/ai/faq.json",
]
TRAINING_BOT = re.compile(r"\b(ClaudeBot|Google-Extended)\b")
SEARCH_WORDING = re.compile(r"\b(citations?|critical|search|ai overviews?|overview)\b", re.IGNORECASE)
# Exact phrases that place these bots correctly; they are cut out before the check, so
# "ClaudeBot (training + citations)" still fails.
CORRECT_PHRASES = (
    "Training: GPTBot, ClaudeBot, Google-Extended",
    "training bots GPTBot, ClaudeBot, Google-Extended",
    "Training bots: `GPTBot`, `ClaudeBot`, `Google-Extended`",
    "training bots `GPTBot`, `ClaudeBot` and `Google-Extended`",
    "training bots (`GPTBot`, `ClaudeBot`, `Google-Extended`)",
    "Disallow GPTBot + ClaudeBot + Google-Extended",
    "for `GPTBot`, `ClaudeBot` and `Google-Extended` to opt out of training",
    "`ClaudeBot`, `GPTBot` and `Google-Extended` are training-tier",
    "`GPTBot`, `ClaudeBot`, `Google-Extended`, `CCBot` |",
    "training (GPTBot, ClaudeBot, Google-Extended",
    "`ClaudeBot` is Anthropic's training crawler",
    "Training crawlers such as GPTBot and ClaudeBot",
    "Google-Extended: Gemini/Vertex training token",
    "not by `Google-Extended`",
    "`Google-Extended` is a robots.txt token",
    "`Google-Extended` is a `robots.txt` token",
    "| `Google-Extended` | Training (token) |",
    "Blocking Google-Extended alone does not opt a site out of AI Overviews",
)
DEPRECATED_UA = re.compile(r"^User-agent: (anthropic-ai|claude-web)|^\| `(anthropic-ai|claude-web)`", re.MULTILINE)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_bot_files_name_claude_searchbot():
    robots_advice = [p for p in FILES if "troubleshooting" not in p.name]
    missing = [p.name for p in robots_advice if "robots.txt" in _text(p) and "Claude-SearchBot" not in _text(p)]
    assert not missing, f"robots.txt advice without Claude-SearchBot: {missing}"


def test_training_bots_never_called_citation_or_search_bots():
    bad = []
    for p in FILES:
        for line in _text(p).splitlines():
            rest = line
            for phrase in CORRECT_PHRASES:
                rest = rest.replace(phrase, "")
            if TRAINING_BOT.search(rest) and SEARCH_WORDING.search(rest):
                bad.append(f"{p.relative_to(ROOT)}: {line.strip()}")
    assert not bad, f"training bots described as citation/search bots: {bad}"


def test_training_bot_table_rows_say_training():
    bad = [
        f"{p.relative_to(ROOT)}: {line.strip()}"
        for p in FILES
        for line in _text(p).splitlines()
        if re.match(r"\| `(ClaudeBot|Google-Extended)`", line) and "Training" not in line
    ]
    assert not bad, f"ClaudeBot/Google-Extended rows not labelled Training: {bad}"


def test_deprecated_anthropic_agents_are_gone():
    stale = [str(p.relative_to(ROOT)) for p in FILES if DEPRECATED_UA.search(_text(p))]
    stale += [p.name for p in FILES if p.suffix == ".json" and "anthropic-ai" in _text(p)]
    stale += [p.name for p in CONTEXT_DIR.iterdir() if "anthropic-ai" in _text(p) or "claude-web" in _text(p)]
    assert not stale, f"anthropic-ai/claude-web are no longer in config.AI_BOTS: {stale}"


def test_chatgpt_instructions_fit_the_field_limit():
    assert len(_text(CONTEXT_DIR / "chatgpt-instructions.md")) <= 1500
