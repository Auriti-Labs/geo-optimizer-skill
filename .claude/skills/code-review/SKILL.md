---
name: code-review
description: Review codice GEO Optimizer per sicurezza, qualità e aderenza all'architettura
allowed tools: Read, Grep, Glob
---

# Code Review — GEO Optimizer

## VINCOLI INDEROGABILI

1. **core/ non stampa mai** — `print()`, `click.echo()`, `logging.warning()` con testo user-facing sono vietati in `core/`. Solo return di dataclasses.
2. **Anti-SSRF su ogni URL** — qualsiasi URL da input utente DEVE passare per `validators.resolve_and_validate_url()` o `validate_public_url()`.
3. **fetch_url() obbligatorio** — MAI `requests.get()` diretto. Usare `utils.http.fetch_url()` che include DNS pinning + streaming + size check.
4. **Costanti centralizzate** — nessun valore hardcodato in `core/` o `cli/`. Tutto da `models/config.py`.
5. **Dataclasses per return** — funzioni core ritornano tipi da `models/results.py`, mai dict.
6. **Python 3.9 compat** — `from __future__ import annotations`, no `match/case`, no `str | int` senza future import.
7. **Test senza rete** — ogni test deve mockare HTTP. Zero chiamate reali.

## MAI FARE

- Aggiungere `allow_redirects=True` in chiamate requests reali (redirect gestiti manualmente in `_fetch_with_manual_redirects`)
- Importare `validators` al top-level in `http.py` (circular import)
- Usare `datetime.utcnow()` — usare `datetime.now(timezone.utc)`
- Aggiungere `type: ignore` senza commento che spieghi perché
- Hardcodare punteggi scoring fuori da `SCORING` dict in `config.py`
- Scrivere test che dipendono dall'ordine di esecuzione

## Checklist review

### Sicurezza
- [ ] URL utente validati con `validate_public_url()` prima del fetch
- [ ] Nessun `requests.get()` diretto — solo `fetch_url()`
- [ ] Nessun path traversal — file paths validati con `validate_safe_path()`
- [ ] Content-Length/body size verificati prima di processare
- [ ] Nessun dato utente in format string non sanitizzato (XSS in HTML output)
- [ ] Nessuna credential/API key hardcodata

### Architettura
- [ ] Separazione core/cli rispettata (core non importa da cli)
- [ ] Costanti da `models/config.py`, non inline
- [ ] Risultati come dataclass da `models/results.py`
- [ ] Import assoluti `from geo_optimizer.*`

### Qualità
- [ ] Funzioni < 40 righe
- [ ] Type hints completi (`from __future__ import annotations`)
- [ ] Docstring in italiano (stile Google)
- [ ] Nessun `# TODO` senza issue number (#XX)
- [ ] ruff clean: `ruff check` passa senza errori

### Test
- [ ] Ogni nuova funzione ha almeno 1 test
- [ ] Mock con `unittest.mock.patch`, non monkey-patching
- [ ] Test pattern AAA (Arrange-Act-Assert)
- [ ] Nessuna dipendenza da rete
