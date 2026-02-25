"""
Test per le fix P0 di sicurezza e stabilità.

Copre:
- #1 SSRF: validate_public_url blocca IP privati e host interni
- #2 JSON Injection: fill_template esegue escape sicuro dei valori
- #3 XSS </script>: schema_to_html_tag esegue escape di </
- #4 script.string None: audit_schema gestisce tag script senza .string
- #5 Scoring: formatters._*_score() usano costanti SCORING
- #6 Domain match: url_belongs_to_domain previene bypass con substring
- #7 Versione PEP 440: __version__ conforme
"""

import json
from unittest.mock import patch, MagicMock

import pytest
from bs4 import BeautifulSoup

from geo_optimizer.utils.validators import (
    validate_public_url,
    validate_safe_path,
    url_belongs_to_domain,
)
from geo_optimizer.core.schema_injector import fill_template, schema_to_html_tag
from geo_optimizer.core.audit import audit_schema
from geo_optimizer.cli.formatters import (
    _robots_score,
    _llms_score,
    _schema_score,
    _meta_score,
    _content_score,
)
from geo_optimizer.models.config import SCORING
from geo_optimizer.models.results import AuditResult


# ============================================================================
# #1 — SSRF: validate_public_url
# ============================================================================


class TestValidatePublicUrl:
    """Test anti-SSRF: blocca IP privati/riservati, host interni."""

    def test_url_pubblica_valida(self):
        """URL pubblica con DNS risolvibile passa la validazione."""
        # Uso un mock per evitare DNS reale nei test
        with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("93.184.216.34", 0)),
            ]
            ok, err = validate_public_url("https://example.com")
            assert ok is True
            assert err is None

    def test_blocca_localhost(self):
        ok, err = validate_public_url("http://localhost/admin")
        assert ok is False
        assert "non consentito" in err.lower() or "Host" in err

    def test_blocca_ip_privato_rfc1918(self):
        ok, err = validate_public_url("http://192.168.1.1/secret")
        assert ok is False

    def test_blocca_cloud_metadata(self):
        ok, err = validate_public_url("http://169.254.169.254/latest/meta-data/")
        assert ok is False

    def test_blocca_schema_non_consentito(self):
        ok, err = validate_public_url("file:///etc/passwd")
        assert ok is False
        assert "Schema non consentito" in err

    def test_blocca_ftp(self):
        ok, err = validate_public_url("ftp://internal.server/data")
        assert ok is False

    def test_blocca_credenziali_embedded(self):
        ok, err = validate_public_url("https://user:pass@example.com")
        assert ok is False
        assert "credenziali" in err.lower()

    def test_blocca_dns_risolve_a_ip_privato(self):
        """DNS rebinding: hostname pubblico che risolve a IP privato."""
        with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("10.0.0.1", 0)),
            ]
            ok, err = validate_public_url("https://evil.example.com")
            assert ok is False
            assert "rete privata" in err.lower()

    def test_dns_non_risolvibile_passa(self):
        """DNS non risolvibile non è un errore di sicurezza."""
        import socket
        with patch("geo_optimizer.utils.validators.socket.getaddrinfo") as mock_dns:
            mock_dns.side_effect = socket.gaierror("Name resolution failed")
            ok, err = validate_public_url("https://nonexistent.example.com")
            assert ok is True

    def test_blocca_loopback_ipv4(self):
        ok, err = validate_public_url("http://127.0.0.1:8080/admin")
        assert ok is False

    def test_blocca_metadata_google_internal(self):
        ok, err = validate_public_url("http://metadata.google.internal/computeMetadata/v1/")
        assert ok is False

    def test_hostname_mancante(self):
        ok, err = validate_public_url("https://")
        assert ok is False
        assert "Hostname" in err


# ============================================================================
# #2 — JSON Injection: fill_template con escape sicuro
# ============================================================================


class TestFillTemplateInjection:
    """Test anti-injection: fill_template esegue escape dei caratteri speciali."""

    def test_valore_con_virgolette(self):
        """Le virgolette nel valore non rompono il JSON."""
        template = {"name": "{{name}}"}
        values = {"name": 'Test "quoted" value'}
        result = fill_template(template, values)
        assert result["name"] == 'Test "quoted" value'

    def test_valore_con_backslash(self):
        """I backslash nel valore non causano escape spurii."""
        template = {"path": "{{path}}"}
        values = {"path": "C:\\Users\\test"}
        result = fill_template(template, values)
        assert result["path"] == "C:\\Users\\test"

    def test_valore_con_newline(self):
        """I newline nel valore vengono gestiti correttamente."""
        template = {"desc": "{{desc}}"}
        values = {"desc": "Line 1\nLine 2"}
        result = fill_template(template, values)
        assert result["desc"] == "Line 1\nLine 2"

    def test_valore_con_injection_json(self):
        """Tentativo di injection JSON tramite chiusura stringa + nuova chiave."""
        template = {"name": "{{name}}", "url": "{{url}}"}
        malicious = '", "injected": "evil", "x": "'
        values = {"name": malicious, "url": "https://safe.com"}
        result = fill_template(template, values)
        # Il valore maligno deve essere trattato come stringa letterale
        assert result["name"] == malicious
        assert "injected" not in result  # Nessuna chiave iniettata

    def test_valore_none(self):
        """None viene convertito in stringa vuota."""
        template = {"name": "{{name}}"}
        values = {"name": None}
        result = fill_template(template, values)
        assert result["name"] == ""

    def test_placeholder_in_struttura_annidata(self):
        """Placeholder in oggetti annidati funzionano correttamente."""
        template = {"author": {"@type": "Person", "name": "{{author}}"}}
        values = {"author": "Juan 'Camilo' Auriti"}
        result = fill_template(template, values)
        assert result["author"]["name"] == "Juan 'Camilo' Auriti"


# ============================================================================
# #3 — XSS: schema_to_html_tag esegue escape di </script>
# ============================================================================


class TestSchemaXssEscape:
    """Test anti-XSS: escape di '</' nel JSON-LD previene chiusura tag prematura."""

    def test_escape_closing_script(self):
        """'</script>' nel valore viene escaped a '<\\/script>'."""
        schema = {
            "@type": "WebSite",
            "description": "Test </script><script>alert('xss')</script>",
        }
        html = schema_to_html_tag(schema)
        # Il JSON-LD non deve contenere '</script>' letterale
        assert "</script>" not in html.split("\n", 1)[1].rsplit("\n", 1)[0]
        # Ma deve contenere la versione escaped
        assert r"<\/script>" in html

    def test_escape_generic_closing_tag(self):
        """Qualsiasi '</' viene escaped, non solo </script>."""
        schema = {"content": "Test </div> content"}
        html = schema_to_html_tag(schema)
        assert r"<\/div>" in html
        assert "</div>" not in html.split("\n", 1)[1].rsplit("\n", 1)[0]

    def test_schema_senza_html_non_cambia(self):
        """Schema senza '</' non viene modificato."""
        schema = {"@type": "WebSite", "name": "Safe Name", "url": "https://example.com"}
        html = schema_to_html_tag(schema)
        assert "Safe Name" in html
        assert '<script type="application/ld+json">' in html


# ============================================================================
# #4 — script.string None: audit_schema gestisce il caso
# ============================================================================


class TestAuditSchemaScriptStringNone:
    """Test stabilità: audit_schema non crasha se script.string è None."""

    def test_script_con_figli_multipli(self):
        """Tag <script> con nodi figli multipli (script.string → None)."""
        html = """
        <html><head>
        <script type="application/ld+json">
        <!-- commento -->
        {"@type": "WebSite", "name": "Test"}
        </script>
        </head></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = audit_schema(soup, "https://example.com")
        # Deve gestire il caso senza crashare
        # Il risultato dipende da BeautifulSoup, ma non deve lanciare TypeError
        assert result is not None

    def test_script_vuoto(self):
        """Tag <script> vuoto non causa errore."""
        html = """
        <html><head>
        <script type="application/ld+json"></script>
        </head></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = audit_schema(soup, "https://example.com")
        assert result is not None
        assert len(result.found_types) == 0

    def test_script_con_solo_spazi(self):
        """Tag <script> con solo whitespace non causa errore."""
        html = """
        <html><head>
        <script type="application/ld+json">   \n\t  </script>
        </head></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = audit_schema(soup, "https://example.com")
        assert result is not None
        assert len(result.found_types) == 0

    def test_script_valido_funziona(self):
        """Script JSON-LD valido viene parsato correttamente."""
        html = """
        <html><head>
        <script type="application/ld+json">
        {"@type": "WebSite", "name": "Test", "url": "https://example.com"}
        </script>
        </head></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = audit_schema(soup, "https://example.com")
        assert "WebSite" in result.found_types
        assert result.has_website is True


# ============================================================================
# #5 — Scoring: formatters usano costanti SCORING
# ============================================================================


class TestScoringConsistency:
    """Test coerenza: i punteggi dei formatters corrispondono a SCORING."""

    def _make_result(self, **overrides) -> AuditResult:
        """Crea un AuditResult con campi personalizzati."""
        result = AuditResult(url="https://test.com")
        for key, value in overrides.items():
            parts = key.split(".")
            obj = result
            for part in parts[:-1]:
                obj = getattr(obj, part)
            setattr(obj, parts[-1], value)
        return result

    def test_robots_score_citation_ok(self):
        r = self._make_result(**{
            "robots.found": True,
            "robots.citation_bots_ok": True,
        })
        expected = SCORING["robots_found"] + SCORING["robots_citation_ok"]
        assert _robots_score(r) == expected

    def test_robots_score_some_allowed(self):
        r = self._make_result(**{
            "robots.found": True,
            "robots.bots_allowed": ["GPTBot"],
        })
        expected = SCORING["robots_found"] + SCORING["robots_some_allowed"]
        assert _robots_score(r) == expected

    def test_robots_score_found_only(self):
        r = self._make_result(**{"robots.found": True})
        assert _robots_score(r) == SCORING["robots_found"]

    def test_robots_score_zero(self):
        r = self._make_result()
        assert _robots_score(r) == 0

    def test_llms_score_full(self):
        r = self._make_result(**{
            "llms.found": True,
            "llms.has_h1": True,
            "llms.has_sections": True,
            "llms.has_links": True,
        })
        expected = (
            SCORING["llms_found"]
            + SCORING["llms_h1"]
            + SCORING["llms_sections"]
            + SCORING["llms_links"]
        )
        assert _llms_score(r) == expected

    def test_schema_score_full(self):
        r = self._make_result(**{
            "schema.has_website": True,
            "schema.has_faq": True,
            "schema.has_webapp": True,
        })
        expected = (
            SCORING["schema_website"]
            + SCORING["schema_faq"]
            + SCORING["schema_webapp"]
        )
        assert _schema_score(r) == expected

    def test_meta_score_full(self):
        r = self._make_result(**{
            "meta.has_title": True,
            "meta.has_description": True,
            "meta.has_canonical": True,
            "meta.has_og_title": True,
            "meta.has_og_description": True,
        })
        expected = (
            SCORING["meta_title"]
            + SCORING["meta_description"]
            + SCORING["meta_canonical"]
            + SCORING["meta_og"]
        )
        assert _meta_score(r) == expected

    def test_content_score_full(self):
        r = self._make_result(**{
            "content.has_h1": True,
            "content.has_numbers": True,
            "content.has_links": True,
        })
        expected = (
            SCORING["content_h1"]
            + SCORING["content_numbers"]
            + SCORING["content_links"]
        )
        assert _content_score(r) == expected

    def test_somma_totale_100(self):
        """La somma di tutti i punteggi massimi deve essere 100."""
        r = self._make_result(**{
            "robots.found": True,
            "robots.citation_bots_ok": True,
            "llms.found": True,
            "llms.has_h1": True,
            "llms.has_sections": True,
            "llms.has_links": True,
            "schema.has_website": True,
            "schema.has_faq": True,
            "schema.has_webapp": True,
            "meta.has_title": True,
            "meta.has_description": True,
            "meta.has_canonical": True,
            "meta.has_og_title": True,
            "meta.has_og_description": True,
            "content.has_h1": True,
            "content.has_numbers": True,
            "content.has_links": True,
        })
        total = (
            _robots_score(r)
            + _llms_score(r)
            + _schema_score(r)
            + _meta_score(r)
            + _content_score(r)
        )
        assert total == 100


# ============================================================================
# #6 — Domain match: url_belongs_to_domain sicuro
# ============================================================================


class TestUrlBelongsToDomain:
    """Test sicurezza: domain match esatto, no substring."""

    def test_dominio_esatto(self):
        assert url_belongs_to_domain("https://example.com/page", "example.com") is True

    def test_subdomain_legittimo(self):
        assert url_belongs_to_domain("https://blog.example.com/post", "example.com") is True

    def test_blocca_substring_match(self):
        """evil-example.com NON appartiene a example.com."""
        assert url_belongs_to_domain("https://evil-example.com/page", "example.com") is False

    def test_blocca_prefisso_match(self):
        """example.com.evil.com NON appartiene a example.com."""
        assert url_belongs_to_domain("https://example.com.evil.com/page", "example.com") is False

    def test_blocca_credenziali_embedded(self):
        assert url_belongs_to_domain("https://user@example.com/page", "example.com") is False

    def test_case_insensitive(self):
        assert url_belongs_to_domain("https://Example.COM/page", "example.com") is True

    def test_con_porta(self):
        assert url_belongs_to_domain("https://example.com:8080/page", "example.com") is True


# ============================================================================
# #7 — Versione PEP 440
# ============================================================================


class TestVersionPep440:
    """Verifica che __version__ sia conforme a PEP 440."""

    def test_version_format(self):
        from geo_optimizer import __version__
        # PEP 440: non deve contenere trattini
        assert "-" not in __version__
        # Deve essere "2.0.0b1" (o simile)
        assert "b" in __version__ or "." in __version__


# ============================================================================
# validate_safe_path
# ============================================================================


class TestValidateSafePath:
    """Test validazione percorsi file."""

    def test_percorso_valido(self):
        ok, err = validate_safe_path("/tmp/test.html", allowed_extensions={".html"})
        assert ok is True

    def test_estensione_non_consentita(self):
        ok, err = validate_safe_path("/tmp/test.exe", allowed_extensions={".html", ".htm"})
        assert ok is False
        assert "Estensione non consentita" in err

    def test_file_non_esistente_con_must_exist(self):
        ok, err = validate_safe_path("/tmp/nonexistent_file_xyz.html", must_exist=True)
        assert ok is False
        assert "non trovato" in err.lower()
