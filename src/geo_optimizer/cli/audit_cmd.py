"""
CLI command: geo audit

Runs the full GEO audit on a website and displays results.
"""

import sys

import click

from geo_optimizer.cli.formatters import format_audit_json, format_audit_text
from geo_optimizer.core.audit import run_full_audit
from geo_optimizer.utils.validators import validate_public_url


@click.command()
@click.option("--url", default=None, help="URL of the site to audit (e.g. https://example.com)")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "rich", "html", "github"]),
    default=None,
    help="Output format: text (default), json, rich, html, or github",
)
@click.option("--output", "output_file", default=None, help="Output file path (optional)")
@click.option("--verbose", is_flag=True, help="Show detailed check output")
@click.option("--cache", is_flag=True, help="Use local HTTP cache for faster repeated audits")
@click.option("--clear-cache", is_flag=True, help="Clear the local HTTP cache and exit")
@click.option("--config", "config_file", default=None, help="Path to .geo-optimizer.yml config file")
@click.option("--no-plugins", is_flag=True, help="Disable loading of third-party check plugins")
def audit(url, output_format, output_file, verbose, cache, clear_cache, config_file, no_plugins):
    """Audit a website's GEO (Generative Engine Optimization) readiness."""
    # Carica configurazione progetto (se disponibile)
    from geo_optimizer.models.project_config import load_config

    config_path = None
    if config_file:
        from pathlib import Path

        config_path = Path(config_file)

    project_config = load_config(config_path)

    # Applica defaults da config (CLI ha precedenza)
    if url is None:
        url = project_config.audit.url
    if output_format is None:
        output_format = project_config.audit.format or "text"
    if output_file is None:
        output_file = project_config.audit.output
    if not cache:
        cache = project_config.audit.cache

    if not url and not clear_cache:
        raise click.UsageError("Manca l'opzione '--url'. Specificala via CLI o in .geo-optimizer.yml")

    # Gestione --clear-cache
    if clear_cache:
        from geo_optimizer.utils.cache import FileCache

        fc = FileCache()
        count = fc.clear()
        click.echo(f"✅ Cache svuotata ({count} file rimossi)")
        return

    # Carica plugin (se non disabilitati)
    if not no_plugins:
        from geo_optimizer.core.registry import CheckRegistry

        CheckRegistry.load_entry_points()

    # Validazione anti-SSRF: blocca URL verso reti private/interne
    safe, reason = validate_public_url(url if url.startswith(("http://", "https://")) else f"https://{url}")
    if not safe:
        click.echo(f"\n❌ URL non sicuro: {reason}", err=True)
        sys.exit(1)

    try:
        result = run_full_audit(url, use_cache=cache)
    except SystemExit:
        raise
    except Exception as e:
        if output_format == "json":
            import json

            error_data = {"error": str(e), "url": url}
            click.echo(json.dumps(error_data, indent=2))
        else:
            click.echo(f"\n❌ ERROR: {e}", err=True)
        sys.exit(1)

    if output_format == "json":
        output = format_audit_json(result)
    elif output_format == "rich":
        from geo_optimizer.cli.rich_formatter import format_audit_rich, is_rich_available

        if is_rich_available():
            output = format_audit_rich(result)
        else:
            click.echo("⚠️  rich non installato. Usa: pip install geo-optimizer-skill[rich]", err=True)
            output = format_audit_text(result)
    elif output_format == "html":
        from geo_optimizer.cli.html_formatter import format_audit_html

        output = format_audit_html(result)
    elif output_format == "github":
        from geo_optimizer.cli.github_formatter import format_audit_github

        output = format_audit_github(result)
    else:
        output = format_audit_text(result)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)
        click.echo(f"✅ Report written to: {output_file}")
    else:
        click.echo(output)

    return result.score
