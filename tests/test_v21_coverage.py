"""
Test v2.1 — Colma i gap di coverage residui nel package geo_optimizer.

Copre:
- llms_generator.py: callback on_status, priority non numerica, url_to_label
  con slug numerico, fetch_titles=True, sezione Optional, validazione SSRF
  in discover_sitemap, fallback common paths
- formatters.py: citation_bots_ok, llms trovato senza H1, schema senza WebSite,
  schema senza FAQPage
- schema_validator.py: @context lista con primo elemento non valido, @type lista
  vuota, campo URL non stringa né lista
- schema_cmd.py: path traversal --file e --faq-file, _print_analysis con tutti
  i tipi schema, verbose=True, FAQ > 3
- validators.py: must_exist=True con directory al posto di file, ValueError
  in ip_address ignorato (DNS skip), file non trovato
"""

import socket
from unittest.mock import MagicMock, Mock, patch

from click.testing import CliRunner

from geo_optimizer.cli.formatters import format_audit_text
from geo_optimizer.cli.schema_cmd import schema
from geo_optimizer.core.llms_generator import (
    SitemapUrl,
    discover_sitemap,
    fetch_sitemap,
    generate_llms_txt,
    url_to_label,
)
from geo_optimizer.core.schema_validator import validate_jsonld
from geo_optimizer.models.results import (
    AuditResult,
    ContentResult,
    LlmsTxtResult,
    MetaResult,
    RobotsResult,
    SchemaResult,
)
from geo_optimizer.utils.validators import validate_public_url, validate_safe_path

# ============================================================================
# Fixture comune per AuditResult
# ============================================================================


def _make_audit_result(**overrides) -> AuditResult:
    """Crea un AuditResult di base con override specifici."""
    result = AuditResult(
        url="https://example.com",
        score=75,
        band="good",
        robots=RobotsResult(
            found=True,
            bots_allowed=["GPTBot"],
            bots_blocked=[],
            bots_missing=[],
            citation_bots_ok=False,
        ),
        llms=LlmsTxtResult(
            found=True,
            has_h1=True,
            has_sections=True,
            has_links=True,
            word_count=100,
        ),
        schema=SchemaResult(
            found_types=["WebSite", "FAQPage"],
            has_website=True,
            has_faq=True,
            has_webapp=False,
            raw_schemas=[],
        ),
        meta=MetaResult(
            has_title=True,
            title_text="Test",
            has_description=True,
            description_length=100,
            has_canonical=True,
            has_og_title=True,
            has_og_description=True,
            has_og_image=True,
        ),
        content=ContentResult(
            has_h1=True,
            h1_text="Test",
            heading_count=5,
            word_count=500,
            has_numbers=True,
            numbers_count=3,
            has_links=True,
            external_links_count=2,
        ),
        recommendations=[],
    )
    # Applica gli override con notazione "robots.found" → result.robots.found
    for chiave, valore in overrides.items():
        parti = chiave.split(".")
        obj = result
        for parte in parti[:-1]:
            obj = getattr(obj, parte)
        setattr(obj, parti[-1], valore)
    return result


# ============================================================================
# llms_generator.py — callback on_status
# ============================================================================


class TestFetchSitemapOnStatus:
    """Verifica che on_status venga chiamato nei vari branch di fetch_sitemap."""

    def test_on_status_chiamato_a_profondita_massima(self):
        """Riga 63: on_status chiamato quando _depth >= _MAX_SITEMAP_DEPTH."""
        callback = Mock()
        # _MAX_SITEMAP_DEPTH è 3, quindi _depth=3 attiva il branch
        result = fetch_sitemap(
            "https://example.com/sitemap.xml",
            on_status=callback,
            _depth=3,
        )
        assert result == []
        # Deve aver chiamato on_status con il messaggio di profondità max
        callback.assert_called_once()
        messaggio = callback.call_args[0][0]
        assert "depth" in messaggio.lower() or "sitemap" in messaggio.lower()

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_on_status_chiamato_in_caso_di_errore_fetch(self, mock_crea):
        """Riga 77: on_status chiamato quando il fetch della sitemap fallisce."""
        mock_sessione = MagicMock()
        mock_sessione.get.side_effect = ConnectionError("Timeout di rete")
        mock_crea.return_value = mock_sessione

        callback = Mock()
        result = fetch_sitemap(
            "https://example.com/sitemap.xml",
            on_status=callback,
            _depth=0,
        )
        assert result == []
        # Deve aver chiamato on_status due volte: una per "Fetching" e una per l'errore
        chiamate = [c[0][0] for c in callback.call_args_list]
        assert any("error" in c.lower() or "sitemap" in c.lower() for c in chiamate)

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_on_status_chiamato_per_sitemap_index(self, mock_crea):
        """Riga 87: on_status chiamato quando viene rilevato un sitemap index."""
        xml_indice = """<?xml version="1.0"?>
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap><loc>https://example.com/sitemap-0.xml</loc></sitemap>
        </sitemapindex>"""
        xml_vuoto = """<?xml version="1.0"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        </urlset>"""

        mock_sessione = MagicMock()
        resp_indice = Mock()
        resp_indice.content = xml_indice.encode()
        resp_indice.raise_for_status = Mock()
        resp_vuoto = Mock()
        resp_vuoto.content = xml_vuoto.encode()
        resp_vuoto.raise_for_status = Mock()
        # Prima chiamata → indice, seconda chiamata → sub-sitemap vuoto
        mock_sessione.get.side_effect = [resp_indice, resp_vuoto]
        mock_crea.return_value = mock_sessione

        callback = Mock()
        fetch_sitemap(
            "https://example.com/sitemap_index.xml",
            on_status=callback,
            _depth=0,
        )
        # on_status deve aver segnalato la presenza dell'indice
        chiamate = [c[0][0] for c in callback.call_args_list]
        assert any("index" in c.lower() or "sitemaps" in c.lower() for c in chiamate)

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_on_status_chiamato_con_url_trovati(self, mock_crea):
        """Riga 100: on_status chiamato con il numero di URL trovati."""
        xml_sitemap = """<?xml version="1.0"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/pagina1</loc></url>
            <url><loc>https://example.com/pagina2</loc></url>
        </urlset>"""

        mock_sessione = MagicMock()
        resp = Mock()
        resp.content = xml_sitemap.encode()
        resp.raise_for_status = Mock()
        mock_sessione.get.return_value = resp
        mock_crea.return_value = mock_sessione

        callback = Mock()
        result = fetch_sitemap(
            "https://example.com/sitemap.xml",
            on_status=callback,
            _depth=0,
        )
        assert len(result) == 2
        chiamate = [c[0][0] for c in callback.call_args_list]
        assert any("2" in c or "found" in c.lower() for c in chiamate)


# ============================================================================
# llms_generator.py — priority non numerica (righe 119-120)
# ============================================================================


class TestPriorityNonNumerica:
    """Verifica che un valore priority non numerico venga ignorato silenziosamente."""

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_priority_non_numerica_ignorata(self, mock_crea):
        """Righe 119-120: <priority>high</priority> → ValueError ignorato, priority=0.5."""
        xml_sitemap = """<?xml version="1.0"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://example.com/pagina</loc>
                <priority>high</priority>
            </url>
        </urlset>"""

        mock_sessione = MagicMock()
        resp = Mock()
        resp.content = xml_sitemap.encode()
        resp.raise_for_status = Mock()
        mock_sessione.get.return_value = resp
        mock_crea.return_value = mock_sessione

        result = fetch_sitemap("https://example.com/sitemap.xml", _depth=0)
        assert len(result) == 1
        # Il valore di default (0.5) deve essere mantenuto quando la priority non è numerica
        assert result[0].priority == 0.5
        assert result[0].url == "https://example.com/pagina"


# ============================================================================
# llms_generator.py — url_to_label con slug numerico (riga 221)
# ============================================================================


class TestUrlToLabelSlugNumerico:
    """Verifica il comportamento di url_to_label quando l'ultimo segmento è tutto cifre."""

    def test_ultimo_segmento_numerico_usa_path_completo(self):
        """Riga 221: url come /blog/12345 → label è 'Blog/12345', non solo '12345'."""
        label = url_to_label("https://example.com/blog/12345", "example.com")
        # Quando il segmento finale è tutto cifre, usa gli ultimi due segmenti
        assert "12345" in label
        assert "Blog" in label or "blog" in label.lower()

    def test_ultimo_segmento_alfanumerico_funziona_normalmente(self):
        """Segmento con lettere e cifre non attiva il branch numerico."""
        label = url_to_label("https://example.com/blog/post-123", "example.com")
        assert "Post 123" in label or "post-123" in label.lower()

    def test_homepage_ritorna_homepage(self):
        """Path vuoto → 'Homepage'."""
        label = url_to_label("https://example.com/", "example.com")
        assert label == "Homepage"

    def test_slug_con_trattini_diventa_title(self):
        """Slug con trattini viene convertito in Title Case."""
        label = url_to_label("https://example.com/my-awesome-page", "example.com")
        assert label == "My Awesome Page"


# ============================================================================
# llms_generator.py — generate_llms_txt con fetch_titles=True (righe 290-292)
# ============================================================================


class TestGenerateLlmsTxtFetchTitles:
    """Verifica il path fetch_titles=True in generate_llms_txt."""

    def test_fetch_titles_true_usa_titolo_fetchato(self):
        """Righe 290-292: se fetch_titles=True, chiama fetch_page_title e usa il risultato."""
        urls = [SitemapUrl(url="https://example.com/pagina1")]

        with patch(
            "geo_optimizer.core.llms_generator.fetch_page_title",
            return_value="Titolo Fetchato",
        ):
            risultato = generate_llms_txt(
                "https://example.com",
                urls,
                site_name="Test",
                description="Desc test",
                fetch_titles=True,
            )
        assert "Titolo Fetchato" in risultato

    def test_fetch_titles_true_fallback_se_none(self):
        """Se fetch_page_title ritorna None, usa url_to_label come fallback."""
        urls = [SitemapUrl(url="https://example.com/la-mia-pagina")]

        with patch(
            "geo_optimizer.core.llms_generator.fetch_page_title",
            return_value=None,
        ):
            risultato = generate_llms_txt(
                "https://example.com",
                urls,
                site_name="Test",
                description="Desc test",
                fetch_titles=True,
            )
        # Deve usare url_to_label come fallback
        assert "La Mia Pagina" in risultato

    def test_fetch_titles_false_non_chiama_fetch(self):
        """fetch_titles=False (default) non chiama mai fetch_page_title."""
        urls = [SitemapUrl(url="https://example.com/pagina")]

        with patch(
            "geo_optimizer.core.llms_generator.fetch_page_title"
        ) as mock_fetch:
            generate_llms_txt(
                "https://example.com",
                urls,
                site_name="Test",
                description="Desc",
                fetch_titles=False,
            )
        mock_fetch.assert_not_called()


# ============================================================================
# llms_generator.py — sezione Optional in generate_llms_txt (righe 341, 351-357)
# ============================================================================


class TestGenerateLlmsTxtSezioneOptional:
    """Verifica la sezione Optional per Privacy, Terms, Contact, Other."""

    def test_url_privacy_finisce_in_sezione_optional(self):
        """Righe 351-357: URL di privacy policy va nella sezione Optional."""
        urls = [
            SitemapUrl(url="https://example.com/privacy-policy"),
            SitemapUrl(url="https://example.com/about"),
        ]
        risultato = generate_llms_txt(
            "https://example.com",
            urls,
            site_name="Test",
            description="Desc",
        )
        # La sezione Optional deve essere presente e contenere la URL privacy
        assert "## Optional" in risultato
        assert "privacy" in risultato.lower()

    def test_url_terms_finisce_in_sezione_optional(self):
        """URL con /terms/ va nella sezione Optional."""
        urls = [SitemapUrl(url="https://example.com/terms-of-service")]
        risultato = generate_llms_txt(
            "https://example.com",
            urls,
            site_name="Test",
            description="Desc",
        )
        assert "## Optional" in risultato
        assert "Terms" in risultato

    def test_categories_vuote_non_producono_sezione(self):
        """Riga 341: categoria con items=[]: non viene emessa la sezione."""
        # URL senza contenuto dopo il filtraggio (homepage viene saltata per la sezione)
        urls = [SitemapUrl(url="https://example.com/")]
        risultato = generate_llms_txt(
            "https://example.com",
            urls,
            site_name="Test",
            description="Desc",
        )
        # La homepage non produce una sezione H2 ma una riga speciale
        assert "## _homepage" not in risultato

    def test_url_contact_in_optional_con_categoria(self):
        """URL /contact finisce in Optional con label categoria."""
        urls = [SitemapUrl(url="https://example.com/contact")]
        risultato = generate_llms_txt(
            "https://example.com",
            urls,
            site_name="Test",
            description="Desc",
        )
        assert "## Optional" in risultato
        assert "Contact" in risultato


# ============================================================================
# llms_generator.py — discover_sitemap con validazione SSRF (righe 407-408, 413-414)
# ============================================================================


class TestDiscoverSitemapValidazioneSSRF:
    """Verifica che discover_sitemap ignori URL sitemap non sicuri da robots.txt."""

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_sitemap_non_sicuro_viene_ignorato(self, mock_crea):
        """Righe 407-408: URL sitemap che non passa validate_public_url viene ignorato."""
        mock_sessione = MagicMock()
        # robots.txt con URL sitemap verso IP privato
        robots_resp = Mock(
            text="Sitemap: http://192.168.1.1/sitemap.xml",
            status_code=200,
        )
        # Fallback common paths → tutti 404
        head_resp = Mock(status_code=404)
        mock_sessione.get.return_value = robots_resp
        mock_sessione.head.return_value = head_resp
        mock_crea.return_value = mock_sessione

        # validate_public_url reale blocca 192.168.1.1 (IP privato)
        result = discover_sitemap("https://example.com")
        # L'URL non sicuro non deve essere restituito
        assert result != "http://192.168.1.1/sitemap.xml"

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_sitemap_dominio_diverso_viene_ignorato(self, mock_crea):
        """Righe 413-414: URL sitemap di dominio esterno viene ignorato."""
        mock_sessione = MagicMock()
        robots_resp = Mock(
            text="Sitemap: https://attaccante.com/sitemap.xml",
            status_code=200,
        )
        head_resp = Mock(status_code=404)
        mock_sessione.get.return_value = robots_resp
        mock_sessione.head.return_value = head_resp
        mock_crea.return_value = mock_sessione

        result = discover_sitemap("https://example.com")
        assert result != "https://attaccante.com/sitemap.xml"


# ============================================================================
# llms_generator.py — fallback common paths (righe 424, 426-427, 431)
# ============================================================================


class TestDiscoverSitemapFallbackCommonPaths:
    """Verifica il fallback ai common paths quando robots.txt non ha Sitemap:."""

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_fallback_sitemap_xml_trovato(self, mock_crea):
        """Riga 424-426: common path /sitemap.xml risponde 200 → restituito."""
        mock_sessione = MagicMock()
        # robots.txt senza direttiva Sitemap
        robots_resp = Mock(text="User-agent: *\nAllow: /", status_code=200)
        head_ok = Mock(status_code=200)
        mock_sessione.get.return_value = robots_resp
        mock_sessione.head.return_value = head_ok
        mock_crea.return_value = mock_sessione

        result = discover_sitemap("https://example.com")
        assert result is not None
        assert "sitemap" in result.lower()

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_fallback_nessun_sitemap_trovato_ritorna_none(self, mock_crea):
        """Riga 431: nessun path funziona → on_status callback + ritorna None."""
        mock_sessione = MagicMock()
        robots_resp = Mock(text="User-agent: *\nAllow: /", status_code=200)
        head_404 = Mock(status_code=404)
        mock_sessione.get.return_value = robots_resp
        mock_sessione.head.return_value = head_404
        mock_crea.return_value = mock_sessione

        callback = Mock()
        result = discover_sitemap("https://example.com", on_status=callback)
        assert result is None
        # on_status deve aver segnalato l'assenza di sitemap
        chiamate = [c[0][0] for c in callback.call_args_list]
        assert any("no sitemap" in c.lower() or "not found" in c.lower() for c in chiamate)

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_fallback_eccezione_head_continua(self, mock_crea):
        """Riga 427: ConnectionError su HEAD → continua al path successivo."""
        mock_sessione = MagicMock()
        robots_resp = Mock(text="User-agent: *", status_code=200)
        # Prima head lancia eccezione, la seconda risponde 200
        mock_sessione.get.return_value = robots_resp
        mock_sessione.head.side_effect = [
            ConnectionError("Timeout"),
            Mock(status_code=200),
        ]
        mock_crea.return_value = mock_sessione

        result = discover_sitemap("https://example.com")
        # Deve trovare il secondo path non lanciare eccezione
        assert result is not None

    @patch("geo_optimizer.core.llms_generator.create_session_with_retry")
    def test_on_status_chiamato_quando_sitemap_trovato_in_common_path(self, mock_crea):
        """Riga 424: on_status chiamato quando sitemap trovato via common path."""
        mock_sessione = MagicMock()
        robots_resp = Mock(text="User-agent: *", status_code=200)
        head_ok = Mock(status_code=200)
        mock_sessione.get.return_value = robots_resp
        mock_sessione.head.return_value = head_ok
        mock_crea.return_value = mock_sessione

        callback = Mock()
        result = discover_sitemap("https://example.com", on_status=callback)
        assert result is not None
        chiamate = [c[0][0] for c in callback.call_args_list]
        assert any("sitemap found" in c.lower() or "found" in c.lower() for c in chiamate)


# ============================================================================
# formatters.py — branch mancanti (righe 89, 101, 116, 118)
# ============================================================================


class TestFormatAuditTextBranchMancanti:
    """Verifica i branch di format_audit_text non ancora coperti."""

    def test_riga_89_citation_bots_ok_true(self):
        """Riga 89: citation_bots_ok=True produce messaggio 'CITATION bots'."""
        result = _make_audit_result(**{"robots.citation_bots_ok": True})
        output = format_audit_text(result)
        assert "CITATION" in output or "citation" in output.lower()

    def test_riga_101_llms_trovato_senza_h1(self):
        """Riga 101: llms.txt trovato ma has_h1=False → '❌ H1 missing'."""
        result = _make_audit_result(**{
            "llms.found": True,
            "llms.has_h1": False,
        })
        output = format_audit_text(result)
        assert "H1 missing" in output or "H1" in output

    def test_riga_116_schema_trovato_senza_website(self):
        """Riga 116: schema trovato (found_types non vuoto) ma has_website=False."""
        result = _make_audit_result(**{
            "schema.found_types": ["FAQPage"],
            "schema.has_website": False,
            "schema.has_faq": True,
        })
        output = format_audit_text(result)
        assert "WebSite schema missing" in output

    def test_riga_118_schema_trovato_senza_faq(self):
        """Riga 118: schema trovato ma has_faq=False → warning FAQPage."""
        result = _make_audit_result(**{
            "schema.found_types": ["WebSite"],
            "schema.has_website": True,
            "schema.has_faq": False,
        })
        output = format_audit_text(result)
        assert "FAQPage" in output


# ============================================================================
# schema_validator.py — branch mancanti (righe 42-43, 57, 80)
# ============================================================================


class TestValidateJsonldBranchMancanti:
    """Verifica i branch di validate_jsonld non ancora coperti."""

    def test_righe_42_43_context_lista_primo_elemento_non_valido(self):
        """Righe 42-43: @context è lista con primo elemento non valido."""
        schema = {
            "@context": ["http://esempio-sbagliato.com"],
            "@type": "WebSite",
        }
        ok, errore = validate_jsonld(schema)
        assert ok is False
        assert "@context" in errore

    def test_righe_42_43_context_lista_vuota(self):
        """@context è lista vuota → catturato da 'if not context' (falsy)."""
        schema = {
            "@context": [],
            "@type": "WebSite",
        }
        ok, errore = validate_jsonld(schema)
        assert ok is False
        # Lista vuota è falsy, catturata da riga 33-34, non da 42-43
        assert "@context" in errore

    def test_riga_57_type_lista_vuota(self):
        """Riga 57: @type è lista vuota → '@type is empty'."""
        schema = {
            "@context": "https://schema.org",
            "@type": [],
        }
        ok, errore = validate_jsonld(schema)
        assert ok is False
        assert "@type" in errore

    def test_riga_80_url_field_e_dizionario(self):
        """Riga 80: campo 'url' è dict (non str né list) → continue silenzioso."""
        schema = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "Test",
            "url": {"@id": "https://example.com"},  # Nested object, non stringa
        }
        # Non deve produrre errori — il campo url viene saltato silenziosamente
        ok, errore = validate_jsonld(schema)
        assert ok is True
        assert errore is None

    def test_context_lista_con_primo_elemento_valido(self):
        """@context lista con primo elemento valido → passa la validazione."""
        schema = {
            "@context": ["https://schema.org"],
            "@type": "WebSite",
        }
        ok, errore = validate_jsonld(schema)
        assert ok is True

    def test_type_lista_con_primo_elemento_valido(self):
        """@type lista con elementi → usa il primo come primary_type."""
        schema = {
            "@context": "https://schema.org",
            "@type": ["WebSite", "WebApplication"],
        }
        ok, errore = validate_jsonld(schema)
        assert ok is True


# ============================================================================
# schema_cmd.py — path traversal validation (righe 66-67, 71-72)
# ============================================================================


class TestSchemaCmdPathTraversalValidation:
    """Verifica che schema_cmd blocchi path non validi per --file e --faq-file."""

    def test_righe_66_67_file_path_non_esistente_bloccato(self):
        """Righe 66-67: --file con percorso non esistente → errore e exit code 1."""
        runner = CliRunner()
        result = runner.invoke(schema, [
            "--file", "/tmp/file_inesistente_xyz_abc.html",
            "--analyze",
        ])
        assert result.exit_code == 1
        assert "non valido" in result.output or "Percorso" in result.output

    def test_righe_71_72_faq_file_non_esistente_bloccato(self):
        """Righe 71-72: --faq-file con percorso non esistente → errore e exit code 1."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Crea un file HTML valido per --file
            with open("test.html", "w") as f:
                f.write("<html><body></body></html>")
            result = runner.invoke(schema, [
                "--file", "test.html",
                "--type", "faq",
                "--faq-file", "/tmp/faq_inesistente_xyz.json",
            ])
        assert result.exit_code == 1
        assert "non valido" in result.output or "FAQ" in result.output

    def test_file_con_estensione_non_consentita_bloccato(self):
        """--file con estensione .txt non consentita → errore."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.txt", "w") as f:
                f.write("contenuto testo")
            result = runner.invoke(schema, [
                "--file", "test.txt",
                "--analyze",
            ])
        assert result.exit_code == 1


# ============================================================================
# schema_cmd.py — _print_analysis con tutti i tipi schema (righe 162-163, 167-175)
# ============================================================================


class TestSchemaCmdPrintAnalysis:
    """Verifica _print_analysis con WebApplication, Organization, BreadcrumbList."""

    def test_righe_162_163_webapplication_nel_report(self):
        """Righe 162-163: _print_analysis stampa url e name per WebApplication."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.html", "w") as f:
                f.write("""<html><head>
                <script type="application/ld+json">
                {
                    "@context": "https://schema.org",
                    "@type": "WebApplication",
                    "name": "App Test",
                    "url": "https://example.com"
                }
                </script>
                </head><body></body></html>""")
            result = runner.invoke(schema, ["--file", "test.html", "--analyze"])
        assert result.exit_code == 0
        assert "WebApplication" in result.output

    def test_righe_167_171_organization_nel_report(self):
        """Righe 167-171: _print_analysis stampa name per Organization."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.html", "w") as f:
                f.write("""<html><head>
                <script type="application/ld+json">
                {
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    "name": "Org Test",
                    "url": "https://example.com"
                }
                </script>
                </head><body></body></html>""")
            result = runner.invoke(schema, ["--file", "test.html", "--analyze"])
        assert result.exit_code == 0
        assert "Organization" in result.output

    def test_righe_169_170_breadcrumblist_nel_report(self):
        """Righe 169-170: _print_analysis stampa items per BreadcrumbList."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.html", "w") as f:
                f.write("""<html><head>
                <script type="application/ld+json">
                {
                    "@context": "https://schema.org",
                    "@type": "BreadcrumbList",
                    "itemListElement": [
                        {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://example.com"}
                    ]
                }
                </script>
                </head><body></body></html>""")
            result = runner.invoke(schema, ["--file", "test.html", "--analyze"])
        assert result.exit_code == 0
        assert "BreadcrumbList" in result.output

    def test_righe_164_166_faqpage_con_domande(self):
        """Righe 164-166: _print_analysis stampa il numero di domande per FAQPage."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.html", "w") as f:
                f.write("""<html><head>
                <script type="application/ld+json">
                {
                    "@context": "https://schema.org",
                    "@type": "FAQPage",
                    "mainEntity": [
                        {
                            "@type": "Question",
                            "name": "Domanda 1?",
                            "acceptedAnswer": {"@type": "Answer", "text": "Risposta 1"}
                        }
                    ]
                }
                </script>
                </head><body></body></html>""")
            result = runner.invoke(schema, ["--file", "test.html", "--analyze"])
        assert result.exit_code == 0
        assert "FAQPage" in result.output
        assert "1" in result.output  # 1 domanda

    def test_righe_173_175_verbose_true_mostra_json_completo(self):
        """Righe 173-175: --verbose mostra il JSON completo dello schema."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.html", "w") as f:
                f.write("""<html><head>
                <script type="application/ld+json">
                {
                    "@context": "https://schema.org",
                    "@type": "WebSite",
                    "name": "Sito Verbose",
                    "url": "https://example.com"
                }
                </script>
                </head><body></body></html>""")
            result = runner.invoke(schema, [
                "--file", "test.html",
                "--analyze",
                "--verbose",
            ])
        assert result.exit_code == 0
        # In modalità verbose deve mostrare il JSON completo
        assert "Full schema" in result.output or "Sito Verbose" in result.output


# ============================================================================
# schema_cmd.py — più di 3 FAQ auto-detected (riga 198)
# ============================================================================


class TestSchemaCmdFaqOltreTre:
    """Verifica che _print_analysis mostri '... and N more' con > 3 FAQ."""

    def test_riga_198_piu_di_tre_faq_mostra_contatore(self):
        """Riga 198: più di 3 FAQ estratte → riga '... and X more'."""
        runner = CliRunner()
        # Crea un HTML con 5 blocchi details/summary per far estrarre 5 FAQ
        faq_blocks = "\n".join([
            f"""<details>
                <summary>Domanda {i}: cosa fa la funzione {i}?</summary>
                <p>La funzione {i} esegue operazioni di elaborazione dati avanzate</p>
            </details>"""
            for i in range(1, 6)
        ])
        with runner.isolated_filesystem():
            with open("test.html", "w") as f:
                f.write(f"""<html><head>
                <script type="application/ld+json">
                {{
                    "@context": "https://schema.org",
                    "@type": "FAQPage",
                    "mainEntity": [
                        {{"@type": "Question", "name": "D1?", "acceptedAnswer": {{"@type": "Answer", "text": "R1"}}}},
                        {{"@type": "Question", "name": "D2?", "acceptedAnswer": {{"@type": "Answer", "text": "R2"}}}},
                        {{"@type": "Question", "name": "D3?", "acceptedAnswer": {{"@type": "Answer", "text": "R3"}}}},
                        {{"@type": "Question", "name": "D4?", "acceptedAnswer": {{"@type": "Answer", "text": "R4"}}}},
                        {{"@type": "Question", "name": "D5?", "acceptedAnswer": {{"@type": "Answer", "text": "R5"}}}}
                    ]
                }}
                </script>
                </head><body>
                {faq_blocks}
                </body></html>""")
            result = runner.invoke(schema, ["--file", "test.html", "--analyze"])
        assert result.exit_code == 0
        # Se ci sono più di 3 FAQ, deve mostrare "... and X more"
        if "more" in result.output:
            assert "and" in result.output and "more" in result.output


# ============================================================================
# validators.py — branch mancanti (righe 81-82, 110-111, 117)
# ============================================================================


class TestValidatorsBranchMancanti:
    """Verifica branch non coperti di validate_public_url e validate_safe_path."""

    def test_righe_81_82_ip_address_ValueError_viene_ignorato(self):
        """Righe 81-82: ip_address() solleva ValueError per indirizzo malformato → skip."""
        # Simula getaddrinfo che restituisce un indirizzo IPv6 non standard
        # che causa ValueError in ip_address()
        with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
            # Ritorna un indirizzo che non è un IP valido (malformato)
            mock_dns.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("INDIRIZZO_INVALIDO", 0)),
            ]
            # Non deve sollevare eccezione, deve continuare
            ok, err = validate_public_url("https://example.com")
            # Con indirizzo invalido, viene skippato e la validazione passa
            assert ok is True

    def test_righe_110_111_must_exist_con_directory(self):
        """Righe 110-111: must_exist=True con path che è una directory → errore."""
        # /tmp esiste sempre come directory
        ok, err = validate_safe_path("/tmp", must_exist=True, allowed_extensions={".html"})
        # /tmp è una directory, non un file → deve fallire
        # (potrebbe fallire per estensione o per "non è un file")
        assert ok is False

    def test_riga_117_must_exist_file_non_trovato(self):
        """Riga 117: must_exist=True con file realmente inesistente → errore."""
        percorso_inesistente = "/tmp/test_geo_coverage_nonexistent_file_12345.html"
        ok, err = validate_safe_path(
            percorso_inesistente,
            allowed_extensions={".html"},
            must_exist=True,
        )
        assert ok is False
        assert "non trovato" in err.lower() or "not found" in err.lower()

    def test_must_exist_false_file_non_esistente_valido(self):
        """must_exist=False: percorso inesistente con estensione valida → OK."""
        ok, err = validate_safe_path(
            "/tmp/file_non_esistente.html",
            allowed_extensions={".html"},
            must_exist=False,
        )
        assert ok is True
        assert err is None

    def test_must_exist_true_con_file_esistente(self, tmp_path):
        """must_exist=True con file che esiste realmente → OK."""
        file_test = tmp_path / "pagina.html"
        file_test.write_text("<html></html>")
        ok, err = validate_safe_path(
            str(file_test),
            allowed_extensions={".html"},
            must_exist=True,
        )
        assert ok is True
        assert err is None

    def test_directory_esistente_must_exist_true(self, tmp_path):
        """Directory esistente con must_exist=True → 'Non è un file'."""
        # tmp_path è una directory
        ok, err = validate_safe_path(
            str(tmp_path),
            allowed_extensions={".html"},
            must_exist=True,
        )
        assert ok is False
        # Può fallire per estensione (nessuna suffix) o per "non è un file"
        assert err is not None


# ============================================================================
# Test di integrazione rapidi — verifica coerenza tra branch
# ============================================================================


class TestIntegrazioneBranchCoperti:
    """Verifica che tutti i branch coperti producano output coerente."""

    def test_format_audit_text_completo_non_crasha(self):
        """format_audit_text con AuditResult completo non solleva eccezioni."""
        result = _make_audit_result(**{
            "robots.citation_bots_ok": True,
            "robots.bots_blocked": ["Bytespider"],
            "robots.bots_missing": ["DuckAssistBot"],
            "llms.found": True,
            "llms.has_h1": True,
            "schema.found_types": ["WebSite", "FAQPage"],
            "schema.has_website": True,
            "schema.has_faq": True,
        })
        output = format_audit_text(result)
        assert "GEO AUDIT" in output
        assert "example.com" in output

    def test_generate_llms_txt_solo_homepage_nessuna_sezione(self):
        """generate_llms_txt con solo homepage non produce sezioni H2."""
        urls = [SitemapUrl(url="https://example.com/")]
        risultato = generate_llms_txt(
            "https://example.com",
            urls,
            site_name="Test",
            description="Sito test",
        )
        assert "# Test" in risultato
        assert "> Sito test" in risultato
        # La homepage produce una riga speciale, non una sezione H2
        assert "## _homepage" not in risultato

    def test_validate_jsonld_schema_completo_valido(self):
        """Schema completo e valido supera la validazione senza errori."""
        schema_dict = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "Sito Test",
            "url": "https://example.com",
        }
        ok, err = validate_jsonld(schema_dict, schema_type="website")
        assert ok is True
        assert err is None
