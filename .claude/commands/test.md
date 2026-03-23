# Test

Esegui la test suite del progetto.

## Passi

1. Verifica che l'ambiente virtuale esista:
   ```bash
   ls .venv/bin/pytest || echo "Ambiente non trovato, usa: pip install -e '.[dev]'"
   ```

2. Esegui la suite completa:
   ```bash
   pytest tests/ -v --tb=short
   ```

3. Per un singolo file:
   ```bash
   pytest tests/test_core.py -v
   ```

4. Per un singolo test:
   ```bash
   pytest tests/test_core.py::test_nome -v
   ```

5. Con coverage:
   ```bash
   pytest tests/ -v --cov=geo_optimizer --cov-report=term-missing
   ```

6. Solo test non-network (come CI):
   ```bash
   pytest tests/ -v -m "not network"
   ```

## Verifica finale

Dopo i test, esegui lint:
```bash
ruff check src/geo_optimizer/ scripts/
```
