"""
GEO scoring calculation functions shared across all CLI formatters.
v4.0: delegates to core/scoring.py for consistency and per-category breakdown.
"""

from __future__ import annotations

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
from geo_optimizer.models.results import AuditResult


def robots_score(r: AuditResult) -> int:
    """robots.txt score — delegates to core/scoring.py."""
    return robots_score_impl(r.robots)


def llms_score(r: AuditResult) -> int:
    """llms.txt score — delegates to core/scoring.py."""
    return llms_score_impl(r.llms)


def schema_score(r: AuditResult) -> int:
    """JSON-LD schema score — delegates to core/scoring.py."""
    return schema_score_impl(r.schema)


def meta_score(r: AuditResult) -> int:
    """Meta tag score — delegates to core/scoring.py."""
    return meta_score_impl(r.meta)


def content_score(r: AuditResult) -> int:
    """Content quality score — delegates to core/scoring.py."""
    return content_score_impl(r.content)


def signals_score(r: AuditResult) -> int:
    """Technical signals score v4.0 — delegates to core/scoring.py."""
    return signals_score_impl(r.signals) if r.signals else 0


def brand_entity_score(r: AuditResult) -> int:
    """Brand & Entity score v4.3 — delegates to core/scoring.py."""
    return brand_entity_score_impl(r.brand_entity) if r.brand_entity else 0
