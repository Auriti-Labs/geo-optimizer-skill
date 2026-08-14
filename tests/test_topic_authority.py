"""Tests for geo authority — site-level topical authority analysis.

All HTTP mocked — zero real network calls.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

from click.testing import CliRunner

from geo_optimizer.cli.main import cli
from geo_optimizer.core.topic_authority import (
    _extract_internal_links,
    _normalize_page_url,
    run_topic_authority,
)
from geo_optimizer.models.results import SitemapUrl


def _page(title: str, body: str, links: list[str] | None = None) -> str:
    anchors = "".join(f'<a href="{href}">link</a>' for href in (links or []))
    return f"""<html lang="en"><head><title>{title}</title></head>
    <body><h1>{title}</h1><p>{body}</p>{anchors}</body></html>"""


def _mock_fetch(pages: dict[str, str]):
    """Build a fetch_url mock returning the HTML mapped to each URL."""

    def fetch(url, *args, **kwargs):
        html = pages.get(url)
        if html is None:
            return None, "not found"
        return Mock(status_code=200, text=html), None

    return fetch


# Body repeats the topic term (capitalized multi-word) so it passes the
# extractor frequency threshold (>= 2 occurrences).
_TOPIC_BODY = "Geo Audit tools matter. A Geo Audit improves AI visibility. Geo Audit weekly."


class TestHelpers:
    def test_normalize_page_url(self):
        assert _normalize_page_url("https://www.a.com/page/") == "a.com/page"
        assert _normalize_page_url("https://a.com/") == "a.com/"

    def test_extract_internal_links_filters_external(self):
        from bs4 import BeautifulSoup

        html = _page("T", "body", links=["/guides/", "https://a.com/x#frag", "https://other.com/y", "mailto:x@a.com"])
        soup = BeautifulSoup(html, "html.parser")
        links = _extract_internal_links(soup, "https://a.com/start")
        assert links == {"a.com/guides", "a.com/x"}


class TestRunTopicAuthority:
    def _run(self, pages: dict[str, str], **kwargs):
        entries = [SitemapUrl(url=u) for u in pages]
        with (
            patch("geo_optimizer.core.topic_authority.fetch_sitemap", return_value=entries),
            patch("geo_optimizer.core.topic_authority.fetch_url", side_effect=_mock_fetch(pages)),
        ):
            return run_topic_authority("https://a.com/sitemap.xml", **kwargs)

    def test_empty_sitemap_skips(self):
        with patch("geo_optimizer.core.topic_authority.fetch_sitemap", return_value=[]):
            result = run_topic_authority("https://a.com/sitemap.xml")
        assert result.checked and result.skipped_reason is not None

    def test_cluster_detection_with_pillar_and_links(self):
        pages = {
            "https://a.com/geo-audit": _page("Geo Audit Guide", _TOPIC_BODY, links=["/geo-audit-faq"]),
            "https://a.com/geo-audit-faq": _page("FAQ", _TOPIC_BODY, links=["/geo-audit"]),
            "https://a.com/contact": _page("Contact", "Write to us soon. Write to us now."),
        }
        result = self._run(pages)

        assert result.pages_analyzed == 3
        assert result.clusters, "expected at least one cluster"
        best = result.clusters[0]
        assert best.topic == "Geo Audit"
        assert best.pages_count == 2
        assert best.pillar_url == "https://a.com/geo-audit"  # title states the topic
        assert best.interlink_ratio == 1.0  # both pages link to each other
        assert result.authority_score > 0

    def test_orphan_cluster_gets_interlink_recommendation(self):
        pages = {
            "https://a.com/p1": _page("Geo Audit Guide", _TOPIC_BODY),
            "https://a.com/p2": _page("Other Title", _TOPIC_BODY),
        }
        result = self._run(pages)

        best = result.clusters[0]
        assert best.interlink_ratio == 0.0
        assert any("interlinked" in r for r in result.recommendations)
        assert any("supporting pages" in r for r in result.recommendations)  # 2 < target 5

    def test_orphan_pages_detected_excludes_homepage(self):
        pages = {
            "https://a.com/": _page("Home", "Welcome here now."),
            "https://a.com/geo-audit": _page("Geo Audit Guide", _TOPIC_BODY, links=["/geo-audit-faq"]),
            "https://a.com/geo-audit-faq": _page("FAQ", _TOPIC_BODY, links=["/geo-audit"]),
            "https://a.com/lost-page": _page("Lost", "Nobody links here at all."),
        }
        result = self._run(pages)

        assert result.orphan_pages == ["https://a.com/lost-page"]
        assert any("orphan" in r.lower() for r in result.recommendations)

    def test_no_orphan_pages_when_all_linked(self):
        pages = {
            "https://a.com/geo-audit": _page("Geo Audit Guide", _TOPIC_BODY, links=["/geo-audit-faq"]),
            "https://a.com/geo-audit-faq": _page("FAQ", _TOPIC_BODY, links=["/geo-audit"]),
        }
        result = self._run(pages)

        assert result.orphan_pages == []

    def test_brand_excluded_from_clusters(self):
        body = "Acme Corp ships fast. Acme Corp is loved. Acme Corp grows."
        pages = {
            "https://a.com/p1": _page("One", body),
            "https://a.com/p2": _page("Two", body),
        }
        with_brand = self._run(pages, brand="Acme Corp")
        without_brand = self._run(pages)

        assert all("acme" not in c.topic.lower() for c in with_brand.clusters)
        assert any("acme" in c.topic.lower() for c in without_brand.clusters)

    def test_boilerplate_terms_excluded_by_document_frequency(self):
        """Terms on >80% of pages (nav/footer labels) are not topics."""
        nav = "Site Map everywhere. Site Map again."
        topic_pages = {f"https://a.com/geo-{i}": _page(f"Page {i}", f"{_TOPIC_BODY} {nav}") for i in range(3)}
        other_pages = {f"https://a.com/other-{i}": _page(f"Other {i}", nav) for i in range(3)}
        result = self._run({**topic_pages, **other_pages})  # 6 pages: nav on 6/6, topic on 3/6

        topics = [c.topic for c in result.clusters]
        assert "Site Map" not in topics
        assert "Geo Audit" in topics

    def test_brand_match_ignores_spacing(self):
        body = "Geo Ready rocks. Geo Ready ships. Geo Ready wins."
        pages = {
            "https://a.com/p1": _page("One", body),
            "https://a.com/p2": _page("Two", body),
        }
        result = self._run(pages, brand="GeoReady")
        assert all("geo ready" not in c.topic.lower() for c in result.clusters)

    def test_no_recurring_topic_recommendation(self):
        pages = {
            "https://a.com/p1": _page("One", "Alpha Beta here. Alpha Beta there."),
            "https://a.com/p2": _page("Two", "Gamma Delta here. Gamma Delta there."),
        }
        result = self._run(pages)

        assert result.clusters == []
        assert result.authority_score == 0
        assert any("No recurring topic" in r for r in result.recommendations)


class TestAuthorityCli:
    def test_cli_text_output(self):
        pages = {
            "https://a.com/geo-audit": _page("Geo Audit Guide", _TOPIC_BODY, links=["/geo-audit-faq"]),
            "https://a.com/geo-audit-faq": _page("FAQ", _TOPIC_BODY, links=["/geo-audit"]),
        }
        entries = [SitemapUrl(url=u) for u in pages]
        with (
            patch("geo_optimizer.cli.authority_cmd.validate_public_url", return_value=(True, None)),
            patch("geo_optimizer.core.topic_authority.fetch_sitemap", return_value=entries),
            patch("geo_optimizer.core.topic_authority.fetch_url", side_effect=_mock_fetch(pages)),
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["authority", "--sitemap", "https://a.com/sitemap.xml"])

        assert result.exit_code == 0
        assert "TOPIC AUTHORITY" in result.output
        assert "Geo Audit" in result.output
        assert "pillar" in result.output

    def test_cli_json_output(self):
        pages = {"https://a.com/p1": _page("One", _TOPIC_BODY), "https://a.com/p2": _page("Two", _TOPIC_BODY)}
        entries = [SitemapUrl(url=u) for u in pages]
        with (
            patch("geo_optimizer.cli.authority_cmd.validate_public_url", return_value=(True, None)),
            patch("geo_optimizer.core.topic_authority.fetch_sitemap", return_value=entries),
            patch("geo_optimizer.core.topic_authority.fetch_url", side_effect=_mock_fetch(pages)),
        ):
            import json

            runner = CliRunner()
            result = runner.invoke(cli, ["authority", "--sitemap", "https://a.com/sitemap.xml", "--format", "json"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["checked"] is True
        assert payload["clusters"][0]["topic"] == "Geo Audit"

    def test_cli_rejects_private_url(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["authority", "--sitemap", "http://127.0.0.1/sitemap.xml"])
        assert result.exit_code == 1
        assert "Invalid sitemap URL" in result.output
