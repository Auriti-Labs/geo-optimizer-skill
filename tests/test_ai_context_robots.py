"""I file ai-context/ e i riferimenti sui bot seguono SKILL.md: ClaudeBot e Google-Extended sono training."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTEXT_DIR = ROOT / "ai-context"
BOT_DOCS = [
    ROOT / "references/ai-bots-list.md",
    ROOT / "docs/ai-bots-reference.md",
    ROOT / "src/geo_optimizer/web/docs/ai-bots-reference.md",
    ROOT / "frontend/src/content/docs/docs/ai-bots-reference.md",
]
FILES = sorted(p for p in CONTEXT_DIR.iterdir() if p.is_file()) + BOT_DOCS
TRAINING_BOT = re.compile(r"\b(ClaudeBot|Google-Extended)\b")
SEARCH_WORDING = re.compile(r"\b(citations?|critical|search)\b", re.IGNORECASE)
# Lines that place the bot correctly ("training", "not Search", "not by", "not a crawler") are allowed.
CORRECT_WORDING = re.compile(r"training|not search|not by|not a crawler|token", re.IGNORECASE)
DEPRECATED_UA = re.compile(r"^User-agent: (anthropic-ai|claude-web)|^\| `(anthropic-ai|claude-web)`", re.MULTILINE)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_bot_files_name_claude_searchbot():
    missing = [p.name for p in FILES if "robots.txt" in _text(p) and "Claude-SearchBot" not in _text(p)]
    assert not missing, f"robots.txt advice without Claude-SearchBot: {missing}"


def test_training_bots_never_called_citation_or_search_bots():
    bad = [
        f"{p.relative_to(ROOT)}: {line.strip()}"
        for p in FILES
        for line in _text(p).splitlines()
        if TRAINING_BOT.search(line) and SEARCH_WORDING.search(line) and not CORRECT_WORDING.search(line)
    ]
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
    stale += [p.name for p in CONTEXT_DIR.iterdir() if "anthropic-ai" in _text(p) or "claude-web" in _text(p)]
    assert not stale, f"anthropic-ai/claude-web are no longer in config.AI_BOTS: {stale}"


def test_chatgpt_instructions_fit_the_field_limit():
    assert len(_text(CONTEXT_DIR / "chatgpt-instructions.md")) <= 1500
