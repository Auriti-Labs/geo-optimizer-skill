"""Deterministic buyer-intent prompt generation. Pure, no I/O.

Given an entity's fields, fill the taxonomy templates. Templates referencing a
missing field (e.g. no city) are skipped so we never emit prompts with empty
placeholders. Output order is stable for reproducible runs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from geoready_platform.services.probe.taxonomy import CATEGORIES, TAXONOMY_VERSION

_PLACEHOLDER = re.compile(r"\{(\w+)\}")


@dataclass(frozen=True)
class GeneratedPrompt:
    category: str
    text: str


def _fields(name: str, category: str | None, city: str | None, country: str | None) -> dict[str, str]:
    return {
        "name": (name or "").strip(),
        "category": (category or "").strip(),
        "city": (city or "").strip(),
        "country": (country or "").strip(),
    }


def _render(template: str, values: dict[str, str]) -> str | None:
    needed = set(_PLACEHOLDER.findall(template))
    if any(not values.get(field) for field in needed):
        return None  # skip templates whose required fields are missing
    return template.format(**values)


def generate_prompts(
    *,
    name: str,
    category: str | None = None,
    city: str | None = None,
    country: str | None = None,
    max_prompts: int = 8,
) -> list[GeneratedPrompt]:
    """Return up to ``max_prompts`` prompts spread across taxonomy categories.

    Round-robins one template per category first (breadth before depth) so a
    small cap still covers multiple intents.
    """
    values = _fields(name, category, city, country)
    if not values["name"]:
        return []

    # Build per-category rendered lists.
    rendered: list[list[GeneratedPrompt]] = []
    for cat in CATEGORIES:
        items = [GeneratedPrompt(cat.key, text) for t in cat.templates if (text := _render(t, values))]
        if items:
            rendered.append(items)

    # Round-robin across categories for breadth.
    out: list[GeneratedPrompt] = []
    idx = 0
    while len(out) < max_prompts and any(idx < len(lst) for lst in rendered):
        for lst in rendered:
            if idx < len(lst):
                out.append(lst[idx])
                if len(out) >= max_prompts:
                    break
        idx += 1
    return out


def current_taxonomy_version() -> str:
    return TAXONOMY_VERSION
