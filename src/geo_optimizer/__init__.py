"""
GEO Optimizer — Generative Engine Optimization Toolkit

Audit and fix the technical signals AI search engines need to reach, parse and cite a website
(ChatGPT, Perplexity, Claude, Gemini).

Based on the Princeton KDD 2024 research paper (arxiv.org/abs/2311.09735).

Programmatic usage::

    from geo_optimizer import audit, AuditResult
    result = audit("https://example.com")
    print(result.score, result.band)
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("geo-optimizer-skill")
except PackageNotFoundError:
    __version__ = "4.23.0"

# ─── Public API ──────────────────────────────────────────────────────────────

from geo_optimizer.core.audit import run_full_audit as audit
from geo_optimizer.core.audit import run_full_audit_async as audit_async
from geo_optimizer.core.registry import AuditCheck, CheckRegistry, CheckResult
from geo_optimizer.models.results import (
    AuditResult,
    CitabilityResult,
    ContentResult,
    FixItem,
    FixPlan,
    LlmsTxtResult,
    MetaResult,
    MethodScore,
    RobotsResult,
    SchemaAnalysis,
    SchemaResult,
    SitemapUrl,
)

__all__ = [
    # Version
    "__version__",
    # Main functions
    "audit",
    "audit_async",
    # Plugin system
    "CheckRegistry",
    "AuditCheck",
    "CheckResult",
    # Result dataclasses
    "AuditResult",
    "RobotsResult",
    "LlmsTxtResult",
    "SchemaResult",
    "MetaResult",
    "ContentResult",
    "CitabilityResult",
    "MethodScore",
    "FixPlan",
    "FixItem",
    "SchemaAnalysis",
    "SitemapUrl",
]
