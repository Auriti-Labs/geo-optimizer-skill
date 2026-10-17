"""Render assets/benchmark.svg from GeoReady's public benchmark endpoint.

The endpoint returns aggregates only (median, average, llms.txt and JSON-LD adoption,
sample size label), so the chart never carries a domain or an identifier. Re-run it
when the README numbers are refreshed:

    python scripts/render_benchmark_chart.py            # writes assets/benchmark.svg
    python scripts/render_benchmark_chart.py --print    # prints the numbers only
"""

from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ENDPOINT = "https://geoready.dev/api/public/benchmark"
OUT = Path(__file__).resolve().parent.parent / "assets" / "benchmark.svg"

# Score bands as published in the README: (label, first point, last point, fill)
BANDS = [
    ("Critical", 0, 35, "#F4C7C3"),
    ("Foundation", 36, 67, "#F7E1A8"),
    ("Good", 68, 85, "#BFE6E1"),
    ("Excellent", 86, 100, "#7CCFC5"),
]
X0, WIDTH = 40, 720  # horizontal extent of the 0-100 scale and of the 0-100 % bars
TEAL, INK, MUTED = "#0B8076", "#17201f", "#4a5654"


def fetch() -> dict:
    with urllib.request.urlopen(ENDPOINT, timeout=20) as response:  # noqa: S310 - fixed https URL
        return json.load(response)


def x_of(points: float) -> float:
    return X0 + WIDTH * points / 100


def render(data: dict) -> str:
    median, average = data["score"]["median"], data["score"]["average"]
    llms, schema = data["adoption"]["llms_txt"] * 100, data["adoption"]["schema_jsonld"] * 100
    sample = data["sample_size_label"]
    day = datetime.fromisoformat(data["updated_at"]).strftime("%-d %B %Y")

    # Each band runs from its first point to the next band's first point; the last ends at 100
    edges = [lo for _, lo, _, _ in BANDS] + [100]
    bands = "".join(
        f'<rect x="{x_of(edges[i]):.1f}" y="92" width="{x_of(edges[i + 1]) - x_of(edges[i]):.1f}" height="40" fill="{fill}"/>'
        f'<text x="{(x_of(edges[i]) + x_of(edges[i + 1])) / 2:.1f}" y="108" text-anchor="middle" font-size="13" fill="{INK}">{label}</text>'
        f'<text x="{(x_of(edges[i]) + x_of(edges[i + 1])) / 2:.1f}" y="124" text-anchor="middle" font-size="12" fill="{MUTED}">{lo}\u2013{hi}</text>'
        for i, (label, lo, hi, fill) in enumerate(BANDS)
    )
    bars = "".join(
        f'<text x="{X0}" y="{y}" font-size="14" fill="{INK}">{label}</text>'
        f'<rect x="{X0}" y="{y + 8}" width="{WIDTH}" height="16" rx="3" fill="#E4E7E6"/>'
        f'<rect x="{X0}" y="{y + 8}" width="{WIDTH * pct / 100:.1f}" height="16" rx="3" fill="{TEAL}"/>'
        f'<text x="{X0 + WIDTH}" y="{y}" text-anchor="end" font-size="14" font-weight="700" fill="{INK}">{pct:.0f}%</text>'
        for label, pct, y in (
            ("Publish an llms.txt file", llms, 196),
            ("Ship JSON-LD structured data", schema, 246),
        )
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 352" width="800" height="352" \
font-family="system-ui,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif" role="img" \
aria-labelledby="t d">
<title id="t">Where {sample} stand on AI readiness</title>
<desc id="d">Median score {median:g} out of 100, average {average:g}. {llms:.0f}% publish an llms.txt file and {schema:.0f}% ship JSON-LD structured data. Latest audit per domain on {day}; self-selected sample.</desc>
<rect width="800" height="352" rx="10" fill="#F6F5F1" stroke="#D9D7CF"/>
<text x="{X0}" y="38" font-size="20" font-weight="700" fill="{INK}">Where {sample} stand on AI readiness</text>
<text x="{X0}" y="60" font-size="13" fill="{MUTED}">GEO score, 0–100, one latest audit per domain</text>
{bands}
<path d="M{x_of(median):.1f} 90 l-6 -9 h12 z" fill="{INK}"/>
<text x="{x_of(median):.1f}" y="76" text-anchor="middle" font-size="13" font-weight="700" fill="{INK}">median {median:g}</text>
<path d="M{x_of(average):.1f} 134 l-6 9 h12 z" fill="{MUTED}"/>
<text x="{x_of(average):.1f}" y="158" text-anchor="middle" font-size="13" fill="{MUTED}">average {average:g}</text>
{bars}
<text x="{X0}" y="298" font-size="12" fill="{MUTED}">Source: GeoReady public benchmark, {day}. Scheduled re-audits excluded.</text>
<text x="{X0}" y="316" font-size="12" fill="{MUTED}">Self-selected sample: directional, not a census of the web.</text>
<text x="{X0}" y="338" font-size="13" font-weight="700" fill="{TEAL}">Check where your site lands: geoready.dev</text>
</svg>
"""


if __name__ == "__main__":
    benchmark = fetch()
    if "--print" in sys.argv:
        print(json.dumps(benchmark, indent=2))
    else:
        OUT.write_text(render(benchmark), encoding="utf-8")
        print(f"wrote {OUT}")
