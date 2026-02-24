"""
CLI command: geo audit

Runs the full GEO audit on a website and displays results.
"""

import sys

import click

from geo_optimizer.core.audit import run_full_audit
from geo_optimizer.cli.formatters import format_audit_json, format_audit_text


@click.command()
@click.option("--url", required=True, help="URL of the site to audit (e.g. https://example.com)")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text",
              help="Output format: text (default) or json")
@click.option("--output", "output_file", default=None, help="Output file path (optional)")
@click.option("--verbose", is_flag=True, help="Show detailed check output")
def audit(url, output_format, output_file, verbose):
    """Audit a website's GEO (Generative Engine Optimization) readiness."""
    try:
        result = run_full_audit(url)
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
    else:
        output = format_audit_text(result)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)
        click.echo(f"✅ Report written to: {output_file}")
    else:
        click.echo(output)

    return result.score
