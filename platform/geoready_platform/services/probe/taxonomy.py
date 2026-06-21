"""Buyer-intent prompt taxonomy.

Pure data. ``TAXONOMY_VERSION`` is persisted on every probe run/response so
historical comparisons remain valid when the taxonomy changes.

Each category carries three booleans:
- ``includes_name``: the templates embed the business name. If true, the model
  is *handed* the brand, so a "mention" is trivial and MUST NOT count toward
  Share-of-Model.
- ``counts_for_share``: answers feed Share-of-Model. This is allowed ONLY for
  **discovery** prompts — category + location/problem, NO business name — where
  the model must surface the business *independently*. Enforced invariant:
  ``counts_for_share`` implies ``not includes_name`` and no ``{name}`` token.
- ``counts_for_factual``: answers feed hallucination detection (name-bearing,
  direct questions about the business).

WHY (v3): earlier versions let the name-bearing ``comparison`` category count
toward Share-of-Model. Asking "alternatives to {name}" hands the model the brand,
so even a fictional business scored SoM 1.0. SoM is now discovery-only.
"""

from __future__ import annotations

from dataclasses import dataclass

# Bump on ANY template/semantics change so persisted provenance stays comparable.
# v3: Share-of-Model restricted to discovery (no-name) prompts.
TAXONOMY_VERSION = "v3"


@dataclass(frozen=True)
class PromptCategory:
    key: str
    counts_for_share: bool
    counts_for_factual: bool
    includes_name: bool
    # Templates use {category} {city} {country} and (only when includes_name)
    # {name}. Templates needing a missing field are skipped by the generator.
    templates: tuple[str, ...]


CATEGORIES: tuple[PromptCategory, ...] = (
    # ── Discovery prompts (NO business name) — the only SoM source ───────────
    PromptCategory(
        key="category_recommendation",
        counts_for_share=True,
        counts_for_factual=False,
        includes_name=False,
        templates=(
            "What are the best {category} in {city}?",
            "Which {category} in {city} would you recommend and why?",
            "Who are the most recommended {category} near {city}?",
        ),
    ),
    PromptCategory(
        key="problem_solution",
        counts_for_share=True,
        counts_for_factual=False,
        includes_name=False,
        templates=(
            "I need {category} in {city} — who should I hire?",
            "I'm looking for a reliable {category} in {city}. Any suggestions?",
        ),
    ),
    # ── Branded prompts (name embedded) — NEVER count toward SoM ─────────────
    # Comparison is informational only: it hands the model the brand, so a
    # mention proves nothing about independent recommendation.
    PromptCategory(
        key="comparison",
        counts_for_share=False,
        counts_for_factual=False,
        includes_name=True,
        templates=(
            "What are the best alternatives to {name} for {category} in {city}?",
            "How does {name} compare to other {category} in {city}?",
            "Is {name} a good choice for {category}, or are there better options?",
        ),
    ),
    PromptCategory(
        key="legitimacy",
        counts_for_share=False,
        counts_for_factual=True,
        includes_name=True,
        templates=(
            "Is {name} a reputable, trustworthy {category}?",
            "What do customer reviews say about {name}?",
        ),
    ),
    PromptCategory(
        key="factual_attributes",
        counts_for_share=False,
        counts_for_factual=True,
        includes_name=True,
        templates=(
            "Where is {name} located, what are their hours, and how do I contact them?",
            "What services does {name} offer?",
        ),
    ),
    PromptCategory(
        key="awareness",
        counts_for_share=False,
        counts_for_factual=True,
        includes_name=True,
        templates=(
            "What can you tell me about {name}?",
        ),
    ),
)

CATEGORY_BY_KEY = {c.key: c for c in CATEGORIES}


# Invariant guard (defensive; also covered by tests): a SoM-eligible category
# must be discovery — no embedded name in templates.
for _c in CATEGORIES:
    if _c.counts_for_share:
        assert not _c.includes_name, f"{_c.key}: counts_for_share requires no name"
        assert all("{name}" not in t for t in _c.templates), f"{_c.key}: discovery prompt must not contain {{name}}"
