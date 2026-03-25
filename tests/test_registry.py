"""
Test per geo_optimizer.core.registry — CheckRegistry e AuditCheck Protocol.

Coverage fix #153: il modulo era a 0% di coverage.
"""

from unittest.mock import MagicMock, patch

import pytest

from geo_optimizer.core.registry import AuditCheck, CheckRegistry, CheckResult


# ─── Fixture: check valido che implementa il Protocol ────────────────────────


class _MockCheck:
    """Check di test che implementa il Protocol AuditCheck."""

    name = "mock_check"
    description = "Check di test"
    max_score = 10

    def run(self, url: str, soup=None, **kwargs) -> CheckResult:
        return CheckResult(
            name=self.name,
            score=10,
            max_score=self.max_score,
            passed=True,
            message="OK",
        )


class _FailingCheck:
    """Check che solleva sempre un'eccezione durante run()."""

    name = "failing_check"
    description = "Check che fallisce sempre"
    max_score = 5

    def run(self, url: str, soup=None, **kwargs) -> CheckResult:
        raise RuntimeError("Errore simulato nel check")


class _MissingMethodCheck:
    """Oggetto che NON implementa il Protocol AuditCheck (manca run)."""

    name = "bad_check"
    description = "Check incompleto"
    max_score = 10
    # run() mancante → non implementa il Protocol


# ─── Setup: pulisci il registry prima di ogni test ───────────────────────────


@pytest.fixture(autouse=True)
def clear_registry():
    """Pulisce il registry prima e dopo ogni test per evitare interferenze."""
    CheckRegistry.clear()
    yield
    CheckRegistry.clear()


# ─── Test: inizializzazione ───────────────────────────────────────────────────


def test_registry_init_vuoto():
    """CheckRegistry parte senza check registrati."""
    assert CheckRegistry.all() == []
    assert CheckRegistry.names() == []


# ─── Test: register ───────────────────────────────────────────────────────────


def test_register_check_valido():
    """Registra un check valido e verifica che sia presente."""
    check = _MockCheck()
    CheckRegistry.register(check)

    assert "mock_check" in CheckRegistry.names()
    assert CheckRegistry.get("mock_check") is check


def test_register_check_duplicato_solleva_errore():
    """Registrare due check con lo stesso nome solleva ValueError."""
    CheckRegistry.register(_MockCheck())
    with pytest.raises(ValueError, match="already registered"):
        CheckRegistry.register(_MockCheck())


def test_register_oggetto_non_protocol_solleva_typeerror():
    """Un oggetto che non implementa AuditCheck solleva TypeError."""
    # _MissingMethodCheck non ha run() → non è AuditCheck
    with pytest.raises(TypeError, match="does not implement"):
        CheckRegistry.register(_MissingMethodCheck())


def test_unregister_rimuove_check():
    """unregister() rimuove un check registrato."""
    CheckRegistry.register(_MockCheck())
    CheckRegistry.unregister("mock_check")
    assert CheckRegistry.get("mock_check") is None


def test_unregister_nome_inesistente_non_solleva():
    """unregister() su nome non esistente non solleva eccezioni."""
    CheckRegistry.unregister("nome_inesistente")  # non deve sollevare


def test_get_nome_inesistente_ritorna_none():
    """get() su nome non registrato ritorna None."""
    assert CheckRegistry.get("inesistente") is None


# ─── Test: discover (load_entry_points) ──────────────────────────────────────


def test_load_entry_points_nessun_plugin(monkeypatch):
    """load_entry_points() con nessun plugin installato ritorna 0."""
    # Mock entry_points per simulare assenza di plugin
    with patch("geo_optimizer.core.registry.sys") as mock_sys:
        mock_sys.version_info = (3, 10, 0)
        with patch("importlib.metadata.entry_points", return_value=[]):
            count = CheckRegistry.load_entry_points()
    assert count == 0


def test_load_entry_points_non_ricarica_se_gia_caricato():
    """load_entry_points() chiamato due volte salta il secondo caricamento."""
    # Prima chiamata: setta _loaded_entry_points = True
    with patch("importlib.metadata.entry_points", return_value=[]) as mock_ep:
        CheckRegistry.load_entry_points()
        CheckRegistry.load_entry_points()
        # Deve essere chiamato solo una volta (la seconda salta)
        assert mock_ep.call_count <= 1


def test_load_entry_points_con_plugin_valido():
    """load_entry_points() carica un plugin che espone una classe check."""
    # Crea un entry point mock che ritorna _MockCheck
    mock_ep = MagicMock()
    mock_ep.load.return_value = _MockCheck

    # Patch sys.version_info per il branch Python >= 3.10
    import sys

    original_version = sys.version_info

    with patch("geo_optimizer.core.registry.sys") as mock_sys:
        mock_sys.version_info = (3, 10, 0)
        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            count = CheckRegistry.load_entry_points()

    assert count == 1
    assert "mock_check" in CheckRegistry.names()


def test_load_entry_points_plugin_fallito_non_blocca():
    """Plugin che fallisce durante il caricamento non blocca gli altri."""
    mock_ep_ok = MagicMock()
    mock_ep_ok.load.return_value = _MockCheck

    mock_ep_fail = MagicMock()
    mock_ep_fail.load.side_effect = ImportError("modulo non trovato")

    with patch("geo_optimizer.core.registry.sys") as mock_sys:
        mock_sys.version_info = (3, 10, 0)
        with patch("importlib.metadata.entry_points", return_value=[mock_ep_fail, mock_ep_ok]):
            count = CheckRegistry.load_entry_points()

    # Solo il plugin valido deve essere stato caricato
    assert count == 1
    assert "mock_check" in CheckRegistry.names()


# ─── Test: run_all ────────────────────────────────────────────────────────────


def test_run_all_nessun_check_registrato():
    """run_all() senza check registrati ritorna lista vuota."""
    results = CheckRegistry.run_all("https://example.com")
    assert results == []


def test_run_all_esegue_check_registrato():
    """run_all() esegue il check e ritorna CheckResult con score corretto."""
    CheckRegistry.register(_MockCheck())
    results = CheckRegistry.run_all("https://example.com")

    assert len(results) == 1
    r = results[0]
    assert r.name == "mock_check"
    assert r.score == 10
    assert r.passed is True


def test_run_all_check_fallito_non_blocca_altri():
    """Check che solleva eccezione produce CheckResult con score 0 ma non blocca gli altri."""
    CheckRegistry.register(_FailingCheck())
    CheckRegistry.register(_MockCheck())

    results = CheckRegistry.run_all("https://example.com")

    assert len(results) == 2

    # Trova i risultati per nome
    risultati_per_nome = {r.name: r for r in results}

    # Il check fallito deve avere score 0 e messaggio di errore
    failing = risultati_per_nome["failing_check"]
    assert failing.score == 0
    assert failing.passed is False
    assert "Error" in failing.message

    # Il check valido deve funzionare normalmente
    ok = risultati_per_nome["mock_check"]
    assert ok.score == 10
    assert ok.passed is True


def test_run_all_passa_kwargs_al_check():
    """run_all() passa kwargs aggiuntivi al metodo run() del check."""
    kwargs_ricevuti = {}

    class _KwargsCheck:
        name = "kwargs_check"
        description = "Check che registra i kwargs"
        max_score = 5

        def run(self, url: str, soup=None, **kwargs) -> CheckResult:
            kwargs_ricevuti.update(kwargs)
            return CheckResult(name=self.name, score=5, max_score=5, passed=True)

    CheckRegistry.register(_KwargsCheck())
    CheckRegistry.run_all("https://example.com", extra_param="valore_test")

    assert kwargs_ricevuti.get("extra_param") == "valore_test"


# ─── Test: CheckResult dataclass ─────────────────────────────────────────────


def test_check_result_defaults():
    """CheckResult ha valori di default corretti."""
    r = CheckResult(name="test")
    assert r.score == 0
    assert r.max_score == 10
    assert r.passed is False
    assert r.details == {}
    assert r.message == ""


def test_check_result_completo():
    """CheckResult accetta tutti i campi esplicitamente."""
    r = CheckResult(
        name="completo",
        score=8,
        max_score=10,
        passed=True,
        details={"chiave": "valore"},
        message="Tutto ok",
    )
    assert r.score == 8
    assert r.passed is True
    assert r.details["chiave"] == "valore"


# ─── Test: clear ─────────────────────────────────────────────────────────────


def test_clear_svuota_registry():
    """clear() rimuove tutti i check e resetta _loaded_entry_points."""
    CheckRegistry.register(_MockCheck())
    assert len(CheckRegistry.all()) == 1

    CheckRegistry.clear()

    assert CheckRegistry.all() == []
    assert CheckRegistry._loaded_entry_points is False
