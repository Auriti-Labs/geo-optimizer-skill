"""
Test per geo_optimizer.cli.pdf_formatter — generazione report PDF.

Verifica che il formatter PDF generi output valido e gestisca
correttamente l'assenza di weasyprint.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from geo_optimizer.models.results import (
    AuditResult,
    ContentResult,
    LlmsTxtResult,
    MetaResult,
    RobotsResult,
    SchemaResult,
)


def _make_result(**overrides) -> AuditResult:
    """Crea un AuditResult di esempio per i test."""
    result = AuditResult(
        url="https://example.com",
        score=72,
        band="good",
        robots=RobotsResult(
            found=True,
            bots_allowed=["GPTBot", "ClaudeBot"],
            bots_missing=[],
            bots_blocked=[],
            citation_bots_ok=True,
        ),
        llms=LlmsTxtResult(found=True, has_h1=True, has_description=True),
        schema=SchemaResult(has_website=True, found_types=["WebSite", "FAQPage"]),
        meta=MetaResult(has_title=True, has_description=True),
        content=ContentResult(has_h1=True, word_count=500),
        recommendations=["Add FAQ schema", "Improve llms.txt sections"],
        http_status=200,
        page_size=12000,
    )
    for key, value in overrides.items():
        parts = key.split(".")
        obj = result
        for part in parts[:-1]:
            obj = getattr(obj, part)
        setattr(obj, parts[-1], value)
    return result


class TestPdfFormatterImportError:
    """Test che l'errore di import sia chiaro quando weasyprint non è installato."""

    def test_import_error_without_weasyprint(self):
        """Senza weasyprint, format_audit_pdf alza ImportError con messaggio chiaro."""
        result = _make_result()

        # Rimuoviamo weasyprint dai moduli disponibili per simulare l'assenza
        with patch.dict(sys.modules, {"weasyprint": None}):
            # Forza re-import del modulo per pulire la cache
            if "geo_optimizer.cli.pdf_formatter" in sys.modules:
                del sys.modules["geo_optimizer.cli.pdf_formatter"]

            from geo_optimizer.cli.pdf_formatter import format_audit_pdf

            with pytest.raises(ImportError, match="weasyprint"):
                format_audit_pdf(result)

    def test_import_error_message_contains_install_hint(self):
        """Il messaggio di errore contiene le istruzioni di installazione."""
        result = _make_result()

        with patch.dict(sys.modules, {"weasyprint": None}):
            if "geo_optimizer.cli.pdf_formatter" in sys.modules:
                del sys.modules["geo_optimizer.cli.pdf_formatter"]

            from geo_optimizer.cli.pdf_formatter import format_audit_pdf

            with pytest.raises(ImportError, match=r"pip install geo-optimizer-skill\[pdf\]"):
                format_audit_pdf(result)


class TestPdfFormatterWithMock:
    """Test con weasyprint mockato per verificare la generazione PDF."""

    def test_format_audit_pdf_returns_bytes(self):
        """format_audit_pdf ritorna bytes non vuoti quando weasyprint è disponibile."""
        result = _make_result()

        # Mock weasyprint.HTML
        mock_html_cls = MagicMock()
        fake_pdf = b"%PDF-1.4 fake pdf content bytes"
        mock_html_cls.return_value.write_pdf.return_value = fake_pdf

        mock_weasyprint = MagicMock()
        mock_weasyprint.HTML = mock_html_cls

        with patch.dict(sys.modules, {"weasyprint": mock_weasyprint}):
            if "geo_optimizer.cli.pdf_formatter" in sys.modules:
                del sys.modules["geo_optimizer.cli.pdf_formatter"]

            from geo_optimizer.cli.pdf_formatter import format_audit_pdf

            pdf_bytes = format_audit_pdf(result)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes == fake_pdf

    def test_format_audit_pdf_passes_html_to_weasyprint(self):
        """Verifica che l'HTML generato venga passato a weasyprint.HTML(string=...)."""
        result = _make_result()

        mock_html_cls = MagicMock()
        mock_html_cls.return_value.write_pdf.return_value = b"%PDF"

        mock_weasyprint = MagicMock()
        mock_weasyprint.HTML = mock_html_cls

        with patch.dict(sys.modules, {"weasyprint": mock_weasyprint}):
            if "geo_optimizer.cli.pdf_formatter" in sys.modules:
                del sys.modules["geo_optimizer.cli.pdf_formatter"]

            from geo_optimizer.cli.pdf_formatter import format_audit_pdf

            format_audit_pdf(result)

        # Verifica che HTML sia stato chiamato con string= contenente il report
        mock_html_cls.assert_called_once()
        call_kwargs = mock_html_cls.call_args
        html_string = (
            call_kwargs.kwargs.get("string") or call_kwargs.args[0]
            if call_kwargs.args
            else call_kwargs[1].get("string", "")
        )
        assert "GEO Audit Report" in html_string
        assert "example.com" in html_string

    def test_format_audit_pdf_with_different_scores(self):
        """Verifica generazione PDF con punteggi diversi (bande diverse)."""
        mock_html_cls = MagicMock()
        mock_html_cls.return_value.write_pdf.return_value = b"%PDF-test"

        mock_weasyprint = MagicMock()
        mock_weasyprint.HTML = mock_html_cls

        # Testa tutte le bande
        test_cases = [
            {"score": 95, "band": "excellent"},
            {"score": 72, "band": "good"},
            {"score": 45, "band": "foundation"},
            {"score": 15, "band": "critical"},
        ]

        for case in test_cases:
            with patch.dict(sys.modules, {"weasyprint": mock_weasyprint}):
                if "geo_optimizer.cli.pdf_formatter" in sys.modules:
                    del sys.modules["geo_optimizer.cli.pdf_formatter"]

                from geo_optimizer.cli.pdf_formatter import format_audit_pdf

                result = _make_result(score=case["score"], band=case["band"])
                pdf_bytes = format_audit_pdf(result)
                assert isinstance(pdf_bytes, bytes), f"Fallito per banda {case['band']}"
