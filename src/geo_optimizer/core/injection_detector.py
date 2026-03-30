"""
Rilevamento pattern di prompt injection nel contenuto web (#276).

Rileva 8 categorie di manipolazione AI nel contenuto:
1. Testo nascosto via CSS (display:none, visibility:hidden, font-size:0)
2. Caratteri Unicode invisibili (zero-width, RTL marks)
3. Istruzioni dirette a LLM ("ignore previous instructions", token speciali)
4. Prompt nei commenti HTML (<!-- instruction: ... -->)
5. Testo monocromatico (colore ≈ sfondo)
6. Micro-font injection (font-size < 2px)
7. Data attribute injection (data-ai-*, data-prompt-*)
8. aria-hidden con contenuto istruttivo

Basato su UC Berkeley EMNLP 2024: text injections can manipulate AI search rankings.
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

# ─── Pattern compilati (una volta sola all'import) ───────────────────────────

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
    """Tronca il testo alla lunghezza massima con ellissi."""
    return text[:max_len] + "…" if len(text) > max_len else text


def _get_text_safe(element) -> str:
    """Estrae testo da un elemento BeautifulSoup in modo sicuro."""
    try:
        return element.get_text(strip=True)
    except Exception:
        return ""


# ─── Categoria 1: Testo nascosto via CSS ─────────────────────────────────────


def _detect_hidden_text(soup) -> tuple[bool, int, list[str]]:
    """Rileva testo nascosto tramite CSS inline."""
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


# ─── Categoria 2: Unicode invisibile ─────────────────────────────────────────


def _detect_invisible_unicode(soup) -> tuple[bool, int]:
    """Rileva caratteri Unicode invisibili nel body text."""
    body = soup.find("body")
    if not body:
        return False, 0

    text = _get_text_safe(body)
    matches = _INVISIBLE_UNICODE_RE.findall(text)
    count = len(matches)

    return count >= PROMPT_INJECTION_UNICODE_THRESHOLD, count


# ─── Categoria 3: Istruzioni LLM ─────────────────────────────────────────────


def _detect_llm_instructions(raw_html: str) -> tuple[bool, int, list[str]]:
    """Rileva istruzioni dirette a LLM nel contenuto HTML."""
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


# ─── Categoria 4: Commenti HTML con prompt ────────────────────────────────────


def _detect_html_comment_injection(raw_html: str) -> tuple[bool, int, list[str]]:
    """Rileva prompt injection nei commenti HTML."""
    found_count = 0
    samples: list[str] = []

    for match in _HTML_COMMENT_RE.finditer(raw_html):
        comment = match.group(1).strip()
        if not comment:
            continue

        is_suspicious = False

        # Commento troppo lungo
        if len(comment) > PROMPT_INJECTION_COMMENT_MAX_LEN:
            is_suspicious = True

        # Parole chiave sospette
        comment_lower = comment.lower()
        if any(kw in comment_lower for kw in PROMPT_INJECTION_COMMENT_KEYWORDS):
            is_suspicious = True

        # Pattern LLM nel commento
        if any(p.search(comment) for p in _LLM_PATTERNS_COMPILED):
            is_suspicious = True

        if is_suspicious:
            found_count += 1
            if len(samples) < PROMPT_INJECTION_MAX_SAMPLES:
                samples.append(_truncate(comment))

    return found_count > 0, found_count, samples


# ─── Categoria 5: Testo monocromatico ────────────────────────────────────────


def _normalize_hex(h: str) -> str:
    """Normalizza un colore hex a 6 cifre lowercase."""
    h = h.lower()
    if len(h) == 3:
        return h[0] * 2 + h[1] * 2 + h[2] * 2
    return h


def _detect_monochrome_text(soup) -> tuple[bool, int]:
    """Rileva testo con colore uguale o simile allo sfondo."""
    found_count = 0

    for el in soup.find_all(style=True):
        style = el.get("style", "")
        text = _get_text_safe(el)
        if len(text) < 3:
            continue

        # Check rgba con alpha trasparente
        alpha_match = _RGBA_ALPHA_RE.search(style)
        if alpha_match and float(alpha_match.group(1)) < 0.05:
            found_count += 1
            continue

        # Check colore hex == background hex
        fg_match = _COLOR_HEX_RE.search(style)
        bg_match = _BG_HEX_RE.search(style)
        if fg_match and bg_match:
            fg = _normalize_hex(fg_match.group(1))
            bg = _normalize_hex(bg_match.group(1))
            if fg == bg:
                found_count += 1

    return found_count > 0, found_count


# ─── Categoria 6: Micro-font ─────────────────────────────────────────────────


def _detect_microfont(soup) -> tuple[bool, int]:
    """Rileva elementi con font-size < 2px che contengono testo."""
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
            # Converti a px approssimativo
            if unit == "pt":
                value *= 1.33
            elif unit in ("em", "rem"):
                value *= 16
            if value < MICROFONT_SIZE_THRESHOLD_PX:
                found_count += 1

    return found_count > 0, found_count


# ─── Categoria 7: Data attribute injection ────────────────────────────────────


def _detect_data_attr_injection(soup) -> tuple[bool, int, list[str]]:
    """Rileva data attribute sospetti (data-ai-*, data-prompt-*, ecc.)."""
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


# ─── Categoria 8: aria-hidden injection ───────────────────────────────────────


def _detect_aria_hidden_injection(soup) -> tuple[bool, int, list[str]]:
    """Rileva aria-hidden con contenuto istruttivo per AI."""
    found_count = 0
    samples: list[str] = []

    for el in soup.find_all(attrs={"aria-hidden": "true"}):
        text = _get_text_safe(el)
        if not text:
            continue

        is_suspicious = False

        # Testo troppo lungo per un elemento decorativo
        if len(text.split()) > 50:
            is_suspicious = True

        # Contiene istruzioni LLM
        if any(p.search(text) for p in _LLM_PATTERNS_COMPILED):
            is_suspicious = True

        if is_suspicious:
            found_count += 1
            if len(samples) < PROMPT_INJECTION_MAX_SAMPLES:
                samples.append(_truncate(text))

    return found_count > 0, found_count, samples


# ─── Orchestratore ────────────────────────────────────────────────────────────


def audit_prompt_injection(soup, raw_html: str) -> PromptInjectionResult:
    """Analizza il contenuto per pattern di prompt injection.

    Zero richieste HTTP — lavora solo su dati già disponibili.

    Args:
        soup: BeautifulSoup del documento HTML.
        raw_html: testo grezzo dell'HTML per regex su commenti e attributi.

    Returns:
        PromptInjectionResult con severity e dettagli per categoria.
    """
    result = PromptInjectionResult(checked=True)

    # Cat 1: testo nascosto CSS
    result.hidden_text_found, result.hidden_text_count, result.hidden_text_samples = _detect_hidden_text(soup)

    # Cat 2: Unicode invisibile
    result.invisible_unicode_found, result.invisible_unicode_count = _detect_invisible_unicode(soup)

    # Cat 3: istruzioni LLM
    result.llm_instruction_found, result.llm_instruction_count, result.llm_instruction_samples = (
        _detect_llm_instructions(raw_html)
    )

    # Cat 4: commenti HTML con prompt
    result.html_comment_injection_found, result.html_comment_injection_count, result.html_comment_samples = (
        _detect_html_comment_injection(raw_html)
    )

    # Cat 5: testo monocromatico
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

    # Calcola summary
    _compute_severity(result)

    return result


def _compute_severity(result: PromptInjectionResult) -> None:
    """Calcola severity e risk_level in base ai pattern trovati."""
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

    # Severity: la presenza di istruzioni LLM o commenti con prompt è sempre critica
    if result.llm_instruction_found or result.html_comment_injection_found:
        result.severity = "critical"
    elif categories_active >= 3:
        result.severity = "critical"
    elif categories_active >= 1:
        result.severity = "suspicious"
    else:
        result.severity = "clean"

    # Risk level granulare
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
