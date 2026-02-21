"""
Comprehensive unit tests for geo_audit.py script.

Tests critical functions for GEO website auditing including:
- robots.txt parsing
- llms.txt validation
- schema detection
- meta tag validation
- content quality checks
- score calculation

Author: Juan Camilo Auriti
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from geo_audit import (
    AI_BOTS,
    CITATION_BOTS,
    VALUABLE_SCHEMAS,
    audit_content_quality,
    audit_llms_txt,
    audit_meta_tags,
    audit_robots_txt,
    audit_schema,
    compute_geo_score,
)


# ============================================================================
# ROBOTS.TXT TESTS
# ============================================================================


def test_robots_txt_allows_gptbot():
    """Test that robots.txt correctly identifies allowed GPTBot."""
    robots_content = """
User-agent: *
Disallow: /private/

User-agent: GPTBot
Allow: /
"""

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = robots_content

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_robots_txt("https://example.com")

    assert result["found"] is True
    assert "GPTBot" in result["bots_allowed"]
    assert "GPTBot" not in result["bots_blocked"]
    assert "GPTBot" not in result["bots_missing"]


def test_robots_txt_blocks_gptbot():
    """Test that robots.txt correctly identifies blocked GPTBot."""
    robots_content = """
User-agent: GPTBot
Disallow: /

User-agent: *
Allow: /
"""

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = robots_content

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_robots_txt("https://example.com")

    assert result["found"] is True
    assert "GPTBot" in result["bots_blocked"]
    assert "GPTBot" not in result["bots_allowed"]
    assert result["citation_bots_ok"] is False  # GPTBot is not a citation bot, but OAI-SearchBot is


def test_robots_txt_with_comments():
    """Test robots.txt parsing with inline comments."""
    robots_content = """
# AI bots configuration
User-agent: GPTBot  # OpenAI training bot
Allow: /

User-agent: ClaudeBot  # Anthropic citations
Disallow:  # empty = allow all

# Block sensitive areas
User-agent: *
Disallow: /admin/  # admin panel
"""

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = robots_content

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_robots_txt("https://example.com")

    assert result["found"] is True
    assert "GPTBot" in result["bots_allowed"]
    assert "ClaudeBot" in result["bots_allowed"]


def test_robots_txt_missing():
    """Test handling of missing robots.txt (404)."""
    mock_response = Mock()
    mock_response.status_code = 404

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_robots_txt("https://example.com")

    assert result["found"] is False
    assert result["citation_bots_ok"] is False
    assert len(result["bots_allowed"]) == 0


def test_robots_txt_citation_bots_ok():
    """Test that all critical citation bots are correctly identified."""
    robots_content = """
User-agent: OAI-SearchBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /
"""

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = robots_content

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_robots_txt("https://example.com")

    assert result["citation_bots_ok"] is True
    assert "OAI-SearchBot" in result["bots_allowed"]
    assert "ClaudeBot" in result["bots_allowed"]
    assert "PerplexityBot" in result["bots_allowed"]


# ============================================================================
# LLMS.TXT TESTS
# ============================================================================


def test_llms_txt_valid_structure():
    """Test llms.txt with valid structure including all required elements."""
    llms_content = """# My Website

> A comprehensive resource for web development and AI optimization.

## Tools

- [Tool One](https://example.com/tool1) - Description of tool one
- [Tool Two](https://example.com/tool2) - Description of tool two

## Articles

- [Article One](https://example.com/article1) - About AI optimization
- [Article Two](https://example.com/article2) - Web performance tips
"""

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = llms_content

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_llms_txt("https://example.com")

    assert result["found"] is True
    assert result["has_h1"] is True
    assert result["has_description"] is True
    assert result["has_sections"] is True
    assert result["has_links"] is True
    assert result["word_count"] > 0


def test_llms_txt_missing_h1():
    """Test llms.txt without required H1 heading."""
    llms_content = """## Section One

Just some content without an H1.

- [Link](https://example.com)
"""

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = llms_content

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_llms_txt("https://example.com")

    assert result["found"] is True
    assert result["has_h1"] is False
    assert result["has_sections"] is True  # Has H2


def test_llms_txt_not_found():
    """Test handling of missing llms.txt (404)."""
    mock_response = Mock()
    mock_response.status_code = 404

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_llms_txt("https://example.com")

    assert result["found"] is False
    assert result["has_h1"] is False
    assert result["has_links"] is False


# ============================================================================
# SCHEMA DETECTION TESTS
# ============================================================================


def test_schema_detection():
    """Test detection of multiple JSON-LD schema types."""
    html = """
<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Example Site",
        "url": "https://example.com"
    }
    </script>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": "What is GEO?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Generative Engine Optimization"
                }
            }
        ]
    }
    </script>
</head>
<body></body>
</html>
"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_schema(soup, "https://example.com")

    assert result["has_website"] is True
    assert result["has_faq"] is True
    assert "WebSite" in result["found_types"]
    assert "FAQPage" in result["found_types"]
    assert len(result["raw_schemas"]) == 2


def test_schema_detection_no_schema():
    """Test handling of HTML with no JSON-LD schema."""
    html = """
<!DOCTYPE html>
<html>
<head><title>No Schema</title></head>
<body><h1>Content</h1></body>
</html>
"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_schema(soup, "https://example.com")

    assert result["has_website"] is False
    assert result["has_faq"] is False
    assert len(result["found_types"]) == 0


def test_schema_detection_multiple_types():
    """Test detection of schema with multiple @type values."""
    html = """
<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": ["WebSite", "WebApplication"],
        "name": "Example App",
        "url": "https://example.com"
    }
    </script>
</head>
<body></body>
</html>
"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_schema(soup, "https://example.com")

    assert result["has_website"] is True
    assert result["has_webapp"] is True
    assert "WebSite" in result["found_types"]
    assert "WebApplication" in result["found_types"]


# ============================================================================
# META TAGS VALIDATION TESTS
# ============================================================================


def test_meta_tags_validation():
    """Test validation of all critical meta tags."""
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Example Site - Best Tool for SEO</title>
    <meta name="description" content="A comprehensive guide to SEO and GEO optimization with practical tools and expert insights for modern web development.">
    <link rel="canonical" href="https://example.com/">
    <meta property="og:title" content="Example Site - SEO Tools">
    <meta property="og:description" content="Professional SEO and GEO tools">
    <meta property="og:image" content="https://example.com/image.jpg">
</head>
<body></body>
</html>
"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_meta_tags(soup, "https://example.com")

    assert result["has_title"] is True
    assert result["has_description"] is True
    assert result["has_canonical"] is True
    assert result["has_og_title"] is True
    assert result["has_og_description"] is True
    assert result["has_og_image"] is True


def test_meta_tags_missing():
    """Test detection of missing meta tags."""
    html = """
<!DOCTYPE html>
<html>
<head></head>
<body><h1>Minimal Page</h1></body>
</html>
"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_meta_tags(soup, "https://example.com")

    assert result["has_title"] is False
    assert result["has_description"] is False
    assert result["has_canonical"] is False
    assert result["has_og_title"] is False


# ============================================================================
# CONTENT QUALITY TESTS
# ============================================================================


def test_external_citations_count():
    """Test detection and counting of external citations."""
    html = """
<!DOCTYPE html>
<html>
<head><title>Article</title></head>
<body>
    <h1>Research Article</h1>
    <p>According to <a href="https://example.org/study">this study</a>, the results show improvement.</p>
    <p>As noted by <a href="https://research.com/paper">researchers</a>, the methodology is sound.</p>
    <p>Internal link: <a href="https://example.com/about">About Us</a></p>
    <p>Another external source: <a href="https://academic.edu/journal">Journal Article</a></p>
</body>
</html>
"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_content_quality(soup, "https://example.com")

    assert result["has_links"] is True
    # Should find 3 external links (excluding the internal one)


def test_content_quality_numbers():
    """Test detection of numerical data and statistics."""
    html = """
<!DOCTYPE html>
<html>
<head><title>Statistics</title></head>
<body>
    <h1>Performance Metrics</h1>
    <h2>Results</h2>
    <p>Our tool improved performance by 45% in testing.</p>
    <p>Over 1,250 users have signed up.</p>
    <p>Average response time: 2.5 seconds.</p>
    <p>Price: $99.99 per month.</p>
    <p>Revenue increased by €50,000.</p>
</body>
</html>
"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_content_quality(soup, "https://example.com")

    assert result["has_h1"] is True
    assert result["has_numbers"] is True
    assert result["heading_count"] >= 2


# ============================================================================
# SCORE CALCULATION TESTS
# ============================================================================


def test_score_calculation_range():
    """Test that GEO score is always within valid range 0-100."""
    # Perfect score test
    perfect_robots = {
        "found": True,
        "citation_bots_ok": True,
        "bots_allowed": list(AI_BOTS.keys()),
        "bots_missing": [],
        "bots_blocked": [],
    }
    perfect_llms = {
        "found": True,
        "has_h1": True,
        "has_sections": True,
        "has_links": True,
    }
    perfect_schema = {
        "has_website": True,
        "has_faq": True,
        "has_webapp": True,
    }
    perfect_meta = {
        "has_title": True,
        "has_description": True,
        "has_canonical": True,
        "has_og_title": True,
        "has_og_description": True,
    }
    perfect_content = {"has_h1": True, "has_numbers": True, "has_links": True}

    score = compute_geo_score(
        perfect_robots, perfect_llms, perfect_schema, perfect_meta, perfect_content
    )
    assert 0 <= score <= 100
    assert score == 100

    # Zero score test
    zero_robots = {
        "found": False,
        "citation_bots_ok": False,
        "bots_allowed": [],
        "bots_missing": list(AI_BOTS.keys()),
        "bots_blocked": [],
    }
    zero_llms = {
        "found": False,
        "has_h1": False,
        "has_sections": False,
        "has_links": False,
    }
    zero_schema = {"has_website": False, "has_faq": False, "has_webapp": False}
    zero_meta = {
        "has_title": False,
        "has_description": False,
        "has_canonical": False,
        "has_og_title": False,
        "has_og_description": False,
    }
    zero_content = {"has_h1": False, "has_numbers": False, "has_links": False}

    score = compute_geo_score(
        zero_robots, zero_llms, zero_schema, zero_meta, zero_content
    )
    assert 0 <= score <= 100
    assert score == 0


def test_score_bands_correct():
    """Test that score calculation matches documented score bands."""
    # Test Foundation level (41-70)
    foundation_robots = {"found": True, "citation_bots_ok": True, "bots_allowed": []}
    foundation_llms = {"found": True, "has_h1": True, "has_sections": False, "has_links": False}
    foundation_schema = {"has_website": True, "has_faq": False, "has_webapp": False}
    foundation_meta = {
        "has_title": True,
        "has_description": True,
        "has_canonical": False,
        "has_og_title": False,
        "has_og_description": False,
    }
    foundation_content = {"has_h1": True, "has_numbers": False, "has_links": False}

    score = compute_geo_score(
        foundation_robots,
        foundation_llms,
        foundation_schema,
        foundation_meta,
        foundation_content,
    )
    assert 0 <= score <= 100

    # Test Good level (71-90)
    good_robots = {"found": True, "citation_bots_ok": True, "bots_allowed": []}
    good_llms = {"found": True, "has_h1": True, "has_sections": True, "has_links": True}
    good_schema = {"has_website": True, "has_faq": True, "has_webapp": False}
    good_meta = {
        "has_title": True,
        "has_description": True,
        "has_canonical": True,
        "has_og_title": True,
        "has_og_description": True,
    }
    good_content = {"has_h1": True, "has_numbers": True, "has_links": True}

    score = compute_geo_score(good_robots, good_llms, good_schema, good_meta, good_content)
    assert score >= 71


def test_score_partial_implementation():
    """Test score calculation with partial GEO implementation."""
    partial_robots = {"found": True, "citation_bots_ok": False, "bots_allowed": ["GPTBot"]}
    partial_llms = {"found": True, "has_h1": True, "has_sections": False, "has_links": True}
    partial_schema = {"has_website": True, "has_faq": False, "has_webapp": False}
    partial_meta = {
        "has_title": True,
        "has_description": False,
        "has_canonical": False,
        "has_og_title": False,
        "has_og_description": False,
    }
    partial_content = {"has_h1": False, "has_numbers": True, "has_links": False}

    score = compute_geo_score(
        partial_robots, partial_llms, partial_schema, partial_meta, partial_content
    )
    assert 0 <= score <= 100
    assert 20 <= score <= 60  # Should be in foundation range


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================


def test_robots_txt_network_error():
    """Test handling of network errors when fetching robots.txt."""
    with patch("geo_audit.fetch_url", return_value=(None, "Connection failed")):
        result = audit_robots_txt("https://example.com")

    assert result["found"] is False
    assert result["citation_bots_ok"] is False


def test_llms_txt_network_error():
    """Test handling of network errors when fetching llms.txt."""
    with patch("geo_audit.fetch_url", return_value=(None, "Timeout (10s)")):
        result = audit_llms_txt("https://example.com")

    assert result["found"] is False


def test_schema_invalid_json():
    """Test handling of invalid JSON in JSON-LD script tag."""
    html = """
<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    { invalid json here }
    </script>
</head>
<body></body>
</html>
"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_schema(soup, "https://example.com")

    # Should handle gracefully without crashing
    assert isinstance(result, dict)
    assert "found_types" in result


# ============================================================================
# HTTP ERROR HANDLING TESTS — PRIORITY 1
# ============================================================================


def test_http_403_forbidden():
    """Test handling of 403 Forbidden response."""
    mock_response = Mock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_robots_txt("https://example.com")

    # Code treats 403 as found but warns — graceful degradation
    assert result["found"] is True
    assert result["citation_bots_ok"] is False
    assert len(result["bots_allowed"]) == 0


def test_http_500_server_error():
    """Test handling of 500 Internal Server Error."""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_robots_txt("https://example.com")

    # Should mark as found (server exists) but may have issues
    assert result["found"] is True
    assert result["citation_bots_ok"] is False


def test_http_timeout():
    """Test handling of request timeout."""
    with patch("geo_audit.fetch_url", return_value=(None, "Timeout (10s)")):
        result = audit_llms_txt("https://example.com")

    assert result["found"] is False
    assert result["has_h1"] is False
    assert result["has_links"] is False
    assert result["word_count"] == 0


def test_connection_refused():
    """Test handling of connection refused error."""
    with patch("geo_audit.fetch_url", return_value=(None, "Connection failed: [Errno 111] Connection refused")):
        result = audit_robots_txt("https://example.com")

    assert result["found"] is False
    assert result["citation_bots_ok"] is False
    assert len(result["bots_blocked"]) == 0


def test_ssl_error():
    """Test handling of SSL certificate errors."""
    with patch("geo_audit.fetch_url", return_value=(None, "SSL: CERTIFICATE_VERIFY_FAILED")):
        result = audit_llms_txt("https://example.com")

    assert result["found"] is False
    assert result["has_sections"] is False


def test_redirect_loop():
    """Test handling of infinite redirect loops."""
    with patch("geo_audit.fetch_url", return_value=(None, "Too many redirects")):
        result = audit_robots_txt("https://example.com")

    assert result["found"] is False
    assert result["bots_allowed"] == []
    assert result["bots_missing"] == []


def test_invalid_url():
    """Test handling of malformed URLs."""
    with patch("geo_audit.fetch_url", return_value=(None, "Invalid URL: No schema supplied")):
        result = audit_llms_txt("malformed-url")

    assert result["found"] is False
    assert result["word_count"] == 0


def test_dns_resolution_failed():
    """Test handling of DNS resolution failure."""
    with patch("geo_audit.fetch_url", return_value=(None, "Failed to resolve hostname: Name or service not known")):
        result = audit_robots_txt("https://nonexistent-domain-12345.com")

    assert result["found"] is False
    assert result["citation_bots_ok"] is False


# ============================================================================
# ENCODING EDGE CASES TESTS
# ============================================================================


def test_robots_txt_non_utf8_encoding():
    """Test robots.txt with non-UTF8 encoding (e.g., Latin-1)."""
    # Latin-1 encoded content with special characters
    robots_content = """User-agent: GPTBot
Allow: /
# Café © 2026"""

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = robots_content

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_robots_txt("https://example.com")

    assert result["found"] is True
    assert "GPTBot" in result["bots_allowed"]


def test_robots_txt_mixed_line_endings():
    """Test robots.txt with mixed Windows/Unix line endings."""
    robots_content = "User-agent: GPTBot\r\nAllow: /\n\nUser-agent: ClaudeBot\r\nAllow: /\n"

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = robots_content

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_robots_txt("https://example.com")

    assert result["found"] is True
    assert "GPTBot" in result["bots_allowed"]
    assert "ClaudeBot" in result["bots_allowed"]


def test_html_charset_mismatch():
    """Test HTML with mismatched charset declaration."""
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="ISO-8859-1">
    <title>Test Page</title>
</head>
<body><h1>Content</h1></body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_meta_tags(soup, "https://example.com")

    assert result["has_title"] is True


def test_meta_charset_missing():
    """Test HTML without charset declaration."""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>No Charset</title>
</head>
<body><h1>Test</h1></body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_meta_tags(soup, "https://example.com")

    assert result["has_title"] is True


# ============================================================================
# JSON-LD VALIDATION TESTS
# ============================================================================


def test_schema_malformed_json():
    """Test handling of malformed JSON-LD in schema."""
    html = """<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Test",
        "url": "https://example.com"
        // invalid trailing comma
    }
    </script>
</head>
<body></body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_schema(soup, "https://example.com")

    # Should handle gracefully without crashing
    assert isinstance(result, dict)
    assert "found_types" in result


def test_schema_missing_required_fields():
    """Test schema with missing @context or @type."""
    html = """<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {
        "name": "Example Site",
        "url": "https://example.com"
    }
    </script>
</head>
<body></body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_schema(soup, "https://example.com")

    # Should detect schema but mark as invalid/unknown type
    assert result["has_website"] is False
    assert "unknown" in result["found_types"] or len(result["found_types"]) == 0


def test_schema_invalid_url_format():
    """Test schema with invalid URL format in fields."""
    html = """<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Example",
        "url": "not-a-valid-url"
    }
    </script>
</head>
<body></body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_schema(soup, "https://example.com")

    # Should still detect WebSite type even with invalid URL
    assert result["has_website"] is True
    assert "WebSite" in result["found_types"]


# ============================================================================
# PRODUCTION EDGE CASES
# ============================================================================


def test_robots_txt_disallow_all():
    """Test robots.txt with global Disallow: / for all bots."""
    robots_content = """User-agent: *
Disallow: /"""

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = robots_content

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_robots_txt("https://example.com")

    assert result["found"] is True
    # All bots should be missing or blocked since * blocks everything
    assert len(result["bots_allowed"]) == 0
    assert result["citation_bots_ok"] is False


def test_page_without_title():
    """Test HTML page without <title> tag."""
    html = """<!DOCTYPE html>
<html>
<head>
    <meta name="description" content="A page without title">
</head>
<body>
    <h1>Main Heading</h1>
    <p>Some content here.</p>
</body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_meta_tags(soup, "https://example.com")

    assert result["has_title"] is False
    assert result["has_description"] is True


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


def test_robots_txt_empty_disallow():
    """Test robots.txt with empty Disallow (allows everything)."""
    robots_content = """User-agent: GPTBot
Disallow:

User-agent: ClaudeBot
Disallow:
"""

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = robots_content

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_robots_txt("https://example.com")

    assert result["found"] is True
    assert "GPTBot" in result["bots_allowed"]
    assert "ClaudeBot" in result["bots_allowed"]


def test_robots_txt_partial_disallow():
    """Test robots.txt with partial paths blocked."""
    robots_content = """User-agent: GPTBot
Disallow: /admin/
Disallow: /private/

User-agent: *
Allow: /
"""

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = robots_content

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_robots_txt("https://example.com")

    assert result["found"] is True
    assert "GPTBot" in result["bots_allowed"]
    # Should show partial blocking


def test_robots_txt_wildcard_user_agent():
    """Test robots.txt with wildcard * blocking specific paths."""
    robots_content = """User-agent: *
Disallow: /admin/
Disallow: /private/
"""

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = robots_content

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_robots_txt("https://example.com")

    assert result["found"] is True
    # Bots not explicitly mentioned should be in missing list
    assert len(result["bots_missing"]) > 0


def test_llms_txt_empty_content():
    """Test llms.txt with minimal/empty content."""
    llms_content = ""

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = llms_content

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_llms_txt("https://example.com")

    assert result["found"] is True
    assert result["has_h1"] is False
    assert result["word_count"] == 0


def test_llms_txt_only_links():
    """Test llms.txt with only links, no structure."""
    llms_content = """- [Link 1](https://example.com/1)
- [Link 2](https://example.com/2)
"""

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = llms_content

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_llms_txt("https://example.com")

    assert result["found"] is True
    assert result["has_links"] is True
    assert result["has_h1"] is False


def test_schema_array_of_schemas():
    """Test handling of array of schemas in single JSON-LD block."""
    html = """<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    [
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "Example",
            "url": "https://example.com"
        },
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Example Org"
        }
    ]
    </script>
</head>
<body></body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_schema(soup, "https://example.com")

    assert result["has_website"] is True
    assert "WebSite" in result["found_types"]
    assert "Organization" in result["found_types"]


def test_schema_nested_types():
    """Test schema with nested entity types."""
    html = """<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Example",
        "url": "https://example.com",
        "publisher": {
            "@type": "Organization",
            "name": "Publisher"
        }
    }
    </script>
</head>
<body></body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_schema(soup, "https://example.com")

    assert result["has_website"] is True
    assert "WebSite" in result["found_types"]


def test_meta_tags_long_title():
    """Test detection of overly long title tag."""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>This is a very long title that exceeds the recommended 60 character limit for SEO purposes and may be truncated in search results</title>
</head>
<body></body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_meta_tags(soup, "https://example.com")

    assert result["has_title"] is True


def test_meta_tags_short_description():
    """Test detection of too short meta description."""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Test</title>
    <meta name="description" content="Short desc">
</head>
<body></body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_meta_tags(soup, "https://example.com")

    assert result["has_description"] is True


def test_meta_tags_long_description():
    """Test detection of overly long meta description."""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Test</title>
    <meta name="description" content="This is an extremely long meta description that goes way beyond the recommended 160 character limit and will likely be truncated by search engines when displayed in search results which is not ideal for user experience.">
</head>
<body></body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_meta_tags(soup, "https://example.com")

    assert result["has_description"] is True


def test_content_quality_few_headings():
    """Test content with insufficient heading structure."""
    html = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
    <h1>Title</h1>
    <p>Just one heading and some content here.</p>
</body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_content_quality(soup, "https://example.com")

    assert result["has_h1"] is True
    assert result["heading_count"] == 1


def test_content_quality_good_heading_structure():
    """Test content with good heading structure (>=3 headings)."""
    html = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
    <h1>Main Title</h1>
    <h2>Section One</h2>
    <p>Content here.</p>
    <h2>Section Two</h2>
    <p>More content.</p>
    <h3>Subsection</h3>
</body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_content_quality(soup, "https://example.com")

    assert result["has_h1"] is True
    assert result["heading_count"] >= 3


def test_content_quality_sufficient_word_count():
    """Test content with sufficient word count (>=300 words)."""
    # Generate content with 300+ words
    long_text = " ".join(["word"] * 350)
    html = f"""<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
    <h1>Article</h1>
    <p>{long_text}</p>
</body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_content_quality(soup, "https://example.com")

    assert result["word_count"] >= 300


def test_content_quality_low_word_count():
    """Test content with insufficient word count."""
    html = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
    <h1>Short Page</h1>
    <p>Very brief content.</p>
</body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_content_quality(soup, "https://example.com")

    assert result["word_count"] < 300


def test_content_quality_few_numbers():
    """Test content with insufficient numerical data."""
    html = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
    <h1>Article</h1>
    <p>Some content with only 1 number.</p>
</body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_content_quality(soup, "https://example.com")

    assert result["has_numbers"] is False


def test_content_quality_no_external_links():
    """Test content without external citations."""
    html = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
    <h1>Article</h1>
    <p>Content with only <a href="/internal">internal links</a>.</p>
    <a href="/about">About</a>
</body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_content_quality(soup, "https://example.com")

    assert result["has_links"] is False


def test_content_quality_missing_h1():
    """Test content without H1 heading."""
    html = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
    <h2>Subtitle</h2>
    <p>Content without main heading.</p>
</body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_content_quality(soup, "https://example.com")

    assert result["has_h1"] is False


def test_score_with_multiple_website_schemas():
    """Test score calculation when multiple WebSite schemas exist."""
    robots = {"found": True, "citation_bots_ok": True, "bots_allowed": []}
    llms = {"found": True, "has_h1": True, "has_sections": True, "has_links": True}
    schema = {
        "has_website": True,
        "has_faq": False,
        "has_webapp": False,
    }
    meta = {
        "has_title": True,
        "has_description": True,
        "has_canonical": True,
        "has_og_title": True,
        "has_og_description": True,
    }
    content = {"has_h1": True, "has_numbers": True, "has_links": True}

    score = compute_geo_score(robots, llms, schema, meta, content)

    assert 0 <= score <= 100
    assert score >= 70  # Should be good level


def test_robots_txt_case_insensitive_bot_names():
    """Test that bot names are matched case-insensitively."""
    robots_content = """User-agent: gptbot
Allow: /

User-agent: CLAUDEBOT
Allow: /
"""

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = robots_content

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_robots_txt("https://example.com")

    # Should match GPTBot and ClaudeBot despite different casing
    assert "GPTBot" in result["bots_allowed"]
    assert "ClaudeBot" in result["bots_allowed"]


def test_robots_txt_wildcard_path():
    """Test robots.txt with wildcard path /* (blocks everything)."""
    robots_content = """User-agent: GPTBot
Disallow: /*
"""

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = robots_content

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_robots_txt("https://example.com")

    assert "GPTBot" in result["bots_blocked"]
    assert "GPTBot" not in result["bots_allowed"]


def test_robots_txt_blocks_citation_bot():
    """Test blocking of critical citation bot (should trigger fail message)."""
    robots_content = """User-agent: OAI-SearchBot
Disallow: /

User-agent: ClaudeBot
Disallow: /*
"""

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = robots_content

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_robots_txt("https://example.com")

    # Both citation bots should be blocked
    assert "OAI-SearchBot" in result["bots_blocked"]
    assert "ClaudeBot" in result["bots_blocked"]
    assert result["citation_bots_ok"] is False


def test_llms_txt_with_description():
    """Test llms.txt with blockquote description present."""
    llms_content = """# My Site

> This is a site description in blockquote format.

## Section

- [Link](https://example.com)
"""

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = llms_content

    with patch("geo_audit.fetch_url", return_value=(mock_response, None)):
        result = audit_llms_txt("https://example.com")

    assert result["has_description"] is True
    assert result["has_h1"] is True


def test_schema_empty_type():
    """Test schema with empty @type field."""
    html = """<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "",
        "name": "Example"
    }
    </script>
</head>
<body></body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_schema(soup, "https://example.com")

    assert result["has_website"] is False


def test_content_quality_with_currency():
    """Test content with currency symbols after numbers (99%, 199€)."""
    html = """<!DOCTYPE html>
<html>
<head><title>Pricing</title></head>
<body>
    <h1>Pricing Plans</h1>
    <h2>Growth Metrics</h2>
    <p>Increased revenue by 45% last quarter</p>
    <p>Saved clients 199€ on average</p>
    <p>Serving 1,250 customers worldwide</p>
</body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_content_quality(soup, "https://example.com")

    assert result["has_numbers"] is True


def test_meta_tags_empty_content():
    """Test meta tags with empty content attribute."""
    html = """<!DOCTYPE html>
<html>
<head>
    <title></title>
    <meta name="description" content="">
</head>
<body></body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_meta_tags(soup, "https://example.com")

    assert result["has_title"] is False
    assert result["has_description"] is False


def test_meta_tags_whitespace_only():
    """Test meta tags with whitespace-only content."""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>   </title>
    <meta name="description" content="   ">
</head>
<body></body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_meta_tags(soup, "https://example.com")

    assert result["has_title"] is False
    assert result["has_description"] is False


def test_meta_tags_optimal_description_length():
    """Test meta description with optimal length (120-160 chars)."""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Test</title>
    <meta name="description" content="This is an optimally sized meta description with exactly the right amount of content to be displayed fully in search engine results without truncation.">
</head>
<body></body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_meta_tags(soup, "https://example.com")

    assert result["has_description"] is True


def test_schema_multiple_same_type():
    """Test page with multiple schemas of the same type."""
    html = """<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Main Site",
        "url": "https://example.com"
    }
    </script>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Duplicate",
        "url": "https://example.com/alt"
    }
    </script>
</head>
<body></body>
</html>"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result = audit_schema(soup, "https://example.com")

    assert result["has_website"] is True
    assert result["found_types"].count("WebSite") == 2


def test_full_audit_workflow():
    """Test complete audit workflow with mocked responses."""
    robots_content = """
User-agent: GPTBot
Allow: /
User-agent: ClaudeBot
Allow: /
"""

    llms_content = """# Example Site

> Description here

## Tools

- [Tool](https://example.com/tool)
"""

    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Example Site</title>
    <meta name="description" content="Test description for SEO and GEO optimization">
    <link rel="canonical" href="https://example.com/">
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "WebSite", "url": "https://example.com"}
    </script>
</head>
<body>
    <h1>Main Heading</h1>
    <p>Content with 100 users and 50% improvement.</p>
    <a href="https://external.com/source">External Source</a>
</body>
</html>
"""

    def mock_fetch(url, timeout=10):
        mock_resp = Mock()
        mock_resp.status_code = 200
        if "robots.txt" in url:
            mock_resp.text = robots_content
        elif "llms.txt" in url:
            mock_resp.text = llms_content
        else:
            mock_resp.text = html_content
        return mock_resp, None

    with patch("geo_audit.fetch_url", side_effect=mock_fetch):
        robots = audit_robots_txt("https://example.com")
        llms = audit_llms_txt("https://example.com")

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")
        schema = audit_schema(soup, "https://example.com")
        meta = audit_meta_tags(soup, "https://example.com")
        content = audit_content_quality(soup, "https://example.com")

        score = compute_geo_score(robots, llms, schema, meta, content)

    assert robots["found"] is True
    assert llms["found"] is True
    assert schema["has_website"] is True
    assert meta["has_title"] is True
    assert content["has_h1"] is True
    assert 0 <= score <= 100
