"""
Tests for boost improvements:
- Fix #160: copy.deepcopy() in audit_content_quality
- Fix #161: shared helpers _classify_robots_content / _parse_llms_content
- Fix #162: plugin error handling in _build_audit_result
- Fix #163: SSRF validation in http_async.py

All HTTP calls are mocked — no network access.
"""

from unittest.mock import Mock, patch

from bs4 import BeautifulSoup

from geo_optimizer.core.audit import (
    _audit_llms_from_response,
    _audit_robots_from_response,
    _build_audit_result,
    _classify_robots_content,
    _parse_llms_content,
    audit_content_quality,
    audit_llms_txt,
    audit_robots_txt,
)
from geo_optimizer.models.results import (
    ContentResult,
    LlmsTxtResult,
    MetaResult,
    RobotsResult,
    SchemaResult,
)

# ============================================================================
# Fix #160: copy.deepcopy() prevents original soup modification
# ============================================================================


class TestDeepCopySoup:
    """Verify that audit_content_quality does not modify the original soup."""

    def test_original_soup_not_modified_after_content_audit(self):
        """Script/style tags in original soup must survive audit_content_quality()."""
        html = """
        <html><body>
            <h1>Title</h1>
            <script>var x = 1;</script>
            <style>.foo { color: red; }</style>
            <p>Some content here with enough words to be meaningful 1234</p>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")

        # Count script/style tags before
        scripts_before = len(soup.find_all("script"))
        styles_before = len(soup.find_all("style"))

        assert scripts_before == 1
        assert styles_before == 1

        # Run audit (this used to modify the original soup with copy.copy)
        audit_content_quality(soup, "https://example.com")

        # Verify original soup is NOT modified (fix #160)
        scripts_after = len(soup.find_all("script"))
        styles_after = len(soup.find_all("style"))

        assert scripts_after == scripts_before, "deepcopy failed: script tags removed from original soup"
        assert styles_after == styles_before, "deepcopy failed: style tags removed from original soup"

    def test_content_audit_excludes_script_text_from_word_count(self):
        """Word count should NOT include script/style content."""
        html = """
        <html><body>
            <h1>Title</h1>
            <script>var longVariable = "should not count";</script>
            <p>one two three</p>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = audit_content_quality(soup, "https://example.com")

        # Script content should be excluded
        assert result.word_count < 20


# ============================================================================
# Fix #161: shared helpers _classify_robots_content / _parse_llms_content
# ============================================================================


class TestClassifyRobotsContent:
    """Test the shared robots.txt classification logic."""

    def test_classify_robots_with_allowed_bots(self):
        """Robots.txt allowing GPTBot should be classified correctly."""
        content = """
User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /
"""
        result = _classify_robots_content(content)

        assert result.found is True
        assert "GPTBot" in result.bots_allowed
        assert "ClaudeBot" in result.bots_allowed

    def test_classify_robots_with_blocked_bots(self):
        """Robots.txt blocking bots should be classified correctly."""
        content = """
User-agent: GPTBot
Disallow: /
"""
        result = _classify_robots_content(content)

        assert result.found is True
        assert "GPTBot" in result.bots_blocked

    def test_classify_robots_with_custom_bots(self):
        """Custom bot dict should override default AI_BOTS."""
        content = """
User-agent: CustomBot
Allow: /
"""
        custom_bots = {"CustomBot": "A custom bot"}
        result = _classify_robots_content(content, bots=custom_bots)

        assert result.found is True
        assert "CustomBot" in result.bots_allowed

    def test_classify_robots_empty_content(self):
        """Empty robots.txt should still be found but with all bots missing."""
        result = _classify_robots_content("")

        assert result.found is True

    def test_audit_robots_from_response_uses_shared_logic(self):
        """_audit_robots_from_response should produce same results as _classify_robots_content."""
        content = """
User-agent: GPTBot
Allow: /
"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = content

        from_response = _audit_robots_from_response(mock_response)
        from_content = _classify_robots_content(content)

        assert from_response.found == from_content.found
        assert from_response.bots_allowed == from_content.bots_allowed
        assert from_response.bots_blocked == from_content.bots_blocked

    def test_audit_robots_from_response_none(self):
        """None response should return empty RobotsResult."""
        result = _audit_robots_from_response(None)
        assert result.found is False

    def test_audit_robots_from_response_404(self):
        """404 response should return empty RobotsResult."""
        mock_response = Mock()
        mock_response.status_code = 404
        result = _audit_robots_from_response(mock_response)
        assert result.found is False

    def test_sync_audit_robots_uses_shared_logic(self):
        """audit_robots_txt() should produce same classification as _classify_robots_content."""
        content = """
User-agent: GPTBot
Allow: /
"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = content

        with patch("geo_optimizer.core.audit.fetch_url", return_value=(mock_response, None)):
            sync_result = audit_robots_txt("https://example.com")

        direct_result = _classify_robots_content(content)

        assert sync_result.found == direct_result.found
        assert sync_result.bots_allowed == direct_result.bots_allowed


class TestParseLlmsContent:
    """Test the shared llms.txt parsing logic."""

    def test_parse_well_formed_llms(self):
        """Well-formed llms.txt should be parsed correctly."""
        content = """# My Website

> This is a description of the website.

## Documentation

- [Getting Started](https://example.com/start)
- [API Reference](https://example.com/api)

## Blog

- [Latest Post](https://example.com/blog/post)
"""
        result = _parse_llms_content(content)

        assert result.found is True
        assert result.has_h1 is True
        assert result.has_description is True
        assert result.has_sections is True
        assert result.has_links is True
        assert result.word_count > 0

    def test_parse_minimal_llms(self):
        """Minimal llms.txt with only H1."""
        result = _parse_llms_content("# My Site")

        assert result.found is True
        assert result.has_h1 is True
        assert result.has_description is False
        assert result.has_sections is False
        assert result.has_links is False

    def test_parse_llms_with_bom(self):
        """UTF-8 BOM should be stripped."""
        content = "\ufeff# My Site\n> Description"
        result = _parse_llms_content(content)

        assert result.found is True
        assert result.has_h1 is True
        assert result.has_description is True

    def test_audit_llms_from_response_uses_shared_logic(self):
        """_audit_llms_from_response should produce same results as _parse_llms_content."""
        content = "# Title\n> Desc\n## Sec\n[Link](url)"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = content

        from_response = _audit_llms_from_response(mock_response)
        from_content = _parse_llms_content(content)

        assert from_response.found == from_content.found
        assert from_response.has_h1 == from_content.has_h1
        assert from_response.has_sections == from_content.has_sections
        assert from_response.has_links == from_content.has_links

    def test_audit_llms_from_response_none(self):
        """None response should return empty LlmsTxtResult."""
        result = _audit_llms_from_response(None)
        assert result.found is False

    def test_sync_audit_llms_uses_shared_logic(self):
        """audit_llms_txt() should produce same parsing as _parse_llms_content."""
        content = "# Title\n> Desc\n## Sec\n[Link](url)"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = content

        with patch("geo_optimizer.core.audit.fetch_url", return_value=(mock_response, None)):
            sync_result = audit_llms_txt("https://example.com")

        direct_result = _parse_llms_content(content)

        assert sync_result.found == direct_result.found
        assert sync_result.has_h1 == direct_result.has_h1
        assert sync_result.has_links == direct_result.has_links


# ============================================================================
# Fix #162: plugin error handling in _build_audit_result
# ============================================================================


class TestPluginErrorHandling:
    """Test that plugin failures don't crash the audit."""

    def test_build_audit_result_survives_plugin_crash(self):
        """If CheckRegistry.run_all raises, audit result should still be built."""
        robots = RobotsResult(found=True)
        llms = LlmsTxtResult(found=True)
        schema = SchemaResult()
        meta = MetaResult(has_title=True)
        content = ContentResult(has_h1=True)

        with patch("geo_optimizer.core.registry.CheckRegistry") as mock_registry:
            # Simulate a plugin that crashes
            mock_registry.all.return_value = [Mock()]
            mock_registry.run_all.side_effect = RuntimeError("Plugin crashed!")

            result = _build_audit_result(
                base_url="https://example.com",
                robots=robots,
                llms=llms,
                schema=schema,
                meta=meta,
                content=content,
                http_status=200,
                page_size=5000,
            )

        # The audit result should still be valid
        assert result.url == "https://example.com"
        assert result.score > 0
        assert result.extra_checks == {}

    def test_build_audit_result_with_working_plugins(self):
        """Normal plugin execution should still work after adding error handling."""
        robots = RobotsResult()
        llms = LlmsTxtResult()
        schema = SchemaResult()
        meta = MetaResult()
        content = ContentResult()

        mock_check_result = Mock()
        mock_check_result.name = "test_check"
        mock_check_result.score = 8
        mock_check_result.max_score = 10
        mock_check_result.passed = True
        mock_check_result.message = "OK"
        mock_check_result.details = {}

        with patch("geo_optimizer.core.registry.CheckRegistry") as mock_registry:
            mock_registry.all.return_value = [Mock()]
            mock_registry.run_all.return_value = [mock_check_result]

            result = _build_audit_result(
                base_url="https://example.com",
                robots=robots,
                llms=llms,
                schema=schema,
                meta=meta,
                content=content,
                http_status=200,
                page_size=5000,
            )

        assert "test_check" in result.extra_checks
        assert result.extra_checks["test_check"]["score"] == 8

    def test_build_audit_result_no_plugins(self):
        """When no plugins are registered, extra_checks should be empty."""
        robots = RobotsResult()
        llms = LlmsTxtResult()
        schema = SchemaResult()
        meta = MetaResult()
        content = ContentResult()

        with patch("geo_optimizer.core.registry.CheckRegistry") as mock_registry:
            mock_registry.all.return_value = []

            result = _build_audit_result(
                base_url="https://example.com",
                robots=robots,
                llms=llms,
                schema=schema,
                meta=meta,
                content=content,
                http_status=200,
                page_size=5000,
            )

        assert result.extra_checks == {}


# ============================================================================
# Fix #163: SSRF validation in http_async.py
# ============================================================================


class TestAsyncSSRFProtection:
    """Test that async HTTP client validates URLs against SSRF."""

    def test_async_fetch_blocks_private_ip(self):
        """fetch_url_async should block URLs resolving to private IPs."""
        import asyncio

        from geo_optimizer.utils.http_async import fetch_url_async

        with patch("geo_optimizer.utils.validators.validate_public_url", return_value=(False, "Private IP")):
            result = asyncio.get_event_loop().run_until_complete(fetch_url_async("http://192.168.1.1/secret"))

        response, error = result
        assert response is None
        assert "non sicuro" in error

    def test_async_fetch_blocks_localhost(self):
        """fetch_url_async should block localhost URLs."""
        import asyncio

        from geo_optimizer.utils.http_async import fetch_url_async

        with patch(
            "geo_optimizer.utils.validators.validate_public_url",
            return_value=(False, "Host non consentito: 'localhost'."),
        ):
            response, error = asyncio.get_event_loop().run_until_complete(
                fetch_url_async("http://localhost:8080/admin")
            )

        assert response is None
        assert "non sicuro" in error

    def test_async_fetch_blocks_metadata_endpoint(self):
        """fetch_url_async should block cloud metadata endpoints."""
        import asyncio

        from geo_optimizer.utils.http_async import fetch_url_async

        with patch(
            "geo_optimizer.utils.validators.validate_public_url",
            return_value=(False, "Host non consentito: '169.254.169.254'."),
        ):
            response, error = asyncio.get_event_loop().run_until_complete(
                fetch_url_async("http://169.254.169.254/latest/meta-data/")
            )

        assert response is None
        assert "non sicuro" in error
