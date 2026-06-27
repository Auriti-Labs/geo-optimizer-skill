"""Precise brand-mention matching shared across audit modules.

A bare case-insensitive substring match counts false positives: a short brand
matches inside a longer word (``Acme`` in ``Acmecorp``) and, worse, a
same-named but unrelated domain inflates the brand count (``GeoReady`` matching
``geoready.app`` when the brand's own site is ``geoready.dev``).

These helpers use word boundaries plus a negative lookahead ``(?!\\.\\w)`` so
the brand is not counted when it is merely the root of a domain/host. A
standalone mention, an inline mention, or one ending a sentence still counts.
"""

from __future__ import annotations

import re
from functools import lru_cache


@lru_cache(maxsize=256)
def brand_pattern(brand: str) -> re.Pattern[str]:
    """Compile (and cache) a precise brand-mention matcher.

    Word boundaries are applied *conditionally*: ``\\b`` only behaves as a
    "start/end of word" assertion next to a word character. A brand that
    starts or ends with a non-word char (``C++``, ``Yahoo!``, ``.NET``) would
    never match if we forced ``\\b`` there, so we add the boundary only on the
    side where the brand's own edge is alphanumeric/underscore. The negative
    lookahead ``(?!\\.\\w)`` still excludes same-named domains (``geoready.app``).

    Cached because the same brand is matched against many responses in one
    audit run; compiling once per brand avoids redundant work.
    """
    escaped = re.escape(brand)
    left = r"\b" if brand[:1].isalnum() or brand[:1] == "_" else ""
    right = r"\b" if brand[-1:].isalnum() or brand[-1:] == "_" else ""
    return re.compile(left + escaped + right + r"(?!\.\w)", re.IGNORECASE)


def brand_matches(text: str, brand: str) -> bool:
    """True if ``brand`` is mentioned in ``text`` (excluding same-named domains)."""
    if not brand:
        return False
    return bool(brand_pattern(brand).search(text))


def count_brand_mentions(text: str, brand: str) -> int:
    """Count precise brand mentions in ``text`` (excluding same-named domains)."""
    if not brand:
        return 0
    return len(brand_pattern(brand).findall(text))
