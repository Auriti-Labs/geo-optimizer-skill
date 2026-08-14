"""
Prompt injection pattern detection in web content (#276).

Detects 8 categories of AI manipulation in content:
1. CSS-hidden text (display:none, visibility:hidden, font-size:0)
2. Invisible Unicode characters (zero-width, RTL marks)
3. Direct LLM instructions ("ignore previous instructions", special tokens)
4. Prompts in HTML comments (<!-- instruction: ... -->)
5. Monochrome text (color ≈ background)
6. Micro-font injection (font-size < 2px)
7. Data attribute injection (data-ai-*, data-prompt-*)
8. aria-hidden with instructional content

Based on UC Berkeley EMNLP 2024: text injections can manipulate AI search rankings.
"""

from __future__ import annotations

import re

from geo_optimizer.models.config import (
    MICROFONT_SIZE_THRESHOLD_PX,
    PROMPT_INJECTION_COMMENT_KEYWORDS,
    PROMPT_INJECTION_COMMENT_MAX_LEN,
    PROMPT_INJECTION_LLM_PATTERNS,
    PROMPT_INJECTION_MAX_SAMPLES,
    PROMPT_INJECTION_SAMPLE_MAX_LEN,
    PROMPT_INJECTION_UNICODE_THRESHOLD,
)
from geo_optimizer.models.results import PromptInjectionResult

# ─── Compiled patterns (once at import time) ─────────────────────────────────

_LLM_PATTERNS_COMPILED = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in PROMPT_INJECTION_LLM_PATTERNS]

_HIDDEN_CSS_PATTERNS = [
    re.compile(r"display\s*:\s*none", re.IGNORECASE),
    re.compile(r"visibility\s*:\s*hidden", re.IGNORECASE),
    re.compile(r"font-size\s*:\s*0(?:px|pt|em|rem)?\s*(?:;|$)", re.IGNORECASE),
    re.compile(r"opacity\s*:\s*0(?:\s|;|$)", re.IGNORECASE),
]

_INVISIBLE_UNICODE_RE = re.compile(r"[\u200b\u200c\u200d\u200e\u200f\ufeff\u202a-\u202e\u2060]")

_HTML_COMMENT_RE = re.compile(r"<!--(.*?)-->", re.DOTALL)

_FONT_SIZE_RE = re.compile(r"font-size\s*:\s*([\d.]+)\s*(px|pt|em|rem)", re.IGNORECASE)

_DATA_ATTR_RE = re.compile(r"^data-(?:ai|prompt|llm|instruction|context|system)-", re.IGNORECASE)

_COLOR_HEX_RE = re.compile(r"color\s*:\s*#([0-9a-fA-F]{3,6})", re.IGNORECASE)
_BG_HEX_RE = re.compile(r"background(?:-color)?\s*:\s*#([0-9a-fA-F]{3,6})", re.IGNORECASE)
_RGBA_ALPHA_RE = re.compile(r"rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*(0(?:\.\d+)?)\s*\)", re.IGNORECASE)


def _truncate(text: str, max_len: int = PROMPT_INJECTION_SAMPLE_MAX_LEN) -> str:
    """Truncate text to the maximum length with an ellipsis."""
    return text[:max_len] + "…" if len(text) > max_len else text


def _get_text_safe(element) -> str:
    """Safely extract text from a BeautifulSoup element."""
    try:
        return str(element.get_text(strip=True))
    except Exception:
        return ""


# ─── Category 1: CSS-hidden text ─────────────────────────────────────────────


def _detect_hidden_text(soup) -> tuple[bool, int, list[str]]:
    """Detect text hidden via inline CSS."""
    found_count = 0
    samples: list[str] = []

    for el in soup.find_all(style=True):
        style = el.get("style", "")
        text = _get_text_safe(el)
        if len(text) < 3:
            continue

        for pattern in _HIDDEN_CSS_PATTERNS:
            if pattern.search(style):
                found_count += 1
                if len(samples) < PROMPT_INJECTION_MAX_SAMPLES:
                    samples.append(_truncate(text))
                break

    return found_count > 0, found_count, samples


# ─── Category 2: Invisible Unicode ───────────────────────────────────────────


def _detect_invisible_unicode(soup) -> tuple[bool, int]:
    """Detect invisible Unicode characters in the body text."""
    body = soup.find("body")
    if not body:
        return False, 0

    text = _get_text_safe(body)
    matches = _INVISIBLE_UNICODE_RE.findall(text)
    count = len(matches)

    return count >= PROMPT_INJECTION_UNICODE_THRESHOLD, count


# ─── Category 3: LLM instructions ────────────────────────────────────────────


def _detect_llm_instructions(raw_html: str) -> tuple[bool, int, list[str]]:
    """Detect direct LLM instructions in the HTML content."""
    found_count = 0
    samples: list[str] = []

    for pattern in _LLM_PATTERNS_COMPILED:
        for match in pattern.finditer(raw_html):
            found_count += 1
            if len(samples) < PROMPT_INJECTION_MAX_SAMPLES:
                start = max(0, match.start() - 30)
                end = min(len(raw_html), match.end() + 30)
                context = raw_html[start:end].replace("\n", " ").strip()
                samples.append(_truncate(context))

    return found_count > 0, found_count, samples


# ─── Category 4: HTML comments with prompts ──────────────────────────────────


def _detect_html_comment_injection(raw_html: str) -> tuple[bool, int, list[str]]:
    """Detect prompt injection in HTML comments."""
    found_count = 0
    samples: list[str] = []

    for match in _HTML_COMMENT_RE.finditer(raw_html):
        comment = match.group(1).strip()
        if not comment:
            continue

        is_suspicious = False

        # Comment is too long
        if len(comment) > PROMPT_INJECTION_COMMENT_MAX_LEN:
            is_suspicious = True

        # Suspicious keywords
        comment_lower = comment.lower()
        if any(kw in comment_lower for kw in PROMPT_INJECTION_COMMENT_KEYWORDS):
            is_suspicious = True

        # LLM pattern in the comment
        if any(p.search(comment) for p in _LLM_PATTERNS_COMPILED):
            is_suspicious = True

        if is_suspicious:
            found_count += 1
            if len(samples) < PROMPT_INJECTION_MAX_SAMPLES:
                samples.append(_truncate(comment))

    return found_count > 0, found_count, samples


# ─── Category 5: Monochrome text ─────────────────────────────────────────────


def _normalize_hex(h: str) -> str:
    """Normalize a hex color to 6-digit lowercase."""
    h = h.lower()
    if len(h) == 3:
        return h[0] * 2 + h[1] * 2 + h[2] * 2
    return h


def _detect_monochrome_text(soup) -> tuple[bool, int]:
    """Detect text whose color matches or is very close to the background."""
    found_count = 0

    for el in soup.find_all(style=True):
        style = el.get("style", "")
        text = _get_text_safe(el)
        if len(text) < 3:
            continue

        # Check rgba with transparent alpha
        alpha_match = _RGBA_ALPHA_RE.search(style)
        if alpha_match and float(alpha_match.group(1)) < 0.05:
            found_count += 1
            continue

        # Check hex color == background hex
        fg_match = _COLOR_HEX_RE.search(style)
        bg_match = _BG_HEX_RE.search(style)
        if fg_match and bg_match:
            fg = _normalize_hex(fg_match.group(1))
            bg = _normalize_hex(bg_match.group(1))
            if fg == bg:
                found_count += 1

    return found_count > 0, found_count


# ─── Category 6: Micro-font ──────────────────────────────────────────────────


def _detect_microfont(soup) -> tuple[bool, int]:
    """Detect elements with font-size < 2px that contain text."""
    found_count = 0

    for el in soup.find_all(style=True):
        text = _get_text_safe(el)
        if len(text) < 3:
            continue

        style = el.get("style", "")
        m = _FONT_SIZE_RE.search(style)
        if m:
            value = float(m.group(1))
            unit = m.group(2).lower()
            # Convert to approximate px
            if unit == "pt":
                value *= 1.33
            elif unit in ("em", "rem"):
                value *= 16
            if value < MICROFONT_SIZE_THRESHOLD_PX:
                found_count += 1

    return found_count > 0, found_count


# ─── Category 7: Data attribute injection ────────────────────────────────────


def _detect_data_attr_injection(soup) -> tuple[bool, int, list[str]]:
    """Detect suspicious data attributes (data-ai-*, data-prompt-*, etc.)."""
    found_count = 0
    samples: list[str] = []

    for el in soup.find_all():
        for attr_name, attr_value in el.attrs.items():
            if isinstance(attr_name, str) and _DATA_ATTR_RE.match(attr_name):
                found_count += 1
                if len(samples) < PROMPT_INJECTION_MAX_SAMPLES:
                    val_str = str(attr_value)[:80] if attr_value else ""
                    samples.append(f"{attr_name}={val_str}")

    return found_count > 0, found_count, samples


# ─── Category 8: aria-hidden injection ───────────────────────────────────────


def _is_mostly_link_text(el, total_words: int, threshold: float = 0.8) -> bool:
    """Report whether an element's text lives almost entirely inside anchors.

    Navigation is the legitimate reason for a long aria-hidden block (a collapsed
    mobile menu), and it is recognisable by shape: nearly every word is a link label.

    Args:
        el: The element to inspect.
        total_words: Word count of the element's text, already computed by the caller.
        threshold: Link-word ratio above which the block reads as navigation.

    Returns:
        True when at least `threshold` of the words sit inside <a> tags.
    """
    if total_words <= 0:
        return False
    link_words = sum(len(_get_text_safe(a).split()) for a in el.find_all("a"))
    return link_words / total_words >= threshold


def _detect_aria_hidden_injection(soup) -> tuple[bool, int, list[str]]:
    """Detect aria-hidden elements with instructional AI content."""
    found_count = 0
    samples: list[str] = []

    for el in soup.find_all(attrs={"aria-hidden": "true"}):
        text = _get_text_safe(el)
        if not text:
            continue

        is_suspicious = False

        # Text is too long for a decorative element.
        #
        # gap #4.16.3: a collapsed mobile menu is a long aria-hidden block by design —
        # duplicated navigation, not concealed prose — and the length rule alone flagged
        # it as an injection. Skip the length rule when the text is essentially all link
        # labels; the LLM-instruction rule below still runs on the same text, so hiding
        # directives inside anchors stays detected.
        words = text.split()
        if len(words) > 50 and not _is_mostly_link_text(el, len(words)):
            is_suspicious = True

        # Contains LLM instructions
        if any(p.search(text) for p in _LLM_PATTERNS_COMPILED):
            is_suspicious = True

        if is_suspicious:
            found_count += 1
            if len(samples) < PROMPT_INJECTION_MAX_SAMPLES:
                samples.append(_truncate(text))

    return found_count > 0, found_count, samples


# ─── Orchestrator ─────────────────────────────────────────────────────────────


def audit_prompt_injection(soup, raw_html: str) -> PromptInjectionResult:
    """Analyze content for prompt injection patterns.

    Zero HTTP requests — works only on already-available data.

    Args:
        soup: BeautifulSoup of the HTML document.
        raw_html: Raw HTML text for regex matching on comments and attributes.

    Returns:
        PromptInjectionResult with severity and per-category details.
    """
    result = PromptInjectionResult(checked=True)

    # Cat 1: CSS-hidden text
    result.hidden_text_found, result.hidden_text_count, result.hidden_text_samples = _detect_hidden_text(soup)

    # Cat 2: invisible Unicode
    result.invisible_unicode_found, result.invisible_unicode_count = _detect_invisible_unicode(soup)

    # Cat 3: LLM instructions
    result.llm_instruction_found, result.llm_instruction_count, result.llm_instruction_samples = (
        _detect_llm_instructions(raw_html)
    )

    # Cat 4: HTML comments with prompts
    result.html_comment_injection_found, result.html_comment_injection_count, result.html_comment_samples = (
        _detect_html_comment_injection(raw_html)
    )

    # Cat 5: monochrome text
    result.monochrome_text_found, result.monochrome_text_count = _detect_monochrome_text(soup)

    # Cat 6: micro-font
    result.microfont_found, result.microfont_count = _detect_microfont(soup)

    # Cat 7: data attribute injection
    result.data_attr_injection_found, result.data_attr_injection_count, result.data_attr_samples = (
        _detect_data_attr_injection(soup)
    )

    # Cat 8: aria-hidden injection
    result.aria_hidden_injection_found, result.aria_hidden_injection_count, result.aria_hidden_samples = (
        _detect_aria_hidden_injection(soup)
    )

    # Compute summary
    _compute_severity(result)

    return result


def _compute_severity(result: PromptInjectionResult) -> None:
    """Compute severity and risk_level based on detected patterns."""
    categories_active = sum(
        [
            result.hidden_text_found,
            result.invisible_unicode_found,
            result.llm_instruction_found,
            result.html_comment_injection_found,
            result.monochrome_text_found,
            result.microfont_found,
            result.data_attr_injection_found,
            result.aria_hidden_injection_found,
        ]
    )
    result.patterns_found = categories_active

    # Severity: LLM instructions or prompts in comments are always critical
    if result.llm_instruction_found or result.html_comment_injection_found:
        result.severity = "critical"
    elif categories_active >= 3:
        result.severity = "critical"
    elif categories_active >= 1:
        result.severity = "suspicious"
    else:
        result.severity = "clean"

    # Granular risk level
    if result.llm_instruction_found or result.html_comment_injection_found or categories_active >= 3:
        result.risk_level = "high"
    elif (
        result.hidden_text_found
        or result.monochrome_text_found
        or result.microfont_found
        or result.aria_hidden_injection_found
    ):
        result.risk_level = "medium"
    elif result.data_attr_injection_found or result.invisible_unicode_found:
        result.risk_level = "low"
    else:
        result.risk_level = "none"
