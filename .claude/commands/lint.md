# Lint

Esegui controlli di qualità codice.

## Passi

1. Ruff check (errori e warning):
   ```bash
   ruff check src/geo_optimizer/ scripts/
   ```

2. Ruff format (verifica formattazione):
   ```bash
   ruff format --check src/geo_optimizer/ scripts/
   ```

3. Auto-fix (se necessario):
   ```bash
   ruff check --fix src/geo_optimizer/ scripts/
   ruff format src/geo_optimizer/ scripts/
   ```

4. Audit dipendenze (come CI):
   ```bash
   pip-audit
   ```

## Configurazione

Ruff è configurato in `pyproject.toml`:
- `line-length = 120`
- `target-version = "py39"`
- Regole: E, F, W, I, UP, B, C4, SIM
- Ignorate: E501, SIM108, SIM105, SIM114, SIM110
- Per-file ignores per `scripts/` e `tests/`
