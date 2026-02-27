"""
GEO Optimizer — Generative Engine Optimization Toolkit

Make websites visible and citable by AI search engines
(ChatGPT, Perplexity, Claude, Gemini).

Based on the Princeton KDD 2024 research paper (arxiv.org/abs/2311.09735).

Uso programmatico::

    from geo_optimizer import audit, AuditResult
    result = audit("https://example.com")
    print(result.score, result.band)
"""

__version__ = "3.0.0"

# ─── API pubblica ────────────────────────────────────────────────────────────

from geo_optimizer.core.audit import run_full_audit as audit
from geo_optimizer.core.audit import run_full_audit_async as audit_async
from geo_optimizer.core.registry import AuditCheck, CheckRegistry, CheckResult
from geo_optimizer.models.results import (
    AuditResult,
    ContentResult,
    LlmsTxtResult,
    MetaResult,
    RobotsResult,
    SchemaAnalysis,
    SchemaResult,
    SitemapUrl,
)

__all__ = [
    # Versione
    "__version__",
    # Funzioni principali
    "audit",
    "audit_async",
    # Plugin system
    "CheckRegistry",
    "AuditCheck",
    "CheckResult",
    # Dataclass risultati
    "AuditResult",
    "RobotsResult",
    "LlmsTxtResult",
    "SchemaResult",
    "MetaResult",
    "ContentResult",
    "SchemaAnalysis",
    "SitemapUrl",
]
