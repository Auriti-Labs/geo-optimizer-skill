"""
CLI command: geo audit

Runs the full GEO audit on a website and displays results.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

import click

from geo_optimizer.cli.formatters import (
    format_audit_json,
    format_audit_text,
    format_batch_audit_json,
    format_batch_audit_text,
)
from geo_optimizer.core.audit import run_full_audit
from geo_optimizer.core.batch_audit import run_batch_audit
from geo_optimizer.core.history import HistoryStore, summarize_history
from geo_optimizer.models.config import (
    DEFAULT_HISTORY_RETENTION_DAYS,
    DEFAULT_SCORE_VERSION,
    resolve_user_agent_override,
    set_user_agent_override,
)
from geo_optimizer.utils.validators import normalize_url_scheme, validate_public_url


def _default_format(sitemap: str | None, output_file: str | None) -> str:
    """Dashboard rich in un terminale interattivo, testo per pipe, CI, file e batch."""
    if sitemap or output_file or os.getenv("NO_COLOR"):
        return "text"
    return "rich" if sys.stdout.isatty() else "text"


def _run_with_live_progress(run):
    """Esegue l'audit mostrando su stderr le fasi reali: spinner sulla corrente, ✓ sulle concluse."""
    from rich.console import Console

    console = Console(stderr=True)
    current = {"step": None, "t0": 0.0}

    def _finish_current():
        if current["step"]:
            elapsed = time.perf_counter() - current["t0"]
            console.print(f"  [green]✓[/] {current['step']} [dim]{elapsed:.1f}s[/]")

    with console.status("", spinner="dots") as status:

        def on_step(step: str) -> None:
            _finish_current()
            current.update(step=step, t0=time.perf_counter())
            status.update(f"[bold]{step}…[/]")

        result = run(on_step)
        if result.error:
            console.print(f"  [red]✗[/] {current['step']}")
        else:
            _finish_current()
    return result


def _history_footer(history_result, history_entry) -> str:
    """Righe dello storico locale, condivise da output text e rich."""
    lines = f"\n  Snapshots stored: {history_result.total_snapshots}"
    if history_entry and history_entry.delta is None:
        lines += "\n  Baseline snapshot saved"
    elif history_entry:
        lines += f"\n  Delta vs previous snapshot: {history_entry.delta:+d}"
    return lines


@click.command()
@click.option("--url", default=None, help="URL of the site to audit (e.g. https://example.com)")
@click.option(
    "--sitemap", default=None, help="XML sitemap URL for batch auditing (e.g. https://example.com/sitemap.xml)"
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "rich", "html", "pdf", "github", "sarif", "junit"]),
    default=None,
    help="Output format: rich (default in a terminal), text (default for pipes, files and CI), "
    "json, html, pdf, github, sarif, or junit",
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
    "--score-version",
    type=click.Choice(["1", "2"]),
    default=str(DEFAULT_SCORE_VERSION),
    show_default=True,
    help="Scoring rubric: 2 (Google AI readiness, default) or 1 (legacy, to compare with old history)",
)
@click.option("--save-history", is_flag=True, help="Save the audit result in local GEO history")
@click.option("--regression", is_flag=True, help="Exit with code 1 if score regressed vs the previous saved snapshot")
@click.option(
    "--retention-days",
    default=DEFAULT_HISTORY_RETENTION_DAYS,
    type=click.IntRange(1),
    show_default=True,
    help="Retention window for local history snapshots (minimum 1 day)",
)
@click.option("--history-db", default=None, hidden=True, help="Override local tracking DB path")
@click.option(
    "--threshold",
    default=None,
    type=click.IntRange(0, 100),
    help="Minimum score threshold (0-100). Exit code 1 if score is below.",
)
@click.option(
    "--user-agent",
    default=None,
    help="Override the User-Agent sent when fetching the site (also via GEO_USER_AGENT). "
    "Does not affect the CDN AI-crawler check, which needs its own bot identity.",
)
def audit(
    url,
    sitemap,
    output_format,
    output_file,
    verbose,
    cache,
    clear_cache,
    config_file,
    no_plugins,
    max_urls,
    concurrency,
    score_version,
    save_history,
    regression,
    retention_days,
    history_db,
    threshold,
    user_agent,
):
    """Audit a website's GEO (Generative Engine Optimization) readiness."""
    set_user_agent_override(resolve_user_agent_override(user_agent))
    score_version = int(score_version)

    # Load project configuration (if available)
    from geo_optimizer.models.project_config import load_config

    config_path = Path(config_file) if config_file else None

    project_config = load_config(config_path)

    # Apply defaults from config (CLI takes precedence)
    if url is None:
        url = project_config.audit.url
    # output_file prima del formato: un file da config deve restare text, non ANSI
    if output_file is None:
        output_file = project_config.audit.output
    if output_format is None:
        output_format = project_config.audit.format or _default_format(sitemap, output_file)
    if not cache:
        cache = project_config.audit.cache

    # Fix #121/#144: verbose from config/CLI sets the logging level
    if not verbose:
        verbose = project_config.audit.verbose
    # Root sempre a WARNING (#144): con --verbose httpx/httpcore/urllib3 inondavano il terminale.
    # --verbose alza a DEBUG solo i log del progetto; NOTSET lo riporta al root negli altri casi.
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("geo_optimizer").setLevel(logging.DEBUG if verbose else logging.NOTSET)

    # Fix #145: --threshold takes precedence over min_score from config (YAML as fallback)
    if threshold is not None:
        min_score = threshold
    else:
        min_score = project_config.audit.min_score

    if not url and not sitemap and not clear_cache:
        raise click.UsageError("Missing '--url' or '--sitemap' option. Specify via CLI or in .geo-optimizer.yml")
    if url and sitemap:
        raise click.UsageError("Use either '--url' or '--sitemap', not both")
    if sitemap and (save_history or regression):
        raise click.UsageError("'--save-history' and '--regression' are supported only with '--url'")

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
    safe, reason = validate_public_url(normalize_url_scheme(target_url))
    if not safe:
        hint = (
            " Please use a public URL (e.g., https://example.com)."
            if "Host not allowed" in reason or "localhost" in reason or "non-public" in reason
            else ""
        )
        click.echo(f"\n❌ Unsafe URL: {reason}{hint}", err=True)
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
                score_version=score_version,
            )
            if output_format != "json":
                click.echo("✅ Batch analysis complete.\n", err=True)
        else:
            import asyncio

            _use_async = False
            if not cache:
                try:
                    import httpx  # noqa: F401

                    from geo_optimizer.core.audit import run_full_audit_async

                    _use_async = True
                except ImportError:
                    pass

            def _run(on_step=None):
                audit_kwargs = {"project_config": project_config, "on_step": on_step}
                if score_version != DEFAULT_SCORE_VERSION:
                    audit_kwargs["score_version"] = score_version
                if _use_async:
                    return asyncio.run(run_full_audit_async(url, **audit_kwargs))
                return run_full_audit(url, use_cache=cache, **audit_kwargs)

            if output_format == "rich" and sys.stderr.isatty():
                result = _run_with_live_progress(_run)
            elif output_format == "json":
                result = _run()
            else:
                # Solo le fasi reali notificate dal core, niente righe pre-stampate
                result = _run(on_step=lambda step: click.echo(f"⏳ {step}...", err=True))
                if not result.error:
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

    history_result = None
    history_entry = None
    # A transient network blip must not corrupt the trend history with a
    # fake 0/100 "critical" snapshot: --regression would then report a false
    # positive against real content (comparing against a fabricated
    # baseline), and any later real regression would be masked as an
    # "improvement" relative to that same fabricated 0.
    persist_history = bool(url and (save_history or regression) and not getattr(result, "error", None))
    if persist_history:
        store = HistoryStore(Path(history_db) if history_db else None)
        history_entry = store.save_audit_result(result, retention_days=retention_days)
        history_result = store.build_history_result(result.url, retention_days=retention_days)

    if sitemap and output_format == "json":
        output = format_batch_audit_json(result)
    elif sitemap:
        output = format_batch_audit_text(result)
    elif output_format == "json":
        if persist_history:
            import json

            data = json.loads(format_audit_json(result))
            if history_result:
                data["history"] = summarize_history(history_result)
            output = json.dumps(data, indent=2)
        else:
            output = format_audit_json(result)
    elif output_format == "rich":
        from geo_optimizer.cli.rich_formatter import format_audit_rich, is_rich_available

        if is_rich_available():
            output = format_audit_rich(result, verbose=verbose)
            if history_result:
                output += " History" + _history_footer(history_result, history_entry) + "\n"
        else:
            click.echo("⚠️  rich not installed. Use: pip install --upgrade geo-optimizer-skill", err=True)
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
        if persist_history and history_result:
            output += (
                "\n\n"
                "============================================================\n"
                "  HISTORY\n"
                "============================================================\n"
            )
            output += _history_footer(history_result, history_entry)

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

    regression_failed = bool(history_result and regression and history_result.regression_detected)

    if regression_failed and output_format != "json":
        click.echo("\n❌ Regression detected: score is lower than the previous saved snapshot", err=True)

    exit_code = 0
    if min_score > 0 and result_score < min_score:
        click.echo(
            f"\n❌ Score {result_score}/100 below minimum required ({min_score})",
            err=True,
        )
        exit_code = 1 if threshold is not None else 2
    if regression_failed:
        exit_code = 1
    if exit_code:
        sys.exit(exit_code)

    return result_score
