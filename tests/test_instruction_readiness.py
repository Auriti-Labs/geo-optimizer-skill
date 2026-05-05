"""Tests for Instruction Following Readiness audit (#371)."""

from __future__ import annotations

from bs4 import BeautifulSoup

from geo_optimizer.core.audit_instruction import audit_instruction_readiness


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


class TestInstructionReadiness:
    """Tests for audit_instruction_readiness()."""

    def test_empty_body(self):
        result = audit_instruction_readiness(_soup("<html><body></body></html>"))
        assert result.checked is True
        assert result.readiness_score >= 0

    def test_no_body(self):
        result = audit_instruction_readiness(_soup("<html><head><title>T</title></head></html>"))
        assert result.checked is True

    def test_none_soup(self):
        result = audit_instruction_readiness(None)
        assert result.checked is True
        assert result.labeled_buttons == 0

    # ─── Action clarity ──────────────────────────────────────────────────

    def test_labeled_button(self):
        html = "<html><body><button>Buy Now</button></body></html>"
        result = audit_instruction_readiness(_soup(html))
        assert result.labeled_buttons == 1
        assert result.unlabeled_buttons == 0
        assert result.action_clarity_score == 100

    def test_unlabeled_button_icon_only(self):
        html = '<html><body><button><i class="icon"></i></button></body></html>'
        result = audit_instruction_readiness(_soup(html))
        assert result.unlabeled_buttons == 1
        assert result.labeled_buttons == 0
        assert result.action_clarity_score == 0

    def test_button_with_aria_label(self):
        html = '<html><body><button aria-label="Close dialog">×</button></body></html>'
        result = audit_instruction_readiness(_soup(html))
        assert result.labeled_buttons == 1

    def test_button_with_title(self):
        html = '<html><body><button title="Submit form">→</button></body></html>'
        result = audit_instruction_readiness(_soup(html))
        assert result.labeled_buttons == 1

    def test_cta_link_with_btn_class(self):
        html = '<html><body><a href="/buy" class="btn-primary">Purchase</a></body></html>'
        result = audit_instruction_readiness(_soup(html))
        assert result.labeled_buttons == 1

    def test_cta_link_role_button(self):
        html = '<html><body><a href="#" role="button">Click me</a></body></html>'
        result = audit_instruction_readiness(_soup(html))
        assert result.labeled_buttons == 1

    def test_regular_link_not_counted_as_button(self):
        html = '<html><body><a href="/about">About us</a></body></html>'
        result = audit_instruction_readiness(_soup(html))
        assert result.labeled_buttons == 0
        assert result.unlabeled_buttons == 0

    def test_mixed_buttons(self):
        html = """<html><body>
            <button>OK</button>
            <button><svg></svg></button>
            <button aria-label="Delete">🗑</button>
        </body></html>"""
        result = audit_instruction_readiness(_soup(html))
        assert result.labeled_buttons == 2
        assert result.unlabeled_buttons == 1

    # ─── Form readability ────────────────────────────────────────────────

    def test_labeled_input_with_for(self):
        html = """<html><body>
            <label for="email">Email</label>
            <input id="email" type="email">
        </body></html>"""
        result = audit_instruction_readiness(_soup(html))
        assert result.total_inputs == 1
        assert result.labeled_inputs == 1
        assert result.typed_inputs == 1

    def test_input_with_placeholder(self):
        html = '<html><body><input placeholder="Enter name"></body></html>'
        result = audit_instruction_readiness(_soup(html))
        assert result.labeled_inputs == 1

    def test_input_with_aria_label(self):
        html = '<html><body><input aria-label="Search"></body></html>'
        result = audit_instruction_readiness(_soup(html))
        assert result.labeled_inputs == 1

    def test_input_wrapped_in_label(self):
        html = '<html><body><label>Name <input type="text"></label></body></html>'
        result = audit_instruction_readiness(_soup(html))
        assert result.labeled_inputs == 1

    def test_unlabeled_input(self):
        html = "<html><body><input></body></html>"
        result = audit_instruction_readiness(_soup(html))
        assert result.total_inputs == 1
        assert result.labeled_inputs == 0

    def test_hidden_input_excluded(self):
        html = '<html><body><input type="hidden" name="csrf"></body></html>'
        result = audit_instruction_readiness(_soup(html))
        assert result.total_inputs == 0

    def test_submit_input_excluded(self):
        html = '<html><body><input type="submit" value="Go"></body></html>'
        result = audit_instruction_readiness(_soup(html))
        assert result.total_inputs == 0

    def test_select_counted_as_typed(self):
        html = '<html><body><select aria-label="Country"><option>US</option></select></body></html>'
        result = audit_instruction_readiness(_soup(html))
        assert result.typed_inputs == 1

    def test_textarea_counted(self):
        html = '<html><body><textarea placeholder="Message"></textarea></body></html>'
        result = audit_instruction_readiness(_soup(html))
        assert result.total_inputs == 1
        assert result.labeled_inputs == 1
        assert result.typed_inputs == 1

    def test_form_readability_score_perfect(self):
        html = """<html><body>
            <label for="name">Name</label><input id="name" type="text">
            <label for="email">Email</label><input id="email" type="email">
        </body></html>"""
        result = audit_instruction_readiness(_soup(html))
        assert result.form_readability_score == 100

    def test_form_readability_score_zero(self):
        html = "<html><body><input><input></body></html>"
        result = audit_instruction_readiness(_soup(html))
        assert result.form_readability_score == 0

    def test_no_forms_score_100(self):
        html = "<html><body><p>Just text</p></body></html>"
        result = audit_instruction_readiness(_soup(html))
        assert result.form_readability_score == 100

    # ─── Workflow linearity ──────────────────────────────────────────────

    def test_nav_links_counted(self):
        html = '<html><body><a href="/a">A</a><a href="/b">B</a></body></html>'
        result = audit_instruction_readiness(_soup(html))
        assert result.nav_links == 2

    def test_stateful_urls_query_params(self):
        html = '<html><body><a href="/search?q=test">Search</a></body></html>'
        result = audit_instruction_readiness(_soup(html))
        assert result.stateful_urls is True

    def test_stateful_urls_hash(self):
        html = '<html><body><a href="/page#section">Jump</a></body></html>'
        result = audit_instruction_readiness(_soup(html))
        assert result.stateful_urls is True

    def test_no_stateful_urls(self):
        html = '<html><body><a href="/about">About</a></body></html>'
        result = audit_instruction_readiness(_soup(html))
        assert result.stateful_urls is False

    # ─── Error recovery ──────────────────────────────────────────────────

    def test_aria_live_detected(self):
        html = '<html><body><div aria-live="polite">Status</div></body></html>'
        result = audit_instruction_readiness(_soup(html))
        assert result.has_aria_live is True

    def test_role_alert_detected(self):
        html = '<html><body><div role="alert">Error!</div></body></html>'
        result = audit_instruction_readiness(_soup(html))
        assert result.has_error_roles is True

    def test_aria_invalid_detected(self):
        html = '<html><body><input aria-invalid="true"></body></html>'
        result = audit_instruction_readiness(_soup(html))
        assert result.has_error_roles is True

    def test_no_error_recovery(self):
        html = "<html><body><p>Plain page</p></body></html>"
        result = audit_instruction_readiness(_soup(html))
        assert result.has_aria_live is False
        assert result.has_error_roles is False

    # ─── Readiness levels ────────────────────────────────────────────────

    def test_level_none(self):
        html = "<html><body><button><i></i></button><input></body></html>"
        result = audit_instruction_readiness(_soup(html))
        assert result.readiness_level == "none"

    def test_level_advanced(self):
        html = """<html><body>
            <button>Submit Order</button>
            <label for="q">Search</label><input id="q" type="search">
            <a href="/step?n=2">Next</a>
            <div aria-live="polite"></div>
            <div role="alert"></div>
        </body></html>"""
        result = audit_instruction_readiness(_soup(html))
        assert result.readiness_score >= 80
        assert result.readiness_level == "advanced"

    def test_score_max_100(self):
        html = """<html><body>
            <button>Buy</button><button>Sell</button>
            <label for="a">A</label><input id="a" type="text">
            <a href="/x?s=1">Go</a>
            <div aria-live="assertive"></div>
            <div role="alert"></div>
        </body></html>"""
        result = audit_instruction_readiness(_soup(html))
        assert result.readiness_score <= 100
