"""
CLI command: geo llms

Generates llms.txt from an XML sitemap.
"""

import sys

import click

from geo_optimizer.core.llms_generator import (
    discover_sitemap,
    fetch_sitemap,
    generate_llms_txt,
)


@click.command()
@click.option("--base-url", required=True, help="Base URL of the site (e.g. https://example.com)")
@click.option("--output", default=None, help="Output file (default: stdout)")
@click.option("--sitemap", default=None, help="Sitemap URL (auto-detected if not specified)")
@click.option("--site-name", default=None, help="Site name")
@click.option("--description", default=None, help="Site description (blockquote)")
@click.option("--fetch-titles", is_flag=True, help="Fetch titles from pages (slow)")
@click.option("--max-per-section", type=int, default=20, help="Max URLs per section (default: 20)")
def llms(base_url, output, sitemap, site_name, description, fetch_titles, max_per_section):
    """Generate llms.txt from XML sitemap for GEO optimization."""
    base_url = base_url.rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url

    click.echo(f"\n🌐 GEO llms.txt Generator")
    click.echo(f"   Site: {base_url}")

    sitemap_url = sitemap
    if not sitemap_url:
        click.echo("\n🔍 Searching for sitemap...")
        sitemap_url = discover_sitemap(base_url, on_status=lambda msg: click.echo(f"   {msg}"))

    if not sitemap_url:
        click.echo("❌ No sitemap found. Specify --sitemap manually.")
        site_label = site_name or base_url.split("//")[1].split(".")[0].title()
        desc = description or f"Website available at {base_url}"
        minimal = f"# {site_label}\n\n> {desc}\n\n## Main Pages\n\n- [Homepage]({base_url})\n"
        if output:
            with open(output, "w") as f:
                f.write(minimal)
            click.echo(f"✅ Minimal llms.txt written to: {output}")
        else:
            click.echo(f"\n--- llms.txt ---\n{minimal}")
        return

    click.echo("\n📥 Fetching URLs from sitemap...")
    urls = fetch_sitemap(sitemap_url, on_status=lambda msg: click.echo(f"   {msg}"))

    if not urls:
        click.echo("❌ No URLs found in sitemap")
        sys.exit(1)

    click.echo(f"   Total URLs: {len(urls)}")
    click.echo("\n📝 Generating llms.txt...")

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
        click.echo(f"\n✅ llms.txt written to: {output}")
        click.echo(f"   Size: {len(content)} bytes")
        click.echo(f"   Lines: {len(content.splitlines())}")
        click.echo(f"\n   Upload the file to: {base_url}/llms.txt")
    else:
        click.echo("\n" + "─" * 50)
        click.echo(content)
        click.echo("─" * 50)
        click.echo(f"\n✅ Save with: --output /path/to/public/llms.txt")
