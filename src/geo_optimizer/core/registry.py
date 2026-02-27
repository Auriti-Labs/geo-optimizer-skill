"""
Sistema di plugin per check GEO personalizzati.

Permette a pacchetti di terze parti di registrare check aggiuntivi
tramite entry points ``geo_optimizer.checks`` in pyproject.toml.

Esempio plugin esterno (pyproject.toml del plugin)::

    [project.entry-points."geo_optimizer.checks"]
    my_check = "my_plugin:MyAuditCheck"

Il check deve implementare il Protocol ``AuditCheck``.
"""

import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@dataclass
class CheckResult:
    """Risultato di un check plugin."""

    name: str
    score: int = 0
    max_score: int = 10
    passed: bool = False
    details: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


@runtime_checkable
class AuditCheck(Protocol):
    """Protocol per check GEO personalizzati (PEP 544).

    I plugin devono implementare questo protocol::

        class MyCheck:
            name = "my_check"
            description = "Verifica qualcosa di specifico"
            max_score = 10

            def run(self, url: str, soup=None, **kwargs) -> CheckResult:
                ...
    """

    name: str
    description: str
    max_score: int

    def run(self, url: str, soup: Any = None, **kwargs: Any) -> CheckResult: ...


class CheckRegistry:
    """Registry centrale per check GEO (built-in + plugin).

    Singleton pattern: usa i metodi di classe per registrare e recuperare check.
    """

    _checks: Dict[str, AuditCheck] = {}
    _loaded_entry_points: bool = False

    @classmethod
    def register(cls, check: AuditCheck) -> None:
        """Registra un check nel registry.

        Args:
            check: Istanza che implementa il Protocol AuditCheck.

        Raises:
            TypeError: Se il check non implementa AuditCheck.
            ValueError: Se un check con lo stesso nome è già registrato.
        """
        if not isinstance(check, AuditCheck):
            raise TypeError(f"{type(check).__name__} non implementa il Protocol AuditCheck")

        if check.name in cls._checks:
            raise ValueError(f"Check '{check.name}' già registrato")

        cls._checks[check.name] = check

    @classmethod
    def unregister(cls, name: str) -> None:
        """Rimuovi un check dal registry."""
        cls._checks.pop(name, None)

    @classmethod
    def get(cls, name: str) -> Optional[AuditCheck]:
        """Recupera un check per nome."""
        return cls._checks.get(name)

    @classmethod
    def all(cls) -> List[AuditCheck]:
        """Ritorna tutti i check registrati."""
        return list(cls._checks.values())

    @classmethod
    def names(cls) -> List[str]:
        """Ritorna i nomi di tutti i check registrati."""
        return list(cls._checks.keys())

    @classmethod
    def clear(cls) -> None:
        """Svuota il registry (utile nei test)."""
        cls._checks.clear()
        cls._loaded_entry_points = False

    @classmethod
    def load_entry_points(cls) -> int:
        """Carica check da entry points ``geo_optimizer.checks``.

        Usa importlib.metadata per scoprire plugin installati.
        Ritorna il numero di plugin caricati con successo.
        """
        if cls._loaded_entry_points:
            return 0

        cls._loaded_entry_points = True
        loaded = 0

        if sys.version_info >= (3, 10):
            from importlib.metadata import entry_points

            eps = entry_points(group="geo_optimizer.checks")
        else:
            # Python 3.9: entry_points() ritorna un dict
            from importlib.metadata import entry_points

            all_eps = entry_points()
            eps = all_eps.get("geo_optimizer.checks", [])

        for ep in eps:
            try:
                check_class = ep.load()
                # Istanzia se è una classe, altrimenti usa direttamente
                check = check_class() if isinstance(check_class, type) else check_class
                cls.register(check)
                loaded += 1
            except Exception:
                # Plugin falliti non bloccano l'audit
                pass

        return loaded

    @classmethod
    def run_all(cls, url: str, soup: Any = None, **kwargs: Any) -> List[CheckResult]:
        """Esegui tutti i check registrati e ritorna i risultati.

        Args:
            url: URL del sito da verificare.
            soup: BeautifulSoup della homepage (opzionale).
            **kwargs: Argomenti extra passati ai check.

        Returns:
            Lista di CheckResult per ogni check eseguito.
        """
        results = []
        for check in cls._checks.values():
            try:
                result = check.run(url=url, soup=soup, **kwargs)
                results.append(result)
            except Exception as e:
                # Check fallito: score 0, messaggio errore
                results.append(
                    CheckResult(
                        name=check.name,
                        score=0,
                        max_score=check.max_score,
                        passed=False,
                        message=f"Errore nel check: {e}",
                    )
                )
        return results
