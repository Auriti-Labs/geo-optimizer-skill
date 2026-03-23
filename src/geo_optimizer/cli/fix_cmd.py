"""
CLI command: geo fix

Genera automaticamente artefatti GEO mancanti basandosi sull'audit.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from geo_optimizer.utils.validators import validate_public_url


@click.command()
@click.option("--url", required=True, help="URL of the site to optimize")
@click.option(
    "--output-dir",
    default="./geo-fixes",
    help="Output directory for generated files (default: ./geo-fixes/)",
)
@click.option("--dry-run", is_flag=True, default=True, help="Show preview without writing (default)")
@click.option("--apply", "do_apply", is_flag=True, help="Write generated files to output directory")
@click.option(
    "--only",
    default=None,
    help="Filter categories: robots,llms,schema,meta (comma-separated)",
)
@click.option("--config", "config_file", default=None, help="Path to .geo-optimizer.yml")
def fix(url, output_dir, dry_run, do_apply, only, config_file):
    """Automatically generate GEO fixes for the site."""
    # Se --apply è specificato, disabilita dry-run
    if do_apply:
        dry_run = False

    # Validazione anti-SSRF
    safe_url = url if url.startswith(("http://", "https://")) else f"https://{url}"
    safe, reason = validate_public_url(safe_url)
    if not safe:
        click.echo(f"\n❌ Unsafe URL: {reason}", err=True)
        sys.exit(1)

    # Parsing filtro --only
    only_set = None
    if only:
        only_set = {c.strip().lower() for c in only.split(",")}
        valid_categories = {"robots", "llms", "schema", "meta"}
        invalid = only_set - valid_categories
        if invalid:
            click.echo(f"❌ Invalid categories: {', '.join(invalid)}", err=True)
            click.echo(f"   Valid categories: {', '.join(sorted(valid_categories))}", err=True)
            sys.exit(1)

    # Esegui audit
    click.echo("⏳ Running GEO audit...", err=True)
    from geo_optimizer.core.audit import run_full_audit

    # Carica configurazione progetto
    from geo_optimizer.models.project_config import load_config

    config_path = Path(config_file) if config_file else None
    project_config = load_config(config_path)

    result = run_full_audit(safe_url, project_config=project_config)
    click.echo(f"📊 Current score: {result.score}/100 ({result.band})\n", err=True)

    # Genera fix
    click.echo("🔧 Generating fixes...\n", err=True)
    from geo_optimizer.core.fixer import run_all_fixes

    plan = run_all_fixes(url=safe_url, audit_result=result, only=only_set)

    if not plan.fixes:
        click.echo("✅ No fixes needed — the site is already optimized!")
        return

    # Mostra piano
    click.echo(f"📋 Fix plan — {len(plan.fixes)} fixes found:\n")

    for i, fix_item in enumerate(plan.fixes, 1):
        action_label = {"create": "CREATE", "append": "APPEND", "snippet": "SNIPPET"}.get(fix_item.action, "FIX")
        click.echo(f"  {i}. [{action_label}] {fix_item.description}")
        click.echo(f"     → {fix_item.file_name}")

    if plan.skipped:
        click.echo(f"\n  Skipped: {len(plan.skipped)}")
        for s in plan.skipped:
            click.echo(f"    - {s}")

    click.echo(f"\n📈 Estimated score after fixes: {plan.score_before}/100 → {plan.score_estimated_after}/100")

    if dry_run:
        # Mostra preview del contenuto
        click.echo("\n" + "=" * 60)
        click.echo("PREVIEW (use --apply to write the files)")
        click.echo("=" * 60)

        for fix_item in plan.fixes:
            click.echo(f"\n{'─' * 40}")
            click.echo(f"📄 {fix_item.file_name} ({fix_item.action})")
            click.echo(f"{'─' * 40}")
            # Mostra prime 30 righe per file lunghi
            lines = fix_item.content.split("\n")
            if len(lines) > 30:
                click.echo("\n".join(lines[:30]))
                click.echo(f"\n  ... ({len(lines) - 30} remaining lines)")
            else:
                click.echo(fix_item.content)

        click.echo(f"\n💡 Run: geo fix --url {url} --apply")
    else:
        # Scrivi file
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for fix_item in plan.fixes:
            file_path = output_path / fix_item.file_name
            file_path.write_text(fix_item.content, encoding="utf-8")
            click.echo(f"  ✅ {file_path}")

        click.echo(f"\n✅ {len(plan.fixes)} files written to {output_path}/")
        click.echo(f"📈 Estimated score: {plan.score_before}/100 → {plan.score_estimated_after}/100")
