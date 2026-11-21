"""CLI command: geo logs."""

from __future__ import annotations

import json
from dataclasses import asdict

import click

from geo_optimizer.core.crawler_ips import fetch_ranges, load_ranges
from geo_optimizer.core.log_analyzer import analyze_log_file


@click.command(name="logs")
@click.option("--file", "log_file", required=True, type=click.Path(exists=True), help="Path to server access log")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="Output format",
)
@click.option(
    "--ip-ranges",
    "ranges_dir",
    type=click.Path(exists=True, file_okay=False),
    default=None,
    help="Folder with the vendors' published range files (gptbot.json, searchbot.json, chatgpt-user.json, googlebot.json, "
    "perplexitybot.json, perplexity-user.json, bingbot.json): checks each crawler visit by its source address, offline",
)
@click.option(
    "--fetch-ip-ranges",
    "fetch_ranges_flag",
    is_flag=True,
    help="Same check, downloading those files from the vendors' published URLs (SENDS 7 requests, no log data)",
)
def logs(log_file: str, output_format: str, ranges_dir: str | None, fetch_ranges_flag: bool) -> None:
    """Analyze server logs for AI crawler activity.

    With --ip-ranges or --fetch-ip-ranges every visit that claims a bot name is also checked against the address ranges
    its vendor publishes: verified, outside the ranges, or unverifiable when the vendor publishes none. This is an address check,
    not an RFC 9421 signature check, which access logs cannot support.
    """
    if ranges_dir and fetch_ranges_flag:
        raise click.UsageError("Use either --ip-ranges or --fetch-ip-ranges, not both")
    ranges = sources = None
    if ranges_dir:
        try:
            ranges, sources = load_ranges(ranges_dir)
        except ValueError as exc:
            raise click.UsageError(str(exc)) from exc
    elif fetch_ranges_flag:
        ranges, sources = fetch_ranges()
        if not ranges:
            raise click.ClickException(
                "No vendor range file could be fetched: " + "; ".join(s.get("error", "") for s in sources)
            )

    result = analyze_log_file(log_file, ranges=ranges, range_sources=sources)

    if output_format == "json":
        data = asdict(result)
        if result.verification is None:
            data.pop("verification")  # the output without ranges keeps exactly the keys it had
        click.echo(json.dumps(data, indent=2))
    else:
        _print_text(result)


def _print_text(result) -> None:
    """Format log analysis as human-readable text."""
    click.echo("")
    click.echo("🤖 " * 15)
    click.echo("  AI CRAWLER REPORT")
    click.echo("🤖 " * 15)
    click.echo(f"\n  File: {result.log_file}")
    click.echo(f"  Lines: {result.total_lines:,} | AI requests: {result.ai_requests:,}")
    if result.date_range_start:
        click.echo(f"  Period: {result.date_range_start} → {result.date_range_end}")

    if result.bots:
        click.echo(f"\n  {'Bot':<25} {'Visits':>8} {'Pages':>8}")
        click.echo(f"  {'─' * 25} {'─' * 8} {'─' * 8}")
        for bot in result.bots:
            click.echo(f"  {bot.bot_name:<25} {bot.visits:>8,} {bot.unique_pages:>8}")

    if result.top_pages:
        click.echo("\n  📄 Top crawled pages:")
        for i, page in enumerate(result.top_pages[:10], 1):
            bots_str = ", ".join(page.bots[:3])
            click.echo(f"  {i:>3}. {page.path} ({page.total_visits} visits — {bots_str})")

    if result.verification is not None:
        _print_verification(result.verification)

    if not result.bots:
        click.echo("\n  No AI crawler activity found in this log file.")


def _print_verification(v) -> None:
    """Format the address verification."""
    click.echo("\n  Source address check (published ranges)")
    for source in v.sources:
        where = source.get("file") or source.get("url")
        if "error" in source:
            click.echo(f"    ! {where}: {source['error']}")
        else:
            click.echo(f"    {where}: {source['prefixes']} prefixes, published {source['creation_time'] or 'n/a'}")
    click.echo(f"\n  {'Bot':<22} {'Visits':>8} {'Verified':>9} {'Outside':>8} {'No address':>11}")
    click.echo(f"  {'─' * 22} {'─' * 8} {'─' * 9} {'─' * 8} {'─' * 11}")
    for bot in v.bots:
        if bot.ranges_available:
            click.echo(
                f"  {bot.bot:<22} {bot.hits:>8,} {bot.verified:>9,} {bot.outside_ranges:>8,} {bot.no_address:>11,}"
            )
        else:
            click.echo(f"  {bot.bot:<22} {bot.hits:>8,} {'no published ranges':>29}")
    click.echo(
        f"\n  Verified {v.verified:,} · outside the ranges {v.outside_ranges:,} · unverifiable {v.unverifiable:,}"
    )
    click.echo(f"  {v.note}")
