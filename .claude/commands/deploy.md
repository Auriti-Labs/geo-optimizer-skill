# Deploy

Procedura di deploy per GEO Optimizer (Docker + Railway).

## Pre-deploy

1. Verifica che i test passino:
   ```bash
   pytest tests/ -v --tb=short
   ```

2. Verifica lint:
   ```bash
   ruff check src/geo_optimizer/ scripts/
   ruff format --check src/geo_optimizer/ scripts/
   ```

3. Verifica versione in `pyproject.toml`:
   ```bash
   grep "version" pyproject.toml | head -1
   ```

## Docker CLI

```bash
docker build -t geo-optimizer .
docker run geo-optimizer audit --url https://example.com
```

## Docker Web

```bash
docker build -f Dockerfile.web -t geo-optimizer-web .
docker run -p 8000:8000 geo-optimizer-web
```

## Railway

Il deploy su Railway è automatico via `railway.toml`:
- Push su `main` → deploy automatico
- Usa `Dockerfile.web` come builder
- Health check: `GET /health`

## PyPI (publish)

Il workflow `.github/workflows/publish.yml` pubblica su PyPI al tag:
```bash
git tag v3.0.2
git push origin v3.0.2
```

## Rollback

1. Docker: `docker run geo-optimizer:previous-tag`
2. Railway: revert al commit precedente dalla dashboard
3. PyPI: `pip install geo-optimizer-skill==VERSIONE_PRECEDENTE`
