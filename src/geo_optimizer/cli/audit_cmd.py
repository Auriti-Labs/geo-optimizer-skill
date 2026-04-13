"""
CLI command: geo audit

Runs the full GEO audit on a website and displays results.
"""

from __future__ import annotations

import logging
import sys

import click

from geo_optimizer.cli.formatters import (
    format_audit_json,
    format_audit_text,
    format_batch_audit_json,
    format_batch_audit_text,
)
from geo_optimizer.core.audit import run_full_audit
from geo_optimizer.core.batch_audit import run_batch_audit
from geo_optimizer.utils.validators import validate_public_url


@click.command()
@click.option("--url", default=None, help="URL of the site to audit (e.g. https://example.com)")
@click.option("--sitemap", default=None, help="XML sitemap URL for batch auditing (e.g. https://example.com/sitemap.xml)")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "rich", "html", "pdf", "github", "sarif", "junit"]),
    default=None,
    help="Output format: text (default), json, rich, html, pdf, github, sarif, or junit",
)
@click.option("--output", "output_file", default=None, help="Output file path (optional)")
@click.option("--verbose", is_flag=True, help="Show detailed check output")
@click.option("--cache", is_flag=True, help="Use local HTTP cache for faster repeated audits")
@click.option("--clear-cache", is_flag=True, help="Clear the local HTTP cache and exit")
@click.option("--config", "config_file", default=None, help="Path to .geo-optimizer.yml config file")
@click.option("--no-plugins", is_flag=True, help="Disable loading of third-party check plugins")
@click.option("--max-urls", default=50, type=int, show_default=True, help="Maximum number of sitemap URLs to audit")
@click.option("--concurrency", default=5, type=int, show_default=True, help="Concurrent page audits in sitemap mode")
@click.option(
    "--threshold",
    default=None,
    type=int,
    help="Minimum score threshold (0-100). Exit code 1 if score is below.",
)
def audit(url, sitemap, output_format, output_file, verbose, cache, clear_cache, config_file, no_plugins, max_urls, concurrency, threshold):
    """Audit a website's GEO (Generative Engine Optimization) readiness."""
    # Load project configuration (if available)
    from geo_optimizer.models.project_config import load_config

    config_path = None
    if config_file:
        from pathlib import Path

        config_path = Path(config_file)

    project_config = load_config(config_path)

    # Apply defaults from config (CLI takes precedence)
    if url is None:
        url = project_config.audit.url
    if output_format is None:
        output_format = project_config.audit.format or "text"
    if output_file is None:
        output_file = project_config.audit.output
    if not cache:
        cache = project_config.audit.cache

    # Fix #121/#144: verbose from config/CLI sets the logging level
    if not verbose:
        verbose = project_config.audit.verbose
    if verbose:
        # --verbose: show DEBUG logs for detailed diagnostics
        logging.basicConfig(level=logging.DEBUG)
    else:
        # Without --verbose: suppress logs below WARNING (fix #144)
        logging.basicConfig(level=logging.WARNING)

    # Fix #145: --threshold takes precedence over min_score from config (YAML as fallback)
    if threshold is not None:
        min_score = threshold
    else:
        min_score = project_config.audit.min_score

    if not url and not sitemap and not clear_cache:
        raise click.UsageError("Missing '--url' or '--sitemap' option. Specify via CLI or in .geo-optimizer.yml")
    if url and sitemap:
        raise click.UsageError("Use either '--url' or '--sitemap', not both")

    # Handle --clear-cache
    if clear_cache:
        from geo_optimizer.utils.cache import FileCache

        fc = FileCache()
        count = fc.clear()
        click.echo(f"✅ Cache cleared ({count} files removed)")
        return

    # Load plugins (if not disabled)
    if not no_plugins:
        from geo_optimizer.core.registry import CheckRegistry

        CheckRegistry.load_entry_points()

    if sitemap and output_format not in {"text", "json"}:
        raise click.UsageError("Batch audit via '--sitemap' supports only '--format text' or '--format json'")

    target_url = sitemap or url
    safe, reason = validate_public_url(target_url if target_url.startswith(("http://", "https://")) else f"https://{target_url}")
    if not safe:
        click.echo(f"\n❌ Unsafe URL: {reason}", err=True)
        sys.exit(1)

    try:
        if sitemap:
            if output_format != "json":
                click.echo("⏳ Starting GEO batch analysis from sitemap...", err=True)
                click.echo("⏳ Discovering URLs and aggregating category scores...", err=True)
            result = run_batch_audit(
                sitemap,
                use_cache=cache,
                project_config=project_config,
                max_urls=max_urls,
                concurrency=concurrency,
            )
            if output_format != "json":
                click.echo("✅ Batch analysis complete.\n", err=True)
        else:
            import asyncio

            _use_spinner = output_format == "rich"
            if _use_spinner:
                try:
                    from rich.console import Console as _RichConsole

                    _use_spinner = True
                except ImportError:
                    _use_spinner = False

            _use_async = False
            if not cache:
                try:
                    import httpx  # noqa: F401

                    from geo_optimizer.core.audit import run_full_audit_async

                    _use_async = True
                except ImportError:
                    pass

            if _use_spinner:
                _stderr = _RichConsole(stderr=True)
                with _stderr.status("[bold bright_blue]  Analyzing...[/]", spinner="dots"):
                    if _use_async:
                        result = asyncio.run(run_full_audit_async(url, project_config=project_config))
                    else:
                        result = run_full_audit(url, use_cache=cache, project_config=project_config)
            else:
                if output_format != "json":
                    click.echo("⏳ Starting GEO analysis...", err=True)
                    click.echo("⏳ Checking robots.txt and AI bot access...", err=True)
                    click.echo("⏳ Analyzing llms.txt...", err=True)
                if _use_async:
                    result = asyncio.run(run_full_audit_async(url, project_config=project_config))
                else:
                    result = run_full_audit(url, use_cache=cache, project_config=project_config)
                if output_format != "json":
                    click.echo("⏳ Analyzing JSON-LD schema, meta tags and content...", err=True)
                    click.echo("✅ Analysis complete.\n", err=True)
    except SystemExit:
        raise
    except Exception as e:
        if output_format == "json":
            import json

            # Fix #431: sanitize exception message (don't leak internal details)
            error_msg = type(e).__name__ if not str(e) else str(e).split("\n")[0][:200]
            error_data = {"error": error_msg, "url": target_url}
            click.echo(json.dumps(error_data, indent=2))
        else:
            click.echo(f"\n❌ ERROR: {type(e).__name__}", err=True)
        sys.exit(1)

    if sitemap and output_format == "json":
        output = format_batch_audit_json(result)
    elif sitemap:
        output = format_batch_audit_text(result)
    elif output_format == "json":
        output = format_audit_json(result)
    elif output_format == "rich":
        from geo_optimizer.cli.rich_formatter import format_audit_rich, is_rich_available

        if is_rich_available():
            output = format_audit_rich(result)
        else:
            click.echo("⚠️  rich not installed. Use: pip install geo-optimizer-skill[rich]", err=True)
            output = format_audit_text(result)
    elif output_format == "html":
        from geo_optimizer.cli.html_formatter import format_audit_html

        output = format_audit_html(result)
    elif output_format == "pdf":
        from geo_optimizer.cli.pdf_formatter import format_audit_pdf

        # PDF is binary: write to file and exit (doesn't go through click.echo)
        pdf_path = output_file or "geo-report.pdf"
        try:
            pdf_bytes = format_audit_pdf(result)
        except ImportError as e:
            click.echo(f"\n❌ {e}", err=True)
            sys.exit(1)
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        click.echo(f"✅ PDF report written to: {pdf_path}")

        # Check threshold for PDF output as well
        if min_score > 0 and result.score < min_score:
            click.echo(
                f"\n❌ Score {result.score}/100 below minimum required ({min_score})",
                err=True,
            )
            exit_code = 1 if threshold is not None else 2
            sys.exit(exit_code)
        return result.score
    elif output_format == "github":
        from geo_optimizer.cli.github_formatter import format_audit_github

        output = format_audit_github(result)
    elif output_format == "sarif":
        from geo_optimizer.cli.ci_formatter import format_audit_sarif

        output = format_audit_sarif(result)
    elif output_format == "junit":
        from geo_optimizer.cli.ci_formatter import format_audit_junit

        output = format_audit_junit(result)
    else:
        output = format_audit_text(result)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)
        click.echo(f"✅ Report written to: {output_file}")
    else:
        click.echo(output)

    # Fix #145/#121: exit code if score < minimum threshold
    # --threshold CLI → exit 1 (standard CI convention)
    # min_score from .geo-optimizer.yml → exit 2 (to distinguish from CLI)
    result_score = result.average_score if sitemap else result.score

    if min_score > 0 and result_score < min_score:
        click.echo(
            f"\n❌ Score {result_score}/100 below minimum required ({min_score})",
            err=True,
        )
        exit_code = 1 if threshold is not None else 2
        sys.exit(exit_code)

    return result_score
