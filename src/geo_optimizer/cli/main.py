"""
GEO Optimizer CLI — Unified entry point.

Usage:
    geo audit --url https://example.com
    geo llms --base-url https://example.com
    geo schema --file index.html --analyze
"""

from __future__ import annotations

import click

from geo_optimizer import __version__


@click.group()
@click.version_option(version=__version__, prog_name="geo-optimizer")
@click.option(
    "--lang",
    default=None,
    envvar="GEO_LANG",
    type=click.Choice(["it", "en"], case_sensitive=False),
    help="Lingua output: it (default), en",
)
def cli(lang):
    """GEO Optimizer — Make websites visible to AI search engines."""
    if lang:
        from geo_optimizer.i18n import set_lang

        set_lang(lang)
        # gap #12: i18n strings not yet active — warn the user to avoid silent no-op
        click.echo(
            f"Note: --lang={lang} accepted. Full CLI localization is planned for a future release; "
            "output is currently in English regardless of this flag.",
            err=True,
        )


# Import and register subcommands
from geo_optimizer.cli.access_cmd import access  # noqa: E402
from geo_optimizer.cli.audit_cmd import audit  # noqa: E402
from geo_optimizer.cli.authority_cmd import authority  # noqa: E402
from geo_optimizer.cli.citations_cmd import citations  # noqa: E402
from geo_optimizer.cli.coherence_cmd import coherence  # noqa: E402
from geo_optimizer.cli.diff_cmd import diff  # noqa: E402
from geo_optimizer.cli.drift_cmd import drift  # noqa: E402
from geo_optimizer.cli.fix_cmd import fix  # noqa: E402
from geo_optimizer.cli.history_cmd import history  # noqa: E402
from geo_optimizer.cli.llms_cmd import llms  # noqa: E402
from geo_optimizer.cli.logs_cmd import logs  # noqa: E402
from geo_optimizer.cli.monitor_cmd import monitor  # noqa: E402
from geo_optimizer.cli.schema_cmd import schema  # noqa: E402
from geo_optimizer.cli.snapshots_cmd import snapshots  # noqa: E402
from geo_optimizer.cli.track_cmd import track  # noqa: E402

cli.add_command(access)
cli.add_command(audit)
cli.add_command(authority)
cli.add_command(citations)
cli.add_command(coherence)
cli.add_command(diff)
cli.add_command(drift)
cli.add_command(fix)
cli.add_command(history)
cli.add_command(llms)
cli.add_command(logs)
cli.add_command(monitor)
cli.add_command(schema)
cli.add_command(snapshots)
cli.add_command(track)


if __name__ == "__main__":
    cli()
