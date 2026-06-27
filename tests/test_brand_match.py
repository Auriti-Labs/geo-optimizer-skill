"""Tests for the shared precise brand-mention matcher."""

from __future__ import annotations

from geo_optimizer.utils.brand_match import (
    brand_matches,
    brand_pattern,
    count_brand_mentions,
)


class TestBrandMatches:
    def test_standalone_mention(self):
        assert brand_matches("Acme is one option.", "Acme") is True

    def test_inline_mention(self):
        assert brand_matches("The GeoReady platform rocks", "GeoReady") is True

    def test_sentence_end_mention(self):
        assert brand_matches("Many teams rely on Acme.", "Acme") is True

    def test_same_named_domain_excluded(self):
        # brand GeoReady must NOT match the unrelated geoready.app
        assert brand_matches("check geoready.app for details", "GeoReady") is False

    def test_own_domain_inline_not_a_text_mention(self):
        assert brand_matches("visit GeoReady.dev today", "GeoReady") is False

    def test_substring_of_longer_word_excluded(self):
        assert brand_matches("Acmecorp is different", "Acme") is False

    def test_case_insensitive(self):
        assert brand_matches("we use ACME daily", "acme") is True

    def test_empty_brand_is_false(self):
        assert brand_matches("anything", "") is False

    def test_brand_with_regex_chars_is_escaped(self):
        # a brand containing regex metacharacters must be matched literally
        assert brand_matches("We picked C++ for speed.", "C++") is True
        assert brand_matches("We picked Cxx for speed.", "C++") is False

    def test_brand_ending_in_non_word_char(self):
        # word boundary must be conditional: C++ / Yahoo! must still match
        assert brand_matches("Search on Yahoo! today", "Yahoo!") is True
        assert brand_matches("My carrier is AT&T here", "AT&T") is True

    def test_brand_starting_with_non_word_char(self):
        # leading boundary conditional: .NET matches but not dotNET
        assert brand_matches("We build with .NET daily.", ".NET") is True
        assert brand_matches("Use dotNET instead", ".NET") is False


class TestCountBrandMentions:
    def test_counts_each_standalone_mention(self):
        assert count_brand_mentions("Acme and Acme again, plus Acme.", "Acme") == 3

    def test_excludes_same_named_domain_from_count(self):
        text = "Acme is great. Also see acme.com and acme.io."
        # only the standalone "Acme" counts; the two domains do not
        assert count_brand_mentions(text, "Acme") == 1

    def test_empty_brand_is_zero(self):
        assert count_brand_mentions("anything", "") == 0

    def test_no_mention_is_zero(self):
        assert count_brand_mentions("CompetitorX only", "Acme") == 0


class TestBrandPatternCaching:
    def test_same_brand_returns_cached_pattern(self):
        assert brand_pattern("Acme") is brand_pattern("Acme")
