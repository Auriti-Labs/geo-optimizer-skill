"""
GEO Audit — Signals sub-audit.

Extracted from core/audit.py for maintainability (#402).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from geo_optimizer.core.audit_google_ai import _parse_date
from geo_optimizer.models.config import AI_READINESS_FUTURE_TOLERANCE_DAYS
from geo_optimizer.models.results import SchemaResult, SignalsResult

if TYPE_CHECKING:
    from bs4 import BeautifulSoup


def audit_signals(soup: BeautifulSoup | None, schema_result: SchemaResult) -> SignalsResult:
    """Compute technical signals: lang, RSS, freshness.

    Args:
        soup: BeautifulSoup of the HTML document.
        schema_result: SchemaResult with the JSON-LD schemas found.

    Returns:
        SignalsResult with has_lang, has_rss, has_freshness populated.
    """
    signals = SignalsResult()

    # Fix H-8: guard against None soup
    if soup is None:
        return signals

    # 1. Check lang attribute on <html>
    html_tag = soup.find("html")
    if html_tag:
        lang_val = html_tag.get("lang", "").strip()
        if lang_val:
            signals.has_lang = True
            signals.lang_value = lang_val

    # 2. Check RSS/Atom feed
    rss_link = soup.find("link", attrs={"type": lambda t: t and ("rss" in t.lower() or "atom" in t.lower())})
    if rss_link:
        signals.has_rss = True
        signals.rss_url = rss_link.get("href", "")

    # 3. Check freshness (dateModified in schema or meta tag)
    # Look for dateModified in JSON-LD schemas
    if schema_result and schema_result.raw_schemas:
        for s in schema_result.raw_schemas:
            date_mod = s.get("dateModified", "") or s.get("datePublished", "")
            if date_mod:
                signals.has_freshness = True
                signals.freshness_date = str(date_mod)
                break

    # Fallback: meta tag article:modified_time
    if not signals.has_freshness:
        meta_mod = soup.find("meta", attrs={"property": "article:modified_time"})
        if meta_mod and meta_mod.get("content", "").strip():
            signals.has_freshness = True
            signals.freshness_date = meta_mod["content"].strip()

    if signals.has_freshness:
        parsed_date = _parse_date(signals.freshness_date)
        signals.freshness_valid = bool(
            parsed_date
            and parsed_date <= datetime.now(timezone.utc) + timedelta(days=AI_READINESS_FUTURE_TOLERANCE_DAYS)
        )

    return signals
