"""
Dynamic SVG badge generator for GEO Score.

Generates a Shields.io-style SVG badge with the site's GEO Score.
Embeddable in README, footer, portfolio.

Usage in Markdown:
    [![GEO Score](https://geo.auritidesign.it/badge?url=https://yoursite.com)](https://geo.auritidesign.it/)
"""

from __future__ import annotations

import html as html_lib

# Colors per score band
BAND_COLORS = {
    "excellent": "#22c55e",  # Dark green
    "good": "#06b6d4",  # Cyan
    "foundation": "#eab308",  # Orange
    "critical": "#ef4444",  # Red
}

# Explicit text label whitelist for each band — no external values allowed
BAND_LABELS = {
    "excellent": "Excellent",
    "good": "Good",
    "foundation": "Foundation",
    "critical": "Critical",
}

# Maximum label length (in already-escaped text characters) to prevent abuse
_MAX_LABEL_LENGTH = 50


def _svg_escape(text: str) -> str:
    """Escape special XML/SVG characters to prevent XSS.

    Converts <, >, &, " and ' to the corresponding XML entities.
    """
    return html_lib.escape(text, quote=True)


def generate_badge_svg(score: int, band: str, label: str = "GEO Score", error: bool = False) -> str:
    """Generate SVG badge with score and band color.

    Args:
        score: Score 0-100.
        band: Band (excellent, good, foundation, critical).
        label: Left-side badge label (max 50 chars, sanitized).
        error: If True, shows "Error" with grey color instead of the score.
               Fix #152: avoids "0/100 CRITICAL" badge on audit errors.

    Returns:
        Complete SVG string.
    """
    # Fix #152: if audit fails, show error badge with grey color
    if error:
        color = "#999999"
        score_text = "Error"
        # Validate band and label normally (for the left part of the badge)
        if band not in BAND_COLORS:
            band = "critical"
        safe_label = _svg_escape(label)
        safe_label = safe_label[:_MAX_LABEL_LENGTH]
        # Fix #458: use safe_label (post-escape) for width, not raw label
        label_width = len(safe_label) * 6.5 + 12
        score_width = len(score_text) * 7 + 12
        total_width = label_width + score_width
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20" role="img" aria-label="{safe_label}: {score_text}">
  <title>{safe_label}: {score_text}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{total_width}" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_width}" height="20" fill="#555"/>
    <rect x="{label_width}" width="{score_width}" height="20" fill="{color}"/>
    <rect width="{total_width}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="11">
    <text aria-hidden="true" x="{label_width / 2}" y="15" fill="#010101" fill-opacity=".3">{safe_label}</text>
    <text x="{label_width / 2}" y="14">{safe_label}</text>
    <text aria-hidden="true" x="{label_width + score_width / 2}" y="15" fill="#010101" fill-opacity=".3">{score_text}</text>
    <text x="{label_width + score_width / 2}" y="14">{score_text}</text>
  </g>
</svg>"""

    # Validate band against whitelist
    if band not in BAND_COLORS:
        band = "critical"
    color = BAND_COLORS[band]

    # Clamp score to valid range
    score = max(0, min(100, score))
    score_text = f"{score}/100"

    # Sanitize BEFORE truncating: so the escape is never split in the middle.
    # Example: "&amp;" is safe as a unit; truncating after guarantees that
    # the final text contains only complete XML entities.
    safe_label = _svg_escape(label)
    safe_label = safe_label[:_MAX_LABEL_LENGTH]

    # Fix #15: calculate width on post-escape text (the one actually rendered)
    label_width = len(safe_label) * 6.5 + 12
    score_width = len(score_text) * 7 + 12
    total_width = label_width + score_width

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20" role="img" aria-label="{safe_label}: {score_text}">
  <title>{safe_label}: {score_text}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{total_width}" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_width}" height="20" fill="#555"/>
    <rect x="{label_width}" width="{score_width}" height="20" fill="{color}"/>
    <rect width="{total_width}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="11">
    <text aria-hidden="true" x="{label_width / 2}" y="15" fill="#010101" fill-opacity=".3">{safe_label}</text>
    <text x="{label_width / 2}" y="14">{safe_label}</text>
    <text aria-hidden="true" x="{label_width + score_width / 2}" y="15" fill="#010101" fill-opacity=".3">{score_text}</text>
    <text x="{label_width + score_width / 2}" y="14">{score_text}</text>
  </g>
</svg>"""
