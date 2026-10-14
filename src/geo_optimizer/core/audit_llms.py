"""
Audit llms.txt for AI indexing.

Extracted from audit.py (#402-bis) — separation of concerns.
All functions return dataclasses, NEVER print.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

from geo_optimizer.models.config import BROWSER_USER_AGENT
from geo_optimizer.models.results import LlmsTxtResult
from geo_optimizer.utils.http import fetch_url
from geo_optimizer.utils.text import count_words


def _validate_llms_content(result: LlmsTxtResult, content: str) -> None:
    """Validate llms.txt content against spec v2 and populate result fields.

    Populates has_blockquote, has_optional_section, companion_files_hint
    and validation_warnings on the passed result.

    Args:
        result: LlmsTxtResult already initialized with base fields.
        content: Text content of the llms.txt file (already BOM-stripped).
    """
    lines = content.splitlines()
    warnings: list[str] = []

    # Blockquote validation (> description) — REQUIRED by spec
    blockquotes = [line for line in lines if line.startswith("> ")]
    if blockquotes:
        result.has_blockquote = True
    else:
        warnings.append("llms.txt should have a > blockquote description after H1")

    # H1 validation — must be the first non-empty line
    non_empty_lines = [line for line in lines if line.strip()]
    if non_empty_lines and not non_empty_lines[0].startswith("# "):
        warnings.append("H1 should be the first line of llms.txt")

    # Markdown link validation
    if not result.has_links:
        warnings.append("llms.txt should contain markdown links to site pages")

    # Minimum length validation
    if result.word_count < 100:
        warnings.append("llms.txt is too short, consider adding more content")

    # ## Optional section — best practice
    h2_lines = [line for line in lines if line.startswith("## ")]
    for h2 in h2_lines:
        if "optional" in h2.lower():
            result.has_optional_section = True
            break

    # Companion files: link a file .md (es. something.html.md)
    links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
    for _text, url in links:
        if url.endswith(".md"):
            result.companion_files_hint = True
            break

    result.validation_warnings = warnings


def _browser_like_headers() -> dict:
    """Headers with a real desktop browser UA, for the CDN/WAF retry."""
    return {"User-Agent": BROWSER_USER_AGENT}


def _try_browser_like_retry(url: str, result: LlmsTxtResult) -> None:
    """Re-fetch a blocked URL with a real desktop browser UA.

    If the second attempt returns 200 with a text payload (not a WAF fallback
    HTML page), process it as a valid llms.txt and add a validation warning
    that the CDN/WAF is blocking the auditor's main UA.
    """
    r2, err2 = fetch_url(url, headers=_browser_like_headers())
    if err2 or not r2:
        result.validation_warnings.append(
            "llms.txt may exist but CDN/WAF returned a block, and the browser retry failed"
        )
        return
    if r2.status_code == 200:
        # Guard against a WAF/fallback that answers the browser with an HTML
        # page instead of the real llms.txt — that would be a false positive.
        content_type = (r2.headers.get("Content-Type") or "").lower()
        body = (getattr(r2, "text", "") or "").lstrip("\ufeff").lstrip().lower()
        looks_html = "<html" in body[:200] or "<!doctype" in body[:200]
        if looks_html or ("text/html" in content_type and "text/plain" not in content_type):
            result.validation_warnings.append(
                "CDN/WAF returned a block; the browser retry answered with an HTML page, "
                "so llms.txt status remains unknown"
            )
            return
        result.found = True
        # process the retried (200) response content normally FIRST (its
        # _validate_llms_content overwrites validation_warnings), then append
        # the CDN note so it is not lost.
        _result_from_response(r2, result)
        result.validation_warnings.append(
            "CDN/WAF returned a block for the auditor's User-Agent (recovered via a browser-like retry)"
        )


def _result_from_response(r, result: LlmsTxtResult) -> None:
    """Populate result fields from a 200 response (shared by both audit paths)."""
    content = r.text.lstrip("\ufeff")
    lines = content.splitlines()
    result.word_count = count_words(content)  # CJK-aware (#537)

    # H1 check
    h1_lines = [line for line in lines if line.startswith("# ")]
    if h1_lines:
        result.has_h1 = True

    # Blockquote description
    blockquotes = [line for line in lines if line.startswith("> ")]
    if blockquotes:
        # Fix #317: sync has_description (backward-compat alias) with has_blockquote
        result.has_blockquote = True
        result.has_description = True

    # H2 sections
    h2_lines = [line for line in lines if line.startswith("## ")]
    if h2_lines:
        result.has_sections = True
    result.sections_count = len(h2_lines)

    # Markdown links
    links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
    if links:
        result.has_links = True
    result.links_count = len(links)

    # #39: v2 validation — full spec conformance
    _validate_llms_content(result, content)


def audit_llms_txt(base_url: str) -> LlmsTxtResult:
    """Check for presence and quality of llms.txt. Returns LlmsTxtResult."""
    llms_url = urljoin(base_url, "/llms.txt")
    r, err = fetch_url(llms_url)
    result = LlmsTxtResult()

    # `r is None`, not `not r`: requests.Response.__bool__ is `ok`, so a 403/406
    # is falsy and would skip the CDN/WAF branch below (httpx responses are always
    # truthy, so only the sync path was affected).
    if err or r is None:
        return result

    # A 403/406 means the CDN/WAF refused our User-Agent: llms.txt may well
    # exist but we can't see it. Retry with a browser-like UA to prove it.
    if r.status_code in (403, 406):
        result.blocked_by_cdn = True
        _try_browser_like_retry(llms_url, result)
        if not result.found:
            # second attempt also blocked/failed — llms.txt not retrievable
            return result
        # retry succeeded: content already populated in result.found branch above

    if not result.found and r.status_code != 200:
        return result

    # populate from the original 200 response (non-blocked path), or reuse the
    # retried content when the original was 403/406 but browser-like retry found it
    if r.status_code == 200 and not result.found:
        result.found = True
        _result_from_response(r, result)

    # Check /llms-full.txt (llmstxt.org spec — optional extended version)
    if result.found:
        full_url = urljoin(base_url, "/llms-full.txt")
        r_full, err_full = fetch_url(full_url)
        if r_full and r_full.status_code == 200 and len(r_full.text.strip()) > 0:
            result.has_full = True

    return result


def _audit_llms_from_response(r, r_full=None, url: str | None = None) -> LlmsTxtResult:
    """Analyze llms.txt from an already-downloaded HTTP response.

    Args:
        r: HTTP response for /llms.txt (or None).
        r_full: HTTP response for /llms-full.txt (or None). Fix #184.
        url: The full /llms.txt URL. When present and the response is a
            CDN/WAF block (403/406), a browser-like retry is attempted so the
            main audit flow can actually recover the file (not just flag it).
    """
    result = LlmsTxtResult()

    # `r is None`, not `not r`: a requests 403/406 is falsy (see audit_llms_txt)
    if r is None:
        return result

    # A 403/406 response means the CDN/WAF refused the auditor's User-Agent:
    # llms.txt may exist, so we don't treat it as "not found". If the URL is
    # available we retry with a browser-like UA to recover the real file.
    if r.status_code in (403, 406):
        result.blocked_by_cdn = True
        result.validation_warnings.append(
            f"llms.txt may exist but CDN/WAF returned {r.status_code} - check if your CDN blocks non-browser User-Agents"
        )
        if url:
            _try_browser_like_retry(url, result)
            if result.found:
                # recovered via browser-like retry: still note the CDN block
                result.blocked_by_cdn = True
                if r_full is not None and r_full.status_code == 200 and r_full.text.strip():
                    result.has_full = True
        return result

    if r.status_code != 200:
        return result

    result.found = True
    content = r.text.lstrip("\ufeff")
    lines = content.splitlines()
    result.word_count = count_words(content)  # CJK-aware (#537)

    h1_lines = [line for line in lines if line.startswith("# ")]
    if h1_lines:
        result.has_h1 = True

    blockquotes = [line for line in lines if line.startswith("> ")]
    if blockquotes:
        # Fix #317: sync has_description (backward-compat alias) with has_blockquote
        result.has_blockquote = True
        result.has_description = True

    h2_lines = [line for line in lines if line.startswith("## ")]
    if h2_lines:
        result.has_sections = True
    # #247: count H2 sections for Policy Intelligence
    result.sections_count = len(h2_lines)

    links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
    if links:
        result.has_links = True
    # #247: count links for Policy Intelligence
    result.links_count = len(links)

    # #39: v2 validation — full spec compliance
    _validate_llms_content(result, content)

    # Check /llms-full.txt — fix #184: now works in the async path too
    if r_full and r_full.status_code == 200 and len(r_full.text.strip()) > 0:
        result.has_full = True

    return result
