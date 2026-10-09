"""
Google AI readiness — check deterministici contro la documentazione ufficiale Google.

Modulo puro: nessun fetch, nessuna stampa. Riceve soup, header e URL finale
già scaricati da audit.py e ritorna ReadinessCheck con fonte ed evidenza.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from geo_optimizer.models.config import (
    DATA_NOSNIPPET_FAIL_RATIO,
    DATA_NOSNIPPET_WARN_RATIO,
    GOOGLE_AI_POINTS,
    GOOGLE_AI_SNIPPET_MIN,
    GOOGLE_DOC_URLS,
)
from geo_optimizer.models.results import GoogleAiReadinessResult, ReadinessCheck

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


def _parse_date(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        d = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def check_dates(soup, schemas: list[dict], now: datetime) -> ReadinessCheck:
    dates = [_parse_date(s.get(k)) for s in schemas if isinstance(s, dict) for k in ("datePublished", "dateModified")]
    valid = [d for d in dates if d]
    if any(d > now + timedelta(days=1) for d in valid):
        return _check("G-DATES", "fail", "Future datePublished/dateModified: Google may ignore the page dates")
    visible = soup.find("time", attrs={"datetime": True}) or soup.find(
        "meta", attrs={"property": re.compile(r"^article:(published|modified)_time$")}
    )
    if valid and visible:
        return _check("G-DATES", "pass", "Visible date consistent with structured data")
    if valid:
        return _check("G-DATES", "warn", "Date only in structured data: show it on the page too")
    return _check("G-DATES", "warn", "No valid publication or update date found", "heuristic")


def check_byline(soup, schemas: list[dict]) -> ReadinessCheck:
    for s in schemas:
        authors = s.get("author") if isinstance(s, dict) else None
        for a in authors if isinstance(authors, list) else [authors]:
            name = a.get("name") if isinstance(a, dict) else a
            if isinstance(name, str) and name.strip():
                return _check("G-BYLINE", "pass", "Author declared in structured data")
    if soup.select_one('[rel~="author"], [itemprop="author"], .author, meta[name="author"]'):
        return _check("G-BYLINE", "pass", "Visible author byline")
    return _check("G-BYLINE", "warn", "No author found: Google asks 'who created the content'", "heuristic")


def check_links(soup) -> ReadinessCheck:
    hrefs = [a["href"].strip() for a in soup.find_all("a", href=True)]
    bad = [h for h in hrefs if h.startswith("#/") or h.lower().startswith("javascript:")]
    if not hrefs or len(bad) * 2 > len(hrefs):
        return _check("G-LINKS", "fail", "Links are not crawlable <a href> elements (JS routes or none)")
    return _check("G-LINKS", "pass", f"{len(hrefs) - len(bad)} crawlable <a href> links")


def check_viewport(soup) -> ReadinessCheck:
    if soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.IGNORECASE)}):
        return _check("G-VIEWPORT", "pass", "meta viewport present")
    return _check("G-VIEWPORT", "fail", "No meta viewport: page is not mobile-friendly")


def check_sitemap(robots) -> ReadinessCheck:
    # Solo dichiarazione in robots.txt, nessun fetch della sitemap.
    if robots.sitemaps:
        return _check("G-SITEMAP", "pass", f"Sitemap declared: {robots.sitemaps[0]}")
    if robots.found:
        return _check("G-SITEMAP", "warn", "robots.txt has no Sitemap: directive")
    return _check("G-SITEMAP", "fail", "No robots.txt, no declared sitemap")


def run_google_ai_checks(
    soup,
    *,
    final_url: str,
    http_status: int,
    headers: dict,
    robots,
    schemas: list[dict],
    now: datetime | None = None,
) -> GoogleAiReadinessResult:
    """Esegue tutti i check G-* e somma i punti della categoria google_ai."""
    now = now or datetime.now(timezone.utc)
    directives = parse_robots_directives(soup, headers or {})
    checks = [
        check_index(http_status, directives, robots),
        check_snippet(soup, directives),
        check_canonical(soup, final_url, directives),
        check_dates(soup, schemas, now),
        check_byline(soup, schemas),
        check_links(soup),
        check_viewport(soup),
        check_sitemap(robots),
        _check("G-GENAI-CONTROL", "manual", "Check Search Console > Settings > Search generative AI control"),
    ]
    return GoogleAiReadinessResult(
        checked=True,
        points=sum(c.points for c in checks),
        max_points=sum(c.max_points for c in checks),
        final_url=final_url,
        checks=checks,
    )
