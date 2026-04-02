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

    # Generate self-contained HTML and convert to PDF
    html_content = format_audit_html(result)
    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes
