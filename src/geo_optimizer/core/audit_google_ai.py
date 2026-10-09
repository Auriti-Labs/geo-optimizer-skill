"""
Google AI readiness — check deterministici contro la documentazione ufficiale Google.

Modulo puro: nessun fetch, nessuna stampa. Riceve soup, header e URL finale
già scaricati da audit.py e ritorna ReadinessCheck con fonte ed evidenza.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from geo_optimizer.models.config import (
    DATA_NOSNIPPET_FAIL_RATIO,
    DATA_NOSNIPPET_WARN_RATIO,
    GOOGLE_AI_POINTS,
    GOOGLE_AI_SNIPPET_MIN,
    GOOGLE_DOC_URLS,
)
from geo_optimizer.models.results import ReadinessCheck

_HEADER_UA_PREFIX_RE = re.compile(r"^\s*([a-z0-9_-]+)\s*:\s*(.*)$", re.IGNORECASE)
_KNOWN_DIRECTIVES = (
    "noindex",
    "nosnippet",
    "none",
    "max-snippet",
    "max-image-preview",
    "noarchive",
    "notranslate",
    "noimageindex",
    "unavailable_after",
    "indexifembedded",
    "all",
    "index",
    "follow",
    "nofollow",
)


def _check(cid: str, status: str, evidence: str, level: str = "google-official") -> ReadinessCheck:
    max_points = GOOGLE_AI_POINTS.get(cid, 0)
    points = {"pass": max_points, "warn": max_points // 2}.get(status, 0)
    return ReadinessCheck(cid, status, points, max_points, evidence, GOOGLE_DOC_URLS[cid], level)


def _split(value: str) -> set[str]:
    return {p.strip().lower().replace(" ", "") for p in value.split(",") if p.strip()}


def parse_robots_directives(soup, headers: dict[str, str]) -> set[str]:
    """Direttive valide per Googlebot da meta robots/googlebot e X-Robots-Tag."""
    out: set[str] = set()
    for tag in soup.find_all("meta", attrs={"name": re.compile(r"^(robots|googlebot)$", re.IGNORECASE)}):
        out |= _split(tag.get("content", ""))
    raw = next((v for k, v in headers.items() if k.lower() == "x-robots-tag"), "")
    # Più valori X-Robots-Tag arrivano concatenati da virgole; "ua: dir" si applica solo a quel bot
    for chunk in re.split(r",(?=\s*[a-z0-9_-]+\s*:)", raw, flags=re.IGNORECASE):
        m = _HEADER_UA_PREFIX_RE.match(chunk)
        if m and not m.group(1).lower().startswith(_KNOWN_DIRECTIVES):
            if m.group(1).lower() != "googlebot":
                continue
            chunk = m.group(2)
        out |= _split(chunk)
    if "none" in out:
        out |= {"noindex", "nofollow"}
    return out


def check_index(http_status: int, directives: set[str], robots) -> ReadinessCheck:
    if http_status != 200:
        return _check("G-INDEX", "fail", f"HTTP {http_status}: only 200 pages can be indexed and used in AI features")
    if "noindex" in directives:
        return _check("G-INDEX", "fail", "noindex in meta robots or X-Robots-Tag: page excluded from Search and AI")
    if "Googlebot" in robots.bots_blocked:
        return _check("G-INDEX", "fail", "Googlebot blocked in robots.txt")
    return _check("G-INDEX", "pass", "HTTP 200, indexable, Googlebot allowed")


def _visible_words(node) -> int:
    # Il testo di script/style non è contenuto visibile: gonfierebbe il totale e nasconderebbe data-nosnippet
    if not node:
        return 0
    texts = node.find_all(string=True)
    return sum(len(t.split()) for t in texts if t.parent.name not in {"script", "style", "noscript", "template"})


def check_snippet(soup, directives: set[str]) -> ReadinessCheck:
    if "nosnippet" in directives:
        return _check("G-SNIPPET", "fail", "nosnippet: Google cannot quote this page in AI Overviews / AI Mode")
    for d in directives:
        if d.startswith("max-snippet:"):
            try:
                n = int(d.split(":", 1)[1])
            except ValueError:
                continue
            if 0 <= n < GOOGLE_AI_SNIPPET_MIN:
                return _check("G-SNIPPET", "fail", f"max-snippet:{n} leaves no usable passage for AI answers")
    body = soup.body or soup
    total = _visible_words(body)
    hidden = sum(
        _visible_words(n) for n in body.select("[data-nosnippet]") if not n.find_parent(attrs={"data-nosnippet": True})
    )
    ratio = hidden / total if total else 0.0
    if ratio > DATA_NOSNIPPET_FAIL_RATIO:
        return _check("G-SNIPPET", "fail", f"data-nosnippet hides {ratio:.0%} of the page text")
    if ratio > DATA_NOSNIPPET_WARN_RATIO:
        return _check("G-SNIPPET", "warn", f"data-nosnippet hides {ratio:.0%} of the page text")
    if "max-image-preview:none" in directives:
        return _check("G-SNIPPET", "warn", "max-image-preview:none: no image previews in AI results")
    return _check("G-SNIPPET", "pass", "No snippet restrictions")


def _norm(url: str) -> str:
    p = urlsplit(url)
    query = f"?{p.query}" if p.query else ""
    return f"{p.scheme.lower()}://{p.netloc.lower()}{p.path.rstrip('/') or '/'}{query}"


def check_canonical(soup, final_url: str, directives: set[str]) -> ReadinessCheck:
    # Google ignora rel=canonical fuori da <head>
    head = soup.head or soup
    links = [t for t in head.find_all("link", href=True) if "canonical" in [r.lower() for r in (t.get("rel") or [])]]
    if not links:
        return _check("G-CANONICAL", "fail", "No rel=canonical: Google picks the canonical on its own")
    hrefs = {t["href"].strip() for t in links}
    if len(hrefs) > 1:
        return _check("G-CANONICAL", "fail", f"{len(hrefs)} conflicting canonical URLs: Google ignores them all")
    href = hrefs.pop()
    if not href.lower().startswith(("http://", "https://")):
        return _check("G-CANONICAL", "warn", f"Relative canonical '{href}': use an absolute URL")
    if "noindex" in directives:
        return _check("G-CANONICAL", "warn", "canonical together with noindex sends conflicting signals")
    if _norm(href) != _norm(final_url):
        return _check("G-CANONICAL", "warn", f"Canonical points elsewhere: {href}")
    return _check("G-CANONICAL", "pass", "One absolute canonical matching the final URL")
