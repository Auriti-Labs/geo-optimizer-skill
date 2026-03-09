"""
Formatter GitHub Actions per output audit GEO.

Genera output con annotazioni ``::notice`` e ``::warning`` per
integrazione nativa con GitHub Actions. Usato con ``geo audit --format github``.
"""

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
from geo_optimizer.models.results import AuditResult


def format_audit_github(result: AuditResult) -> str:
    """Formatta AuditResult con annotazioni GitHub Actions."""
    lines = []

    # Score principale
    band_labels = {
        "excellent": "EXCELLENT",
        "good": "GOOD",
        "foundation": "FOUNDATION",
        "critical": "CRITICAL",
    }
    band_label = band_labels.get(result.band, result.band.upper())

    if result.score >= 71:
        lines.append(f"::notice::GEO Score: {result.score}/100 ({band_label}) — {result.url}")
    elif result.score >= 41:
        lines.append(f"::warning::GEO Score: {result.score}/100 ({band_label}) — {result.url}")
    else:
        lines.append(f"::error::GEO Score: {result.score}/100 ({band_label}) — {result.url}")

    # Check individuali
    checks = [
        ("Robots.txt", _robots_score(result), 20, result.robots.citation_bots_ok),
        ("llms.txt", _llms_score(result), 20, result.llms.found and result.llms.has_h1),
        ("Schema JSON-LD", _schema_score(result), 25, result.schema.has_website),
        ("Meta Tags", _meta_score(result), 20, result.meta.has_title and result.meta.has_description),
        ("Content Quality", _content_score(result), 15, result.content.has_h1),
    ]

    for name, score, max_score, passed in checks:
        if not passed:
            lines.append(f"::warning::{name}: {score}/{max_score}")

    # Raccomandazioni
    for rec in result.recommendations:
        lines.append(f"::warning::{rec}")

    return "\n".join(lines)


# Le funzioni _robots_score, _llms_score, _schema_score, _meta_score, _content_score
# sono importate da scoring_helpers (fix #77 — eliminata duplicazione)
