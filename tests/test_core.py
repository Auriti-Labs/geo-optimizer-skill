"""
Comprehensive unit tests for the geo_optimizer core package modules.

Tests all core business logic, utilities, models, and configuration:
- geo_optimizer.core.audit (robots, llms, schema, meta, content, scoring)
- geo_optimizer.core.llms_generator (sitemap fetching, URL filtering, generation)
- geo_optimizer.core.schema_validator (JSON-LD validation)
- geo_optimizer.core.schema_injector (HTML analysis, injection, FAQ extraction)
- geo_optimizer.utils.http (session creation, fetch_url)
- geo_optimizer.utils.robots_parser (robots.txt parsing, bot classification)
- geo_optimizer.models.config (constants verification)
- geo_optimizer.models.results (dataclass instantiation)

All HTTP calls are mocked — no network access.

Author: Juan Camilo Auriti
"""

import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

from bs4 import BeautifulSoup

# ─── Core imports ────────────────────────────────────────────────────────────

from geo_optimizer.core.audit import (
    audit_robots_txt,
    audit_llms_txt,
    audit_schema,
    audit_meta_tags,
    audit_content_quality,
    compute_geo_score,
    get_score_band,
    build_recommendations,
    run_full_audit,
)
from geo_optimizer.core.llms_generator import (
    fetch_sitemap,
    should_skip,
    categorize_url,
    fetch_page_title,
    url_to_label,
    generate_llms_txt,
    discover_sitemap,
)
from geo_optimizer.core.schema_validator import (
    validate_jsonld,
    validate_jsonld_string,
    get_required_fields,
)
from geo_optimizer.core.schema_injector import (
    fill_template,
    schema_to_html_tag,
    extract_faq_from_html,
    analyze_html_file,
    generate_faq_schema,
    inject_schema_into_html,
    generate_astro_snippet,
)

# ─── Utils imports ───────────────────────────────────────────────────────────

from geo_optimizer.utils.http import create_session_with_retry, fetch_url
from geo_optimizer.utils.robots_parser import (
    parse_robots_txt,
    classify_bot,
    AgentRules,
)

# ─── Models imports ──────────────────────────────────────────────────────────

from geo_optimizer.models.config import (
    AI_BOTS,
    CITATION_BOTS,
    SCORING,
    SCORE_BANDS,
    SCHEMA_TEMPLATES,
    SCHEMA_ORG_REQUIRED,
    HEADERS,
    CATEGORY_PATTERNS,
    SKIP_PATTERNS,
    VALUABLE_SCHEMAS,
    SECTION_PRIORITY_ORDER,
    OPTIONAL_CATEGORIES,
    USER_AGENT,
)
from geo_optimizer.models.results import (
    RobotsResult,
    LlmsTxtResult,
    SchemaResult,
    MetaResult,
    ContentResult,
    AuditResult,
    SchemaAnalysis,
    SitemapUrl,
)


# ============================================================================
# 1. ROBOTS PARSER (geo_optimizer.utils.robots_parser)
# ============================================================================


class TestParseRobotsTxt:
    """Tests for parse_robots_txt()."""

    def test_empty_content(self):
        """Empty robots.txt returns empty dict."""
        result = parse_robots_txt("")
        assert result == {}

    def test_comments_only(self):
        """Robots.txt with only comments returns empty dict."""
        result = parse_robots_txt("# This is a comment\n# Another comment\n")
        assert result == {}

    def test_single_agent_disallow(self):
        """Single user-agent with disallow rule."""
        content = "User-agent: GPTBot\nDisallow: /\n"
        result = parse_robots_txt(content)
        assert "GPTBot" in result
        assert "/" in result["GPTBot"].disallow

    def test_single_agent_allow(self):
        """Single user-agent with allow rule."""
        content = "User-agent: GPTBot\nAllow: /public/\n"
        result = parse_robots_txt(content)
        assert "GPTBot" in result
        assert "/public/" in result["GPTBot"].allow

    def test_wildcard_agent(self):
        """Wildcard user-agent."""
        content = "User-agent: *\nDisallow: /private/\n"
        result = parse_robots_txt(content)
        assert "*" in result
        assert "/private/" in result["*"].disallow

    def test_multiple_agents(self):
        """Multiple user-agents with separate rule blocks."""
        content = (
            "User-agent: GPTBot\n"
            "Disallow: /\n"
            "\n"
            "User-agent: ClaudeBot\n"
            "Allow: /\n"
        )
        result = parse_robots_txt(content)
        assert "GPTBot" in result
        assert "ClaudeBot" in result
        assert "/" in result["GPTBot"].disallow
        assert "/" in result["ClaudeBot"].allow

    def test_consecutive_agents_share_rules(self):
        """RFC 9309: consecutive User-agent lines share the same rule block."""
        content = (
            "User-agent: GPTBot\n"
            "User-agent: ChatGPT-User\n"
            "Disallow: /\n"
        )
        result = parse_robots_txt(content)
        assert "/" in result["GPTBot"].disallow
        assert "/" in result["ChatGPT-User"].disallow

    def test_inline_comment_stripping(self):
        """Inline comments after directives are stripped."""
        content = "User-agent: GPTBot # OpenAI\nDisallow: /private/ # secret stuff\n"
        result = parse_robots_txt(content)
        assert "GPTBot" in result
        assert "/private/" in result["GPTBot"].disallow

    def test_case_insensitive_directives(self):
        """Directive names are case-insensitive."""
        content = "user-agent: TestBot\nDISALLOW: /blocked/\nALLOW: /open/\n"
        result = parse_robots_txt(content)
        assert "TestBot" in result
        assert "/blocked/" in result["TestBot"].disallow
        assert "/open/" in result["TestBot"].allow

    def test_non_agent_breaks_stacking(self):
        """Non-agent directive breaks consecutive agent stacking."""
        content = (
            "User-agent: Bot1\n"
            "Disallow: /a/\n"
            "User-agent: Bot2\n"
            "Disallow: /b/\n"
        )
        result = parse_robots_txt(content)
        assert "/a/" in result["Bot1"].disallow
        assert "/b/" in result["Bot2"].disallow
        assert "/b/" not in result["Bot1"].disallow

    def test_empty_disallow(self):
        """Empty Disallow means allow everything (RFC compliant)."""
        content = "User-agent: GPTBot\nDisallow:\n"
        result = parse_robots_txt(content)
        assert "GPTBot" in result
        assert "" in result["GPTBot"].disallow


class TestClassifyBot:
    """Tests for classify_bot()."""

    def test_bot_explicitly_blocked(self):
        """Bot with Disallow: / is classified as blocked."""
        rules = {"GPTBot": AgentRules(disallow=["/"])}
        status = classify_bot("GPTBot", "OpenAI", rules)
        assert status.status == "blocked"
        assert status.matched_agent == "GPTBot"

    def test_bot_explicitly_allowed(self):
        """Bot with no disallow entries is classified as allowed."""
        rules = {"GPTBot": AgentRules(allow=["/"])}
        status = classify_bot("GPTBot", "OpenAI", rules)
        assert status.status == "allowed"
        assert status.matched_agent == "GPTBot"

    def test_bot_missing(self):
        """Bot not in rules and no wildcard is classified as missing."""
        rules = {"OtherBot": AgentRules(disallow=["/"])}
        status = classify_bot("GPTBot", "OpenAI", rules)
        assert status.status == "missing"

    def test_wildcard_fallback(self):
        """Bot falls back to wildcard * when not explicitly listed."""
        rules = {"*": AgentRules(disallow=["/private/"])}
        status = classify_bot("GPTBot", "OpenAI", rules)
        assert status.status == "allowed"
        assert status.matched_agent == "*"

    def test_wildcard_blocked_all(self):
        """Wildcard blocking all paths blocks unlisted bots."""
        rules = {"*": AgentRules(disallow=["/"])}
        status = classify_bot("GPTBot", "OpenAI", rules)
        assert status.status == "blocked"

    def test_case_insensitive_matching(self):
        """Bot matching is case-insensitive."""
        rules = {"gptbot": AgentRules(allow=["/"])}
        status = classify_bot("GPTBot", "OpenAI", rules)
        assert status.status == "allowed"
        assert status.matched_agent == "gptbot"

    def test_blocked_with_allow_override(self):
        """Disallow: / with Allow: / results in allowed."""
        rules = {"GPTBot": AgentRules(disallow=["/"], allow=["/"])}
        status = classify_bot("GPTBot", "OpenAI", rules)
        assert status.status == "allowed"

    def test_bot_status_fields(self):
        """BotStatus dataclass fields are populated correctly."""
        rules = {"GPTBot": AgentRules(disallow=["/secret/"])}
        status = classify_bot("GPTBot", "OpenAI bot", rules)
        assert status.bot == "GPTBot"
        assert status.description == "OpenAI bot"
        assert status.disallow_paths == ["/secret/"]

    def test_empty_disallow_means_allowed(self):
        """Agent with only empty Disallow is classified as allowed."""
        rules = {"GPTBot": AgentRules(disallow=[""])}
        status = classify_bot("GPTBot", "OpenAI", rules)
        assert status.status == "allowed"


# ============================================================================
# 2. HTTP UTILITIES (geo_optimizer.utils.http)
# ============================================================================


class TestCreateSessionWithRetry:
    """Tests for create_session_with_retry()."""

    def test_session_created(self):
        """Session is created with retry adapter."""
        session = create_session_with_retry()
        assert session is not None
        assert hasattr(session, "get")
        assert hasattr(session, "head")

    def test_default_retry_config(self):
        """Default retry configuration is applied."""
        session = create_session_with_retry()
        adapter = session.get_adapter("https://example.com")
        assert adapter.max_retries.total == 3
        assert adapter.max_retries.backoff_factor == 1.0

    def test_custom_retry_params(self):
        """Custom retry parameters are applied."""
        session = create_session_with_retry(
            total_retries=5,
            backoff_factor=2.0,
            status_forcelist=[503],
            allowed_methods=["POST"],
        )
        adapter = session.get_adapter("https://example.com")
        assert adapter.max_retries.total == 5
        assert adapter.max_retries.backoff_factor == 2.0

    def test_headers_applied(self):
        """Default headers are set on the session."""
        session = create_session_with_retry()
        assert session.headers.get("User-Agent") == USER_AGENT

    def test_http_and_https_adapters(self):
        """Both http:// and https:// have retry adapters mounted."""
        session = create_session_with_retry()
        http_adapter = session.get_adapter("http://example.com")
        https_adapter = session.get_adapter("https://example.com")
        assert http_adapter is not None
        assert https_adapter is not None


class TestFetchUrl:
    """Tests for fetch_url()."""

    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_successful_fetch(self, mock_create):
        """Successful fetch returns (response, None)."""
        mock_session = MagicMock()
        mock_response = Mock(status_code=200, text="OK", content=b"OK", headers={})
        mock_session.get.return_value = mock_response
        mock_create.return_value = mock_session

        resp, err = fetch_url("https://example.com")
        assert resp is not None
        assert err is None
        assert resp.status_code == 200

    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_timeout_error(self, mock_create):
        """Timeout returns (None, error_message)."""
        import requests
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.exceptions.Timeout()
        mock_create.return_value = mock_session

        resp, err = fetch_url("https://example.com")
        assert resp is None
        assert "Timeout" in err

    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_connection_error(self, mock_create):
        """Connection error returns (None, error_message)."""
        import requests
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.exceptions.ConnectionError("refused")
        mock_create.return_value = mock_session

        resp, err = fetch_url("https://example.com")
        assert resp is None
        assert "Connection failed" in err

    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_generic_exception(self, mock_create):
        """Generic exception returns (None, error_message)."""
        mock_session = MagicMock()
        mock_session.get.side_effect = RuntimeError("something broke")
        mock_create.return_value = mock_session

        resp, err = fetch_url("https://example.com")
        assert resp is None
        assert "something broke" in err


# ============================================================================
# 3. MODELS: CONFIG (geo_optimizer.models.config)
# ============================================================================


class TestConfig:
    """Tests for configuration constants."""

    def test_ai_bots_is_dict(self):
        assert isinstance(AI_BOTS, dict)
        assert len(AI_BOTS) > 0

    def test_ai_bots_has_known_bots(self):
        assert "GPTBot" in AI_BOTS
        assert "ClaudeBot" in AI_BOTS
        assert "PerplexityBot" in AI_BOTS

    def test_citation_bots_is_set(self):
        assert isinstance(CITATION_BOTS, set)
        assert len(CITATION_BOTS) > 0

    def test_citation_bots_subset_of_ai_bots(self):
        """All citation bots should be in the AI_BOTS dict."""
        for bot in CITATION_BOTS:
            assert bot in AI_BOTS, f"{bot} is in CITATION_BOTS but not in AI_BOTS"

    def test_scoring_dict_has_expected_keys(self):
        expected_keys = [
            "robots_found", "robots_citation_ok", "robots_some_allowed",
            "llms_found", "llms_h1", "llms_sections", "llms_links",
            "schema_website", "schema_faq", "schema_webapp",
            "meta_title", "meta_description", "meta_canonical", "meta_og",
            "content_h1", "content_numbers", "content_links",
        ]
        for key in expected_keys:
            assert key in SCORING, f"SCORING missing key: {key}"

    def test_scoring_values_are_positive_ints(self):
        for key, val in SCORING.items():
            assert isinstance(val, int), f"SCORING[{key}] should be int"
            assert val > 0, f"SCORING[{key}] should be positive"

    def test_score_bands_cover_full_range(self):
        """Score bands should cover 0-100 without gaps."""
        assert "critical" in SCORE_BANDS
        assert "excellent" in SCORE_BANDS
        assert SCORE_BANDS["critical"][0] == 0
        assert SCORE_BANDS["excellent"][1] == 100

    def test_schema_templates_has_required_types(self):
        assert "website" in SCHEMA_TEMPLATES
        assert "faq" in SCHEMA_TEMPLATES
        assert "webapp" in SCHEMA_TEMPLATES
        assert "article" in SCHEMA_TEMPLATES
        assert "organization" in SCHEMA_TEMPLATES

    def test_schema_org_required_has_types(self):
        assert "website" in SCHEMA_ORG_REQUIRED
        assert "faqpage" in SCHEMA_ORG_REQUIRED
        assert "organization" in SCHEMA_ORG_REQUIRED

    def test_headers_has_user_agent(self):
        assert "User-Agent" in HEADERS
        assert "GEO-Optimizer" in HEADERS["User-Agent"]

    def test_skip_patterns_is_list(self):
        assert isinstance(SKIP_PATTERNS, list)
        assert len(SKIP_PATTERNS) > 0

    def test_category_patterns_is_list_of_tuples(self):
        assert isinstance(CATEGORY_PATTERNS, list)
        for item in CATEGORY_PATTERNS:
            assert len(item) == 2, "Each CATEGORY_PATTERN should be (pattern, name)"

    def test_valuable_schemas_is_list(self):
        assert isinstance(VALUABLE_SCHEMAS, list)
        assert "WebSite" in VALUABLE_SCHEMAS
        assert "FAQPage" in VALUABLE_SCHEMAS

    def test_section_priority_order(self):
        assert isinstance(SECTION_PRIORITY_ORDER, list)
        assert len(SECTION_PRIORITY_ORDER) > 0

    def test_optional_categories(self):
        assert isinstance(OPTIONAL_CATEGORIES, set)
        assert "Privacy & Legal" in OPTIONAL_CATEGORIES


# ============================================================================
# 4. MODELS: RESULTS (geo_optimizer.models.results)
# ============================================================================


class TestResultDataclasses:
    """Tests for result dataclass instantiation and defaults."""

    def test_robots_result_defaults(self):
        r = RobotsResult()
        assert r.found is False
        assert r.bots_allowed == []
        assert r.bots_missing == []
        assert r.bots_blocked == []
        assert r.citation_bots_ok is False

    def test_llms_txt_result_defaults(self):
        r = LlmsTxtResult()
        assert r.found is False
        assert r.has_h1 is False
        assert r.word_count == 0

    def test_schema_result_defaults(self):
        r = SchemaResult()
        assert r.found_types == []
        assert r.has_website is False
        assert r.has_webapp is False
        assert r.has_faq is False
        assert r.raw_schemas == []

    def test_meta_result_defaults(self):
        r = MetaResult()
        assert r.has_title is False
        assert r.has_description is False
        assert r.has_canonical is False
        assert r.has_og_title is False
        assert r.has_og_description is False
        assert r.has_og_image is False
        assert r.title_text == ""
        assert r.description_text == ""

    def test_content_result_defaults(self):
        r = ContentResult()
        assert r.has_h1 is False
        assert r.heading_count == 0
        assert r.has_numbers is False
        assert r.word_count == 0

    def test_audit_result_defaults(self):
        r = AuditResult(url="https://example.com")
        assert r.url == "https://example.com"
        assert r.score == 0
        assert r.band == "critical"
        assert isinstance(r.robots, RobotsResult)
        assert isinstance(r.llms, LlmsTxtResult)
        assert r.recommendations == []
        assert r.http_status == 0

    def test_audit_result_timestamp_auto(self):
        r = AuditResult(url="https://example.com")
        assert r.timestamp is not None
        assert len(r.timestamp) > 0

    def test_schema_analysis_defaults(self):
        a = SchemaAnalysis()
        assert a.found_schemas == []
        assert a.found_types == []
        assert a.missing == []
        assert a.extracted_faqs == []
        assert a.duplicates == {}
        assert a.has_head is False
        assert a.total_scripts == 0

    def test_sitemap_url_defaults(self):
        s = SitemapUrl(url="https://example.com/page")
        assert s.url == "https://example.com/page"
        assert s.lastmod is None
        assert s.priority == 0.5
        assert s.title is None

    def test_sitemap_url_with_values(self):
        s = SitemapUrl(url="https://example.com/page", lastmod="2024-01-01", priority=0.9, title="Page")
        assert s.priority == 0.9
        assert s.title == "Page"

    def test_dataclass_instances_are_independent(self):
        """Mutable default fields should not be shared between instances."""
        r1 = RobotsResult()
        r2 = RobotsResult()
        r1.bots_allowed.append("GPTBot")
        assert "GPTBot" not in r2.bots_allowed


# ============================================================================
# 5. SCHEMA VALIDATOR (geo_optimizer.core.schema_validator)
# ============================================================================


class TestValidateJsonld:
    """Tests for validate_jsonld()."""

    def test_valid_website_schema(self):
        schema = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "url": "https://example.com",
            "name": "Example",
        }
        is_valid, error = validate_jsonld(schema, "website")
        assert is_valid is True
        assert error is None

    def test_missing_context(self):
        schema = {"@type": "WebSite", "url": "https://example.com", "name": "Example"}
        is_valid, error = validate_jsonld(schema)
        assert is_valid is False
        assert "@context" in error

    def test_missing_type(self):
        schema = {"@context": "https://schema.org", "url": "https://example.com"}
        is_valid, error = validate_jsonld(schema)
        assert is_valid is False
        assert "@type" in error

    def test_invalid_context_url(self):
        schema = {"@context": "http://wrong.com", "@type": "WebSite"}
        is_valid, error = validate_jsonld(schema)
        assert is_valid is False
        assert "schema.org" in error

    def test_http_context_accepted(self):
        """http://schema.org is an acceptable context (not just https)."""
        schema = {
            "@context": "http://schema.org",
            "@type": "WebSite",
            "url": "https://example.com",
            "name": "Example",
        }
        is_valid, error = validate_jsonld(schema, "website")
        assert is_valid is True

    def test_array_context(self):
        schema = {
            "@context": ["https://schema.org", "https://w3.org"],
            "@type": "WebSite",
            "url": "https://example.com",
            "name": "Example",
        }
        is_valid, error = validate_jsonld(schema, "website")
        assert is_valid is True

    def test_array_type(self):
        schema = {
            "@context": "https://schema.org",
            "@type": ["WebSite", "SearchAction"],
            "url": "https://example.com",
            "name": "Example",
        }
        is_valid, error = validate_jsonld(schema, "website")
        assert is_valid is True

    def test_empty_type_array(self):
        schema = {"@context": "https://schema.org", "@type": []}
        is_valid, error = validate_jsonld(schema)
        assert is_valid is False

    def test_missing_required_field(self):
        schema = {"@context": "https://schema.org", "@type": "WebSite", "name": "X"}
        is_valid, error = validate_jsonld(schema, "website")
        assert is_valid is False
        assert "url" in error

    def test_type_mismatch(self):
        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "Test",
            "author": "Me",
        }
        is_valid, error = validate_jsonld(schema, "website")
        assert is_valid is False
        assert "Expected" in error

    def test_faqpage_valid(self):
        schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": "Q?"}],
        }
        is_valid, error = validate_jsonld(schema, "faqpage")
        assert is_valid is True

    def test_strict_invalid_url(self):
        schema = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "url": "not-a-url",
            "name": "Example",
        }
        is_valid, error = validate_jsonld(schema, "website", strict=True)
        assert is_valid is False
        assert "Invalid URL" in error

    def test_non_strict_invalid_url(self):
        """Non-strict mode ignores invalid URLs."""
        schema = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "url": "not-a-url",
            "name": "Example",
        }
        is_valid, error = validate_jsonld(schema, "website", strict=False)
        assert is_valid is True

    def test_not_a_dict(self):
        is_valid, error = validate_jsonld("string")
        assert is_valid is False
        assert "must be a dict" in error

    def test_not_a_dict_list(self):
        is_valid, error = validate_jsonld([1, 2, 3])
        assert is_valid is False
        assert "must be a dict" in error

    def test_context_as_invalid_type(self):
        schema = {"@context": 42, "@type": "WebSite"}
        is_valid, error = validate_jsonld(schema)
        assert is_valid is False
        assert "string or array" in error

    def test_empty_context_list(self):
        schema = {"@context": [], "@type": "WebSite"}
        is_valid, error = validate_jsonld(schema)
        assert is_valid is False

    def test_url_list_in_sameAs_strict(self):
        """URLs in sameAs array should be validated in strict mode."""
        schema = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Test",
            "url": "https://example.com",
            "sameAs": ["not-valid"],
        }
        is_valid, error = validate_jsonld(schema, "organization", strict=True)
        assert is_valid is False
        assert "sameAs" in error


class TestValidateJsonldString:
    """Tests for validate_jsonld_string()."""

    def test_valid_json_string(self):
        s = '{"@context": "https://schema.org", "@type": "WebSite", "url": "https://example.com", "name": "X"}'
        is_valid, error = validate_jsonld_string(s, "website")
        assert is_valid is True

    def test_invalid_json_string(self):
        s = '{"@context": "https://schema.org"'
        is_valid, error = validate_jsonld_string(s)
        assert is_valid is False
        assert "Invalid JSON" in error

    def test_valid_json_but_invalid_schema(self):
        s = '{"foo": "bar"}'
        is_valid, error = validate_jsonld_string(s)
        assert is_valid is False


class TestGetRequiredFields:
    """Tests for get_required_fields()."""

    def test_known_type(self):
        fields = get_required_fields("website")
        assert "@context" in fields
        assert "url" in fields

    def test_unknown_type(self):
        fields = get_required_fields("nonexistent")
        assert fields == ["@context", "@type"]


# ============================================================================
# 6. AUDIT CORE (geo_optimizer.core.audit)
# ============================================================================


class TestAuditRobotsTxt:
    """Tests for audit_robots_txt()."""

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_robots_found_with_bots(self, mock_fetch):
        content = "User-agent: GPTBot\nAllow: /\n\nUser-agent: ClaudeBot\nAllow: /\n"
        mock_resp = Mock(status_code=200, text=content)
        mock_fetch.return_value = (mock_resp, None)

        result = audit_robots_txt("https://example.com")
        assert result.found is True
        assert "GPTBot" in result.bots_allowed
        assert "ClaudeBot" in result.bots_allowed

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_robots_not_found(self, mock_fetch):
        mock_resp = Mock(status_code=404)
        mock_fetch.return_value = (mock_resp, None)

        result = audit_robots_txt("https://example.com")
        assert result.found is False

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_robots_fetch_error(self, mock_fetch):
        mock_fetch.return_value = (None, "Connection error")

        result = audit_robots_txt("https://example.com")
        assert result.found is False

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_robots_blocks_all_bots(self, mock_fetch):
        content = "User-agent: *\nDisallow: /\n"
        mock_resp = Mock(status_code=200, text=content)
        mock_fetch.return_value = (mock_resp, None)

        result = audit_robots_txt("https://example.com")
        assert result.found is True
        assert len(result.bots_blocked) > 0
        assert result.citation_bots_ok is False

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_citation_bots_ok(self, mock_fetch):
        """When all CITATION_BOTS are allowed, citation_bots_ok is True."""
        lines = []
        for bot in CITATION_BOTS:
            lines.append(f"User-agent: {bot}\nAllow: /\n")
        content = "\n".join(lines)
        mock_resp = Mock(status_code=200, text=content)
        mock_fetch.return_value = (mock_resp, None)

        result = audit_robots_txt("https://example.com")
        assert result.citation_bots_ok is True


class TestAuditLlmsTxt:
    """Tests for audit_llms_txt()."""

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_llms_found_full(self, mock_fetch):
        content = (
            "# My Site\n\n> A description\n\n## Section\n\n"
            "- [Link](https://example.com)\n"
        )
        mock_resp = Mock(status_code=200, text=content)
        mock_fetch.return_value = (mock_resp, None)

        result = audit_llms_txt("https://example.com")
        assert result.found is True
        assert result.has_h1 is True
        assert result.has_description is True
        assert result.has_sections is True
        assert result.has_links is True
        assert result.word_count > 0

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_llms_not_found(self, mock_fetch):
        mock_resp = Mock(status_code=404)
        mock_fetch.return_value = (mock_resp, None)

        result = audit_llms_txt("https://example.com")
        assert result.found is False

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_llms_minimal(self, mock_fetch):
        content = "Just some text without headers or links"
        mock_resp = Mock(status_code=200, text=content)
        mock_fetch.return_value = (mock_resp, None)

        result = audit_llms_txt("https://example.com")
        assert result.found is True
        assert result.has_h1 is False
        assert result.has_links is False

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_llms_fetch_error(self, mock_fetch):
        mock_fetch.return_value = (None, "Network error")

        result = audit_llms_txt("https://example.com")
        assert result.found is False


class TestAuditSchema:
    """Tests for audit_schema()."""

    def test_website_schema_detected(self):
        html = '''<html><head><script type="application/ld+json">
        {"@context":"https://schema.org","@type":"WebSite","name":"Test","url":"https://example.com"}
        </script></head><body></body></html>'''
        soup = BeautifulSoup(html, "html.parser")
        result = audit_schema(soup, "https://example.com")
        assert "WebSite" in result.found_types
        assert result.has_website is True

    def test_faq_schema_detected(self):
        html = '''<html><head><script type="application/ld+json">
        {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}
        </script></head><body></body></html>'''
        soup = BeautifulSoup(html, "html.parser")
        result = audit_schema(soup, "https://example.com")
        assert result.has_faq is True

    def test_webapp_schema_detected(self):
        html = '''<html><head><script type="application/ld+json">
        {"@context":"https://schema.org","@type":"WebApplication","name":"App","url":"https://example.com"}
        </script></head><body></body></html>'''
        soup = BeautifulSoup(html, "html.parser")
        result = audit_schema(soup, "https://example.com")
        assert result.has_webapp is True

    def test_no_schema(self):
        html = "<html><head></head><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = audit_schema(soup, "https://example.com")
        assert result.found_types == []
        assert result.has_website is False

    def test_multiple_schemas(self):
        ws = '{"@context":"https://schema.org","@type":"WebSite",'
        ws += '"name":"T","url":"https://example.com"}'
        faq = '{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}'
        html = (
            f'<html><head>'
            f'<script type="application/ld+json">{ws}</script>'
            f'<script type="application/ld+json">{faq}</script>'
            f'</head><body></body></html>'
        )
        soup = BeautifulSoup(html, "html.parser")
        result = audit_schema(soup, "https://example.com")
        assert result.has_website is True
        assert result.has_faq is True
        assert len(result.found_types) == 2

    def test_invalid_json_in_script(self):
        html = '''<html><head><script type="application/ld+json">
        {not valid json}
        </script></head><body></body></html>'''
        soup = BeautifulSoup(html, "html.parser")
        result = audit_schema(soup, "https://example.com")
        assert result.found_types == []

    def test_array_type_schema(self):
        html = '''<html><head><script type="application/ld+json">
        {"@context":"https://schema.org","@type":["WebSite","SearchAction"],"name":"T","url":"https://example.com"}
        </script></head><body></body></html>'''
        soup = BeautifulSoup(html, "html.parser")
        result = audit_schema(soup, "https://example.com")
        assert "WebSite" in result.found_types
        assert result.has_website is True

    def test_schema_array_in_script(self):
        """JSON-LD can be a list of schemas."""
        html = '''<html><head><script type="application/ld+json">
        [{"@context":"https://schema.org","@type":"WebSite","name":"T","url":"https://example.com"},
         {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}]
        </script></head><body></body></html>'''
        soup = BeautifulSoup(html, "html.parser")
        result = audit_schema(soup, "https://example.com")
        assert result.has_website is True
        assert result.has_faq is True


class TestAuditMetaTags:
    """Tests for audit_meta_tags()."""

    def test_full_meta_tags(self):
        html = '''<html><head>
        <title>My Site</title>
        <meta name="description" content="A description of my site">
        <link rel="canonical" href="https://example.com">
        <meta property="og:title" content="My Site">
        <meta property="og:description" content="Description">
        <meta property="og:image" content="https://example.com/image.jpg">
        </head><body></body></html>'''
        soup = BeautifulSoup(html, "html.parser")
        result = audit_meta_tags(soup, "https://example.com")
        assert result.has_title is True
        assert result.title_text == "My Site"
        assert result.has_description is True
        assert result.has_canonical is True
        assert result.canonical_url == "https://example.com"
        assert result.has_og_title is True
        assert result.has_og_description is True
        assert result.has_og_image is True

    def test_no_meta_tags(self):
        html = "<html><head></head><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = audit_meta_tags(soup, "https://example.com")
        assert result.has_title is False
        assert result.has_description is False
        assert result.has_canonical is False

    def test_empty_title(self):
        html = "<html><head><title>  </title></head><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = audit_meta_tags(soup, "https://example.com")
        assert result.has_title is False

    def test_empty_description(self):
        html = '<html><head><meta name="description" content=""></head><body></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        result = audit_meta_tags(soup, "https://example.com")
        assert result.has_description is False

    def test_title_and_description_lengths(self):
        html = '''<html><head>
        <title>Test Title</title>
        <meta name="description" content="This is the description">
        </head><body></body></html>'''
        soup = BeautifulSoup(html, "html.parser")
        result = audit_meta_tags(soup, "https://example.com")
        assert result.title_length == len("Test Title")
        assert result.description_length == len("This is the description")


class TestAuditContentQuality:
    """Tests for audit_content_quality()."""

    def test_rich_content(self):
        html = '''<html><body>
        <h1>Main Title</h1>
        <h2>Sub</h2><h3>Sub-sub</h3>
        <p>There are 1000 users and 50% growth rate. Revenue: $2000000.</p>
        <a href="https://external.com/source">External link</a>
        </body></html>'''
        soup = BeautifulSoup(html, "html.parser")
        result = audit_content_quality(soup, "https://example.com")
        assert result.has_h1 is True
        assert result.h1_text == "Main Title"
        assert result.heading_count >= 3
        assert result.has_numbers is True
        assert result.has_links is True
        assert result.word_count > 0

    def test_empty_content(self):
        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = audit_content_quality(soup, "https://example.com")
        assert result.has_h1 is False
        assert result.heading_count == 0
        assert result.has_numbers is False
        assert result.has_links is False

    def test_internal_links_not_counted(self):
        html = '''<html><body>
        <a href="https://example.com/internal">Internal</a>
        </body></html>'''
        soup = BeautifulSoup(html, "html.parser")
        result = audit_content_quality(soup, "https://example.com")
        assert result.has_links is False
        assert result.external_links_count == 0

    def test_few_numbers_not_enough(self):
        """Need at least 3 numbers to flag has_numbers."""
        html = "<html><body><p>There are 50% and 100 items.</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = audit_content_quality(soup, "https://example.com")
        assert result.numbers_count == 2
        assert result.has_numbers is False


# ============================================================================
# 7. SCORING & RECOMMENDATIONS (geo_optimizer.core.audit)
# ============================================================================


class TestComputeGeoScore:
    """Tests for compute_geo_score()."""

    def test_zero_score(self):
        """All defaults should yield zero."""
        score = compute_geo_score(
            RobotsResult(), LlmsTxtResult(), SchemaResult(),
            MetaResult(), ContentResult(),
        )
        assert score == 0

    def test_full_robots_score(self):
        robots = RobotsResult(found=True, citation_bots_ok=True)
        score = compute_geo_score(
            robots, LlmsTxtResult(), SchemaResult(),
            MetaResult(), ContentResult(),
        )
        assert score == SCORING["robots_found"] + SCORING["robots_citation_ok"]

    def test_robots_some_allowed(self):
        robots = RobotsResult(found=True, bots_allowed=["GPTBot"], citation_bots_ok=False)
        score = compute_geo_score(
            robots, LlmsTxtResult(), SchemaResult(),
            MetaResult(), ContentResult(),
        )
        assert score == SCORING["robots_found"] + SCORING["robots_some_allowed"]

    def test_full_llms_score(self):
        llms = LlmsTxtResult(found=True, has_h1=True, has_sections=True, has_links=True)
        score = compute_geo_score(
            RobotsResult(), llms, SchemaResult(),
            MetaResult(), ContentResult(),
        )
        expected = sum(SCORING[k] for k in ["llms_found", "llms_h1", "llms_sections", "llms_links"])
        assert score == expected

    def test_full_schema_score(self):
        schema = SchemaResult(has_website=True, has_faq=True, has_webapp=True)
        score = compute_geo_score(
            RobotsResult(), LlmsTxtResult(), schema,
            MetaResult(), ContentResult(),
        )
        expected = SCORING["schema_website"] + SCORING["schema_faq"] + SCORING["schema_webapp"]
        assert score == expected

    def test_full_meta_score(self):
        meta = MetaResult(
            has_title=True, has_description=True, has_canonical=True,
            has_og_title=True, has_og_description=True,
        )
        score = compute_geo_score(
            RobotsResult(), LlmsTxtResult(), SchemaResult(),
            meta, ContentResult(),
        )
        expected = sum(SCORING[k] for k in ["meta_title", "meta_description", "meta_canonical", "meta_og"])
        assert score == expected

    def test_og_requires_both_title_and_description(self):
        """OG points only awarded when BOTH og:title and og:description present."""
        meta = MetaResult(has_og_title=True, has_og_description=False)
        score = compute_geo_score(
            RobotsResult(), LlmsTxtResult(), SchemaResult(),
            meta, ContentResult(),
        )
        assert score == 0

    def test_full_content_score(self):
        content = ContentResult(has_h1=True, has_numbers=True, has_links=True)
        score = compute_geo_score(
            RobotsResult(), LlmsTxtResult(), SchemaResult(),
            MetaResult(), content,
        )
        expected = SCORING["content_h1"] + SCORING["content_numbers"] + SCORING["content_links"]
        assert score == expected

    def test_max_score_capped_at_100(self):
        """Score should never exceed 100."""
        robots = RobotsResult(found=True, citation_bots_ok=True, bots_allowed=["x"])
        llms = LlmsTxtResult(found=True, has_h1=True, has_sections=True, has_links=True)
        schema = SchemaResult(has_website=True, has_faq=True, has_webapp=True)
        meta = MetaResult(
            has_title=True, has_description=True, has_canonical=True,
            has_og_title=True, has_og_description=True,
        )
        content = ContentResult(has_h1=True, has_numbers=True, has_links=True)
        score = compute_geo_score(robots, llms, schema, meta, content)
        assert score <= 100


class TestGetScoreBand:
    """Tests for get_score_band()."""

    def test_critical_band(self):
        assert get_score_band(0) == "critical"
        assert get_score_band(40) == "critical"

    def test_foundation_band(self):
        assert get_score_band(41) == "foundation"
        assert get_score_band(70) == "foundation"

    def test_good_band(self):
        assert get_score_band(71) == "good"
        assert get_score_band(90) == "good"

    def test_excellent_band(self):
        assert get_score_band(91) == "excellent"
        assert get_score_band(100) == "excellent"

    def test_out_of_range_defaults_critical(self):
        assert get_score_band(150) == "critical"


class TestBuildRecommendations:
    """Tests for build_recommendations()."""

    def test_all_bad_gives_recommendations(self):
        recs = build_recommendations(
            "https://example.com",
            RobotsResult(), LlmsTxtResult(), SchemaResult(),
            MetaResult(), ContentResult(),
        )
        assert len(recs) > 0
        assert any("robots.txt" in r for r in recs)
        assert any("llms.txt" in r for r in recs)
        assert any("WebSite" in r for r in recs)
        assert any("FAQPage" in r or "FAQ" in r for r in recs)
        assert any("description" in r.lower() for r in recs)
        assert any("statistics" in r.lower() or "numerical" in r.lower() for r in recs)
        assert any("external" in r.lower() or "cite" in r.lower() for r in recs)

    def test_all_good_gives_no_recommendations(self):
        recs = build_recommendations(
            "https://example.com",
            RobotsResult(citation_bots_ok=True),
            LlmsTxtResult(found=True),
            SchemaResult(has_website=True, has_faq=True),
            MetaResult(has_description=True),
            ContentResult(has_numbers=True, has_links=True),
        )
        assert len(recs) == 0

    def test_partial_recommendations(self):
        recs = build_recommendations(
            "https://example.com",
            RobotsResult(citation_bots_ok=True),
            LlmsTxtResult(found=False),
            SchemaResult(has_website=True, has_faq=True),
            MetaResult(has_description=True),
            ContentResult(has_numbers=True, has_links=True),
        )
        assert len(recs) == 1
        assert "llms.txt" in recs[0]


# ============================================================================
# 8. RUN FULL AUDIT (geo_optimizer.core.audit)
# ============================================================================


class TestRunFullAudit:
    """Tests for run_full_audit()."""

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_full_audit_success(self, mock_fetch):
        html = '''<html><head>
        <title>My Site</title>
        <meta name="description" content="Description here">
        <script type="application/ld+json">
        {"@context":"https://schema.org","@type":"WebSite","name":"My Site","url":"https://example.com"}
        </script>
        </head><body><h1>Welcome</h1></body></html>'''

        # Homepage fetch
        mock_homepage = Mock(status_code=200, text=html)
        # robots.txt fetch
        mock_robots = Mock(status_code=200, text="User-agent: *\nAllow: /\n")
        # llms.txt fetch
        mock_llms = Mock(
            status_code=200,
            text="# My Site\n\n> Desc\n\n## Section\n\n- [Link](https://example.com)\n",
        )

        mock_fetch.side_effect = [
            (mock_homepage, None),  # homepage
            (mock_robots, None),    # robots.txt
            (mock_llms, None),      # llms.txt
        ]

        result = run_full_audit("https://example.com")
        assert isinstance(result, AuditResult)
        assert result.url == "https://example.com"
        assert result.score > 0
        assert result.http_status == 200
        assert result.page_size > 0

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_full_audit_unreachable(self, mock_fetch):
        mock_fetch.return_value = (None, "Connection refused")

        result = run_full_audit("https://example.com")
        assert result.score == 0
        assert len(result.recommendations) > 0
        assert "Unable to reach" in result.recommendations[0]

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_full_audit_url_normalization(self, mock_fetch):
        """URL without scheme gets https:// prepended."""
        mock_fetch.return_value = (None, "Connection refused")

        result = run_full_audit("example.com")
        assert result.url == "https://example.com"

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_full_audit_strips_trailing_slash(self, mock_fetch):
        mock_fetch.return_value = (None, "err")
        result = run_full_audit("https://example.com/")
        assert result.url == "https://example.com"


# ============================================================================
# 9. LLMS GENERATOR (geo_optimizer.core.llms_generator)
# ============================================================================


class TestShouldSkip:
    """Tests for should_skip()."""

    def test_skip_wp_admin(self):
        assert should_skip("https://example.com/wp-admin/") is True

    def test_skip_login(self):
        assert should_skip("https://example.com/login") is True

    def test_skip_cart(self):
        assert should_skip("https://example.com/cart") is True

    def test_skip_xml_extension(self):
        assert should_skip("https://example.com/feed.xml") is True

    def test_skip_tag(self):
        assert should_skip("https://example.com/tag/python") is True

    def test_keep_blog(self):
        assert should_skip("https://example.com/blog/my-post") is False

    def test_keep_homepage(self):
        assert should_skip("https://example.com/") is False

    def test_keep_about(self):
        assert should_skip("https://example.com/about") is False

    def test_skip_page_number(self):
        assert should_skip("https://example.com/page/2") is True


class TestCategorizeUrl:
    """Tests for categorize_url()."""

    def test_blog_url(self):
        cat = categorize_url("https://example.com/blog/my-post", "example.com")
        assert cat == "Blog & Articles"

    def test_docs_url(self):
        cat = categorize_url("https://example.com/docs/getting-started", "example.com")
        assert cat == "Documentation"

    def test_about_url(self):
        cat = categorize_url("https://example.com/about", "example.com")
        assert cat == "About"

    def test_homepage(self):
        cat = categorize_url("https://example.com/", "example.com")
        assert cat == "_homepage"

    def test_top_level_page(self):
        cat = categorize_url("https://example.com/pricing", "example.com")
        assert cat == "Main Pages"

    def test_deep_unknown_page(self):
        cat = categorize_url("https://example.com/some/deep/path", "example.com")
        assert cat == "Other"

    def test_calculator_url(self):
        cat = categorize_url("https://example.com/calculators/mortgage", "example.com")
        assert cat == "Calculators"

    def test_privacy_url(self):
        cat = categorize_url("https://example.com/privacy-policy", "example.com")
        assert cat == "Privacy & Legal"


class TestUrlToLabel:
    """Tests for url_to_label()."""

    def test_homepage(self):
        label = url_to_label("https://example.com/", "example.com")
        assert label == "Homepage"

    def test_slug_to_title(self):
        label = url_to_label("https://example.com/my-cool-page", "example.com")
        assert label == "My Cool Page"

    def test_underscore_slug(self):
        label = url_to_label("https://example.com/my_cool_page", "example.com")
        assert label == "My Cool Page"

    def test_nested_path(self):
        label = url_to_label("https://example.com/blog/my-article", "example.com")
        assert label == "My Article"

    def test_empty_path(self):
        label = url_to_label("https://example.com", "example.com")
        assert label == "Homepage"


class TestFetchPageTitle:
    """Tests for fetch_page_title()."""

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_fetch_title(self, mock_create):
        mock_session = MagicMock()
        mock_resp = Mock(status_code=200, text="<html><head><title>My Page Title</title></head></html>")
        mock_session.get.return_value = mock_resp
        mock_create.return_value = mock_session

        title = fetch_page_title("https://example.com/page")
        assert title == "My Page Title"

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_fetch_title_from_h1(self, mock_create):
        mock_session = MagicMock()
        mock_resp = Mock(status_code=200, text="<html><body><h1>Heading Title</h1></body></html>")
        mock_session.get.return_value = mock_resp
        mock_create.return_value = mock_session

        title = fetch_page_title("https://example.com/page")
        assert title == "Heading Title"

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_fetch_title_error(self, mock_create):
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Timeout")
        mock_create.return_value = mock_session

        title = fetch_page_title("https://example.com/page")
        assert title is None

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_fetch_title_no_title_no_h1(self, mock_create):
        mock_session = MagicMock()
        mock_resp = Mock(text="<html><body><p>No title here</p></body></html>")
        mock_session.get.return_value = mock_resp
        mock_create.return_value = mock_session

        title = fetch_page_title("https://example.com/page")
        assert title is None


class TestFetchSitemap:
    """Tests for fetch_sitemap()."""

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_parse_simple_sitemap(self, mock_create):
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://example.com/</loc><priority>1.0</priority></url>
          <url><loc>https://example.com/about</loc><lastmod>2024-01-01</lastmod></url>
        </urlset>'''
        mock_session = MagicMock()
        mock_resp = Mock()
        mock_resp.content = xml.encode()
        mock_resp.raise_for_status = Mock()
        mock_session.get.return_value = mock_resp
        mock_create.return_value = mock_session

        urls = fetch_sitemap("https://example.com/sitemap.xml")
        assert len(urls) == 2
        assert urls[0].url == "https://example.com/"
        assert urls[0].priority == 1.0
        assert urls[1].lastmod == "2024-01-01"

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_sitemap_index(self, mock_create):
        """Sitemap index should recursively fetch sub-sitemaps."""
        index_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <sitemap><loc>https://example.com/sitemap-1.xml</loc></sitemap>
        </sitemapindex>'''
        sub_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://example.com/page1</loc></url>
        </urlset>'''
        mock_session = MagicMock()
        mock_resp_index = Mock()
        mock_resp_index.content = index_xml.encode()
        mock_resp_index.raise_for_status = Mock()
        mock_resp_sub = Mock()
        mock_resp_sub.content = sub_xml.encode()
        mock_resp_sub.raise_for_status = Mock()
        mock_session.get.side_effect = [mock_resp_index, mock_resp_sub]
        mock_create.return_value = mock_session

        urls = fetch_sitemap("https://example.com/sitemap.xml")
        assert len(urls) == 1
        assert urls[0].url == "https://example.com/page1"

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_sitemap_fetch_error(self, mock_create):
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Network error")
        mock_create.return_value = mock_session

        urls = fetch_sitemap("https://example.com/sitemap.xml")
        assert urls == []

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_sitemap_with_on_status_callback(self, mock_create):
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://example.com/</loc></url>
        </urlset>'''
        mock_session = MagicMock()
        mock_resp = Mock()
        mock_resp.content = xml.encode()
        mock_resp.raise_for_status = Mock()
        mock_session.get.return_value = mock_resp
        mock_create.return_value = mock_session

        status_msgs = []
        urls = fetch_sitemap("https://example.com/sitemap.xml", on_status=status_msgs.append)
        assert len(urls) == 1
        assert any("Fetching" in m for m in status_msgs)


class TestGenerateLlmsTxt:
    """Tests for generate_llms_txt()."""

    def test_basic_generation(self):
        urls = [
            SitemapUrl(url="https://example.com/", priority=1.0),
            SitemapUrl(url="https://example.com/about", priority=0.8),
            SitemapUrl(url="https://example.com/blog/post-1", priority=0.5),
        ]
        result = generate_llms_txt("https://example.com", urls)
        assert "# Example" in result
        assert ">" in result  # blockquote
        assert "## " in result  # sections
        assert "[" in result and "](" in result  # markdown links

    def test_custom_site_name_and_description(self):
        urls = [SitemapUrl(url="https://example.com/", priority=1.0)]
        result = generate_llms_txt(
            "https://example.com", urls,
            site_name="My Cool Site",
            description="The best site ever",
        )
        assert "# My Cool Site" in result
        assert "> The best site ever" in result

    def test_skip_unwanted_urls(self):
        urls = [
            SitemapUrl(url="https://example.com/about", priority=0.8),
            SitemapUrl(url="https://example.com/wp-admin/settings", priority=0.5),
        ]
        result = generate_llms_txt("https://example.com", urls)
        assert "wp-admin" not in result

    def test_deduplication(self):
        urls = [
            SitemapUrl(url="https://example.com/about", priority=0.8),
            SitemapUrl(url="https://example.com/about", priority=0.5),
        ]
        result = generate_llms_txt("https://example.com", urls)
        # Should only appear once
        assert result.count("about") <= 2  # label + link

    def test_max_urls_per_section(self):
        urls = [
            SitemapUrl(url=f"https://example.com/blog/post-{i}", priority=0.5)
            for i in range(30)
        ]
        result = generate_llms_txt("https://example.com", urls, max_urls_per_section=5)
        blog_links = [line for line in result.splitlines() if "blog/post-" in line]
        assert len(blog_links) <= 5

    def test_urls_outside_domain_skipped(self):
        urls = [
            SitemapUrl(url="https://example.com/about", priority=0.8),
            SitemapUrl(url="https://other-domain.com/hack", priority=0.5),
        ]
        result = generate_llms_txt("https://example.com", urls)
        assert "other-domain" not in result

    def test_empty_urls(self):
        result = generate_llms_txt("https://example.com", [])
        assert "# Example" in result  # Still has header
        assert ">" in result  # Still has description


class TestDiscoverSitemap:
    """Tests for discover_sitemap()."""

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_discover_from_robots_txt(self, mock_create):
        mock_session = MagicMock()
        robots_resp = Mock()
        robots_resp.text = "User-agent: *\nDisallow:\nSitemap: https://example.com/sitemap.xml"
        mock_session.get.return_value = robots_resp
        mock_create.return_value = mock_session

        url = discover_sitemap("https://example.com")
        assert url == "https://example.com/sitemap.xml"

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_discover_from_common_paths(self, mock_create):
        mock_session = MagicMock()
        # robots.txt has no Sitemap directive
        robots_resp = Mock()
        robots_resp.text = "User-agent: *\nDisallow:\n"
        # HEAD requests: first path returns 200
        head_200 = Mock(status_code=200)
        mock_session.get.return_value = robots_resp
        mock_session.head.return_value = head_200
        mock_create.return_value = mock_session

        url = discover_sitemap("https://example.com")
        assert url is not None

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_discover_none_found(self, mock_create):
        mock_session = MagicMock()
        robots_resp = Mock()
        robots_resp.text = "User-agent: *\nDisallow:\n"
        mock_session.get.return_value = robots_resp
        head_404 = Mock(status_code=404)
        mock_session.head.return_value = head_404
        mock_create.return_value = mock_session

        url = discover_sitemap("https://example.com")
        assert url is None

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_discover_with_on_status_callback(self, mock_create):
        mock_session = MagicMock()
        robots_resp = Mock()
        robots_resp.text = "Sitemap: https://example.com/sitemap.xml"
        mock_session.get.return_value = robots_resp
        mock_create.return_value = mock_session

        msgs = []
        url = discover_sitemap("https://example.com", on_status=msgs.append)
        assert url is not None
        assert any("Sitemap found" in m for m in msgs)


# ============================================================================
# 10. SCHEMA INJECTOR (geo_optimizer.core.schema_injector)
# ============================================================================


class TestFillTemplate:
    """Tests for fill_template()."""

    def test_basic_replacement(self):
        template = {"name": "{{name}}", "url": "{{url}}"}
        result = fill_template(template, {"name": "My Site", "url": "https://example.com"})
        assert result["name"] == "My Site"
        assert result["url"] == "https://example.com"

    def test_nested_replacement(self):
        template = {"author": {"name": "{{author}}", "@type": "Person"}}
        result = fill_template(template, {"author": "John"})
        assert result["author"]["name"] == "John"

    def test_missing_value_becomes_empty(self):
        template = {"name": "{{name}}"}
        result = fill_template(template, {"name": None})
        assert result["name"] == ""

    def test_no_placeholders(self):
        template = {"name": "Fixed"}
        result = fill_template(template, {"name": "Different"})
        assert result["name"] == "Fixed"

    def test_multiple_placeholders_same_key(self):
        template = {"title": "{{name}} - {{name}}"}
        result = fill_template(template, {"name": "Test"})
        assert result["title"] == "Test - Test"


class TestSchemaToHtmlTag:
    """Tests for schema_to_html_tag()."""

    def test_basic_conversion(self):
        schema = {"@context": "https://schema.org", "@type": "WebSite"}
        tag = schema_to_html_tag(schema)
        assert '<script type="application/ld+json">' in tag
        assert "</script>" in tag
        assert "schema.org" in tag

    def test_preserves_unicode(self):
        schema = {"name": "Cafe \u00e9"}
        tag = schema_to_html_tag(schema)
        assert "\u00e9" in tag


class TestExtractFaqFromHtml:
    """Tests for extract_faq_from_html()."""

    def test_dt_dd_pattern(self):
        html = "<dl><dt>What is GEO?</dt><dd>Generative Engine Optimization helps sites</dd></dl>"
        soup = BeautifulSoup(html, "html.parser")
        faqs = extract_faq_from_html(soup)
        assert len(faqs) == 1
        assert faqs[0]["question"] == "What is GEO?"

    def test_details_summary_pattern(self):
        html = (
            "<details><summary>What is SEO optimization?</summary>"
            "SEO is the process of improving your site visibility</details>"
        )
        soup = BeautifulSoup(html, "html.parser")
        faqs = extract_faq_from_html(soup)
        assert len(faqs) == 1
        assert "SEO" in faqs[0]["question"]

    def test_faq_class_pattern(self):
        html = (
            '<div class="faq-item"><h3>How do I start with GEO?</h3>'
            '<p>Start by running the audit tool on your website</p></div>'
        )
        soup = BeautifulSoup(html, "html.parser")
        faqs = extract_faq_from_html(soup)
        assert len(faqs) == 1

    def test_no_faqs_found(self):
        html = "<p>Just a paragraph with no FAQs at all.</p>"
        soup = BeautifulSoup(html, "html.parser")
        faqs = extract_faq_from_html(soup)
        assert faqs == []

    def test_short_question_skipped(self):
        """Questions shorter than 6 chars are skipped."""
        html = "<dl><dt>Hi?</dt><dd>This is a really long answer that should be enough.</dd></dl>"
        soup = BeautifulSoup(html, "html.parser")
        faqs = extract_faq_from_html(soup)
        assert faqs == []

    def test_short_answer_skipped(self):
        """Answers shorter than 11 chars are skipped."""
        html = "<dl><dt>What is this thing?</dt><dd>Short.</dd></dl>"
        soup = BeautifulSoup(html, "html.parser")
        faqs = extract_faq_from_html(soup)
        assert faqs == []


class TestGenerateFaqSchema:
    """Tests for generate_faq_schema()."""

    def test_basic_faq_schema(self):
        items = [
            {"question": "What is GEO?", "answer": "Generative Engine Optimization"},
            {"question": "Why?", "answer": "Because AI search is growing"},
        ]
        schema = generate_faq_schema(items)
        assert schema["@type"] == "FAQPage"
        assert schema["@context"] == "https://schema.org"
        assert len(schema["mainEntity"]) == 2
        assert schema["mainEntity"][0]["@type"] == "Question"
        assert schema["mainEntity"][0]["acceptedAnswer"]["@type"] == "Answer"

    def test_empty_faq_items(self):
        schema = generate_faq_schema([])
        assert schema["mainEntity"] == []


class TestAnalyzeHtmlFile:
    """Tests for analyze_html_file()."""

    def test_analyze_file_with_schemas(self):
        html = '''<html><head>
        <script type="application/ld+json">
        {"@context":"https://schema.org","@type":"WebSite","name":"Test","url":"https://example.com"}
        </script>
        </head><body></body></html>'''

        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html)
            f.flush()
            path = f.name

        try:
            analysis = analyze_html_file(path)
            assert "WebSite" in analysis.found_types
            assert analysis.has_head is True
            assert analysis.total_scripts == 1
            assert "webapp" in analysis.missing
            assert "faq" in analysis.missing
        finally:
            os.unlink(path)

    def test_analyze_file_no_schemas(self):
        html = "<html><head></head><body><p>No schemas here</p></body></html>"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html)
            f.flush()
            path = f.name

        try:
            analysis = analyze_html_file(path)
            assert analysis.found_types == []
            assert "website" in analysis.missing
            assert analysis.total_scripts == 0
        finally:
            os.unlink(path)

    def test_analyze_file_with_faqs(self):
        html = '''<html><head></head><body>
        <dl>
        <dt>What is GEO optimization?</dt>
        <dd>GEO is Generative Engine Optimization for AI visibility</dd>
        </dl>
        </body></html>'''
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html)
            f.flush()
            path = f.name

        try:
            analysis = analyze_html_file(path)
            assert len(analysis.extracted_faqs) >= 1
        finally:
            os.unlink(path)

    def test_analyze_duplicate_schemas(self):
        ws1 = '{"@context":"https://schema.org","@type":"WebSite",'
        ws1 += '"name":"T","url":"https://example.com"}'
        ws2 = '{"@context":"https://schema.org","@type":"WebSite",'
        ws2 += '"name":"T2","url":"https://example.com"}'
        html = (
            f'<html><head>'
            f'<script type="application/ld+json">{ws1}</script>'
            f'<script type="application/ld+json">{ws2}</script>'
            f'</head><body></body></html>'
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html)
            f.flush()
            path = f.name

        try:
            analysis = analyze_html_file(path)
            assert "WebSite" in analysis.duplicates
            assert analysis.duplicates["WebSite"] == 2
        finally:
            os.unlink(path)

    def test_analyze_invalid_json_in_script(self):
        html = '''<html><head>
        <script type="application/ld+json">{invalid json}</script>
        </head><body></body></html>'''
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html)
            f.flush()
            path = f.name

        try:
            analysis = analyze_html_file(path)
            assert analysis.found_types == []
        finally:
            os.unlink(path)


class TestInjectSchemaIntoHtml:
    """Tests for inject_schema_into_html()."""

    def test_inject_valid_schema(self):
        html = "<html><head><title>Test</title></head><body></body></html>"
        schema = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "Test",
            "url": "https://example.com",
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html)
            f.flush()
            path = f.name

        try:
            success, msg = inject_schema_into_html(path, schema, backup=False)
            assert success is True
            assert msg is None

            with open(path) as fh:
                content = fh.read()
            assert "application/ld+json" in content
            assert "WebSite" in content
        finally:
            os.unlink(path)

    def test_inject_with_backup(self):
        html = "<html><head><title>Test</title></head><body></body></html>"
        schema = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "Test",
            "url": "https://example.com",
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html)
            f.flush()
            path = f.name

        try:
            success, msg = inject_schema_into_html(path, schema, backup=True)
            assert success is True
            assert os.path.exists(path + ".bak")
        finally:
            os.unlink(path)
            if os.path.exists(path + ".bak"):
                os.unlink(path + ".bak")

    def test_inject_no_head_tag(self):
        html = "<html><body></body></html>"
        schema = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "Test",
            "url": "https://example.com",
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html)
            f.flush()
            path = f.name

        try:
            success, msg = inject_schema_into_html(path, schema, backup=False)
            assert success is False
            assert "No <head>" in msg
        finally:
            os.unlink(path)

    def test_inject_invalid_schema_rejected(self):
        html = "<html><head></head><body></body></html>"
        schema = {"@type": "WebSite"}  # Missing @context
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html)
            f.flush()
            path = f.name

        try:
            success, msg = inject_schema_into_html(path, schema, backup=False, validate=True)
            assert success is False
            assert "validation failed" in msg
        finally:
            os.unlink(path)

    def test_inject_skip_validation(self):
        html = "<html><head></head><body></body></html>"
        schema = {"custom": "data"}  # Not valid JSON-LD but validation skipped
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html)
            f.flush()
            path = f.name

        try:
            success, msg = inject_schema_into_html(path, schema, backup=False, validate=False)
            assert success is True
        finally:
            os.unlink(path)


class TestGenerateAstroSnippet:
    """Tests for generate_astro_snippet()."""

    def test_basic_snippet(self):
        snippet = generate_astro_snippet("https://example.com", "My Site")
        assert "https://example.com" in snippet
        assert "My Site" in snippet
        assert "schema.org" in snippet
        assert "WebSite" in snippet
        assert "BaseLayout.astro" in snippet

    def test_different_values(self):
        snippet = generate_astro_snippet("https://other.com", "Other")
        assert "https://other.com" in snippet
        assert "Other" in snippet
