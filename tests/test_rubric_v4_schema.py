"""Rubric v4: schema points apply only where they make sense (page type).

v4 is v3 (robots as access) plus an applicability rule for FAQPage and Article.
v2 stays the default; v2 and v3 schema numbers must not change.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from geo_optimizer.core.audit_meta import audit_meta_tags
from geo_optimizer.core.audit_schema import audit_schema
from geo_optimizer.core.scoring import _score_schema
from geo_optimizer.models.config import (
    CATEGORY_MAX_BY_VERSION,
    DEFAULT_SCORE_VERSION,
    SCORING_BY_VERSION,
)
from geo_optimizer.models.results import MetaResult, SchemaResult


def _score(schema: SchemaResult, version: int, meta: MetaResult | None = None) -> int:
    return _score_schema(schema, SCORING_BY_VERSION[version], meta, CATEGORY_MAX_BY_VERSION[version]["schema"])


def _homepage(**extra) -> SchemaResult:
    """Organization + WebSite, valid, rich, name visible: every point a homepage can earn (10 of 14)."""
    base = {
        "any_schema_found": True,
        "has_organization": True,
        "has_website": True,
        "schema_richness_score": 2,
        "visible_match": True,
    }
    return SchemaResult(**{**base, **extra})


class TestVersionTable:
    def test_default_stays_v2(self):
        assert DEFAULT_SCORE_VERSION == 2

    def test_v4_only_adds_applicability_to_v3(self):
        v3, v4 = SCORING_BY_VERSION[3], SCORING_BY_VERSION[4]
        assert {k for k in v3.keys() | v4.keys() if v3.get(k) != v4.get(k)} == {"schema_applicability"}
        assert CATEGORY_MAX_BY_VERSION[4] == CATEGORY_MAX_BY_VERSION[2]


class TestSchemaScore:
    def test_v2_and_v3_numbers_do_not_change(self):
        homepage = _homepage()
        assert _score(homepage, 2) == _score(homepage, 3) == 10
        full = _homepage(has_faq=True, has_article=True)
        assert _score(full, 2) == _score(full, 3) == 14

    def test_homepage_without_faq_or_article_is_full_in_v4(self):
        assert _score(_homepage(), 4) == 14

    def test_article_page_without_article_markup_loses_the_article_points(self):
        meta = MetaResult(og_type="article")
        # Article applies and is missing: 10 earned of 12 possible (FAQ does not apply), rescaled to 14
        assert _score(_homepage(), 4, meta) == 12

    def test_article_page_with_markup_earns_them(self):
        # 12 earned of 12 possible (FAQ does not apply)
        assert _score(_homepage(has_article=True), 4) == 14

    def test_visible_faq_without_markup_costs_the_faq_points(self):
        schema = _homepage(has_visible_faq=True)
        assert _score(schema, 4) == 12  # FAQ applies and is missing: 10 of 12 possible, rescaled to 14
        assert _score(_homepage(has_visible_faq=True, has_faq=True), 4) == 14

    def test_never_above_the_category_maximum_or_below_zero(self):
        for schema in (SchemaResult(), _homepage(), _homepage(has_faq=True, has_article=True, has_visible_faq=True)):
            for meta in (None, MetaResult(og_type="article")):
                assert 0 <= _score(schema, 4, meta) <= CATEGORY_MAX_BY_VERSION[4]["schema"]

    def test_no_schema_at_all_is_zero_in_v4(self):
        assert _score(SchemaResult(), 4) == 0


class TestDetection:
    @staticmethod
    def _soup(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    def test_visible_faq_needs_two_questions(self):
        one = self._soup("<body><h2>What does it cost to start?</h2><p>Nothing.</p></body>")
        two = self._soup(
            "<body><h2>What does it cost to start?</h2><p>x</p><details><summary>Can I cancel at any time?</summary>y</details></body>"
        )
        assert audit_schema(one, "https://e.com").has_visible_faq is False
        assert audit_schema(two, "https://e.com").has_visible_faq is True

    def test_visible_faq_is_detected_without_any_json_ld(self):
        page = self._soup("<body><h3>How do I reset my password?</h3><h3>Where is my invoice?</h3></body>")
        result = audit_schema(page, "https://e.com")
        assert result.has_visible_faq and not result.any_schema_found

    def test_og_type_is_read_and_lowercased(self):
        page = self._soup('<head><meta property="og:type" content="Article"></head>')
        assert audit_meta_tags(page, "https://e.com").og_type == "article"


class TestFalsePositivesAndRounding:
    @staticmethod
    def _faq(html: str) -> bool:
        return audit_schema(BeautifulSoup(html, "html.parser"), "https://e.com").has_visible_faq

    def test_blog_index_with_linked_question_titles_is_not_an_faq(self):
        posts = "".join(f'<h2><a href="/p{i}">How do I fix problem number {i}?</a></h2>' for i in range(5))
        assert self._faq(f"<body>{posts}</body>") is False

    def test_questions_in_navigation_or_a_cookie_banner_are_not_an_faq(self):
        nav = "<nav><dl><dt>Where is my invoice?</dt><dt>How do I log in?</dt></dl></nav>"
        banner = '<div class="cookie-banner"><h2>Do you accept cookies?</h2><h3>Can we store a preference?</h3></div>'
        assert self._faq(f"<body>{nav}</body>") is False
        assert self._faq(f"<body>{banner}</body>") is False

    def test_fullwidth_question_mark_is_recognised(self):
        assert self._faq("<body><h2>送料はいくらですか？</h2><p>x</p><h2>返品はできますか？</h2></body>")
        assert self._faq(
            "<body><h2>What does shipping cost to Japan？</h2><h2>Can I return an item after a week？</h2></body>"
        )

    def test_rescale_rounds_half_up(self):
        # earned 3 of 12 possible -> 3.5 -> 4; earned 9 of 12 -> 10.5 -> 11 (round() would give 10)
        schema = SchemaResult(any_schema_found=True, has_organization=True, has_faq=True)  # 2 + 3 + 2 = 7, article n/a
        assert _score(schema, 4) == (7 * 14 + 6) // 12
        nine = SchemaResult(
            any_schema_found=True, has_organization=True, has_website=True, has_faq=True, schema_richness_score=2
        )  # 2+2+3+1+2 = 10 earned of 12 possible
        assert _score(nine, 4) == (10 * 14 + 6) // 12


class TestSurfaces:
    def test_breakdown_through_compute_score_breakdown(self):
        from geo_optimizer.core.scoring import compute_score_breakdown
        from geo_optimizer.models.results import ContentResult, LlmsTxtResult, RobotsResult

        args = {"robots": RobotsResult(), "llms": LlmsTxtResult(), "meta": MetaResult(), "content": ContentResult()}
        assert compute_score_breakdown(schema=_homepage(), version=2, **args)["schema"] == 10
        assert compute_score_breakdown(schema=_homepage(), version=4, **args)["schema"] == 14

    def _recs(self, schema: SchemaResult, version: int) -> list[str]:
        from geo_optimizer.core.audit import build_categorized_recommendations
        from geo_optimizer.models.results import ContentResult, LlmsTxtResult, RobotsResult

        recs = build_categorized_recommendations(
            "https://example.com",
            RobotsResult(),
            LlmsTxtResult(),
            schema,
            MetaResult(),
            ContentResult(),
            score_version=version,
        )
        return [text for category, text in recs if category == "schema"]

    def test_faq_recommendation_only_where_questions_are_shown_in_v4(self):
        assert any("FAQPage" in t for t in self._recs(_homepage(), 2))
        assert not any("FAQPage" in t for t in self._recs(_homepage(), 4))
        assert any("FAQPage" in t for t in self._recs(_homepage(has_visible_faq=True), 4))
