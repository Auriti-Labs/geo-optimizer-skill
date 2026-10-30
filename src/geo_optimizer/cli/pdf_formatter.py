"""
PDF formatter for GEO audit reports.

Generates a PDF report from the self-contained HTML produced by
html_formatter, converted via weasyprint (optional dependency).
Install with: ``pip install geo-optimizer-skill[pdf]``
"""

from __future__ import annotations

from geo_optimizer.models.results import AuditResult


def format_audit_pdf(result: AuditResult) -> bytes:
    """Generate PDF report from audit result. Requires weasyprint."""
    from geo_optimizer.cli.html_formatter import format_audit_html

    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise ImportError(
            "PDF generation requires weasyprint. Install with: pip install geo-optimizer-skill[pdf]"
        ) from exc

    # The HTML is self-contained (fonts as data URIs): no network or local file fetches
    html_content = format_audit_html(result)
    pdf_bytes = HTML(string=html_content, url_fetcher=_data_only_fetcher()).write_pdf()
    return bytes(pdf_bytes)


def _data_only_fetcher():
    """URL fetcher that only resolves ``data:`` URIs."""
    try:
        from weasyprint import URLFetcher  # weasyprint >= 68
    except ImportError:
        from weasyprint import default_url_fetcher

        def fetch(url, *args, **kwargs):
            if not url.startswith("data:"):
                raise ValueError(f"Blocked non-data URL: {url[:60]}")
            return default_url_fetcher(url, *args, **kwargs)

        return fetch
    return URLFetcher(allowed_protocols=("data",))
