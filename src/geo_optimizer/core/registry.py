"""
Plugin system for custom GEO checks.

Allows third-party packages to register additional checks
via entry points ``geo_optimizer.checks`` in pyproject.toml.

External plugin example (plugin's pyproject.toml)::

    [project.entry-points."geo_optimizer.checks"]
    my_check = "my_plugin:MyAuditCheck"

The check must implement the ``AuditCheck`` Protocol.
"""

import logging
import sys
import threading
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Result of a plugin check."""

    name: str
    score: int = 0
    max_score: int = 10
    passed: bool = False
    details: dict[str, Any] = field(default_factory=dict)
    message: str = ""


@runtime_checkable
class AuditCheck(Protocol):
    """Protocol for custom GEO checks (PEP 544).

    Plugins must implement this protocol::

        class MyCheck:
            name = "my_check"
            description = "Checks something specific"
            max_score = 10

            def run(self, url: str, soup=None, **kwargs) -> CheckResult:
                ...
    """

    name: str
    description: str
    max_score: int

    def run(self, url: str, soup: Any = None, **kwargs: Any) -> CheckResult: ...


class CheckRegistry:
    """Central registry for GEO checks (built-in + plugin).

    Singleton pattern: use class methods to register and retrieve checks.
    """

    _checks: dict[str, AuditCheck] = {}
    _loaded_entry_points: bool = False
    _lock = threading.Lock()  # Thread-safe entry point loading (fix #189)

    @classmethod
    def register(cls, check: AuditCheck) -> None:
        """Register a check in the registry.

        Args:
            check: Instance implementing the AuditCheck Protocol.

        Raises:
            TypeError: If the check does not implement AuditCheck.
            ValueError: If a check with the same name is already registered.
        """
        if not isinstance(check, AuditCheck):
            raise TypeError(f"{type(check).__name__} does not implement the AuditCheck Protocol")

        if check.name in cls._checks:
            raise ValueError(f"Check '{check.name}' already registered")

        cls._checks[check.name] = check

    @classmethod
    def unregister(cls, name: str) -> None:
        """Remove a check from the registry."""
        cls._checks.pop(name, None)

    @classmethod
    def get(cls, name: str) -> Optional[AuditCheck]:
        """Retrieve a check by name."""
        return cls._checks.get(name)

    @classmethod
    def all(cls) -> list[AuditCheck]:
        """Return all registered checks."""
        return list(cls._checks.values())

    @classmethod
    def names(cls) -> list[str]:
        """Return the names of all registered checks."""
        return list(cls._checks.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear the registry (useful in tests)."""
        cls._checks.clear()
        cls._loaded_entry_points = False

    @classmethod
    def load_entry_points(cls) -> int:
        """Load checks from ``geo_optimizer.checks`` entry points.

        Uses importlib.metadata to discover installed plugins.
        Returns the number of plugins successfully loaded.
        """
        with cls._lock:
            if cls._loaded_entry_points:
                return 0
            cls._loaded_entry_points = True

        loaded = 0

        from importlib.metadata import entry_points

        if sys.version_info >= (3, 10):
            eps = entry_points(group="geo_optimizer.checks")
        else:
            # Python 3.9: entry_points() may return dict or SelectableGroups
            all_eps = entry_points()
            if isinstance(all_eps, dict):
                eps = all_eps.get("geo_optimizer.checks", [])
            elif hasattr(all_eps, "select"):
                eps = all_eps.select(group="geo_optimizer.checks")
            else:
                # Fallback: filter the list manually
                eps = [ep for ep in all_eps if ep.group == "geo_optimizer.checks"]

        for ep in eps:
            try:
                check_class = ep.load()
                # Instantiate if it is a class, otherwise use directly
                check = check_class() if isinstance(check_class, type) else check_class
                cls.register(check)
                loaded += 1
            except Exception as exc:
                # Failed plugins do not block the audit, but log for debugging (fix #202)
                logger.warning("Plugin '%s' failed to load: %s", ep.name, exc)

        return loaded

    @classmethod
    def run_all(cls, url: str, soup: Any = None, **kwargs: Any) -> list[CheckResult]:
        """Run all registered checks and return results.

        Args:
            url: URL of the site to check.
            soup: BeautifulSoup of the homepage (optional).
            **kwargs: Extra arguments passed to the checks.

        Returns:
            List of CheckResult for each check executed.
        """
        results = []
        for check in cls._checks.values():
            try:
                result = check.run(url=url, soup=soup, **kwargs)
                results.append(result)
            except Exception as e:
                # Check failed: score 0, error message
                results.append(
                    CheckResult(
                        name=check.name,
                        score=0,
                        max_score=check.max_score,
                        passed=False,
                        message=f"Error in check: {e}",
                    )
                )
        return results
