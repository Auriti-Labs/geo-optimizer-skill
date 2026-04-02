"""
HTML formatter for standalone GEO audit reports.

Generates a self-contained HTML file with embedded CSS, openable
directly in the browser. Used with ``geo audit --format html``.
"""

from __future__ import annotations

from datetime import datetime, timezone

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
from geo_optimizer.models.config import SCORING
from geo_optimizer.models.results import AuditResult

# Max scores computed dynamically from SCORING (fix #325)
_MAX_SCHEMA = sum(v for k, v in SCORING.items() if k.startswith("schema_"))
_MAX_CONTENT = sum(v for k, v in SCORING.items() if k.startswith("content_"))
_MAX_SIGNALS = sum(v for k, v in SCORING.items() if k.startswith("signals_"))
_MAX_AI_DISC = sum(v for k, v in SCORING.items() if k.startswith("ai_discovery_"))
_MAX_BRAND = sum(v for k, v in SCORING.items() if k.startswith("brand_"))


def format_audit_html(result: AuditResult) -> str:
    """Generate standalone HTML report with embedded CSS."""
    band_colors = {
        "excellent": "#22c55e",
        "good": "#06b6d4",
        "foundation": "#eab308",
        "critical": "#ef4444",
    }
    band_labels = {
        "excellent": "EXCELLENT",
        "good": "GOOD",
        "foundation": "FOUNDATION",
        "critical": "CRITICAL",
    }
    color = band_colors.get(result.band, "#888")
    band_label = band_labels.get(result.band, result.band.upper())

    # Build check table rows (fix #325, #341: max dinamici + 3 categorie mancanti)
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

    check_rows = ""
    for name, score, max_score, passed in checks:
        icon = "✅" if passed else "❌"
        pct = int(score / max_score * 100) if max_score > 0 else 0
        check_rows += f"""
        <tr>
            <td>{name}</td>
            <td>{score}/{max_score}</td>
            <td>
                <div class="bar-bg"><div class="bar-fill" style="width:{pct}%"></div></div>
            </td>
            <td class="status">{icon}</td>
        </tr>"""

    # Recommendations
    recs_html = ""
    if result.recommendations:
        recs_items = "".join(f"<li>{_escape(r)}</li>" for r in result.recommendations)
        recs_html = f"""
        <div class="section">
            <h2>Recommendations</h2>
            <ol>{recs_items}</ol>
        </div>"""

    # Found schemas
    schemas_html = ""
    if result.schema.found_types:
        tags = " ".join(f'<span class="tag">{_escape(t)}</span>' for t in result.schema.found_types)
        schemas_html = f'<div class="schemas">Found schemas: {tags}</div>'

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GEO Audit — {_escape(result.url)}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
background:#0f172a;color:#e2e8f0;padding:2rem;max-width:800px;margin:0 auto}}
h1{{font-size:1.5rem;margin-bottom:.5rem}}
h2{{font-size:1.1rem;margin-bottom:.75rem;color:#94a3b8}}
.header{{text-align:center;margin-bottom:2rem}}
.url{{color:#94a3b8;font-size:.9rem;word-break:break-all}}
.score-ring{{display:inline-flex;align-items:center;justify-content:center;
width:140px;height:140px;border-radius:50%;border:6px solid {color};
margin:1.5rem 0;font-size:2.5rem;font-weight:700;color:{color}}}
.band{{font-size:1.1rem;font-weight:600;color:{color};margin-bottom:1rem}}
.section{{background:#1e293b;border-radius:8px;padding:1.25rem;margin-bottom:1rem}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:.5rem .75rem;text-align:left}}
th{{color:#94a3b8;font-weight:500;font-size:.85rem;border-bottom:1px solid #334155}}
td{{border-bottom:1px solid #1e293b}}
.bar-bg{{background:#334155;border-radius:4px;height:8px;width:100px}}
.bar-fill{{background:{color};border-radius:4px;height:8px;transition:width .3s}}
.status{{text-align:center}}
.tag{{display:inline-block;background:#334155;padding:.15rem .5rem;border-radius:4px;
font-size:.8rem;margin:.15rem}}
.schemas{{margin-top:.75rem}}
ol{{padding-left:1.5rem}}
li{{margin-bottom:.4rem;line-height:1.5}}
.footer{{text-align:center;margin-top:2rem;color:#64748b;font-size:.8rem}}
.footer a{{color:#60a5fa}}
</style>
</head>
<body>
<div class="header">
    <h1>GEO Audit Report</h1>
    <div class="url">{_escape(result.url)}</div>
    <div class="score-ring">{result.score}</div>
    <div class="band">{band_label}</div>
</div>

<div class="section">
    <h2>Check Results</h2>
    <table>
        <thead>
            <tr><th>Check</th><th>Score</th><th>Progress</th><th>Status</th></tr>
        </thead>
        <tbody>{check_rows}
        </tbody>
    </table>
    {schemas_html}
</div>

{recs_html}

<div class="footer">
    Generated on {timestamp} by
    <a href="https://github.com/auriti-labs/geo-optimizer-skill">GEO Optimizer</a>
</div>
</body>
</html>"""


def _escape(text: str) -> str:
    """Escape special HTML characters (fix #20: usa html.escape standard)."""
    import html as _html

    return _html.escape(text, quote=True)


# Functions _robots_score, _llms_score, _schema_score, _meta_score, _content_score
# are imported from scoring_helpers (fix #77 — removed duplication)
