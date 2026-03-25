"""
GEO scoring calculation functions shared across all CLI formatters.
v4.0: delega a core/scoring.py per consistenza e breakdown per categoria.
"""

from geo_optimizer.core.scoring import (
    _score_content as content_score_impl,
)
from geo_optimizer.core.scoring import (
    _score_llms as llms_score_impl,
)
from geo_optimizer.core.scoring import (
    _score_meta as meta_score_impl,
)
from geo_optimizer.core.scoring import (
    _score_robots as robots_score_impl,
)
from geo_optimizer.core.scoring import (
    _score_schema as schema_score_impl,
)
from geo_optimizer.core.scoring import (
    _score_signals as signals_score_impl,
)
from geo_optimizer.models.results import AuditResult


def robots_score(r: AuditResult) -> int:
    """Punteggio robots.txt — delega a core/scoring.py."""
    return robots_score_impl(r.robots)


def llms_score(r: AuditResult) -> int:
    """Punteggio llms.txt — delega a core/scoring.py."""
    return llms_score_impl(r.llms)


def schema_score(r: AuditResult) -> int:
    """Punteggio schema JSON-LD — delega a core/scoring.py."""
    return schema_score_impl(r.schema)


def meta_score(r: AuditResult) -> int:
    """Punteggio meta tag — delega a core/scoring.py."""
    return meta_score_impl(r.meta)


def content_score(r: AuditResult) -> int:
    """Punteggio qualità contenuto — delega a core/scoring.py."""
    return content_score_impl(r.content)


def signals_score(r: AuditResult) -> int:
    """Punteggio segnali tecnici v4.0 — delega a core/scoring.py."""
    return signals_score_impl(r.signals) if r.signals else 0
