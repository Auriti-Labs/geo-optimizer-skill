"""Test della verifica opt-in dei link interni (`geo audit --check-links`).

Due invarianti, entrambe nate dal difetto che questi test chiudono:
1. ``empty_links_count`` conta SOLO href vuoti/placeholder, senza alcuna richiesta;
2. ``broken_links_count`` resta ``None`` ("non verificato") finché non si chiede
   esplicitamente la verifica — mai 0 per difetto.

Zero rete: ``fetch_url`` è sempre mockata.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

from bs4 import BeautifulSoup

from geo_optimizer.core.audit_negative import audit_negative_signals, check_internal_links, internal_link_targets
from geo_optimizer.models.config import LINK_CHECK_MAX_REQUESTS
from geo_optimizer.models.results import ContentResult, MetaResult, SchemaResult

BASE = "https://example.com"


def _content(word_count=500, h1="Test Page", heading_count=3):
    return ContentResult(word_count=word_count, h1_text=h1, heading_count=heading_count, has_h1=True)


def _meta():
    return MetaResult(has_title=True, title_text="Test", description_text="Test description")


def _soup(body: str):
    return BeautifulSoup(f"<html><body><main>{body}<p>Content</p></main></body></html>", "html.parser")


def _response(status: int):
    r = Mock()
    r.status_code = status
    return r


def _fetch_map(status_by_url: dict[str, int], calls: list[str]):
    """fetch_url fake: registra ogni URL richiesto e ritorna lo status mappato."""

    def _fake_fetch(url, *args, **kwargs):
        calls.append(url)
        if url not in status_by_url:
            return None, "Connection failed"
        return _response(status_by_url[url]), None

    return _fake_fetch


# ── 1. Il rename: si contano solo gli href vuoti/placeholder ──────────────────


def test_empty_links_counts_only_placeholder_hrefs():
    """href reali (anche relativi) non entrano in empty_links_count."""
    body = (
        '<a href="">a</a>'
        '<a href="#">b</a>'
        '<a href="javascript:void(0)">c</a>'
        '<a href="javascript:;">d</a>'
        '<a href="/real-page">e</a>'
        '<a href="https://example.com/other">f</a>'
        '<a href="#section">g</a>'  # ancora interna: non è un placeholder vuoto
    )
    result = audit_negative_signals(_soup(body), "", _content(), _meta(), SchemaResult())
    assert result.empty_links_count == 4
    assert result.has_empty_links is True


def test_empty_links_below_threshold_is_not_flagged():
    body = '<a href="#">a</a><a href="#">b</a>'
    result = audit_negative_signals(_soup(body), "", _content(), _meta(), SchemaResult())
    assert result.empty_links_count == 2
    assert result.has_empty_links is False


# ── 2. Senza --check-links nessun campo broken_* viene asserito ───────────────


def test_without_check_links_broken_fields_stay_unverified():
    """Nessun flag → None (non verificato), e nessuna richiesta HTTP."""
    body = '<a href="/dead">dead</a><a href="/also-dead">dead2</a>'
    with patch("geo_optimizer.utils.http.fetch_url") as mock_fetch:
        result = audit_negative_signals(_soup(body), "", _content(), _meta(), SchemaResult(), base_url=BASE)
    mock_fetch.assert_not_called()
    assert result.broken_links_count is None
    assert result.has_broken_links is None
    assert result.links_checked_count == 0
    assert result.broken_link_samples == []


def test_check_links_without_base_url_stays_unverified():
    """check_links=True senza base_url non può verificare nulla: resta None."""
    body = '<a href="/dead">dead</a>'
    with patch("geo_optimizer.utils.http.fetch_url") as mock_fetch:
        result = audit_negative_signals(
            _soup(body), "", _content(), _meta(), SchemaResult(), base_url=None, check_links=True
        )
    mock_fetch.assert_not_called()
    assert result.broken_links_count is None


# ── 3. 404 è rotto, 403/429/timeout no ───────────────────────────────────────


def test_404_counts_as_broken_and_403_does_not():
    body = (
        '<a href="/dead">404</a>'
        '<a href="/gone">410</a>'
        '<a href="/forbidden">403</a>'
        '<a href="/throttled">429</a>'
        '<a href="/server-error">500</a>'
        '<a href="/ok">200</a>'
    )
    calls: list[str] = []
    status = {
        f"{BASE}/dead": 404,
        f"{BASE}/gone": 410,
        f"{BASE}/forbidden": 403,
        f"{BASE}/throttled": 429,
        f"{BASE}/server-error": 500,
        f"{BASE}/ok": 200,
    }
    with patch("geo_optimizer.utils.http.fetch_url", side_effect=_fetch_map(status, calls)):
        count, broken = check_internal_links(_soup(body), BASE, max_checks=LINK_CHECK_MAX_REQUESTS)
    assert len(calls) == 6
    assert count == 2
    assert broken == [f"{BASE}/dead", f"{BASE}/gone"]


def test_unreachable_link_is_not_counted_as_broken():
    """Timeout / connection error = non verificabile, non rotto."""
    body = '<a href="/timeout">x</a>'
    with patch("geo_optimizer.utils.http.fetch_url", return_value=(None, "Timeout (5s) dopo retry esponenziale")):
        count, broken = check_internal_links(_soup(body), BASE)
    assert count == 0
    assert broken == []


def test_audit_populates_broken_fields_when_requested():
    body = '<a href="/dead">404</a><a href="/ok">200</a>'
    calls: list[str] = []
    status = {f"{BASE}/dead": 404, f"{BASE}/ok": 200}
    with patch("geo_optimizer.utils.http.fetch_url", side_effect=_fetch_map(status, calls)):
        result = audit_negative_signals(
            _soup(body), "", _content(), _meta(), SchemaResult(), base_url=BASE, check_links=True
        )
    assert result.broken_links_count == 1
    assert result.has_broken_links is True
    assert result.broken_link_samples == [f"{BASE}/dead"]
    assert result.links_checked_count == 2
    assert result.links_check_truncated is False


def test_zero_broken_is_reported_as_verified_zero():
    """Con il flag, 0 rotti è un vero zero: campo int, non None."""
    body = '<a href="/ok">200</a>'
    with patch("geo_optimizer.utils.http.fetch_url", side_effect=_fetch_map({f"{BASE}/ok": 200}, [])):
        result = audit_negative_signals(
            _soup(body), "", _content(), _meta(), SchemaResult(), base_url=BASE, check_links=True
        )
    assert result.broken_links_count == 0
    assert result.has_broken_links is False


# ── 4. Il cap sul numero di richieste ────────────────────────────────────────


def test_request_cap_is_enforced():
    body = "".join(f'<a href="/p{i}">p{i}</a>' for i in range(LINK_CHECK_MAX_REQUESTS + 15))
    calls: list[str] = []
    status = {f"{BASE}/p{i}": 404 for i in range(LINK_CHECK_MAX_REQUESTS + 15)}
    with patch("geo_optimizer.utils.http.fetch_url", side_effect=_fetch_map(status, calls)):
        count, _ = check_internal_links(_soup(body), BASE, max_checks=LINK_CHECK_MAX_REQUESTS)
    assert len(calls) == LINK_CHECK_MAX_REQUESTS
    assert count == LINK_CHECK_MAX_REQUESTS


def test_truncation_is_reported_in_the_result():
    body = "".join(f'<a href="/p{i}">p{i}</a>' for i in range(LINK_CHECK_MAX_REQUESTS + 5))
    calls: list[str] = []
    status = {f"{BASE}/p{i}": 200 for i in range(LINK_CHECK_MAX_REQUESTS + 5)}
    with patch("geo_optimizer.utils.http.fetch_url", side_effect=_fetch_map(status, calls)):
        result = audit_negative_signals(
            _soup(body), "", _content(), _meta(), SchemaResult(), base_url=BASE, check_links=True
        )
    assert len(calls) == LINK_CHECK_MAX_REQUESTS
    assert result.links_checked_count == LINK_CHECK_MAX_REQUESTS
    assert result.links_check_truncated is True


def test_broken_samples_are_capped():
    from geo_optimizer.models.config import LINK_CHECK_SAMPLES_CAP

    body = "".join(f'<a href="/p{i}">p{i}</a>' for i in range(LINK_CHECK_SAMPLES_CAP + 5))
    status = {f"{BASE}/p{i}": 404 for i in range(LINK_CHECK_SAMPLES_CAP + 5)}
    with patch("geo_optimizer.utils.http.fetch_url", side_effect=_fetch_map(status, [])):
        result = audit_negative_signals(
            _soup(body), "", _content(), _meta(), SchemaResult(), base_url=BASE, check_links=True
        )
    assert result.broken_links_count == LINK_CHECK_SAMPLES_CAP + 5
    assert len(result.broken_link_samples) == LINK_CHECK_SAMPLES_CAP


# ── 5. I link esterni non vengono MAI richiesti ──────────────────────────────


def test_external_links_are_never_requested():
    body = (
        '<a href="https://evil.example.net/x">external</a>'
        '<a href="https://other.example.com/y">other subdomain</a>'
        '<a href="http://169.254.169.254/latest/meta-data">metadata</a>'
        '<a href="mailto:a@example.com">mail</a>'
        '<a href="tel:+390000">tel</a>'
        '<a href="javascript:void(0)">js</a>'
        '<a href="data:text/html,x">data</a>'
        '<a href="/internal">internal</a>'
    )
    calls: list[str] = []
    with patch("geo_optimizer.utils.http.fetch_url", side_effect=_fetch_map({f"{BASE}/internal": 200}, calls)):
        check_internal_links(_soup(body), BASE)
    assert calls == [f"{BASE}/internal"]


def test_targets_are_absolute_deduplicated_and_exclude_the_page_itself():
    body = (
        '<a href="/a">a</a>'
        '<a href="/a#top">a again</a>'
        '<a href="a">relative</a>'  # risolve su /a rispetto a base
        '<a href="https://example.com/">home</a>'
        '<a href="/b?q=1">b</a>'
    )
    targets = internal_link_targets(_soup(body), BASE)
    assert targets == [f"{BASE}/a", f"{BASE}/b?q=1"]


def test_empty_base_url_yields_no_targets():
    assert internal_link_targets(_soup('<a href="/a">a</a>'), "") == []


# ── 6. Presentazione: "non verificato" non diventa "0 link rotti" ────────────


def _audit_result(ns):
    from geo_optimizer.models.results import AuditResult

    result = AuditResult(url=BASE, score=70, band="good", http_status=200)
    result.negative_signals = ns
    return result


def _negative(check_links: bool):
    body = '<a href="#">a</a><a href="/ok">ok</a>'
    with patch("geo_optimizer.utils.http.fetch_url", side_effect=_fetch_map({f"{BASE}/ok": 200}, [])):
        return audit_negative_signals(
            _soup(body), "", _content(), _meta(), SchemaResult(), base_url=BASE, check_links=check_links
        )


def test_json_reports_null_when_links_were_not_checked():
    import json

    from geo_optimizer.cli.formatters import format_audit_json

    data = json.loads(format_audit_json(_audit_result(_negative(check_links=False))))["negative_signals"]
    assert data["empty_links_count"] == 1
    assert data["broken_links_count"] is None
    assert data["has_broken_links"] is None

    checked = json.loads(format_audit_json(_audit_result(_negative(check_links=True))))["negative_signals"]
    assert checked["broken_links_count"] == 0
    assert checked["links_checked_count"] == 1


def test_rich_card_says_not_checked_instead_of_zero_broken_links():
    import re

    import pytest

    pytest.importorskip("rich")
    from geo_optimizer.cli.rich_formatter import format_audit_rich

    def _render(check_links: bool) -> str:
        rendered = format_audit_rich(_audit_result(_negative(check_links)), verbose=True, width=100)
        return re.sub(r"\x1b\[[0-9;]*m", "", rendered)

    out = _render(check_links=False)
    assert "not checked" in out
    assert "Empty links" in out

    checked = _render(check_links=True)
    assert "not checked" not in checked
    assert "Broken links" in checked


def test_rich_card_states_the_scope_even_when_no_link_is_broken():
    """Un controllo fermato dal cap non deve leggersi come un controllo completo."""
    import re

    import pytest

    pytest.importorskip("rich")
    from geo_optimizer.cli.rich_formatter import format_audit_rich
    from geo_optimizer.models.results import NegativeSignalsResult

    def _render(ns) -> str:
        rendered = format_audit_rich(_audit_result(ns), verbose=True, width=100)
        return re.sub(r"\x1b\[[0-9;]*m", "", rendered)

    full = _render(
        NegativeSignalsResult(checked=True, broken_links_count=0, has_broken_links=False, links_checked_count=7)
    )
    assert "7 internal links checked" in full
    assert "capped" not in full

    capped = _render(
        NegativeSignalsResult(
            checked=True,
            broken_links_count=0,
            has_broken_links=False,
            links_checked_count=25,
            links_check_truncated=True,
        )
    )
    assert "25 internal links checked, capped" in capped

    one = _render(
        NegativeSignalsResult(checked=True, broken_links_count=0, has_broken_links=False, links_checked_count=1)
    )
    assert "1 internal link checked" in one
