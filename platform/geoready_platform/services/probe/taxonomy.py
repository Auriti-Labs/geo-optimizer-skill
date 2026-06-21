"""Buyer-intent prompt taxonomy.

Pure data. ``TAXONOMY_VERSION`` is persisted on every probe run/response so
historical comparisons remain valid when the taxonomy changes.

Categories are tagged with two booleans:
- ``counts_for_share``: answers in this class feed Share-of-Model (does AI
  recommend / mention the business when a buyer asks?).
- ``counts_for_factual``: answers in this class feed hallucination detection
  (does AI state correct facts about the business?).
"""

from __future__ import annotations

from dataclasses import dataclass

TAXONOMY_VERSION = "v1"


@dataclass(frozen=True)
class PromptCategory:
    key: str
    counts_for_share: bool
    counts_for_factual: bool
    # Templates use {name} {category} {city} {country}. Templates that need a
    # field which is missing on the entity are skipped by the generator.
    templates: tuple[str, ...]


CATEGORIES: tuple[PromptCategory, ...] = (
    PromptCategory(
        key="category_recommendation",
        counts_for_share=True,
        counts_for_factual=False,
        templates=(
            "What are the best {category} in {city}?",
            "Can you recommend a good {category} in {city}?",
            "Who are the top-rated {category} in {city}?",
        ),
    ),
    PromptCategory(
        key="comparison",
        counts_for_share=True,
        counts_for_factual=False,
        templates=(
            "What are the best alternatives to {name} for {category}?",
            "How does {name} compare to other {category} in {city}?",
        ),
    ),
    PromptCategory(
        key="legitimacy",
        counts_for_share=False,
        counts_for_factual=True,
        templates=(
            "Is {name} a reputable {category}?",
            "What do reviews say about {name}?",
        ),
    ),
    PromptCategory(
        key="factual_attributes",
        counts_for_share=False,
        counts_for_factual=True,
        templates=(
            "What are {name}'s hours, location, and contact details?",
            "What services does {name} offer and where are they based?",
        ),
    ),
    PromptCategory(
        key="problem_solution",
        counts_for_share=True,
        counts_for_factual=False,
        templates=(
            "Who should I hire for {category} in {city}?",
        ),
    ),
    PromptCategory(
        key="awareness",
        counts_for_share=False,
        counts_for_factual=True,
        templates=(
            "What do you know about {name}?",
        ),
    ),
)

CATEGORY_BY_KEY = {c.key: c for c in CATEGORIES}
