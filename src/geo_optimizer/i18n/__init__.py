"""
Internationalization (i18n) for GEO Optimizer.

Uses Python standard library gettext. Italian as the primary language
(built-in), English as secondary.

Language configuration:
    - CLI flag: ``geo audit --lang en``
    - Environment variable: ``GEO_LANG=en``
    - Default: ``it`` (Italian)
"""

import gettext
import os
from pathlib import Path

# Directory containing .mo translation files
LOCALES_DIR = Path(__file__).parent / "locales"

# Default language
DEFAULT_LANG = "it"

# Supported languages
SUPPORTED_LANGS = {"it", "en"}

# Global translation instance
_current_translation = None


def get_lang() -> str:
    """Determine the current language from GEO_LANG or default."""
    lang = os.environ.get("GEO_LANG", DEFAULT_LANG).lower()
    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG
    return lang


def setup_i18n(lang: str = None) -> gettext.GNUTranslations:
    """Initialize the i18n system for the specified language.

    Args:
        lang: Language code (it, en). If None, uses get_lang().

    Returns:
        GNUTranslations object (or NullTranslations if .mo file is missing).
    """
    global _current_translation

    if lang is None:
        lang = get_lang()

    try:
        translation = gettext.translation(
            "geo_optimizer",
            localedir=str(LOCALES_DIR),
            languages=[lang],
        )
    except FileNotFoundError:
        # Fallback: no translation (passthrough strings)
        translation = gettext.NullTranslations()

    _current_translation = translation
    return translation


def _(message: str) -> str:
    """Translate a message into the current language.

    Main translation function. Usage::

        from geo_optimizer.i18n import _
        print(_("Score GEO"))
    """
    global _current_translation

    if _current_translation is None:
        setup_i18n()

    return _current_translation.gettext(message)


def set_lang(lang: str) -> None:
    """Change the current language at runtime."""
    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG
    setup_i18n(lang)
