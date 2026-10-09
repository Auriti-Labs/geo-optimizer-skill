"""
GEO scoring calculation functions shared across all CLI formatters.
v4.0: delegates to core/scoring.py for consistency and per-category breakdown.
"""

from __future__ import annotations

from geo_optimizer.core.scoring import (
    _score_ai_discovery as ai_discovery_score_impl,
)
from geo_optimizer.core.scoring import (
    _score_brand_entity as brand_entity_score_impl,
)
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
from geo_optimizer.models.config import CATEGORY_MAX
from geo_optimizer.models.results import AuditResult

_V1_IMPL = {
    "robots": lambda r: robots_score_impl(r.robots),
    "llms": lambda r: llms_score_impl(r.llms),
    "schema": lambda r: schema_score_impl(r.schema),
    "meta": lambda r: meta_score_impl(r.meta),
    "content": lambda r: content_score_impl(r.content),
    "signals": lambda r: signals_score_impl(r.signals) if r.signals else 0,
    "ai_discovery": lambda r: ai_discovery_score_impl(r.ai_discovery) if r.ai_discovery else 0,
    "brand_entity": lambda r: brand_entity_score_impl(r.brand_entity) if r.brand_entity else 0,
}


def category_score(r: AuditResult, cat: str) -> int:
    """Punteggio categoria dal risultato, con ricalcolo v1 per risultati legacy."""
    if cat in r.score_breakdown:
        return r.score_breakdown[cat]
    impl = _V1_IMPL.get(cat)
    return impl(r) if impl else 0


def category_max(r: AuditResult, cat: str) -> int:
    """Massimo categoria per la versione di rubrica del risultato."""
    return (r.score_max or CATEGORY_MAX).get(cat, 0)


def categories(r: AuditResult) -> list[str]:
    """Categorie della rubrica del risultato, con fallback v1 per risultati legacy."""
    return list(r.score_max or CATEGORY_MAX)


def robots_score(r: AuditResult) -> int:
    """robots.txt score — delegates to core/scoring.py."""
    return category_score(r, "robots")


def llms_score(r: AuditResult) -> int:
    """llms.txt score — delegates to core/scoring.py."""
    return category_score(r, "llms")


def schema_score(r: AuditResult) -> int:
    """JSON-LD schema score — delegates to core/scoring.py."""
    return category_score(r, "schema")


def meta_score(r: AuditResult) -> int:
    """Meta tag score — delegates to core/scoring.py."""
    return category_score(r, "meta")


def content_score(r: AuditResult) -> int:
    """Content quality score — delegates to core/scoring.py."""
    return category_score(r, "content")


def signals_score(r: AuditResult) -> int:
    """Technical signals score v4.0 — delegates to core/scoring.py."""
    return category_score(r, "signals")


def brand_entity_score(r: AuditResult) -> int:
    """Brand & Entity score v4.3 — delegates to core/scoring.py."""
    return category_score(r, "brand_entity")


def ai_discovery_score(r: AuditResult) -> int:
    """AI Discovery score — delegates to core/scoring.py."""
    return category_score(r, "ai_discovery")
