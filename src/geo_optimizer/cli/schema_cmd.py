"""
CLI command: geo schema

Manages JSON-LD schema: analyze, generate, inject into HTML, generate Astro snippets.
"""

import json
import sys

import click

from geo_optimizer.core.schema_injector import (
    analyze_html_file,
    fill_template,
    generate_astro_snippet,
    generate_faq_schema,
    inject_schema_into_html,
    schema_to_html_tag,
)
from geo_optimizer.models.config import SCHEMA_TEMPLATES
from geo_optimizer.utils.validators import validate_safe_path


@click.command()
@click.option("--file", "file_path", default=None, help="HTML file to analyze/modify")
@click.option("--type", "schema_type", type=click.Choice(list(SCHEMA_TEMPLATES.keys())),
              help="Type of schema to generate")
@click.option("--name", default=None, help="Site/application name")
@click.option("--url", default=None, help="Site URL")
@click.option("--description", default=None, help="Description")
@click.option("--author", default=None, help="Author")
@click.option("--logo-url", default=None, help="Logo URL")
@click.option("--faq-file", default=None, help="JSON file with FAQs [{question, answer}]")
@click.option("--auto-extract", is_flag=True, help="Auto-extract FAQ from HTML")
@click.option("--astro", is_flag=True, help="Generate Astro BaseLayout snippet")
@click.option("--inject", is_flag=True, help="Inject schema directly into --file")
@click.option("--no-backup", is_flag=True, help="Do not create backup before modifying")
@click.option("--no-validate", is_flag=True, help="Skip schema validation before injection")
@click.option("--analyze", is_flag=True, help="Analyze file for existing schemas")
@click.option("--verbose", is_flag=True, help="Show full schema JSON in analysis")
def schema(file_path, schema_type, name, url, description, author, logo_url,
           faq_file, auto_extract, astro, inject, no_backup, no_validate,
           analyze, verbose):
    """Manage JSON-LD schema for GEO optimization."""

    # Validazione anti-path-traversal per tutti i percorsi file
    _ALLOWED_HTML_EXT = {".html", ".htm", ".astro", ".svelte", ".vue", ".jsx", ".tsx"}
    if file_path:
        safe, reason = validate_safe_path(file_path, allowed_extensions=_ALLOWED_HTML_EXT, must_exist=True)
        if not safe:
            click.echo(f"❌ Percorso file non valido: {reason}")
            sys.exit(1)
    if faq_file:
        safe, reason = validate_safe_path(faq_file, allowed_extensions={".json"}, must_exist=True)
        if not safe:
            click.echo(f"❌ Percorso FAQ file non valido: {reason}")
            sys.exit(1)

    # Mode 1: Analyze
    if analyze:
        if not file_path:
            click.echo("❌ --file required for --analyze")
            sys.exit(1)

        analysis = analyze_html_file(file_path)
        _print_analysis(analysis, verbose=verbose)
        return

    # Mode 2: Astro snippet
    if astro:
        if not url or not name:
            click.echo("❌ --url and --name required for --astro")
            sys.exit(1)

        snippet = generate_astro_snippet(url, name)
        click.echo(snippet)
        return

    # Mode 3: Generate / inject schema
    if schema_type:
        if schema_type == "faq":
            if auto_extract and file_path:
                analysis = analyze_html_file(file_path)
                faq_items = analysis.extracted_faqs
                if not faq_items:
                    click.echo("❌ No FAQ items found in HTML")
                    sys.exit(1)
                click.echo(f"✅ Extracted {len(faq_items)} FAQ items")
                schema_dict = generate_faq_schema(faq_items)
            elif faq_file:
                with open(faq_file, "r") as f:
                    faq_items = json.load(f)
                schema_dict = generate_faq_schema(faq_items)
            else:
                click.echo("❌ --auto-extract or --faq-file required for FAQ schema")
                sys.exit(1)
        else:
            values = {
                "name": name or "",
                "url": url or "",
                "description": description or "",
                "author": author or "",
                "logo_url": logo_url or "",
            }
            schema_dict = fill_template(SCHEMA_TEMPLATES[schema_type], values)

        if inject:
            if not file_path:
                click.echo("❌ --file required for --inject")
                sys.exit(1)

            success, error = inject_schema_into_html(
                file_path,
                schema_dict,
                backup=not no_backup,
                validate=not no_validate,
            )
            if success:
                click.echo(f"✅ Schema injected into {file_path}")
            else:
                click.echo(f"❌ {error or 'Failed to inject schema'}")
                sys.exit(1)
        else:
            click.echo(schema_to_html_tag(schema_dict))
    else:
        click.echo("❌ Use --analyze, --astro, or --type to specify an action.")
        sys.exit(1)


def _print_analysis(analysis, verbose=False):
    """Pretty-print schema analysis results."""
    click.echo(f"\n{'=' * 60}")
    click.echo("  SCHEMA ANALYSIS")
    click.echo(f"{'=' * 60}\n")

    if analysis.found_schemas:
        click.echo(f"✅ Found {len(analysis.found_schemas)} schema(s):\n")
        for idx, s in enumerate(analysis.found_schemas, 1):
            schema_type = s["type"]
            data = s["data"]
            click.echo(f"   {idx}. {schema_type}")

            if schema_type == "WebSite":
                click.echo(f"      url: {data.get('url', 'N/A')}")
                click.echo(f"      name: {data.get('name', 'N/A')}")
            elif schema_type == "WebApplication":
                click.echo(f"      url: {data.get('url', 'N/A')}")
                click.echo(f"      name: {data.get('name', 'N/A')}")
            elif schema_type == "FAQPage":
                faq_count = len(data.get("mainEntity", []))
                click.echo(f"      questions: {faq_count}")
            elif schema_type == "Organization":
                click.echo(f"      name: {data.get('name', 'N/A')}")
            elif schema_type == "BreadcrumbList":
                items = len(data.get("itemListElement", []))
                click.echo(f"      items: {items}")

            if verbose:
                click.echo(f"\n      Full schema:")
                click.echo(f"      {json.dumps(data, indent=6, ensure_ascii=False)}\n")
            click.echo()
    else:
        click.echo("⚠️  No JSON-LD schemas found\n")

    if analysis.duplicates:
        click.echo("⚠️  DUPLICATE SCHEMAS DETECTED:\n")
        for schema_type, count in analysis.duplicates.items():
            click.echo(f"   • {schema_type}: {count} instances (should be 1)")
        click.echo()

    if analysis.missing:
        click.echo("💡 Suggested schemas to add:\n")
        for schema_type in analysis.missing:
            click.echo(f"   • {schema_type.upper()}")
        click.echo()

    if analysis.extracted_faqs:
        click.echo(f"📋 Auto-detected {len(analysis.extracted_faqs)} FAQ items:\n")
        for idx, faq in enumerate(analysis.extracted_faqs[:3], 1):
            q = faq["question"][:60] + "..." if len(faq["question"]) > 60 else faq["question"]
            click.echo(f"   {idx}. {q}")
        if len(analysis.extracted_faqs) > 3:
            click.echo(f"   ... and {len(analysis.extracted_faqs) - 3} more")
        click.echo()
        click.echo("   💡 Use --type faq --auto-extract --inject to add FAQPage schema")
        click.echo()
