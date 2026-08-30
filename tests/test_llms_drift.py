"""Tests for check_llms_drift() — llms.txt vs. current-sitemap freshness check.

llms.txt is generated once and then trusted by AI agents as a map of the
site; nothing previously checked whether that map still matched reality.
This reuses the sitemap fetch `geo llms` already does for generation, so
these tests mock discover_sitemap/fetch_sitemap/fetch_url rather than
hitting the network — no live HTTP per listed URL, by design.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

from geo_optimizer.core.llms_generator import check_llms_drift
from geo_optimizer.models.results import SitemapUrl

_LLMS_TXT = """# Example

> An example site.

## Main Pages

- [Home](https://example.com/)
- [About](https://example.com/about)
- [Old Campaign](https://example.com/campaigns/2025-launch)
"""


def _sitemap(urls: list[str]) -> list[SitemapUrl]:
    return [SitemapUrl(url=u) for u in urls]


class TestCheckLlmsDrift:
    def test_detects_stale_urls(self):
        """A URL in llms.txt that's gone from the sitemap is stale."""
        with (
            patch("geo_optimizer.core.llms_generator.discover_sitemap", return_value="https://example.com/sitemap.xml"),
            patch(
                "geo_optimizer.core.llms_generator.fetch_sitemap",
                return_value=_sitemap(["https://example.com/", "https://example.com/about"]),
            ),
        ):
            result = check_llms_drift("https://example.com", llms_txt_content=_LLMS_TXT)

        assert result.checked is True
        assert result.error is None
        assert result.stale_url_count == 1
        assert result.stale_urls == ["https://example.com/campaigns/2025-launch"]

    def test_detects_missing_urls(self):
        """A sitemap URL not yet listed in llms.txt is 'missing', not stale."""
        with (
            patch("geo_optimizer.core.llms_generator.discover_sitemap", return_value="https://example.com/sitemap.xml"),
            patch(
                "geo_optimizer.core.llms_generator.fetch_sitemap",
                return_value=_sitemap(
                    [
                        "https://example.com/",
                        "https://example.com/about",
                        "https://example.com/campaigns/2025-launch",
                        "https://example.com/new-page",
                    ]
                ),
            ),
        ):
            result = check_llms_drift("https://example.com", llms_txt_content=_LLMS_TXT)

        assert result.stale_url_count == 0
        assert result.missing_url_count == 1
        assert result.missing_urls == ["https://example.com/new-page"]

    def test_no_drift_when_matching(self):
        with (
            patch("geo_optimizer.core.llms_generator.discover_sitemap", return_value="https://example.com/sitemap.xml"),
            patch(
                "geo_optimizer.core.llms_generator.fetch_sitemap",
                return_value=_sitemap(
                    ["https://example.com/", "https://example.com/about", "https://example.com/campaigns/2025-launch"]
                ),
            ),
        ):
            result = check_llms_drift("https://example.com", llms_txt_content=_LLMS_TXT)

        assert result.checked is True
        assert result.stale_url_count == 0
        assert result.missing_url_count == 0

    def test_trailing_slash_is_not_drift(self):
        """The same page linked with/without a trailing slash must compare equal."""
        llms_txt = "# Example\n\n> Desc\n\n- [Home](https://example.com/about/)\n"
        with (
            patch("geo_optimizer.core.llms_generator.discover_sitemap", return_value="https://example.com/sitemap.xml"),
            patch(
                "geo_optimizer.core.llms_generator.fetch_sitemap",
                return_value=_sitemap(["https://example.com/about"]),
            ),
        ):
            result = check_llms_drift("https://example.com", llms_txt_content=llms_txt)

        assert result.stale_url_count == 0
        assert result.missing_url_count == 0

    def test_urls_outside_domain_are_ignored(self):
        """An external link in llms.txt (e.g. to a social profile) is not drift."""
        llms_txt = "# Example\n\n> Desc\n\n- [Twitter](https://twitter.com/example)\n- [Home](https://example.com/)\n"
        with (
            patch("geo_optimizer.core.llms_generator.discover_sitemap", return_value="https://example.com/sitemap.xml"),
            patch(
                "geo_optimizer.core.llms_generator.fetch_sitemap",
                return_value=_sitemap(["https://example.com/"]),
            ),
        ):
            result = check_llms_drift("https://example.com", llms_txt_content=llms_txt)

        assert result.llms_txt_url_count == 1
        assert result.stale_url_count == 0

    def test_fetches_llms_txt_when_not_provided(self):
        mock_response = Mock(text=_LLMS_TXT)
        with (
            patch("geo_optimizer.core.llms_generator.fetch_url", return_value=(mock_response, None)) as mock_fetch,
            patch("geo_optimizer.core.llms_generator.discover_sitemap", return_value="https://example.com/sitemap.xml"),
            patch(
                "geo_optimizer.core.llms_generator.fetch_sitemap",
                return_value=_sitemap(["https://example.com/", "https://example.com/about"]),
            ),
        ):
            result = check_llms_drift("https://example.com")

        mock_fetch.assert_called_once_with("https://example.com/llms.txt")
        assert result.checked is True

    def test_error_when_llms_txt_unreachable(self):
        with patch("geo_optimizer.core.llms_generator.fetch_url", return_value=(None, "Connection failed")):
            result = check_llms_drift("https://example.com")

        assert result.checked is False
        assert result.error == "Connection failed"

    def test_error_when_sitemap_not_found(self):
        with patch("geo_optimizer.core.llms_generator.discover_sitemap", return_value=None):
            result = check_llms_drift("https://example.com", llms_txt_content=_LLMS_TXT)

        assert result.checked is False
        assert result.error == "Sitemap not found"

    def test_large_diff_is_capped_but_count_is_exact(self):
        stale_llms_txt = "# Example\n\n> Desc\n\n" + "\n".join(
            f"- [Page {i}](https://example.com/gone-{i})" for i in range(30)
        )
        with (
            patch("geo_optimizer.core.llms_generator.discover_sitemap", return_value="https://example.com/sitemap.xml"),
            patch("geo_optimizer.core.llms_generator.fetch_sitemap", return_value=_sitemap([])),
        ):
            result = check_llms_drift("https://example.com", llms_txt_content=stale_llms_txt)

        assert result.stale_url_count == 30
        assert len(result.stale_urls) == 20
