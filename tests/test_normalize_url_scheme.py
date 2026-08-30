"""Tests for normalize_url_scheme() — case-insensitive URL scheme normalization.

Found via live dogfooding before this session's release push: 15 call sites
across the codebase each inlined `if not url.startswith(("http://",
"https://"))`, a case-sensitive check. A URL typed or pasted with an
uppercase scheme — `HTTP://example.com` — fails that check despite already
having a scheme, so it gets a second one prepended:
`https://HTTP://example.com`. `urlparse` then reads `HTTP:` as the netloc
and the real host disappears into the path, so the URL fails DNS resolution
with an error that blames the domain instead of the parsing bug.

Confirmed live: `geo audit --url HTTP://geoready.dev` failed with "DNS
resolution failed: hostname not resolvable" against geoready.dev, which
resolves fine — and now returns the same score as `https://geoready.dev`.
"""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from geo_optimizer.cli.main import cli
from geo_optimizer.utils.validators import normalize_url_scheme


class TestNormalizeUrlScheme:
    def test_bare_domain_gets_https_prepended(self):
        assert normalize_url_scheme("example.com") == "https://example.com"

    def test_lowercase_http_unchanged(self):
        assert normalize_url_scheme("http://example.com") == "http://example.com"

    def test_lowercase_https_unchanged(self):
        assert normalize_url_scheme("https://example.com") == "https://example.com"

    def test_uppercase_http_unchanged(self):
        """The bug: this used to become 'https://HTTP://example.com'."""
        assert normalize_url_scheme("HTTP://example.com") == "HTTP://example.com"

    def test_uppercase_https_unchanged(self):
        assert normalize_url_scheme("HTTPS://example.com") == "HTTPS://example.com"

    def test_mixed_case_scheme_unchanged(self):
        assert normalize_url_scheme("Http://example.com") == "Http://example.com"
        assert normalize_url_scheme("hTTps://example.com") == "hTTps://example.com"

    def test_path_and_query_preserved(self):
        assert normalize_url_scheme("example.com/page?q=1") == "https://example.com/page?q=1"
        assert normalize_url_scheme("HTTP://example.com/page") == "HTTP://example.com/page"

    def test_does_not_double_prefix_an_already_normalized_url(self):
        """Idempotent: calling it twice must not stack a second scheme."""
        once = normalize_url_scheme("example.com")
        twice = normalize_url_scheme(once)
        assert once == twice == "https://example.com"


class TestUppercaseSchemeEndToEnd:
    """A sample of call sites, proving the wiring works, not just the helper."""

    def test_audit_cmd_accepts_uppercase_scheme(self):
        runner = CliRunner()
        with patch("geo_optimizer.cli.audit_cmd.validate_public_url") as mock_validate:
            mock_validate.return_value = (False, "stopped before fetch — validation call is what's under test")
            runner.invoke(cli, ["audit", "--url", "HTTP://geoready.dev"])

        validated_url = mock_validate.call_args[0][0]
        assert validated_url == "HTTP://geoready.dev"
        assert not validated_url.startswith("https://HTTP")

    def test_llms_cmd_accepts_uppercase_scheme(self):
        runner = CliRunner()
        with patch("geo_optimizer.cli.llms_cmd.validate_public_url") as mock_validate:
            mock_validate.return_value = (False, "stopped before fetch — validation call is what's under test")
            runner.invoke(cli, ["llms", "--base-url", "HTTP://geoready.dev"])

        validated_url = mock_validate.call_args[0][0]
        assert validated_url == "HTTP://geoready.dev"
        assert not validated_url.startswith("https://HTTP")

    def test_fix_cmd_accepts_uppercase_scheme(self):
        runner = CliRunner()
        with patch("geo_optimizer.cli.fix_cmd.validate_public_url") as mock_validate:
            mock_validate.return_value = (False, "stopped before fetch — validation call is what's under test")
            runner.invoke(cli, ["fix", "--url", "HTTP://geoready.dev"])

        validated_url = mock_validate.call_args[0][0]
        assert validated_url == "HTTP://geoready.dev"
        assert not validated_url.startswith("https://HTTP")
