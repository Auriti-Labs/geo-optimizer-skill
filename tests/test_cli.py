"""
Comprehensive tests for the Click CLI commands in geo_optimizer.

Tests all CLI subcommands (audit, llms, schema) using Click's CliRunner,
with all external dependencies mocked via unittest.mock.patch.
"""

import json
import os
import tempfile
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from geo_optimizer import __version__
from geo_optimizer.cli.main import cli
from geo_optimizer.models.results import (
    AuditResult,
    ContentResult,
    LlmsTxtResult,
    MetaResult,
    RobotsResult,
    SchemaAnalysis,
    SchemaResult,
    SitemapUrl,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def runner():
    """Create a Click CliRunner for invoking CLI commands."""
    return CliRunner()


@pytest.fixture
def sample_audit_result():
    """Create a fully populated AuditResult for testing."""
    return AuditResult(
        url="https://example.com",
        timestamp="2026-01-15T12:00:00+00:00",
        score=75,
        band="good",
        http_status=200,
        page_size=15000,
        robots=RobotsResult(
            found=True,
            bots_allowed=["GPTBot", "ClaudeBot"],
            bots_blocked=["Bytespider"],
            bots_missing=["PerplexityBot"],
            citation_bots_ok=False,
        ),
        llms=LlmsTxtResult(
            found=True,
            has_h1=True,
            has_description=True,
            has_sections=True,
            has_links=True,
            word_count=350,
        ),
        schema=SchemaResult(
            found_types=["WebSite", "FAQPage"],
            has_website=True,
            has_webapp=False,
            has_faq=True,
        ),
        meta=MetaResult(
            has_title=True,
            has_description=True,
            has_canonical=True,
            has_og_title=True,
            has_og_description=True,
            has_og_image=True,
            title_text="Example Site",
            description_text="An example site for testing",
            description_length=28,
            title_length=12,
            canonical_url="https://example.com",
        ),
        content=ContentResult(
            has_h1=True,
            heading_count=5,
            has_numbers=True,
            has_links=True,
            word_count=500,
            h1_text="Welcome to Example",
            numbers_count=8,
            external_links_count=3,
        ),
        recommendations=["Add WebApplication schema", "Improve robots.txt coverage"],
    )


@pytest.fixture
def minimal_audit_result():
    """Create a minimal AuditResult with mostly default/empty values."""
    return AuditResult(
        url="https://minimal.example.com",
        timestamp="2026-01-15T12:00:00+00:00",
        score=15,
        band="critical",
        http_status=200,
        page_size=500,
    )


@pytest.fixture
def sample_schema_analysis():
    """Create a SchemaAnalysis result for testing."""
    return SchemaAnalysis(
        found_schemas=[
            {"type": "WebSite", "data": {"url": "https://example.com", "name": "Example"}},
            {"type": "FAQPage", "data": {"mainEntity": [{"name": "Q1"}, {"name": "Q2"}]}},
        ],
        found_types=["WebSite", "FAQPage"],
        missing=["organization"],
        extracted_faqs=[
            {"question": "What is GEO?", "answer": "Generative Engine Optimization"},
            {"question": "Why use it?", "answer": "To be visible to AI search engines"},
        ],
        duplicates={},
        has_head=True,
        total_scripts=2,
    )


# ============================================================================
# 1. VERSION & HELP
# ============================================================================


class TestCLIVersionAndHelp:
    """Tests for --version and --help flags on the main CLI group."""

    def test_version_output(self, runner):
        """geo --version outputs the package version."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output
        assert "geo-optimizer" in result.output

    def test_help_lists_all_commands(self, runner):
        """geo --help lists audit, llms, and schema commands."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "audit" in result.output
        assert "llms" in result.output
        assert "schema" in result.output
        assert "GEO Optimizer" in result.output

    def test_audit_help(self, runner):
        """geo audit --help shows audit-specific options."""
        result = runner.invoke(cli, ["audit", "--help"])
        assert result.exit_code == 0
        assert "--url" in result.output
        assert "--format" in result.output
        assert "--output" in result.output
        assert "--verbose" in result.output

    def test_llms_help(self, runner):
        """geo llms --help shows llms-specific options."""
        result = runner.invoke(cli, ["llms", "--help"])
        assert result.exit_code == 0
        assert "--base-url" in result.output
        assert "--output" in result.output
        assert "--sitemap" in result.output
        assert "--fetch-titles" in result.output

    def test_schema_help(self, runner):
        """geo schema --help shows schema-specific options."""
        result = runner.invoke(cli, ["schema", "--help"])
        assert result.exit_code == 0
        assert "--file" in result.output
        assert "--type" in result.output
        assert "--analyze" in result.output
        assert "--astro" in result.output
        assert "--inject" in result.output

    def test_no_args_shows_usage(self, runner):
        """Running geo with no arguments shows help."""
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "Usage" in result.output


# ============================================================================
# 2. AUDIT COMMAND
# ============================================================================


class TestAuditCommand:
    """Tests for the `geo audit` CLI command."""

    @patch("geo_optimizer.cli.audit_cmd.run_full_audit")
    def test_audit_text_output(self, mock_audit, runner, sample_audit_result):
        """geo audit --url URL produces text output by default."""
        mock_audit.return_value = sample_audit_result
        result = runner.invoke(cli, ["audit", "--url", "https://example.com"])
        assert result.exit_code == 0
        assert "GEO AUDIT" in result.output
        assert "example.com" in result.output
        assert "ROBOTS.TXT" in result.output
        assert "LLMS.TXT" in result.output
        assert "SCHEMA JSON-LD" in result.output
        assert "META TAGS" in result.output
        assert "CONTENT QUALITY" in result.output
        assert "75/100" in result.output
        mock_audit.assert_called_once_with("https://example.com")

    @patch("geo_optimizer.cli.audit_cmd.run_full_audit")
    def test_audit_json_output(self, mock_audit, runner, sample_audit_result):
        """geo audit --url URL --format json produces valid JSON."""
        mock_audit.return_value = sample_audit_result
        result = runner.invoke(cli, ["audit", "--url", "https://example.com", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["url"] == "https://example.com"
        assert data["score"] == 75
        assert data["band"] == "good"
        assert "checks" in data
        assert "robots_txt" in data["checks"]
        assert "llms_txt" in data["checks"]
        assert "schema_jsonld" in data["checks"]
        assert "meta_tags" in data["checks"]
        assert "content" in data["checks"]
        assert "recommendations" in data

    @patch("geo_optimizer.cli.audit_cmd.run_full_audit")
    def test_audit_json_check_scores(self, mock_audit, runner, sample_audit_result):
        """JSON output includes per-check scores and max values."""
        mock_audit.return_value = sample_audit_result
        result = runner.invoke(cli, ["audit", "--url", "https://example.com", "--format", "json"])
        data = json.loads(result.output)
        for check_name, check_data in data["checks"].items():
            assert "score" in check_data, f"Missing 'score' in {check_name}"
            assert "max" in check_data, f"Missing 'max' in {check_name}"
            assert "passed" in check_data, f"Missing 'passed' in {check_name}"
            assert "details" in check_data, f"Missing 'details' in {check_name}"

    @patch("geo_optimizer.cli.audit_cmd.run_full_audit")
    def test_audit_file_output(self, mock_audit, runner, sample_audit_result):
        """geo audit --output FILE writes the report to a file."""
        mock_audit.return_value = sample_audit_result
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            output_path = f.name
        try:
            result = runner.invoke(cli, [
                "audit", "--url", "https://example.com", "--output", output_path
            ])
            assert result.exit_code == 0
            assert "Report written to" in result.output
            assert output_path in result.output
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "GEO AUDIT" in content
            assert "example.com" in content
        finally:
            os.unlink(output_path)

    @patch("geo_optimizer.cli.audit_cmd.run_full_audit")
    def test_audit_json_file_output(self, mock_audit, runner, sample_audit_result):
        """geo audit --format json --output FILE writes valid JSON to a file."""
        mock_audit.return_value = sample_audit_result
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_path = f.name
        try:
            result = runner.invoke(cli, [
                "audit", "--url", "https://example.com",
                "--format", "json", "--output", output_path,
            ])
            assert result.exit_code == 0
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data["score"] == 75
        finally:
            os.unlink(output_path)

    @patch("geo_optimizer.cli.audit_cmd.run_full_audit")
    def test_audit_error_text_format(self, mock_audit, runner):
        """Audit errors in text mode print error message and exit 1."""
        mock_audit.side_effect = ConnectionError("Connection refused")
        result = runner.invoke(cli, ["audit", "--url", "https://broken.example.com"])
        assert result.exit_code == 1
        # Error message is written to stderr via click.echo(err=True);
        # CliRunner merges stderr into output by default.
        combined = result.output
        assert "ERROR" in combined
        assert "Connection refused" in combined

    @patch("geo_optimizer.cli.audit_cmd.run_full_audit")
    def test_audit_error_json_format(self, mock_audit, runner):
        """Audit errors in JSON mode produce a JSON error object on stdout."""
        mock_audit.side_effect = RuntimeError("Server error")
        result = runner.invoke(cli, [
            "audit", "--url", "https://broken.example.com", "--format", "json"
        ])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert "error" in data
        assert data["error"] == "Server error"
        assert data["url"] == "https://broken.example.com"

    def test_audit_missing_url(self, runner):
        """geo audit without --url exits with an error."""
        result = runner.invoke(cli, ["audit"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    @patch("geo_optimizer.cli.audit_cmd.run_full_audit")
    def test_audit_invalid_format_choice(self, mock_audit, runner):
        """geo audit --format xml is rejected by Click's choice validation."""
        result = runner.invoke(cli, [
            "audit", "--url", "https://example.com", "--format", "xml"
        ])
        assert result.exit_code != 0

    @patch("geo_optimizer.cli.audit_cmd.run_full_audit")
    def test_audit_minimal_result_text(self, mock_audit, runner, minimal_audit_result):
        """Text output handles a minimal result (mostly empty/default fields)."""
        mock_audit.return_value = minimal_audit_result
        result = runner.invoke(cli, ["audit", "--url", "https://minimal.example.com"])
        assert result.exit_code == 0
        assert "15/100" in result.output
        assert "CRITICAL" in result.output

    @patch("geo_optimizer.cli.audit_cmd.run_full_audit")
    def test_audit_recommendations_listed(self, mock_audit, runner, sample_audit_result):
        """Text output includes the recommendation list."""
        mock_audit.return_value = sample_audit_result
        result = runner.invoke(cli, ["audit", "--url", "https://example.com"])
        assert result.exit_code == 0
        assert "Add WebApplication schema" in result.output
        assert "Improve robots.txt coverage" in result.output
        assert "NEXT PRIORITY STEPS" in result.output

    @patch("geo_optimizer.cli.audit_cmd.run_full_audit")
    def test_audit_no_recommendations(self, mock_audit, runner):
        """Text output shows 'Great!' when there are no recommendations."""
        audit_result = AuditResult(
            url="https://perfect.example.com",
            timestamp="2026-01-15T12:00:00+00:00",
            score=95,
            band="excellent",
            http_status=200,
            page_size=10000,
            recommendations=[],
        )
        mock_audit.return_value = audit_result
        result = runner.invoke(cli, ["audit", "--url", "https://perfect.example.com"])
        assert result.exit_code == 0
        assert "Great!" in result.output or "implemented" in result.output


# ============================================================================
# 3. LLMS COMMAND
# ============================================================================


class TestLlmsCommand:
    """Tests for the `geo llms` CLI command."""

    @patch("geo_optimizer.cli.llms_cmd.generate_llms_txt")
    @patch("geo_optimizer.cli.llms_cmd.fetch_sitemap")
    @patch("geo_optimizer.cli.llms_cmd.discover_sitemap")
    def test_llms_with_sitemap_found(self, mock_discover, mock_fetch, mock_generate, runner):
        """geo llms --base-url URL discovers sitemap and generates output."""
        mock_discover.return_value = "https://example.com/sitemap.xml"
        mock_fetch.return_value = [
            SitemapUrl(url="https://example.com/"),
            SitemapUrl(url="https://example.com/about"),
            SitemapUrl(url="https://example.com/blog/post-1"),
        ]
        mock_generate.return_value = "# Example\n\n> A site\n\n## Pages\n\n- [Home](https://example.com/)\n"

        result = runner.invoke(cli, ["llms", "--base-url", "https://example.com"])
        assert result.exit_code == 0
        assert "# Example" in result.output
        mock_discover.assert_called_once()
        mock_fetch.assert_called_once_with(
            "https://example.com/sitemap.xml",
            on_status=mock_fetch.call_args[1]["on_status"],
        )
        mock_generate.assert_called_once()

    @patch("geo_optimizer.cli.llms_cmd.discover_sitemap")
    def test_llms_no_sitemap_found_minimal_output(self, mock_discover, runner):
        """When no sitemap is found, a minimal llms.txt is output."""
        mock_discover.return_value = None
        result = runner.invoke(cli, ["llms", "--base-url", "https://example.com"])
        assert result.exit_code == 0
        assert "No sitemap found" in result.output
        assert "# Example" in result.output or "Homepage" in result.output
        assert "https://example.com" in result.output

    @patch("geo_optimizer.cli.llms_cmd.discover_sitemap")
    def test_llms_no_sitemap_custom_name_and_description(self, mock_discover, runner):
        """Minimal output uses --site-name and --description when sitemap missing."""
        mock_discover.return_value = None
        result = runner.invoke(cli, [
            "llms", "--base-url", "https://example.com",
            "--site-name", "My Custom Site",
            "--description", "A custom description",
        ])
        assert result.exit_code == 0
        assert "My Custom Site" in result.output
        assert "A custom description" in result.output

    @patch("geo_optimizer.cli.llms_cmd.discover_sitemap")
    def test_llms_no_sitemap_file_output(self, mock_discover, runner):
        """Minimal llms.txt is written to --output file when no sitemap found."""
        mock_discover.return_value = None
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            output_path = f.name
        try:
            result = runner.invoke(cli, [
                "llms", "--base-url", "https://example.com", "--output", output_path
            ])
            assert result.exit_code == 0
            assert "Minimal llms.txt written to" in result.output
            with open(output_path, "r") as f:
                content = f.read()
            assert "Homepage" in content
            assert "https://example.com" in content
        finally:
            os.unlink(output_path)

    @patch("geo_optimizer.cli.llms_cmd.generate_llms_txt")
    @patch("geo_optimizer.cli.llms_cmd.fetch_sitemap")
    @patch("geo_optimizer.cli.llms_cmd.discover_sitemap")
    def test_llms_file_output(self, mock_discover, mock_fetch, mock_generate, runner):
        """geo llms --output FILE writes content to a file."""
        mock_discover.return_value = "https://example.com/sitemap.xml"
        mock_fetch.return_value = [SitemapUrl(url="https://example.com/")]
        content_str = "# Example\n\n> Site description\n\n## Pages\n\n- [Home](https://example.com/)\n"
        mock_generate.return_value = content_str
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            output_path = f.name
        try:
            result = runner.invoke(cli, [
                "llms", "--base-url", "https://example.com", "--output", output_path
            ])
            assert result.exit_code == 0
            assert "llms.txt written to" in result.output
            with open(output_path, "r") as f:
                written = f.read()
            assert written == content_str
        finally:
            os.unlink(output_path)

    @patch("geo_optimizer.cli.llms_cmd.generate_llms_txt")
    @patch("geo_optimizer.cli.llms_cmd.fetch_sitemap")
    @patch("geo_optimizer.cli.llms_cmd.discover_sitemap")
    def test_llms_fetch_titles_flag(self, mock_discover, mock_fetch, mock_generate, runner):
        """--fetch-titles flag is passed through to generate_llms_txt."""
        mock_discover.return_value = "https://example.com/sitemap.xml"
        mock_fetch.return_value = [SitemapUrl(url="https://example.com/")]
        mock_generate.return_value = "# Example\n"

        runner.invoke(cli, [
            "llms", "--base-url", "https://example.com", "--fetch-titles"
        ])
        call_kwargs = mock_generate.call_args[1]
        assert call_kwargs["fetch_titles"] is True

    @patch("geo_optimizer.cli.llms_cmd.generate_llms_txt")
    @patch("geo_optimizer.cli.llms_cmd.fetch_sitemap")
    @patch("geo_optimizer.cli.llms_cmd.discover_sitemap")
    def test_llms_max_per_section(self, mock_discover, mock_fetch, mock_generate, runner):
        """--max-per-section is passed through to generate_llms_txt."""
        mock_discover.return_value = "https://example.com/sitemap.xml"
        mock_fetch.return_value = [SitemapUrl(url="https://example.com/")]
        mock_generate.return_value = "# Example\n"

        runner.invoke(cli, [
            "llms", "--base-url", "https://example.com", "--max-per-section", "5"
        ])
        call_kwargs = mock_generate.call_args[1]
        assert call_kwargs["max_urls_per_section"] == 5

    @patch("geo_optimizer.cli.llms_cmd.generate_llms_txt")
    @patch("geo_optimizer.cli.llms_cmd.fetch_sitemap")
    @patch("geo_optimizer.cli.llms_cmd.discover_sitemap")
    def test_llms_explicit_sitemap(self, mock_discover, mock_fetch, mock_generate, runner):
        """--sitemap URL bypasses sitemap discovery."""
        mock_fetch.return_value = [SitemapUrl(url="https://example.com/")]
        mock_generate.return_value = "# Example\n"

        runner.invoke(cli, [
            "llms", "--base-url", "https://example.com",
            "--sitemap", "https://example.com/custom-sitemap.xml"
        ])
        mock_discover.assert_not_called()
        mock_fetch.assert_called_once()
        assert "custom-sitemap.xml" in mock_fetch.call_args[0][0]

    @patch("geo_optimizer.cli.llms_cmd.fetch_sitemap")
    @patch("geo_optimizer.cli.llms_cmd.discover_sitemap")
    def test_llms_empty_sitemap_exits(self, mock_discover, mock_fetch, runner):
        """If fetch_sitemap returns empty list, exit with error."""
        mock_discover.return_value = "https://example.com/sitemap.xml"
        mock_fetch.return_value = []

        result = runner.invoke(cli, ["llms", "--base-url", "https://example.com"])
        assert result.exit_code == 1
        assert "No URLs found" in result.output

    @patch("geo_optimizer.cli.llms_cmd.generate_llms_txt")
    @patch("geo_optimizer.cli.llms_cmd.fetch_sitemap")
    @patch("geo_optimizer.cli.llms_cmd.discover_sitemap")
    def test_llms_url_normalization_no_scheme(self, mock_discover, mock_fetch, mock_generate, runner):
        """URLs without http(s):// get https:// prepended."""
        mock_discover.return_value = "https://example.com/sitemap.xml"
        mock_fetch.return_value = [SitemapUrl(url="https://example.com/")]
        mock_generate.return_value = "# Example\n"

        result = runner.invoke(cli, ["llms", "--base-url", "example.com"])
        assert result.exit_code == 0
        assert "https://example.com" in result.output

    def test_llms_missing_base_url(self, runner):
        """geo llms without --base-url exits with an error."""
        result = runner.invoke(cli, ["llms"])
        assert result.exit_code != 0


# ============================================================================
# 4. SCHEMA COMMAND — ANALYZE
# ============================================================================


class TestSchemaAnalyzeCommand:
    """Tests for `geo schema --analyze`."""

    @patch("geo_optimizer.cli.schema_cmd.analyze_html_file")
    def test_analyze_shows_found_schemas(self, mock_analyze, runner, sample_schema_analysis):
        """geo schema --analyze --file FILE reports found schemas."""
        mock_analyze.return_value = sample_schema_analysis
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            f.write(b"<html><head></head><body></body></html>")
            file_path = f.name
        try:
            result = runner.invoke(cli, ["schema", "--analyze", "--file", file_path])
            assert result.exit_code == 0
            assert "SCHEMA ANALYSIS" in result.output
            assert "Found 2 schema(s)" in result.output
            assert "WebSite" in result.output
            assert "FAQPage" in result.output
            mock_analyze.assert_called_once_with(file_path)
        finally:
            os.unlink(file_path)

    @patch("geo_optimizer.cli.schema_cmd.analyze_html_file")
    def test_analyze_shows_missing_schemas(self, mock_analyze, runner, sample_schema_analysis):
        """Analysis output includes suggestions for missing schemas."""
        mock_analyze.return_value = sample_schema_analysis
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            f.write(b"<html><head></head><body></body></html>")
            file_path = f.name
        try:
            result = runner.invoke(cli, ["schema", "--analyze", "--file", file_path])
            assert result.exit_code == 0
            assert "Suggested schemas to add" in result.output
            assert "ORGANIZATION" in result.output
        finally:
            os.unlink(file_path)

    @patch("geo_optimizer.cli.schema_cmd.analyze_html_file")
    def test_analyze_shows_extracted_faqs(self, mock_analyze, runner, sample_schema_analysis):
        """Analysis output shows auto-detected FAQ items."""
        mock_analyze.return_value = sample_schema_analysis
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            f.write(b"<html><head></head><body></body></html>")
            file_path = f.name
        try:
            result = runner.invoke(cli, ["schema", "--analyze", "--file", file_path])
            assert result.exit_code == 0
            assert "Auto-detected 2 FAQ items" in result.output
            assert "What is GEO?" in result.output
        finally:
            os.unlink(file_path)

    @patch("geo_optimizer.cli.schema_cmd.analyze_html_file")
    def test_analyze_no_schemas_found(self, mock_analyze, runner):
        """Analysis output reports when no schemas are found."""
        mock_analyze.return_value = SchemaAnalysis(
            found_schemas=[],
            found_types=[],
            missing=["website"],
            extracted_faqs=[],
            duplicates={},
            has_head=True,
            total_scripts=0,
        )
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            f.write(b"<html><head></head><body></body></html>")
            file_path = f.name
        try:
            result = runner.invoke(cli, ["schema", "--analyze", "--file", file_path])
            assert result.exit_code == 0
            assert "No JSON-LD schemas found" in result.output
        finally:
            os.unlink(file_path)

    @patch("geo_optimizer.cli.schema_cmd.analyze_html_file")
    def test_analyze_shows_duplicates(self, mock_analyze, runner):
        """Analysis output warns about duplicate schemas."""
        mock_analyze.return_value = SchemaAnalysis(
            found_schemas=[
                {"type": "WebSite", "data": {"url": "https://example.com", "name": "Ex"}},
                {"type": "WebSite", "data": {"url": "https://example.com", "name": "Ex2"}},
            ],
            found_types=["WebSite"],
            missing=[],
            extracted_faqs=[],
            duplicates={"WebSite": 2},
            has_head=True,
            total_scripts=2,
        )
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            f.write(b"<html><head></head><body></body></html>")
            file_path = f.name
        try:
            result = runner.invoke(cli, ["schema", "--analyze", "--file", file_path])
            assert result.exit_code == 0
            assert "DUPLICATE SCHEMAS DETECTED" in result.output
            assert "WebSite" in result.output
            assert "2 instances" in result.output
        finally:
            os.unlink(file_path)

    def test_analyze_without_file_exits(self, runner):
        """geo schema --analyze without --file exits with error."""
        result = runner.invoke(cli, ["schema", "--analyze"])
        assert result.exit_code == 1
        assert "--file required" in result.output


# ============================================================================
# 5. SCHEMA COMMAND — GENERATE
# ============================================================================


class TestSchemaGenerateCommand:
    """Tests for `geo schema --type TYPE` generation mode."""

    def test_generate_website_schema(self, runner):
        """geo schema --type website --name X --url Y generates a WebSite script tag."""
        result = runner.invoke(cli, [
            "schema", "--type", "website",
            "--name", "Test Site",
            "--url", "https://test.example.com",
        ])
        assert result.exit_code == 0
        assert 'application/ld+json' in result.output
        assert '"@type": "WebSite"' in result.output
        assert '"name": "Test Site"' in result.output
        assert '"url": "https://test.example.com"' in result.output

    def test_generate_webapp_schema(self, runner):
        """geo schema --type webapp generates a WebApplication script tag."""
        result = runner.invoke(cli, [
            "schema", "--type", "webapp",
            "--name", "My App",
            "--url", "https://app.example.com",
            "--description", "A test app",
        ])
        assert result.exit_code == 0
        assert '"@type": "WebApplication"' in result.output
        assert '"name": "My App"' in result.output

    def test_generate_organization_schema(self, runner):
        """geo schema --type organization generates an Organization script tag."""
        result = runner.invoke(cli, [
            "schema", "--type", "organization",
            "--name", "My Org",
            "--url", "https://org.example.com",
        ])
        assert result.exit_code == 0
        assert '"@type": "Organization"' in result.output
        assert '"name": "My Org"' in result.output

    def test_generate_breadcrumb_schema(self, runner):
        """geo schema --type breadcrumb generates a BreadcrumbList script tag."""
        result = runner.invoke(cli, [
            "schema", "--type", "breadcrumb",
            "--url", "https://example.com",
        ])
        assert result.exit_code == 0
        assert '"@type": "BreadcrumbList"' in result.output
        assert '"itemListElement"' in result.output

    def test_generate_schema_with_all_fields(self, runner):
        """All optional fields are reflected in the generated schema."""
        result = runner.invoke(cli, [
            "schema", "--type", "webapp",
            "--name", "Full App",
            "--url", "https://full.example.com",
            "--description", "Full description",
            "--author", "Test Author",
            "--logo-url", "https://full.example.com/logo.png",
        ])
        assert result.exit_code == 0
        assert '"Full App"' in result.output
        assert '"Full description"' in result.output
        assert '"Test Author"' in result.output


# ============================================================================
# 6. SCHEMA COMMAND — ASTRO SNIPPET
# ============================================================================


class TestSchemaAstroCommand:
    """Tests for `geo schema --astro`."""

    @patch("geo_optimizer.cli.schema_cmd.generate_astro_snippet")
    def test_astro_snippet_output(self, mock_astro, runner):
        """geo schema --astro --name X --url Y outputs an Astro snippet."""
        mock_astro.return_value = "---\n// Astro snippet for Test Site\n---\n<html></html>"
        result = runner.invoke(cli, [
            "schema", "--astro",
            "--name", "Test Site",
            "--url", "https://test.example.com",
        ])
        assert result.exit_code == 0
        assert "Astro snippet" in result.output
        mock_astro.assert_called_once_with("https://test.example.com", "Test Site")

    def test_astro_missing_url(self, runner):
        """geo schema --astro --name X without --url exits with error."""
        result = runner.invoke(cli, ["schema", "--astro", "--name", "Test"])
        assert result.exit_code == 1
        assert "--url" in result.output and "--name" in result.output

    def test_astro_missing_name(self, runner):
        """geo schema --astro --url X without --name exits with error."""
        result = runner.invoke(cli, ["schema", "--astro", "--url", "https://example.com"])
        assert result.exit_code == 1
        assert "--url" in result.output and "--name" in result.output


# ============================================================================
# 7. SCHEMA COMMAND — FAQ FROM FILE
# ============================================================================


class TestSchemaFaqCommand:
    """Tests for `geo schema --type faq` with --faq-file."""

    def test_faq_from_file(self, runner):
        """geo schema --type faq --faq-file FILE generates FAQPage schema."""
        faq_data = [
            {"question": "What is GEO?", "answer": "Generative Engine Optimization"},
            {"question": "Why use it?", "answer": "To be cited by AI search engines"},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(faq_data, f)
            faq_path = f.name
        try:
            result = runner.invoke(cli, [
                "schema", "--type", "faq", "--faq-file", faq_path
            ])
            assert result.exit_code == 0
            assert '"@type": "FAQPage"' in result.output
            assert "What is GEO?" in result.output
            assert "Generative Engine Optimization" in result.output
            assert '"@type": "Question"' in result.output
        finally:
            os.unlink(faq_path)

    @patch("geo_optimizer.cli.schema_cmd.analyze_html_file")
    def test_faq_auto_extract(self, mock_analyze, runner):
        """geo schema --type faq --auto-extract --file FILE extracts FAQs from HTML."""
        mock_analyze.return_value = SchemaAnalysis(
            found_schemas=[],
            found_types=[],
            missing=[],
            extracted_faqs=[
                {"question": "Auto Q1", "answer": "Auto A1"},
                {"question": "Auto Q2", "answer": "Auto A2"},
            ],
            duplicates={},
            has_head=True,
            total_scripts=0,
        )
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            f.write(b"<html><body><dt>Q</dt><dd>A</dd></body></html>")
            file_path = f.name
        try:
            result = runner.invoke(cli, [
                "schema", "--type", "faq", "--auto-extract", "--file", file_path
            ])
            assert result.exit_code == 0
            assert "Extracted 2 FAQ items" in result.output
            assert '"@type": "FAQPage"' in result.output
            assert "Auto Q1" in result.output
        finally:
            os.unlink(file_path)

    @patch("geo_optimizer.cli.schema_cmd.analyze_html_file")
    def test_faq_auto_extract_no_faqs_found(self, mock_analyze, runner):
        """Auto-extract exits with error when no FAQ items are found."""
        mock_analyze.return_value = SchemaAnalysis(
            found_schemas=[], found_types=[], missing=[],
            extracted_faqs=[], duplicates={}, has_head=True, total_scripts=0,
        )
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            f.write(b"<html><body></body></html>")
            file_path = f.name
        try:
            result = runner.invoke(cli, [
                "schema", "--type", "faq", "--auto-extract", "--file", file_path
            ])
            assert result.exit_code == 1
            assert "No FAQ items found" in result.output
        finally:
            os.unlink(file_path)

    def test_faq_without_source_exits(self, runner):
        """geo schema --type faq without --faq-file or --auto-extract exits with error."""
        result = runner.invoke(cli, ["schema", "--type", "faq"])
        assert result.exit_code == 1
        assert "--auto-extract" in result.output or "--faq-file" in result.output


# ============================================================================
# 8. SCHEMA COMMAND — INJECT
# ============================================================================


class TestSchemaInjectCommand:
    """Tests for `geo schema --type TYPE --inject --file FILE`."""

    @patch("geo_optimizer.cli.schema_cmd.inject_schema_into_html")
    def test_inject_success(self, mock_inject, runner):
        """Successful injection reports success message."""
        mock_inject.return_value = (True, None)
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            f.write(b"<html><head></head><body></body></html>")
            file_path = f.name
        try:
            result = runner.invoke(cli, [
                "schema", "--type", "website",
                "--name", "Test", "--url", "https://example.com",
                "--inject", "--file", file_path,
            ])
            assert result.exit_code == 0
            assert "Schema injected" in result.output
            assert file_path in result.output
            mock_inject.assert_called_once()
            call_kwargs = mock_inject.call_args
            assert call_kwargs[1]["backup"] is True
            assert call_kwargs[1]["validate"] is True
        finally:
            os.unlink(file_path)

    @patch("geo_optimizer.cli.schema_cmd.inject_schema_into_html")
    def test_inject_failure(self, mock_inject, runner):
        """Failed injection reports the error and exits 1."""
        mock_inject.return_value = (False, "No <head> tag found in HTML")
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            f.write(b"<html><body></body></html>")
            file_path = f.name
        try:
            result = runner.invoke(cli, [
                "schema", "--type", "website",
                "--name", "Test", "--url", "https://example.com",
                "--inject", "--file", file_path,
            ])
            assert result.exit_code == 1
            assert "No <head> tag found" in result.output
        finally:
            os.unlink(file_path)

    @patch("geo_optimizer.cli.schema_cmd.inject_schema_into_html")
    def test_inject_no_backup_flag(self, mock_inject, runner):
        """--no-backup flag disables backup creation."""
        mock_inject.return_value = (True, None)
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            f.write(b"<html><head></head><body></body></html>")
            file_path = f.name
        try:
            runner.invoke(cli, [
                "schema", "--type", "website",
                "--name", "Test", "--url", "https://example.com",
                "--inject", "--file", file_path, "--no-backup",
            ])
            call_kwargs = mock_inject.call_args
            assert call_kwargs[1]["backup"] is False
        finally:
            os.unlink(file_path)

    @patch("geo_optimizer.cli.schema_cmd.inject_schema_into_html")
    def test_inject_no_validate_flag(self, mock_inject, runner):
        """--no-validate flag skips schema validation."""
        mock_inject.return_value = (True, None)
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            f.write(b"<html><head></head><body></body></html>")
            file_path = f.name
        try:
            runner.invoke(cli, [
                "schema", "--type", "website",
                "--name", "Test", "--url", "https://example.com",
                "--inject", "--file", file_path, "--no-validate",
            ])
            call_kwargs = mock_inject.call_args
            assert call_kwargs[1]["validate"] is False
        finally:
            os.unlink(file_path)

    def test_inject_without_file_exits(self, runner):
        """geo schema --type website --inject without --file exits with error."""
        result = runner.invoke(cli, [
            "schema", "--type", "website",
            "--name", "Test", "--url", "https://example.com",
            "--inject",
        ])
        assert result.exit_code == 1
        assert "--file required" in result.output


# ============================================================================
# 9. SCHEMA COMMAND — ERROR CASES
# ============================================================================


class TestSchemaErrorCases:
    """Tests for schema command error paths."""

    def test_no_action_specified(self, runner):
        """geo schema with no --analyze, --astro, or --type exits with error."""
        result = runner.invoke(cli, ["schema"])
        assert result.exit_code == 1
        assert "--analyze" in result.output or "--astro" in result.output or "--type" in result.output

    def test_invalid_schema_type(self, runner):
        """geo schema --type invalid_type is rejected by Click Choice."""
        result = runner.invoke(cli, [
            "schema", "--type", "invalid_type",
            "--name", "Test", "--url", "https://example.com",
        ])
        assert result.exit_code != 0

    def test_no_action_with_only_file(self, runner):
        """geo schema --file some.html without an action flag exits with error."""
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            f.write(b"<html></html>")
            file_path = f.name
        try:
            result = runner.invoke(cli, ["schema", "--file", file_path])
            assert result.exit_code == 1
        finally:
            os.unlink(file_path)


# ============================================================================
# 10. FORMATTERS — UNIT TESTS
# ============================================================================


class TestFormatters:
    """Direct tests for format_audit_text() and format_audit_json()."""

    def test_format_audit_json_structure(self, sample_audit_result):
        """format_audit_json returns valid JSON with correct top-level keys."""
        from geo_optimizer.cli.formatters import format_audit_json

        output = format_audit_json(sample_audit_result)
        data = json.loads(output)
        assert data["url"] == "https://example.com"
        assert data["score"] == 75
        assert data["band"] == "good"
        assert set(data["checks"].keys()) == {
            "robots_txt", "llms_txt", "schema_jsonld", "meta_tags", "content"
        }

    def test_format_audit_json_robots_details(self, sample_audit_result):
        """JSON robots_txt check includes correct details."""
        from geo_optimizer.cli.formatters import format_audit_json

        data = json.loads(format_audit_json(sample_audit_result))
        robots = data["checks"]["robots_txt"]
        assert robots["max"] == 20
        assert "bots_allowed" in robots["details"]
        assert "GPTBot" in robots["details"]["bots_allowed"]

    def test_format_audit_text_contains_score_bar(self, sample_audit_result):
        """Text output contains the visual score bar."""
        from geo_optimizer.cli.formatters import format_audit_text

        output = format_audit_text(sample_audit_result)
        assert "75/100" in output
        # The bar uses block characters
        assert "\u2588" in output or "\u2591" in output

    def test_format_audit_text_section_headers(self, sample_audit_result):
        """Text output contains all five section headers."""
        from geo_optimizer.cli.formatters import format_audit_text

        output = format_audit_text(sample_audit_result)
        assert "1. ROBOTS.TXT" in output
        assert "2. LLMS.TXT" in output
        assert "3. SCHEMA JSON-LD" in output
        assert "4. META TAGS" in output
        assert "5. CONTENT QUALITY" in output

    def test_format_audit_text_excellent_band(self):
        """Text output shows EXCELLENT label for score >= 91."""
        from geo_optimizer.cli.formatters import format_audit_text

        result = AuditResult(
            url="https://excellent.example.com",
            score=95,
            band="excellent",
        )
        output = format_audit_text(result)
        assert "EXCELLENT" in output

    def test_format_audit_text_critical_band(self):
        """Text output shows CRITICAL label for score <= 40."""
        from geo_optimizer.cli.formatters import format_audit_text

        result = AuditResult(
            url="https://bad.example.com",
            score=10,
            band="critical",
        )
        output = format_audit_text(result)
        assert "CRITICAL" in output

    def test_format_audit_json_recommendations(self, sample_audit_result):
        """JSON output includes the recommendations list."""
        from geo_optimizer.cli.formatters import format_audit_json

        data = json.loads(format_audit_json(sample_audit_result))
        assert len(data["recommendations"]) == 2
        assert "Add WebApplication schema" in data["recommendations"]
