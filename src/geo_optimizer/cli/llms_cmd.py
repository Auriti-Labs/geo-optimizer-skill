"""
CLI command: geo llms

Generates llms.txt from an XML sitemap.
"""

from __future__ import annotations

import sys

import click

from geo_optimizer.core.llms_generator import (
    check_llms_drift,
    discover_sitemap,
    fetch_sitemap,
    generate_llms_txt,
)
from geo_optimizer.models.config import resolve_user_agent_override, set_user_agent_override
from geo_optimizer.utils.validators import validate_public_url


@click.command()
@click.option("--base-url", required=True, help="Base URL of the site (e.g. https://example.com)")
@click.option("--output", default=None, help="Output file (default: stdout)")
@click.option("--sitemap", default=None, help="Sitemap URL (auto-detected if not specified)")
@click.option("--site-name", default=None, help="Site name")
@click.option("--description", default=None, help="Site description (blockquote)")
@click.option("--fetch-titles", is_flag=True, help="Fetch titles from pages (slow)")
@click.option("--max-per-section", type=int, default=20, help="Max URLs per section (default: 20)")
@click.option(
    "--user-agent",
    default=None,
    help="Override the User-Agent sent when fetching the site (also via GEO_USER_AGENT). "
    "Does not affect the CDN AI-crawler check, which needs its own bot identity.",
)
@click.option(
    "--check-drift",
    is_flag=True,
    help="Check whether an existing llms.txt still matches the current sitemap, instead of "
    "generating a new one. Exits 1 if it finds stale URLs (listed in llms.txt, gone from the sitemap).",
)
@click.option(
    "--llms-file",
    default=None,
    help="Local llms.txt file to check (with --check-drift). Default: fetch {base-url}/llms.txt live.",
)
def llms(
    base_url, output, sitemap, site_name, description, fetch_titles, max_per_section, user_agent, check_drift, llms_file
):
    """Generate llms.txt from XML sitemap for GEO optimization."""
    set_user_agent_override(resolve_user_agent_override(user_agent))

    base_url = base_url.rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url

    # Anti-SSRF validation: block URLs pointing to private/internal networks
    safe, reason = validate_public_url(base_url)
    if not safe:
        click.echo(f"\n❌ URL non sicuro: {reason}", err=True)
        sys.exit(1)

    if check_drift:
        _run_check_drift(base_url, llms_file)
        return

    # Status messages on stderr to avoid interfering with redirected output (fix #143)
    click.echo("\n🌐 GEO llms.txt Generator", err=True)
    click.echo(f"   Site: {base_url}", err=True)

    sitemap_url = sitemap
    if not sitemap_url:
        click.echo("\n🔍 Searching for sitemap...", err=True)
        sitemap_url = discover_sitemap(base_url, on_status=lambda msg: click.echo(f"   {msg}", err=True))

    if not sitemap_url:
        click.echo("❌ No sitemap found. Specify --sitemap manually.", err=True)
        site_label = site_name or base_url.split("//")[1].split(".")[0].title()
        desc = description or f"Website available at {base_url}"
        minimal = f"# {site_label}\n\n> {desc}\n\n## Main Pages\n\n- [Homepage]({base_url})\n"
        if output:
            # Fix H-12: always specify encoding to prevent corruption on Windows
            with open(output, "w", encoding="utf-8") as f:
                f.write(minimal)
            click.echo(f"✅ Minimal llms.txt written to: {output}", err=True)
        else:
            # llms.txt content goes to stdout
            click.echo(minimal)
        return

    click.echo("\n📥 Fetching URLs from sitemap...", err=True)
    urls = fetch_sitemap(sitemap_url, on_status=lambda msg: click.echo(f"   {msg}", err=True))

    if not urls:
        click.echo("❌ No URLs found in sitemap", err=True)
        sys.exit(1)

    click.echo(f"   Total URLs: {len(urls)}", err=True)
    click.echo("\n📝 Generating llms.txt...", err=True)

    content = generate_llms_txt(
        base_url=base_url,
        urls=urls,
        site_name=site_name,
        description=description,
        fetch_titles=fetch_titles,
        max_urls_per_section=max_per_section,
    )

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(content)
        click.echo(f"\n✅ llms.txt written to: {output}", err=True)
        click.echo(f"   Size: {len(content)} bytes", err=True)
        click.echo(f"   Lines: {len(content.splitlines())}", err=True)
        click.echo(f"\n   Upload the file to: {base_url}/llms.txt", err=True)
    else:
        # llms.txt content goes to stdout; decorative separator to stderr
        click.echo("\n" + "─" * 50, err=True)
        click.echo(content)
        click.echo("─" * 50, err=True)
        click.echo("\n✅ Save with: --output /path/to/public/llms.txt", err=True)


def _run_check_drift(base_url: str, llms_file: str | None) -> None:
    """Handle `geo llms --check-drift`: report stale/missing URLs and exit non-zero on drift."""
    llms_txt_content = None
    if llms_file:
        try:
            with open(llms_file, encoding="utf-8") as f:
                llms_txt_content = f.read()
        except OSError as exc:
            click.echo(f"\n❌ Could not read {llms_file}: {exc}", err=True)
            sys.exit(1)

    click.echo("\n🔍 Checking llms.txt against the current sitemap...", err=True)
    drift = check_llms_drift(
        base_url,
        llms_txt_content=llms_txt_content,
        on_status=lambda msg: click.echo(f"   {msg}", err=True),
    )

    if drift.error:
        click.echo(f"\n❌ {drift.error}", err=True)
        sys.exit(1)

    click.echo(f"\n   llms.txt URLs: {drift.llms_txt_url_count}", err=True)
    click.echo(f"   Sitemap URLs:  {drift.sitemap_url_count}", err=True)

    if drift.stale_url_count:
        click.echo(f"\n⚠️  {drift.stale_url_count} URL(s) in llms.txt are no longer in the sitemap:", err=True)
        for url in drift.stale_urls:
            click.echo(f"   - {url}", err=True)
        if drift.stale_url_count > len(drift.stale_urls):
            click.echo(f"   ... and {drift.stale_url_count - len(drift.stale_urls)} more", err=True)
    else:
        click.echo("\n✅ No stale URLs — llms.txt matches the current sitemap", err=True)

    if drift.missing_url_count:
        click.echo(f"\n💡 {drift.missing_url_count} sitemap URL(s) not yet in llms.txt:", err=True)
        for url in drift.missing_urls:
            click.echo(f"   - {url}", err=True)
        if drift.missing_url_count > len(drift.missing_urls):
            click.echo(f"   ... and {drift.missing_url_count - len(drift.missing_urls)} more", err=True)

    if drift.stale_url_count:
        sys.exit(1)
