"""
CLI entry point per avviare la web demo.

Uso:
    geo-web                    # Avvia su localhost:8000
    geo-web --port 3000        # Porta personalizzata
    geo-web --host 0.0.0.0     # Accessibile da rete
"""

import click


@click.command()
@click.option("--host", default="127.0.0.1", help="Host su cui ascoltare")
@click.option("--port", default=8000, help="Porta su cui ascoltare")
@click.option("--reload", is_flag=True, help="Auto-reload in sviluppo")
def main(host, port, reload):
    """Avvia la web demo GEO Optimizer."""
    try:
        import uvicorn
    except ImportError:
        click.echo("uvicorn non installato. Usa: pip install geo-optimizer-skill[web]", err=True)
        raise SystemExit(1)

    click.echo(f"GEO Optimizer Web Demo: http://{host}:{port}")
    uvicorn.run(
        "geo_optimizer.web.app:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
