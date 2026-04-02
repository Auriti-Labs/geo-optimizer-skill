"""
GitHub Actions formatter for GEO audit output.

Generates output with ``::notice`` and ``::warning`` annotations for
native GitHub Actions integration. Used with ``geo audit --format github``.
"""

from __future__ import annotations

from geo_optimizer.cli.scoring_helpers import (
    brand_entity_score as _brand_entity_score,
)
from geo_optimizer.cli.scoring_helpers import (
    content_score as _content_score,
)
from geo_optimizer.cli.scoring_helpers import (
    llms_score as _llms_score,
)
from geo_optimizer.cli.scoring_helpers import (
    meta_score as _meta_score,
)
from geo_optimizer.cli.scoring_helpers import (
    robots_score as _robots_score,
)
from geo_optimizer.cli.scoring_helpers import (
    schema_score as _schema_score,
)
from geo_optimizer.cli.scoring_helpers import (
    signals_score as _signals_score,
)
from geo_optimizer.models.config import SCORE_BANDS, SCORING
from geo_optimizer.models.results import AuditResult

# Max scores computed dynamically from SCORING (fix #325)
_MAX_SCHEMA = sum(v for k, v in SCORING.items() if k.startswith("schema_"))
_MAX_CONTENT = sum(v for k, v in SCORING.items() if k.startswith("content_"))
_MAX_SIGNALS = sum(v for k, v in SCORING.items() if k.startswith("signals_"))
_MAX_AI_DISC = sum(v for k, v in SCORING.items() if k.startswith("ai_discovery_"))
_MAX_BRAND = sum(v for k, v in SCORING.items() if k.startswith("brand_"))


def format_audit_github(result: AuditResult) -> str:
    """Format AuditResult with GitHub Actions annotations."""
    lines = []

    # Main score
    band_labels = {
        "excellent": "EXCELLENT",
        "good": "GOOD",
        "foundation": "FOUNDATION",
        "critical": "CRITICAL",
    }
    band_label = band_labels.get(result.band, result.band.upper())

    # Fix #340: soglie allineate a SCORE_BANDS
    if result.score >= SCORE_BANDS["good"][0]:
        lines.append(f"::notice::GEO Score: {result.score}/100 ({band_label}) — {result.url}")
    elif result.score >= SCORE_BANDS["foundation"][0]:
        lines.append(f"::warning::GEO Score: {result.score}/100 ({band_label}) — {result.url}")
    else:
        lines.append(f"::error::GEO Score: {result.score}/100 ({band_label}) — {result.url}")

    # Individual checks (fix #325, #341: max dinamici + 3 categorie mancanti)
    checks = [
        ("Robots.txt", _robots_score(result), 18, result.robots.citation_bots_ok),
        ("llms.txt", _llms_score(result), 18, result.llms.found and result.llms.has_h1),
        ("Schema JSON-LD", _schema_score(result), _MAX_SCHEMA, result.schema.has_website),
        ("Meta Tags", _meta_score(result), 14, result.meta.has_title and result.meta.has_description),
        ("Content Quality", _content_score(result), _MAX_CONTENT, result.content.has_h1),
        ("Signals", _signals_score(result), _MAX_SIGNALS, bool(result.signals and result.signals.has_lang)),
        (
            "AI Discovery",
            result.score_breakdown.get("ai_discovery", 0),
            _MAX_AI_DISC,
            bool(result.ai_discovery and result.ai_discovery.has_well_known_ai),
        ),
        (
            "Brand & Entity",
            _brand_entity_score(result),
            _MAX_BRAND,
            bool(result.brand_entity and result.brand_entity.brand_name_consistent),
        ),
    ]

    for name, score, max_score, passed in checks:
        if not passed:
            lines.append(f"::warning::{name}: {score}/{max_score}")

    # Recommendations
    for rec in result.recommendations:
        lines.append(f"::warning::{rec}")

    return "\n".join(lines)


# Functions _robots_score, _llms_score, _schema_score, _meta_score, _content_score
# are imported from scoring_helpers (fix #77 — removed duplication)
