from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

from geo_optimizer.core.audit_ai_discovery import (
    check_markdown_negotiation,
    check_markdown_negotiation_async,
)
from geo_optimizer.core.audit_content import audit_content_quality
from geo_optimizer.core.audit_schema import audit_schema
from geo_optimizer.core.audit_signals import audit_signals


def test_markdown_negotiation():
    with patch("geo_optimizer.core.audit_ai_discovery.fetch_url") as mock_fetch:
        mock_fetch.return_value = (
            MagicMock(status_code=200, headers={"Content-Type": "text/markdown; charset=utf-8"}),
            None,
        )
        assert check_markdown_negotiation("https://x.test/") is True
        assert mock_fetch.call_args.kwargs["headers"]["Accept"] == "text/markdown"

        mock_fetch.return_value = (MagicMock(status_code=200, headers={"Content-Type": "text/html"}), None)
        assert check_markdown_negotiation("https://x.test/") is False

        mock_fetch.return_value = (None, "Connection failed")
        assert check_markdown_negotiation("https://x.test/") is False


def test_markdown_negotiation_async():
    response = MagicMock(status_code=200, headers={"Content-Type": "text/markdown"})
    with patch("geo_optimizer.core.audit_ai_discovery.fetch_url_async", return_value=(response, None)) as mock_fetch:
        assert asyncio.run(check_markdown_negotiation_async(MagicMock(), "https://x.test/")) is True
        assert mock_fetch.call_args.kwargs["headers"]["Accept"] == "text/markdown"


def test_images_alt_ok_requires_ninety_percent_or_presentation_empty_alt():
    no_images = BeautifulSoup("<html><body><h1>Title</h1></body></html>", "html.parser")
    assert audit_content_quality(no_images, "https://x.test/").images_alt_ok is True

    three_images = BeautifulSoup('<img alt="one"><img alt=""><img alt="" role="presentation">', "html.parser")
    assert audit_content_quality(three_images, "https://x.test/").images_alt_ok is False


def test_visible_match_uses_visible_organization_name():
    html = """
    <html><body><h1>Acme AI</h1>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Organization","name":"Acme AI"}
    </script></body></html>
    """
    result = audit_schema(BeautifulSoup(html, "html.parser"), "https://x.test/")
    assert result.visible_match is True

    hidden_name = html.replace("<h1>Acme AI</h1>", "<h1>Different company</h1>")
    result = audit_schema(BeautifulSoup(hidden_name, "html.parser"), "https://x.test/")
    assert result.visible_match is False


def test_visible_match_ignores_title_text():
    html = """
    <html><head><title>Acme AI</title></head><body>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Organization","name":"Acme AI"}
    </script></body></html>
    """
    result = audit_schema(BeautifulSoup(html, "html.parser"), "https://x.test/")
    assert result.visible_match is False


def test_freshness_valid_rejects_date_more_than_one_day_in_future():
    soup = BeautifulSoup("<html><body></body></html>", "html.parser")
    schema = MagicMock(raw_schemas=[{"@type": "Article", "dateModified": "2030-01-01"}])
    signals = audit_signals(soup, schema)
    assert signals.has_freshness is True
    assert signals.freshness_valid is False
