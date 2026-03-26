"""
PDF formatter for GEO audit reports.

Genera un report PDF a partire dall'HTML self-contained prodotto da
html_formatter, convertito tramite weasyprint (dipendenza opzionale).
Installazione: ``pip install geo-optimizer-skill[pdf]``
"""

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

    # Genera l'HTML self-contained e lo converte in PDF
    html_content = format_audit_html(result)
    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes
