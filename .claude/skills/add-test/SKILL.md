---
name: add-test
description: Scrivere test per GEO Optimizer seguendo le convenzioni del progetto
allowed tools: Read, Grep, Glob, Edit, Write, Bash
---

# Scrivere test

## VINCOLI INDEROGABILI

1. **Zero chiamate HTTP reali** — mockare tutto con `unittest.mock.patch`.
2. **Pattern AAA** — Arrange, Act, Assert chiaramente separati.
3. **Mock su import path corretto** — patchare dove il modulo è USATO, non dove è definito.
4. **CliRunner per test CLI** — `from click.testing import CliRunner`.

## MAI FARE

- Chiamate HTTP reali (neanche in test manuali senza mark `network`)
- Dipendenze tra test (ordine di esecuzione)
- `monkeypatch` di pytest per mock HTTP — usare `unittest.mock.patch`
- Test che scrivono file senza `tempfile` o `tmp_path`

## Template — Test funzione core

```python
"""Test per geo_optimizer.core.nuovo_modulo."""

from unittest.mock import Mock, patch

from geo_optimizer.core.nuovo_modulo import funzione_sotto_test
from geo_optimizer.models.results import RisultatoAtteso


def test_funzione_caso_successo():
    """Scenario: input valido, risposta HTTP 200."""
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><head><title>Test</title></head></html>"
    mock_response.content = mock_response.text.encode()

    # Act
    with patch("geo_optimizer.core.nuovo_modulo.fetch_url", return_value=(mock_response, None)):
        result = funzione_sotto_test("https://example.com")

    # Assert
    assert isinstance(result, RisultatoAtteso)
    assert result.found is True


def test_funzione_errore_rete():
    """Scenario: fetch fallisce."""
    with patch("geo_optimizer.core.nuovo_modulo.fetch_url", return_value=(None, "Connection failed")):
        result = funzione_sotto_test("https://example.com")

    assert result.found is False


def test_funzione_url_ssrf():
    """Scenario: URL verso rete privata."""
    with patch("geo_optimizer.core.nuovo_modulo.fetch_url", return_value=(None, "URL non sicuro")):
        result = funzione_sotto_test("http://169.254.169.254/metadata")

    assert result.found is False
```

## Template — Test command CLI

```python
from unittest.mock import patch

from click.testing import CliRunner

from geo_optimizer.cli.main import cli
from geo_optimizer.models.results import AuditResult


def test_cli_comando_successo(sample_audit_result):
    """geo comando --url ... ritorna exit code 0."""
    runner = CliRunner()

    with patch("geo_optimizer.cli.comando_cmd.funzione_core", return_value=sample_audit_result):
        with patch("geo_optimizer.cli.comando_cmd.validate_public_url", return_value=(True, None)):
            result = runner.invoke(cli, ["comando", "--url", "https://example.com"])

    assert result.exit_code == 0
    assert "atteso nel output" in result.output


def test_cli_comando_url_non_valido():
    """geo comando --url localhost ritorna errore."""
    runner = CliRunner()

    with patch("geo_optimizer.cli.comando_cmd.validate_public_url", return_value=(False, "Host non consentito")):
        result = runner.invoke(cli, ["comando", "--url", "http://localhost"])

    assert result.exit_code != 0
```

## Checklist

1. [ ] Identificare la funzione da testare e i suoi import path
2. [ ] Creare test per: caso successo, errore rete, input invalido
3. [ ] Mockare `fetch_url` sul path di IMPORTAZIONE (non di definizione)
4. [ ] Usare fixture per dati condivisi
5. [ ] Verificare: `pytest tests/test_nuovo.py -v` passa
6. [ ] Coverage: `pytest tests/test_nuovo.py --cov=geo_optimizer.core.nuovo --cov-report=term-missing`
