---
name: add-cli-command
description: Aggiungere un nuovo subcommand Click al CLI geo
allowed tools: Read, Grep, Glob, Edit, Write, Bash
---

# Aggiungere un subcommand CLI

## VINCOLI INDEROGABILI

1. Il subcommand va in un file dedicato `cli/nuovo_cmd.py` — MAI aggiungere a `main.py`.
2. La business logic va in `core/` — il command fa solo I/O e display.
3. URL utente DEVE essere validato con `validate_public_url()` PRIMA di passare al core.
4. Supportare `--config` per `.geo-optimizer.yml` se il command ha parametri defaultabili.
5. Registrare il command con `cli.add_command()` in `main.py`.

## MAI FARE

- Mettere logica di business nel file `*_cmd.py`
- Fare `requests.get()` nel CLI — delegare al core
- Dimenticare di importare e registrare il command in `main.py`

## Template — cli/nuovo_cmd.py

```python
"""
CLI command: geo nuovo
"""

import click

from geo_optimizer.core.nuovo_modulo import funzione_core
from geo_optimizer.utils.validators import validate_public_url


@click.command()
@click.option("--url", required=True, help="URL del sito")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
@click.option("--output", "output_file", default=None, help="File di output (opzionale)")
@click.option("--config", "config_file", default=None, help="Percorso .geo-optimizer.yml")
def nuovo(url, output_format, output_file, config_file):
    """Descrizione breve del comando."""
    # Validazione anti-SSRF
    ok, err = validate_public_url(url)
    if not ok:
        click.echo(f"Errore: {err}", err=True)
        raise SystemExit(1)

    # Invoca business logic dal core
    result = funzione_core(url)

    # Formatta output
    if output_format == "json":
        import json
        output = json.dumps(dataclasses.asdict(result), indent=2, ensure_ascii=False)
    else:
        output = _format_text(result)

    # Scrivi output
    if output_file:
        from pathlib import Path
        Path(output_file).write_text(output, encoding="utf-8")
        click.echo(f"Output salvato in {output_file}")
    else:
        click.echo(output)
```

## Template — Registrazione in cli/main.py

```python
# Aggiungere dopo gli altri import
from geo_optimizer.cli.nuovo_cmd import nuovo  # noqa: E402

cli.add_command(nuovo)
```

## Checklist

1. [ ] Creare `cli/nuovo_cmd.py` con il subcommand Click
2. [ ] Implementare business logic in `core/nuovo_modulo.py` (ritorna dataclass)
3. [ ] Validare URL con `validate_public_url()` nel CLI
4. [ ] Registrare con `cli.add_command()` in `main.py`
5. [ ] Aggiungere test CLI con `CliRunner` in `tests/test_cli.py`
6. [ ] Aggiungere test core in `tests/test_core.py`
7. [ ] Verificare: `geo nuovo --help` funziona, `ruff check`, `pytest tests/ -x`
