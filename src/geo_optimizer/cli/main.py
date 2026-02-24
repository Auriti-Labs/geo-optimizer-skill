"""
GEO Optimizer CLI — Unified entry point.

Usage:
    geo audit --url https://example.com
    geo llms --base-url https://example.com
    geo schema --file index.html --analyze
"""

import click

from geo_optimizer import __version__


@click.group()
@click.version_option(version=__version__, prog_name="geo-optimizer")
def cli():
    """GEO Optimizer — Make websites visible to AI search engines."""
    pass


# Import and register subcommands
from geo_optimizer.cli.audit_cmd import audit  # noqa: E402
from geo_optimizer.cli.llms_cmd import llms  # noqa: E402
from geo_optimizer.cli.schema_cmd import schema  # noqa: E402

cli.add_command(audit)
cli.add_command(llms)
cli.add_command(schema)


if __name__ == "__main__":
    cli()
