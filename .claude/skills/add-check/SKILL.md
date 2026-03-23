---
name: add-check
description: Aggiungere un nuovo check di audit al core GEO Optimizer
allowed tools: Read, Grep, Glob, Edit, Write, Bash
---

# Aggiungere un check di audit

## VINCOLI INDEROGABILI

1. Il check DEVE ritornare una dataclass da `models/results.py` — MAI dict.
2. Se il check fa HTTP, DEVE usare `utils.http.fetch_url()` — MAI `requests.get()`.
3. Le costanti (pattern, pesi, ecc.) vanno in `models/config.py`.
4. Il check va in `core/audit.py` o in un nuovo file `core/check_*.py`.
5. Lo scoring va integrato in `compute_geo_score()` aggiornando `SCORING` in `config.py`.

## MAI FARE

- Stampare in core — ritornare dataclass
- Hardcodare pesi scoring — metterli in `SCORING`
- Fare chiamate HTTP senza anti-SSRF
- Importare da `cli/` in `core/`

## Template — Nuovo sub-audit in core/audit.py

```python
def audit_nuovo_check(base_url: str) -> NuovoCheckResult:
    """Verifica [cosa controlla] per il sito. Ritorna NuovoCheckResult.

    Args:
        base_url: URL base del sito.
    """
    result = NuovoCheckResult()

    # Fetch con protezione anti-SSRF
    r, err = fetch_url(urljoin(base_url, "/percorso"))
    if err or not r:
        return result

    if r.status_code != 200:
        return result

    # Logica di analisi
    result.found = True
    # ... analisi ...

    return result
```

## Template — Dataclass risultato in models/results.py

```python
@dataclass
class NuovoCheckResult:
    """Risultato del check [nome]."""
    found: bool = False
    # Campi specifici del check
    dettaglio_a: bool = False
    dettaglio_b: int = 0
```

## Template — Integrazione scoring in config.py

```python
SCORING = {
    "robots": {"weight": 18, ...},     # Ribilanciare pesi
    "nuovo_check": {"weight": 5, ...}, # Nuovo check
    # ... totale DEVE fare 100
}
```

## Checklist

1. [ ] Creare dataclass risultato in `models/results.py`
2. [ ] Aggiungere costanti necessarie in `models/config.py`
3. [ ] Implementare funzione `audit_*()` in `core/audit.py`
4. [ ] Integrare in `run_full_audit()` — aggiungere campo in `AuditResult`
5. [ ] Aggiungere peso in `SCORING` dict (totale = 100)
6. [ ] Aggiornare `compute_geo_score()` per il nuovo check
7. [ ] Aggiungere output nel formatter (`cli/formatters.py`)
8. [ ] Scrivere test con mock HTTP (in `tests/test_core.py` o file dedicato)
9. [ ] Verificare: `ruff check src/geo_optimizer/` e `pytest tests/ -x`
