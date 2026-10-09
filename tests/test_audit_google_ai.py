from datetime import datetime, timezone

from bs4 import BeautifulSoup

from geo_optimizer.core.audit_google_ai import (
    check_byline,
    check_canonical,
    check_dates,
    check_index,
    check_links,
    check_sitemap,
    check_snippet,
    check_viewport,
    parse_robots_directives,
    run_google_ai_checks,
)
from geo_optimizer.models.results import RobotsResult

NOW = datetime(2026, 10, 9, tzinfo=timezone.utc)


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


def test_dates_mixed_formats_never_raise():
    for val in ("2026-07-10T08:00:00+02:00", "2026-07-10", "July 10, 2026", "garbage", 123, None):
        check_dates(soup(), [{"@type": "Article", "datePublished": val}], NOW)


def test_dates_rules():
    vis = soup(body='<time datetime="2026-07-10">July 10</time>')
    assert check_dates(vis, [{"datePublished": "2026-07-10"}], NOW).status == "pass"
    assert check_dates(soup(), [{"datePublished": "2026-07-10"}], NOW).status == "warn"
    assert check_dates(vis, [{"dateModified": "2027-01-01"}], NOW).status == "fail"
    assert check_dates(soup(), [], NOW).status == "warn"


def test_byline_warn_never_fail():
    assert check_byline(soup(), [{"author": {"name": "Ada"}}]).status == "pass"
    assert check_byline(soup('<meta name="author" content="Ada">'), []).status == "pass"
    assert check_byline(soup(), []).status == "warn"


def test_links_and_viewport():
    assert check_links(soup(body='<a href="/a">a</a>')).status == "pass"
    assert check_links(soup(body='<a href="#/a">a</a><a href="#/b">b</a><a href="/c">c</a>')).status == "fail"
    assert check_links(soup(body="<span onclick='go()'>x</span>")).status == "fail"
    assert check_viewport(soup('<meta name="viewport" content="width=device-width">')).status == "pass"
    assert check_viewport(soup()).status == "fail"


def test_sitemap():
    assert check_sitemap(RobotsResult(found=True, sitemaps=["https://x.test/s.xml"])).status == "pass"
    assert check_sitemap(RobotsResult(found=True)).status == "warn"
    assert check_sitemap(RobotsResult()).status == "fail"


def test_aggregator_points_and_ids():
    s = soup(
        '<link rel="canonical" href="https://x.test/"><meta name="viewport" content="width=device-width">',
        body='<a href="/a">a</a><time datetime="2026-07-10">x</time>' + "<p>" + "w " * 200 + "</p>",
    )
    r = run_google_ai_checks(
        s,
        final_url="https://x.test/",
        http_status=200,
        headers={},
        robots=RobotsResult(found=True, bots_allowed=["Googlebot"], sitemaps=["https://x.test/s.xml"]),
        schemas=[{"datePublished": "2026-07-10", "author": "Ada"}],
        now=NOW,
    )
    assert r.checked and r.max_points == 20 and r.points == 20
    assert [c.id for c in r.checks] == [
        "G-INDEX",
        "G-SNIPPET",
        "G-CANONICAL",
        "G-DATES",
        "G-BYLINE",
        "G-LINKS",
        "G-VIEWPORT",
        "G-SITEMAP",
        "G-GENAI-CONTROL",
    ]


def test_byline_checks_every_author_and_rejects_blank_names():
    from geo_optimizer.core.audit_google_ai import check_byline

    blank = soup(body="<p>text</p>")
    assert check_byline(blank, [{"author": {"name": " "}}]).status == "warn"
    assert check_byline(blank, [{"author": [{"name": ""}, {"name": "Ada"}]}]).status == "pass"
