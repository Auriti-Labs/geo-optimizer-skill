"""
HTML formatter for standalone GEO audit reports.

Generates a self-contained HTML file with embedded CSS, openable
directly in the browser. Used with ``geo audit --format html``.
"""

from __future__ import annotations

import base64
import math
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from geo_optimizer.cli.scoring_helpers import (
    ai_discovery_score as _ai_discovery_score,
)
from geo_optimizer.cli.scoring_helpers import (
    brand_entity_score as _brand_entity_score,
)
from geo_optimizer.cli.scoring_helpers import category_max, category_score
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
from geo_optimizer.models.config import SCORE_BANDS
from geo_optimizer.models.results import AuditResult

_ASSETS = Path(__file__).parent / "report_assets"

# Brand kit v3 roles (light = paper and PDF, dark = screen only). Band colour per score band.
_BAND_LIGHT = {"excellent": "#0F766E", "good": "#0F766E", "foundation": "#8F5800", "critical": "#B42318"}
_BAND_DARK = {"excellent": "#2DD4BF", "good": "#2DD4BF", "foundation": "#F5B544", "critical": "#FB7185"}
_BAND_LABELS = {"excellent": "EXCELLENT", "good": "GOOD", "foundation": "FOUNDATION", "critical": "CRITICAL"}
_RING_R = 52


@lru_cache(maxsize=1)
def _font_faces() -> str:
    """@font-face for Stack Sans as data URIs, so the HTML file and weasyprint need no network (OFL 1.1)."""
    faces = ""
    for family, stem in (("Stack Sans Headline", "headline"), ("Stack Sans Text", "text")):
        data = base64.b64encode((_ASSETS / f"stack-sans-{stem}-latin.woff2").read_bytes()).decode("ascii")
        faces += (
            f'@font-face{{font-family:"{family}";src:url(data:font/woff2;base64,{data}) format("woff2");'
            "font-weight:200 700;font-style:normal}"
        )
    return faces


def format_audit_html(result: AuditResult) -> str:
    """Generate standalone HTML report with embedded CSS (also the source of the PDF)."""
    band_label = _BAND_LABELS.get(result.band) or _escape(str(result.band).upper())
    band_light = _BAND_LIGHT.get(result.band, "#4A554E")
    band_dark = _BAND_DARK.get(result.band, "#A6B0BE")

    # Build check table rows (fix #325, #341: max dinamici + 3 categorie mancanti)
    llms_label = "llms.txt"
    if result.score_version >= 2:
        llms_label += " (Other AI agents · not used by Google Search)"
    checks = [
        ("Robots.txt", _robots_score(result), category_max(result, "robots"), result.robots.citation_bots_ok),
        (
            llms_label,
            _llms_score(result),
            category_max(result, "llms"),
            result.llms.found and result.llms.has_h1,
        ),
        ("Schema JSON-LD", _schema_score(result), category_max(result, "schema"), result.schema.has_website),
        (
            "Meta Tags",
            _meta_score(result),
            category_max(result, "meta"),
            result.meta.has_title and result.meta.has_description,
        ),
        ("Content Quality", _content_score(result), category_max(result, "content"), result.content.has_h1),
        (
            "Signals",
            _signals_score(result),
            category_max(result, "signals"),
            bool(result.signals and result.signals.has_lang),
        ),
        (
            "AI Discovery",
            _ai_discovery_score(result),
            category_max(result, "ai_discovery"),
            bool(result.ai_discovery and result.ai_discovery.has_well_known_ai),
        ),
        (
            "Brand & Entity",
            _brand_entity_score(result),
            category_max(result, "brand_entity"),
            bool(result.brand_entity and result.brand_entity.brand_name_consistent),
        ),
    ]
    if "google_ai" in result.score_max:
        checks.insert(
            0,
            (
                "Google AI Search",
                category_score(result, "google_ai"),
                category_max(result, "google_ai"),
                result.google_ai.checked and not any(check.status == "fail" for check in result.google_ai.checks),
            ),
        )

    check_rows = ""
    for name, score, max_score, passed in checks:
        pct = min(100, int(score / max_score * 100)) if max_score > 0 else 0
        status = '<span class="pill pass">Pass</span>' if passed else '<span class="pill fix">Fix</span>'
        check_rows += f"""
        <tr>
            <td class="name">{_escape(name)}</td>
            <td class="num">{score}/{max_score}</td>
            <td><div class="bar-bg"><div class="bar-fill" style="width:{pct}%"></div></div></td>
            <td class="status">{status}</td>
        </tr>"""
    passed_count = sum(1 for *_, passed in checks if passed)

    # Recommendations
    recs_html = ""
    if result.recommendations:
        recs_items = "".join(f"<li>{_escape(r)}</li>" for r in result.recommendations)
        recs_html = f"""
<section class="section">
    <h2>Recommendations</h2>
    <ol class="recs">{recs_items}</ol>
</section>"""

    # Found schemas
    schemas_html = ""
    if result.schema.found_types:
        tags = " ".join(f'<span class="tag">{_escape(t)}</span>' for t in result.schema.found_types)
        schemas_html = f'<div class="schemas"><span class="label">Found schemas:</span> {tags}</div>'

    error_html = ""
    if result.error:
        error_html = (
            f'<div class="error"><strong>Audit failed:</strong> {_escape(result.error)}. The site could not be '
            "reached — every check below reflects an empty result, not a real score.</div>"
        )

    bands = " · ".join(f"{lo}–{hi} {name}" for name, (lo, hi) in SCORE_BANDS.items())
    circumference = 2 * math.pi * _RING_R
    arc = circumference * max(0, min(100, result.score)) / 100
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GEO Audit — {_escape(result.url)}</title>
<style>
{_font_faces()}
:root{{--bg:#F8FAF8;--paper:#FFFFFF;--surface:#ECF0ED;--ink:#0D110E;--muted:#4A554E;--accent:#0F766E;
--track:#D5DDD8;--hair:#E3E8E5;--pass-wash:#E2EFEC;--warn:#8F5800;--warn-wash:#EEE9DD;--bad:#B42318;
--bad-wash:#F6E4E2;--band:{band_light};color-scheme:light}}
@media screen and (prefers-color-scheme:dark){{:root{{--bg:#0B0F19;--paper:#121B29;--surface:#172334;--ink:#F1F5F9;
--muted:#A6B0BE;--accent:#2DD4BF;--track:#26324A;--hair:#26324A;--pass-wash:#173A3C;--warn:#F5B544;
--warn-wash:#25211E;--bad:#FB7185;--bad-wash:#2A1A24;--band:{band_dark};color-scheme:dark}}}}
@page{{size:A4;margin:16mm 15mm 18mm;
@bottom-left{{content:string(siteurl);font:8pt "Stack Sans Text",sans-serif;color:#4A554E}}
@bottom-right{{content:counter(page) " / " counter(pages);font:8pt "Stack Sans Text",sans-serif;color:#4A554E}}}}
*{{margin:0;padding:0;box-sizing:border-box}}
html{{background:var(--bg)}}
body{{font-family:"Stack Sans Text",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-size:15px;
line-height:1.5;color:var(--ink);background:var(--paper);max-width:820px;margin:2rem auto;padding:2.5rem;
border-radius:12px;box-shadow:0 1px 2px rgb(13 17 14/.06),0 14px 36px -10px rgb(13 17 14/.16)}}
@media print{{html{{background:#FFFFFF;font-size:12.5px}}body{{max-width:none;margin:0;padding:0;border-radius:0;box-shadow:none;
font-size:1rem}}}}
@media screen and (max-width:640px){{body{{margin:0;padding:1.25rem;border-radius:0}}
th:nth-child(3),td:nth-child(3){{display:none}}}}
h1,h2,.score-num{{font-family:"Stack Sans Headline","Stack Sans Text",sans-serif}}
h1{{font-size:1.75rem;font-weight:520;letter-spacing:-.01em;line-height:1.15}}
h2{{font-size:.72rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);
margin-bottom:.75rem}}
.kicker{{font-size:.8rem;font-weight:600;color:var(--accent);margin-bottom:.35rem}}
.header{{display:flex;align-items:center;justify-content:space-between;gap:1.5rem;padding-bottom:1.5rem;
border-bottom:1px solid var(--hair);margin-bottom:1.5rem}}
.header-text{{min-width:0}}
.url{{string-set:siteurl content();color:var(--muted);font-size:.95rem;margin-top:.4rem;overflow-wrap:anywhere}}
.meta{{color:var(--muted);font-size:.8rem;margin-top:.6rem}}
.score{{flex:none;text-align:center}}
.ring{{position:relative;width:132px;height:132px}}
.ring svg{{display:block}}
.ring-track{{stroke:var(--track)}}
.ring-arc{{stroke:var(--band)}}
.score-num{{position:absolute;top:0;left:0;width:132px;line-height:132px;text-align:center;font-size:2.6rem;
font-weight:560;font-variant-numeric:tabular-nums;color:var(--ink)}}
.band{{display:inline-block;margin-top:.5rem;font-size:.72rem;font-weight:600;letter-spacing:.08em;
color:var(--band)}}
.summary{{display:flex;gap:2rem;margin-bottom:1.75rem;font-size:.9rem;color:var(--muted)}}
.summary strong{{display:block;font-family:"Stack Sans Headline",sans-serif;font-size:1.35rem;font-weight:540;
color:var(--ink);font-variant-numeric:tabular-nums}}
.section{{margin-bottom:1.75rem}}
table{{width:100%;border-collapse:collapse}}
th{{text-align:left;font-size:.72rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
color:var(--muted);padding:0 .6rem .5rem;border-bottom:1px solid var(--hair)}}
td{{padding:.55rem .6rem;border-bottom:1px solid var(--hair);vertical-align:middle}}
tr{{page-break-inside:avoid}}
.num{{font-variant-numeric:tabular-nums;white-space:nowrap}}
.bar-bg{{background:var(--track);border-radius:3px;height:6px;width:120px}}
.bar-fill{{background:var(--accent);border-radius:3px;height:6px}}
.status{{text-align:right}}
.pill{{display:inline-block;font-size:.72rem;font-weight:600;padding:.12rem .55rem;border-radius:999px}}
.pill.pass{{background:var(--pass-wash);color:var(--accent)}}
.pill.fix{{background:var(--warn-wash);color:var(--warn)}}
.schemas{{margin-top:1rem;font-size:.85rem;line-height:2}}
.label{{color:var(--muted);margin-right:.25rem}}
.tag{{display:inline-block;background:var(--surface);padding:.05rem .5rem;border-radius:4px;font-size:.78rem;
line-height:1.6;margin:0 .15rem .15rem 0}}
.recs{{list-style:none;counter-reset:rec}}
.recs li{{counter-increment:rec;position:relative;padding:.6rem 0 .6rem 2.25rem;border-bottom:1px solid var(--hair);
page-break-inside:avoid}}
.recs li::before{{content:counter(rec);position:absolute;left:0;top:.6rem;width:1.5rem;height:1.5rem;
line-height:1.5rem;text-align:center;border-radius:50%;background:var(--pass-wash);color:var(--accent);
font-size:.75rem;font-weight:600}}
.error{{background:var(--bad-wash);color:var(--ink);border-left:3px solid var(--bad);padding:1rem;
margin-bottom:1.5rem;border-radius:4px}}
.error strong{{color:var(--bad)}}
.footer{{margin-top:2rem;padding-top:1rem;border-top:1px solid var(--hair);color:var(--muted);font-size:.8rem}}
.footer a{{color:var(--accent)}}
</style>
</head>
<body>
{error_html}
<header class="header">
    <div class="header-text">
        <div class="kicker">GEO Optimizer</div>
        <h1>GEO Audit Report</h1>
        <div class="url">{_escape(result.url)}</div>
        <div class="meta">Score rubric v{int(result.score_version)} · Bands: {bands}</div>
    </div>
    <div class="score">
        <div class="ring">
            <svg width="132" height="132" viewBox="0 0 132 132" aria-hidden="true">
                <circle class="ring-track" cx="66" cy="66" r="{_RING_R}" fill="none" stroke="#D5DDD8" stroke-width="10"/>
                <circle class="ring-arc" cx="66" cy="66" r="{_RING_R}" fill="none" stroke="{band_light}" stroke-width="10"
                    stroke-linecap="round" stroke-dasharray="{arc:.1f} {circumference:.1f}"
                    transform="rotate(-90 66 66)"/>
            </svg>
            <div class="score-num">{int(result.score)}</div>
        </div>
        <div class="band">{band_label}</div>
    </div>
</header>

<div class="summary">
    <div><strong>{passed_count}/{len(checks)}</strong>key checks passed</div>
    <div><strong>{len(result.recommendations)}</strong>recommendations</div>
</div>

<section class="section">
    <h2>Check Results</h2>
    <table>
        <thead>
            <tr><th>Check</th><th>Score</th><th>Progress</th><th class="status">Status</th></tr>
        </thead>
        <tbody>{check_rows}
        </tbody>
    </table>
    {schemas_html}
</section>
{recs_html}

<footer class="footer">
    Generated on {timestamp} by
    <a href="https://github.com/auriti-labs/geo-optimizer-skill">GEO Optimizer</a>
</footer>
</body>
</html>"""


def _escape(text: str) -> str:
    """Escape special HTML characters (fix #20: usa html.escape standard)."""
    import html as _html

    return _html.escape(text, quote=True)


# Functions _robots_score, _llms_score, _schema_score, _meta_score, _content_score
# are imported from scoring_helpers (fix #77 — removed duplication)
