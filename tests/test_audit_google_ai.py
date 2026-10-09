from bs4 import BeautifulSoup

from geo_optimizer.core.audit_google_ai import (
    check_canonical,
    check_index,
    check_snippet,
    parse_robots_directives,
)
from geo_optimizer.models.results import RobotsResult


def soup(head="", body="<p>" + "word " * 200 + "</p>"):
    return BeautifulSoup(f"<html><head>{head}</head><body>{body}</body></html>", "html.parser")


def test_directives_merge_meta_googlebot_and_header_but_ignore_other_bots():
    s = soup('<meta name="robots" content="max-snippet:-1"><meta name="googlebot" content="nosnippet">')
    d = parse_robots_directives(s, {"X-Robots-Tag": "otherbot: noindex, googlebot: noarchive"})
    assert "nosnippet" in d and "noarchive" in d and "noindex" not in d


def test_index_fails_on_noindex_status_or_blocked_googlebot():
    ok = RobotsResult(found=True, bots_allowed=["Googlebot"])
    assert check_index(200, set(), ok).status == "pass"
    assert check_index(200, {"noindex"}, ok).status == "fail"
    assert check_index(404, set(), ok).status == "fail"
    assert check_index(200, set(), RobotsResult(found=True, bots_blocked=["Googlebot"])).status == "fail"


def test_snippet_rules():
    assert check_snippet(soup(), set()).status == "pass"
    assert check_snippet(soup(), {"nosnippet"}).status == "fail"
    assert check_snippet(soup(), {"max-snippet:20"}).status == "fail"
    assert check_snippet(soup(), {"max-snippet:-1"}).status == "pass"
    assert check_snippet(soup(), {"max-image-preview:none"}).status == "warn"


def test_data_nosnippet_ratio_and_no_main_and_empty_body():
    covered = soup(body="<div data-nosnippet>" + "x " * 90 + "</div><p>" + "y " * 10 + "</p>")
    assert check_snippet(covered, set()).status == "fail"
    partial = soup(body="<span data-nosnippet>" + "x " * 20 + "</span><p>" + "y " * 80 + "</p>")
    assert check_snippet(partial, set()).status == "warn"
    assert check_snippet(soup(body=""), set()).status == "pass"  # nessuna divisione per zero


def test_canonical():
    url = "https://x.test/page"
    assert check_canonical(soup(f'<link rel="canonical" href="{url}">'), url, set()).status == "pass"
    assert check_canonical(soup(), url, set()).status == "fail"
    two = f'<link rel="canonical" href="{url}"><link rel="canonical" href="https://x.test/b">'
    assert check_canonical(soup(two), url, set()).status == "fail"
    assert check_canonical(soup('<link rel="canonical" href="/page">'), url, set()).status == "warn"
    other = soup('<link rel="canonical" href="https://x.test/other">')
    assert check_canonical(other, url, set()).status == "warn"
    assert check_canonical(soup(f'<link rel="canonical" href="{url}">'), url, {"noindex"}).status == "warn"


def test_canonical_ignores_body_link_and_compares_query():
    url = "https://x.test/page?a=1"
    in_body = soup(body=f'<link rel="canonical" href="{url}"><p>text</p>')
    assert check_canonical(in_body, url, set()).status == "fail"
    other_query = soup('<link rel="canonical" href="https://x.test/page?a=2">')
    assert check_canonical(other_query, url, set()).status == "warn"


def test_data_nosnippet_ratio_ignores_script_text():
    hidden = "<div data-nosnippet>" + "secret " * 30 + "</div>"
    page = soup(body=hidden + "<p>" + "word " * 100 + "</p><script>" + "x " * 500 + "</script>")
    assert check_snippet(page, set()).status == "warn"
