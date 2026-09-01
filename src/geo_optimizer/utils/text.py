"""Text tokenization helpers shared across audit modules.

Whitespace splitting under-counts languages that do not put spaces between
words (Chinese, Japanese, Korean): a 30-character Chinese sentence is one or
two ``str.split()`` tokens, so word-count and front-loading gates that assume
space-delimited text are effectively unreachable for CJK content.

These helpers count each CJK codepoint as one word-like unit alongside normal
whitespace tokens, so a CJK page is measured comparably to its Latin-script
translation. For text with no CJK codepoints the result is byte-for-byte
identical to ``text.split()``.
"""

from __future__ import annotations

import re

# Han, Hiragana/Katakana, CJK Ext-A, Hangul syllables, half-width Katakana.
_CJK_RANGES = (
    "㐀-䶿"  # CJK Unified Ideographs Extension A
    "一-鿿"  # CJK Unified Ideographs
    "぀-ヿ"  # Hiragana + Katakana
    "가-힯"  # Hangul syllables
    "ｦ-ﾟ"  # Half-width Katakana
)

# One token per CJK codepoint, or one token per run of non-whitespace
# non-CJK characters (which is what ``str.split`` yields for space-delimited
# scripts).
_WORD_TOKEN = re.compile(rf"[{_CJK_RANGES}]|[^\s{_CJK_RANGES}]+")

_CJK_CHAR = re.compile(rf"[{_CJK_RANGES}]")


def tokenize_words(text: str) -> list[str]:
    """Split ``text`` into word-like tokens, CJK-aware.

    Each CJK codepoint counts as one token; everything else is tokenized on
    whitespace. For CJK-free text the output matches ``text.split()``.
    """
    if not text:
        return []
    return _WORD_TOKEN.findall(text)


def count_words(text: str) -> int:
    """Number of word-like tokens in ``text`` (see :func:`tokenize_words`)."""
    if not text:
        return 0
    return len(_WORD_TOKEN.findall(text))


def has_cjk(text: str) -> bool:
    """True if ``text`` contains at least one CJK codepoint."""
    return bool(text) and _CJK_CHAR.search(text) is not None
