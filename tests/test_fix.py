"""
Test per geo_optimizer.core.fixer e geo_optimizer.cli.fix_cmd.

Verifica la generazione di fix automatici (robots, llms, schema, meta)
e il comando CLI geo fix. Tutto mockato — zero chiamate HTTP.
"""

from unittest.mock import Mock, patch

from click.testing import CliRunner

from geo_optimizer.cli.main import cli
from geo_optimizer.core.fixer import (
    generate_llms_fix,
    generate_meta_fix,
    generate_robots_fix,
    generate_schema_fix,
    run_all_fixes,
)
from geo_optimizer.models.results import (
    AuditResult,
    ContentResult,
    LlmsTxtResult,
    MetaResult,
    RobotsResult,
    SchemaResult,
)


# ============================================================================
# FIXTURES
# ============================================================================


def _make_result(**overrides):
    """Crea un AuditResult con valori di default per i test."""
    result = AuditResult(
        url="https://example.com",
        score=30,
        band="critical",
        robots=RobotsResult(
            found=False,
        ),
        llms=LlmsTxtResult(
            found=False,
        ),
        schema=SchemaResult(
            found_types=[],
            has_website=False,
            has_faq=False,
            has_webapp=False,
        ),
        meta=MetaResult(
            has_title=False,
            has_description=False,
            has_canonical=False,
            has_og_title=False,
            has_og_description=False,
            has_og_image=False,
        ),
        content=ContentResult(
            has_h1=False,
        ),
        recommendations=["Add robots.txt", "Add llms.txt"],
    )
    for key, value in overrides.items():
        parts = key.split(".")
        obj = result
        for part in parts[:-1]:
            obj = getattr(obj, part)
        setattr(obj, parts[-1], value)
    return result


def _make_optimized_result():
    """Crea un AuditResult con tutto ottimizzato (nessun fix necessario)."""
    return _make_result(**{
        "score": 95,
        "band": "excellent",
        "robots.found": True,
        "robots.bots_allowed": ["GPTBot", "ClaudeBot", "PerplexityBot"],
        "robots.bots_missing": [],
        "robots.citation_bots_ok": True,
        "robots.citation_bots_explicit": True,
        "llms.found": True,
        "llms.has_h1": True,
        "llms.has_description": True,
        "llms.has_sections": True,
        "llms.has_links": True,
        "schema.has_website": True,
        "schema.has_faq": True,
        "schema.found_types": ["WebSite", "FAQPage", "Organization"],
        "meta.has_title": True,
        "meta.has_description": True,
        "meta.has_canonical": True,
        "meta.has_og_title": True,
        "meta.has_og_description": True,
        "meta.has_og_image": True,
    })


# ============================================================================
# TEST: generate_robots_fix
# ============================================================================


class TestGenerateRobotsFix:
    """Test per la generazione di fix robots.txt."""

    def test_robots_non_trovato_genera_file_completo(self):
        """Se robots.txt non esiste, genera file completo con tutti i bot."""
        result = _make_result()
        fix = generate_robots_fix(result, "https://example.com")

        assert fix is not None
        assert fix.category == "robots"
        assert fix.action == "create"
        assert fix.file_name == "robots.txt"
        assert "GPTBot" in fix.content
        assert "ClaudeBot" in fix.content
        assert "PerplexityBot" in fix.content
        assert "User-agent: *" in fix.content
        assert "Sitemap:" in fix.content

    def test_robots_con_bot_mancanti_genera_append(self):
        """Se robots.txt esiste ma mancano bot, genera righe da appendere."""
        result = _make_result(**{
            "robots.found": True,
            "robots.bots_allowed": ["GPTBot"],
            "robots.bots_missing": ["ClaudeBot", "PerplexityBot"],
        })
        fix = generate_robots_fix(result, "https://example.com")

        assert fix is not None
        assert fix.action == "append"
        assert "ClaudeBot" in fix.content
        assert "PerplexityBot" in fix.content
        assert "GPTBot" not in fix.content  # Già presente, non va aggiunto

    def test_robots_completo_ritorna_none(self):
        """Se tutti i bot sono già consentiti, non serve fix."""
        result = _make_result(**{
            "robots.found": True,
            "robots.bots_missing": [],
        })
        fix = generate_robots_fix(result, "https://example.com")

        assert fix is None


# ============================================================================
# TEST: generate_llms_fix
# ============================================================================


class TestGenerateLlmsFix:
    """Test per la generazione di fix llms.txt."""

    @patch("geo_optimizer.core.llms_generator.fetch_sitemap", return_value=[])
    @patch("geo_optimizer.core.llms_generator.discover_sitemap", return_value=None)
    def test_llms_non_trovato_genera_file(self, mock_discover, mock_fetch):
        """Se llms.txt non esiste, genera file nuovo."""
        result = _make_result()
        fix = generate_llms_fix(result, "https://example.com")

        assert fix is not None
        assert fix.category == "llms"
        assert fix.action == "create"
        assert fix.file_name == "llms.txt"
        assert len(fix.content) > 0

    def test_llms_completo_ritorna_none(self):
        """Se llms.txt è già completo, non serve fix."""
        result = _make_result(**{
            "llms.found": True,
            "llms.has_h1": True,
            "llms.has_sections": True,
            "llms.has_links": True,
        })
        fix = generate_llms_fix(result, "https://example.com")

        assert fix is None


# ============================================================================
# TEST: generate_schema_fix
# ============================================================================


class TestGenerateSchemaFix:
    """Test per la generazione di fix schema JSON-LD."""

    def test_schema_website_mancante(self):
        """Se manca WebSite schema, lo genera."""
        result = _make_result()
        fixes = generate_schema_fix(result, "https://example.com")

        # Deve generare WebSite e Organization
        categories = [f.file_name for f in fixes]
        assert "schema-website.jsonld" in categories
        assert "schema-organization.jsonld" in categories

        website_fix = [f for f in fixes if f.file_name == "schema-website.jsonld"][0]
        assert '"@type": "WebSite"' in website_fix.content
        assert "https://example.com" in website_fix.content

    def test_schema_completo_ritorna_vuoto(self):
        """Se tutti gli schema sono presenti, ritorna lista vuota."""
        result = _make_result(**{
            "schema.has_website": True,
            "schema.found_types": ["WebSite", "Organization"],
        })
        fixes = generate_schema_fix(result, "https://example.com")

        assert len(fixes) == 0


# ============================================================================
# TEST: generate_meta_fix
# ============================================================================


class TestGenerateMetaFix:
    """Test per la generazione di fix meta tag."""

    def test_meta_mancanti_genera_tutti(self):
        """Se mancano tutti i meta tag, li genera tutti."""
        result = _make_result()
        fix = generate_meta_fix(result, "https://example.com")

        assert fix is not None
        assert fix.category == "meta"
        assert "<title>" in fix.content
        assert 'name="description"' in fix.content
        assert 'rel="canonical"' in fix.content
        assert 'og:title' in fix.content
        assert 'og:description' in fix.content
        assert 'og:image' in fix.content

    def test_meta_completo_ritorna_none(self):
        """Se tutti i meta tag sono presenti, non serve fix."""
        result = _make_optimized_result()
        fix = generate_meta_fix(result, "https://example.com")

        assert fix is None


# ============================================================================
# TEST: run_all_fixes
# ============================================================================


class TestRunAllFixes:
    """Test per l'orchestratore run_all_fixes."""

    @patch("geo_optimizer.core.llms_generator.discover_sitemap", return_value=None)
    @patch("geo_optimizer.core.llms_generator.fetch_sitemap", return_value=[])
    def test_genera_tutti_i_fix(self, mock_fetch, mock_discover):
        """Con sito completamente non ottimizzato, genera fix per ogni categoria."""
        result = _make_result()
        plan = run_all_fixes("https://example.com", audit_result=result)

        assert plan.score_before == 30
        assert plan.score_estimated_after > plan.score_before
        assert len(plan.fixes) > 0

        categories = {f.category for f in plan.fixes}
        assert "robots" in categories
        assert "llms" in categories
        assert "schema" in categories
        assert "meta" in categories

    def test_sito_ottimizzato_nessun_fix(self):
        """Con sito già ottimizzato, non genera fix."""
        result = _make_optimized_result()
        plan = run_all_fixes("https://example.com", audit_result=result)

        assert len(plan.fixes) == 0
        assert len(plan.skipped) > 0

    @patch("geo_optimizer.core.llms_generator.discover_sitemap", return_value=None)
    @patch("geo_optimizer.core.llms_generator.fetch_sitemap", return_value=[])
    def test_filtro_only(self, mock_fetch, mock_discover):
        """Il filtro --only limita le categorie."""
        result = _make_result()
        plan = run_all_fixes("https://example.com", audit_result=result, only={"robots"})

        categories = {f.category for f in plan.fixes}
        assert "robots" in categories
        assert "llms" not in categories
        assert "schema" not in categories
        assert "meta" not in categories


# ============================================================================
# TEST: CLI geo fix
# ============================================================================


class TestFixCommand:
    """Test per il comando CLI geo fix."""

    @patch("geo_optimizer.core.audit.run_full_audit")
    def test_fix_dry_run_mostra_preview(self, mock_audit):
        """geo fix --url URL mostra preview senza scrivere file."""
        mock_audit.return_value = _make_result()
        runner = CliRunner()

        with patch("geo_optimizer.core.llms_generator.discover_sitemap", return_value=None):
            with patch("geo_optimizer.core.llms_generator.fetch_sitemap", return_value=[]):
                result = runner.invoke(cli, ["fix", "--url", "https://example.com"])

        assert result.exit_code == 0
        assert "PREVIEW" in result.output or "Fix plan" in result.output

    @patch("geo_optimizer.core.audit.run_full_audit")
    def test_fix_apply_scrive_file(self, mock_audit, tmp_path):
        """geo fix --url URL --apply scrive i file nella directory."""
        mock_audit.return_value = _make_result()
        runner = CliRunner()

        output_dir = str(tmp_path / "geo-fixes")
        with patch("geo_optimizer.core.llms_generator.discover_sitemap", return_value=None):
            with patch("geo_optimizer.core.llms_generator.fetch_sitemap", return_value=[]):
                result = runner.invoke(cli, [
                    "fix", "--url", "https://example.com",
                    "--apply", "--output-dir", output_dir,
                ])

        assert result.exit_code == 0
        # Verifica che almeno un file sia stato scritto
        from pathlib import Path
        output = Path(output_dir)
        assert output.exists()
        files = list(output.iterdir())
        assert len(files) > 0

    @patch("geo_optimizer.core.audit.run_full_audit")
    def test_fix_sito_ottimizzato(self, mock_audit):
        """geo fix su sito già ottimizzato mostra messaggio positivo."""
        mock_audit.return_value = _make_optimized_result()
        runner = CliRunner()

        result = runner.invoke(cli, ["fix", "--url", "https://example.com"])

        assert result.exit_code == 0
        assert "No fixes needed" in result.output

    def test_fix_url_non_sicuro(self):
        """geo fix con URL locale viene bloccato."""
        runner = CliRunner()
        result = runner.invoke(cli, ["fix", "--url", "http://169.254.169.254/metadata"])

        assert result.exit_code != 0

    def test_fix_only_invalido(self):
        """geo fix --only invalido mostra errore."""
        runner = CliRunner()
        result = runner.invoke(cli, ["fix", "--url", "https://example.com", "--only", "invalido"])

        assert result.exit_code != 0
        assert "Invalid categories" in result.output

    def test_fix_help(self):
        """geo fix --help funziona."""
        runner = CliRunner()
        result = runner.invoke(cli, ["fix", "--help"])

        assert result.exit_code == 0
        assert "--url" in result.output
        assert "--apply" in result.output
        assert "--dry-run" in result.output
