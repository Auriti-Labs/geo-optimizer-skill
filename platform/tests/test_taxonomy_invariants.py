"""Taxonomy invariants — guard against re-introducing brand-leading SoM bias."""

from __future__ import annotations

from geoready_platform.services.probe.taxonomy import CATEGORIES, TAXONOMY_VERSION


def test_share_categories_are_discovery_only():
    """Any SoM-eligible category must be discovery: no name flag, no {name} token."""
    for c in CATEGORIES:
        if c.counts_for_share:
            assert not c.includes_name, f"{c.key} counts_for_share but includes_name"
            for t in c.templates:
                assert "{name}" not in t, f"{c.key} discovery template contains {{name}}: {t}"


def test_name_bearing_categories_never_count_for_share():
    for c in CATEGORIES:
        if c.includes_name:
            assert not c.counts_for_share, f"{c.key} embeds name but counts_for_share"


def test_comparison_is_no_longer_a_share_category():
    comparison = next(c for c in CATEGORIES if c.key == "comparison")
    assert comparison.includes_name is True
    assert comparison.counts_for_share is False


def test_at_least_one_discovery_category_exists():
    assert any(c.counts_for_share and not c.includes_name for c in CATEGORIES)


def test_taxonomy_version_bumped():
    # Semantics changed in v3; provenance must reflect it.
    assert TAXONOMY_VERSION == "v3"
