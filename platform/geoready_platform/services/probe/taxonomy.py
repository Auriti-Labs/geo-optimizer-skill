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

# Bumped to v2 when templates were revised for realism/commercial intent.
# Always bump this when templates change so historical comparisons remain valid
# (provenance is persisted per response).
TAXONOMY_VERSION = "v2"


@dataclass(frozen=True)
class PromptCategory:
    key: str
    counts_for_share: bool
    counts_for_factual: bool
    # Templates use {name} {category} {city} {country}. Templates that need a
    # field which is missing on the entity are skipped by the generator.
    templates: tuple[str, ...]


CATEGORIES: tuple[PromptCategory, ...] = (
    # Highest commercial intent: a buyer asking the engine to pick for them.
    PromptCategory(
        key="category_recommendation",
        counts_for_share=True,
        counts_for_factual=False,
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
        templates=(
            "I need {category} in {city} — who should I hire?",
            "I'm looking for a reliable {category} in {city}. Any suggestions?",
        ),
    ),
    PromptCategory(
        key="comparison",
        counts_for_share=True,
        counts_for_factual=False,
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
        templates=(
            "Is {name} a reputable, trustworthy {category}?",
            "What do customer reviews say about {name}?",
        ),
    ),
    PromptCategory(
        key="factual_attributes",
        counts_for_share=False,
        counts_for_factual=True,
        templates=(
            "Where is {name} located, what are their hours, and how do I contact them?",
            "What services does {name} offer?",
        ),
    ),
    PromptCategory(
        key="awareness",
        counts_for_share=False,
        counts_for_factual=True,
        templates=(
            "What can you tell me about {name}?",
        ),
    ),
)

CATEGORY_BY_KEY = {c.key: c for c in CATEGORIES}
