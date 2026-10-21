"""Impact labels are historical: kept in the data, never presented as measured results."""

import re

from bs4 import BeautifulSoup

from geo_optimizer.core.citability import _IMPROVEMENT_SUGGESTIONS, audit_citability

_HTML = """<html lang="en"><head><title>Acme Widgets</title></head><body><main>
<h1>What is a widget?</h1>
<p>A widget is a small device. According to the 2024 survey, 73% of 1,200 buyers prefer widgets.</p>
<blockquote>Widgets changed our workflow. - Jane Doe, CTO</blockquote>
<h2>How do widgets work?</h2>
<p>However, widgets have limitations. See <a href="https://en.wikipedia.org/wiki/Widget">Wikipedia</a>.</p>
</main></body></html>"""


def test_citability_score_unchanged_by_label_rewording():
    """Fixed fixture: values recorded on main before the wording change."""
    r = audit_citability(BeautifulSoup(_HTML, "html.parser"), "https://example.com")
    assert (r.total_score, r.raw_score, r.max_possible, len(r.methods)) == (46, 96, 210, 47)


def test_impact_field_still_exposed_for_consumers():
    r = audit_citability(BeautifulSoup(_HTML, "html.parser"), "https://example.com")
    assert next(m for m in r.methods if m.name == "cite_sources").impact == "+27%"


def test_suggestions_carry_a_percentage_only_with_its_context():
    for key, text in _IMPROVEMENT_SUGGESTIONS.items():
        if re.search(r"[+-]\d+%", text):
            assert "Aggarwal et al. 2023" in text and "not re-measured" in text, key
