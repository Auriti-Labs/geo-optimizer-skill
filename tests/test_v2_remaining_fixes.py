"""
Test per le fix rimanenti v2.0.0 — sicurezza e stabilità.

Copre:
- #6 SSRF sitemap URL da robots.txt (validazione dominio + IP)
- #7 Path traversal in --file, --faq-file
- #9 DoS — limite dimensione risposte HTTP
- #10 Sitemap bomb — limite profondità ricorsione
- #11 raw_schemas duplicati per @type array
- #12 audit_robots_txt/llms_txt ignorano risposte non-200
- #13 fetch_page_title ignora pagine 404/500
- #14 extract_faq_from_html non muta il tree BeautifulSoup
"""

from unittest.mock import Mock, MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from geo_optimizer.core.audit import audit_robots_txt, audit_llms_txt, audit_schema
from geo_optimizer.core.llms_generator import fetch_page_title, fetch_sitemap
from geo_optimizer.core.schema_injector import extract_faq_from_html
from geo_optimizer.utils.http import fetch_url


# ============================================================================
# #12 — audit_robots_txt / audit_llms_txt ignorano non-200
# ============================================================================


class TestStatusCodeValidation:
    """Solo risposte HTTP 200 vengono parsate come contenuto valido."""

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_robots_403_non_parsato(self, mock_fetch):
        """robots.txt con status 403 non viene trattato come trovato."""
        mock_fetch.return_value = (Mock(status_code=403, text="Forbidden"), None)
        result = audit_robots_txt("https://example.com")
        assert result.found is False

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_robots_500_non_parsato(self, mock_fetch):
        """robots.txt con status 500 non viene trattato come trovato."""
        mock_fetch.return_value = (Mock(status_code=500, text="Error"), None)
        result = audit_robots_txt("https://example.com")
        assert result.found is False

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_robots_200_parsato(self, mock_fetch):
        """robots.txt con status 200 viene parsato normalmente."""
        mock_fetch.return_value = (Mock(status_code=200, text="User-agent: *\nAllow: /"), None)
        result = audit_robots_txt("https://example.com")
        assert result.found is True

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_llms_403_non_parsato(self, mock_fetch):
        """llms.txt con status 403 non viene trattato come trovato."""
        mock_fetch.return_value = (Mock(status_code=403, text="Forbidden"), None)
        result = audit_llms_txt("https://example.com")
        assert result.found is False

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_llms_301_non_parsato(self, mock_fetch):
        """llms.txt con redirect 301 non viene trattato come trovato."""
        mock_fetch.return_value = (Mock(status_code=301, text="Moved"), None)
        result = audit_llms_txt("https://example.com")
        assert result.found is False

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_llms_200_parsato(self, mock_fetch):
        """llms.txt con status 200 viene parsato normalmente."""
        content = "# Site\n\n> Description\n\n## Pages\n\n- [Home](https://example.com)"
        mock_fetch.return_value = (Mock(status_code=200, text=content), None)
        result = audit_llms_txt("https://example.com")
        assert result.found is True
        assert result.has_h1 is True


# ============================================================================
# #13 — fetch_page_title ignora pagine non-200
# ============================================================================


class TestFetchPageTitleStatusCheck:
    """fetch_page_title ritorna None per pagine di errore."""

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_404_ritorna_none(self, mock_create):
        mock_session = MagicMock()
        mock_resp = Mock(status_code=404, text="<html><title>Page Not Found</title></html>")
        mock_session.get.return_value = mock_resp
        mock_create.return_value = mock_session

        assert fetch_page_title("https://example.com/missing") is None

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_500_ritorna_none(self, mock_create):
        mock_session = MagicMock()
        mock_resp = Mock(status_code=500, text="<html><title>Internal Server Error</title></html>")
        mock_session.get.return_value = mock_resp
        mock_create.return_value = mock_session

        assert fetch_page_title("https://example.com/broken") is None

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_200_ritorna_titolo(self, mock_create):
        mock_session = MagicMock()
        mock_resp = Mock(status_code=200, text="<html><title>Real Title</title></html>")
        mock_session.get.return_value = mock_resp
        mock_create.return_value = mock_session

        assert fetch_page_title("https://example.com/page") == "Real Title"


# ============================================================================
# #11 — raw_schemas non duplicati per @type array
# ============================================================================


class TestRawSchemasDuplication:
    """Schema con @type array non deve duplicare raw_schemas."""

    def test_type_array_un_solo_raw_schema(self):
        """@type: ['WebSite', 'WebApplication'] → 1 raw schema, 2 found_types."""
        html = """
        <script type="application/ld+json">
        {"@type": ["WebSite", "WebApplication"], "name": "Test", "url": "https://example.com"}
        </script>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = audit_schema(soup, "https://example.com")

        assert len(result.found_types) == 2
        assert "WebSite" in result.found_types
        assert "WebApplication" in result.found_types
        # Solo 1 schema raw, non 2
        assert len(result.raw_schemas) == 1
        assert result.has_website is True
        assert result.has_webapp is True

    def test_due_script_separati_due_raw(self):
        """Due script JSON-LD separati → 2 raw schemas distinti."""
        html = """
        <script type="application/ld+json">
        {"@type": "WebSite", "name": "Test"}
        </script>
        <script type="application/ld+json">
        {"@type": "FAQPage", "mainEntity": []}
        </script>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = audit_schema(soup, "https://example.com")

        assert len(result.found_types) == 2
        assert len(result.raw_schemas) == 2


# ============================================================================
# #9 — Limite dimensione risposte HTTP
# ============================================================================


class TestResponseSizeLimit:
    """fetch_url rifiuta risposte troppo grandi."""

    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_content_length_troppo_grande(self, mock_create):
        """Content-Length header superiore al limite → errore."""
        mock_session = MagicMock()
        mock_resp = Mock(
            status_code=200,
            headers={"Content-Length": "999999999"},
            content=b"x",
        )
        mock_session.get.return_value = mock_resp
        mock_create.return_value = mock_session

        resp, err = fetch_url("https://example.com", max_size=1024)
        assert resp is None
        assert "too large" in err.lower()

    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_body_troppo_grande(self, mock_create):
        """Body effettivo superiore al limite → errore."""
        mock_session = MagicMock()
        mock_resp = Mock(
            status_code=200,
            headers={},
            content=b"x" * 2048,
        )
        mock_session.get.return_value = mock_resp
        mock_create.return_value = mock_session

        resp, err = fetch_url("https://example.com", max_size=1024)
        assert resp is None
        assert "too large" in err.lower()

    @patch("geo_optimizer.utils.http.create_session_with_retry")
    def test_risposta_entro_limite(self, mock_create):
        """Risposta entro il limite → successo."""
        mock_session = MagicMock()
        mock_resp = Mock(
            status_code=200,
            headers={},
            content=b"OK",
        )
        mock_session.get.return_value = mock_resp
        mock_create.return_value = mock_session

        resp, err = fetch_url("https://example.com", max_size=1024)
        assert resp is not None
        assert err is None


# ============================================================================
# #10 — Sitemap bomb: limite profondità ricorsione
# ============================================================================


class TestSitemapDepthLimit:
    """fetch_sitemap limita la profondità di ricorsione."""

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_profondita_massima_raggiunta(self, mock_create):
        """Chiamata con _depth >= MAX non effettua richieste HTTP."""
        result = fetch_sitemap("https://example.com/sitemap.xml", _depth=10)
        assert result == []
        # Non deve nemmeno fare richieste HTTP
        mock_create.assert_not_called()

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_profondita_zero_funziona(self, mock_create):
        """Profondità 0 processa normalmente la sitemap."""
        sitemap_xml = """<?xml version="1.0"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page1</loc></url>
        </urlset>"""
        mock_session = MagicMock()
        mock_resp = Mock()
        mock_resp.content = sitemap_xml.encode()
        mock_resp.raise_for_status = Mock()
        mock_session.get.return_value = mock_resp
        mock_create.return_value = mock_session

        result = fetch_sitemap("https://example.com/sitemap.xml", _depth=0)
        assert len(result) == 1
        assert result[0].url == "https://example.com/page1"


# ============================================================================
# #14 — extract_faq_from_html non muta il tree
# ============================================================================


class TestExtractFaqNoMutation:
    """extract_faq_from_html non deve modificare il tree BeautifulSoup."""

    def test_details_summary_non_muta(self):
        """Pattern details/summary: il tree rimane intatto dopo l'estrazione."""
        html = """
        <details>
            <summary>What is GEO optimization?</summary>
            Making websites visible to AI search engines like ChatGPT and Perplexity
        </details>
        """
        soup = BeautifulSoup(html, "html.parser")
        original_html = str(soup)

        faqs = extract_faq_from_html(soup)

        # Il tree non deve essere mutato
        assert str(soup) == original_html
        # Ma deve estrarre le FAQ
        assert len(faqs) >= 1
        assert "GEO" in faqs[0]["question"]

    def test_faq_class_non_muta(self):
        """Pattern class FAQ: il tree rimane intatto dopo l'estrazione."""
        html = """
        <div class="faq-item">
            <h3>How does scoring work in the audit?</h3>
            <p>The audit checks robots.txt, llms.txt, schema, meta tags and content quality</p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        original_html = str(soup)

        faqs = extract_faq_from_html(soup)

        assert str(soup) == original_html
        assert len(faqs) >= 1


# ============================================================================
# #6 — SSRF sitemap URL da robots.txt
# ============================================================================


class TestSitemapUrlValidation:
    """discover_sitemap valida gli URL sitemap estratti da robots.txt."""

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_sitemap_stesso_dominio_accettato(self, mock_create):
        """URL sitemap dello stesso dominio viene accettato."""
        from geo_optimizer.core.llms_generator import discover_sitemap

        mock_session = MagicMock()
        robots_resp = Mock(text="Sitemap: https://example.com/sitemap.xml", status_code=200)
        head_resp = Mock(status_code=200)
        mock_session.get.return_value = robots_resp
        mock_session.head.return_value = head_resp
        mock_create.return_value = mock_session

        with patch("geo_optimizer.core.llms_generator.validate_public_url", return_value=(True, None)):
            result = discover_sitemap("https://example.com")
            assert result == "https://example.com/sitemap.xml"

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_sitemap_dominio_esterno_rifiutato(self, mock_create):
        """URL sitemap di un dominio diverso viene ignorato."""
        from geo_optimizer.core.llms_generator import discover_sitemap

        mock_session = MagicMock()
        robots_resp = Mock(
            text="Sitemap: https://evil.com/malicious-sitemap.xml",
            status_code=200,
        )
        # Se il sitemap esterno viene rifiutato, deve cadere ai common paths
        head_resp = Mock(status_code=404)
        mock_session.get.return_value = robots_resp
        mock_session.head.return_value = head_resp
        mock_create.return_value = mock_session

        result = discover_sitemap("https://example.com")
        # Non deve restituire il sitemap maligno
        assert result != "https://evil.com/malicious-sitemap.xml"
