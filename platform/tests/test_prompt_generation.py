"""Pure prompt-generation tests (no I/O)."""

from __future__ import annotations

from geoready_platform.services.probe import prompt_generator
from geoready_platform.services.probe.taxonomy import CATEGORY_BY_KEY


def test_generates_breadth_first_across_categories():
    prompts = prompt_generator.generate_prompts(
        name="Acme Plumbing", category="plumbers", city="Austin", max_prompts=4
    )
    assert len(prompts) == 4
    # Breadth-first: 4 prompts should span 4 distinct categories.
    assert len({p.category for p in prompts}) == 4
    assert all(p.category in CATEGORY_BY_KEY for p in prompts)


def test_skips_templates_with_missing_fields():
    # No city -> templates requiring {city} must be skipped (no empty placeholders).
    prompts = prompt_generator.generate_prompts(name="Acme", category="plumbers", city=None, max_prompts=20)
    assert prompts, "should still generate name/category-only prompts"
    assert all("{" not in p.text and "}" not in p.text for p in prompts)
    assert all("  " not in p.text for p in prompts)


def test_no_name_yields_nothing():
    assert prompt_generator.generate_prompts(name="", category="plumbers", city="Austin") == []


def test_respects_max_prompts_cap():
    prompts = prompt_generator.generate_prompts(
        name="Acme", category="plumbers", city="Austin", max_prompts=3
    )
    assert len(prompts) == 3


def test_taxonomy_version_is_stable_string():
    assert isinstance(prompt_generator.current_taxonomy_version(), str)
    assert prompt_generator.current_taxonomy_version()
