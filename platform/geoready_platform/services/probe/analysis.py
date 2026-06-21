"""Per-response signal extraction. Pure, no I/O.

Given one AI answer (text + cited source URLs) and the entity's identity,
derive: was the brand mentioned, was the brand's domain cited, and which other
domains/competitors were named. Domain normalization reuses the engine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse


@dataclass
class ResponseSignals:
    brand_mentioned: bool = False
    domain_cited: bool = False
    competitor_domains: list[str] = field(default_factory=list)
    competitor_names: list[str] = field(default_factory=list)


def normalize_domain(value: str) -> str:
    """Lowercase registrable-ish domain, stripping scheme/www/path."""
    try:
        from geo_optimizer.core.citations import normalize_domain as engine_norm

        return engine_norm(value)
    except Exception:  # noqa: BLE001 — fallback keeps this module importable standalone
        v = value.strip().lower()
        if "://" in v:
            v = urlparse(v).netloc or v
        v = v.split("/")[0]
        return v[4:] if v.startswith("www.") else v


def analyze_response(
    *,
    text: str,
    citations: list[str],
    name: str,
    domain: str,
    competitor_names: list[str] | None = None,
) -> ResponseSignals:
    text = text or ""
    own = normalize_domain(domain)
    cited = [normalize_domain(c) for c in (citations or []) if c]

    brand_mentioned = bool(name) and re.search(re.escape(name), text, re.IGNORECASE) is not None
    domain_cited = own in cited if own else False
    competitor_domains = sorted({d for d in cited if d and d != own})

    matched_names = [
        comp
        for comp in competitor_names_list(competitor_names)
        if re.search(re.escape(comp), text, re.IGNORECASE)
    ]

    return ResponseSignals(
        brand_mentioned=brand_mentioned,
        domain_cited=domain_cited,
        competitor_domains=competitor_domains,
        competitor_names=sorted(set(matched_names)),
    )


def competitor_names_list(value: list[str] | None) -> list[str]:
    return [c.strip() for c in (value or []) if c and c.strip()]
