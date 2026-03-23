"""
GEO Audit business logic.

Extracted from scripts/geo_audit.py. All functions return dataclasses
instead of printing — the CLI layer handles display and formatting.
"""

from __future__ import annotations

import json
import logging
import re
from urllib.parse import urljoin, urlparse

from geo_optimizer.models.config import (  # noqa: F401 (VALUABLE_SCHEMAS re-exported)
    AI_BOTS,
    CITATION_BOTS,
    CONTENT_MIN_WORDS,
    SCORE_BANDS,
    SCORING,
    VALUABLE_SCHEMAS,
)
from geo_optimizer.models.results import (
    AuditResult,
    CachedResponse,
    CitabilityResult,
    ContentResult,
    LlmsTxtResult,
    MetaResult,
    RobotsResult,
    SchemaResult,
)
from geo_optimizer.utils.http import fetch_url
from geo_optimizer.utils.robots_parser import classify_bot, parse_robots_txt


def audit_robots_txt(base_url: str, bots: dict = None) -> RobotsResult:
    """Check robots.txt for AI bot access. Returns RobotsResult.

    Args:
        base_url: URL base del sito.
        bots: Dizionario bot da verificare. Default: AI_BOTS da config.
              Fix #120: permette di passare bot aggiuntivi da project_config.extra_bots.
    """
    robots_url = urljoin(base_url, "/robots.txt")
    r, err = fetch_url(robots_url)

    result = RobotsResult()

    if err or not r:
        return result

    # Solo risposte 200 sono robots.txt validi (403, 500, ecc. non lo sono)
    if r.status_code != 200:
        return result

    result.found = True

    content = r.text

    # Parse robots.txt into structured rules
    agent_rules = parse_robots_txt(content)

    # Usa i bot forniti oppure il default AI_BOTS
    effective_bots = bots if bots is not None else AI_BOTS

    # Classifica ogni AI bot
    for bot, description in effective_bots.items():
        bot_status = classify_bot(bot, description, agent_rules)

        if bot_status.status == "missing":
            result.bots_missing.append(bot)
        elif bot_status.status == "blocked":
            result.bots_blocked.append(bot)
        elif bot_status.status == "partial":
            # #106 — Parzialmente bloccato: lo trattiamo come allowed per compatibilità
            # ma lo tracciamo separatamente in bots_partial
            result.bots_allowed.append(bot)
            result.bots_partial.append(bot)
        else:
            # "allowed" (pienamente consentito)
            result.bots_allowed.append(bot)

    # Check citation bots (allowed include anche partial)
    result.citation_bots_ok = all(b in result.bots_allowed for b in CITATION_BOTS)

    # #111 — Verifica che i citation bot siano consentiti ESPLICITAMENTE (non solo wildcard)
    # Score pieno solo con regole specifiche per i citation bot
    citation_explicit = []
    for bot in CITATION_BOTS:
        bot_status = classify_bot(bot, "", agent_rules)
        if bot_status.status in ("allowed", "partial") and not bot_status.via_wildcard:
            citation_explicit.append(bot)
    result.citation_bots_explicit = len(citation_explicit) == len(CITATION_BOTS)

    return result


def audit_llms_txt(base_url: str) -> LlmsTxtResult:
    """Check for presence and quality of llms.txt. Returns LlmsTxtResult."""
    llms_url = urljoin(base_url, "/llms.txt")
    r, err = fetch_url(llms_url)

    result = LlmsTxtResult()

    if err or not r:
        return result

    # Solo risposte 200 contengono llms.txt valido
    if r.status_code != 200:
        return result

    result.found = True
    # Rimuovi BOM UTF-8 se presente (es. file generati da Yoast SEO)
    content = r.text.lstrip("\ufeff")
    lines = content.splitlines()
    result.word_count = len(content.split())

    # Check H1 (required)
    h1_lines = [line for line in lines if line.startswith("# ")]
    if h1_lines:
        result.has_h1 = True

    # Check blockquote description
    blockquotes = [line for line in lines if line.startswith("> ")]
    if blockquotes:
        result.has_description = True

    # Check H2 sections
    h2_lines = [line for line in lines if line.startswith("## ")]
    if h2_lines:
        result.has_sections = True

    # Check markdown links
    links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
    if links:
        result.has_links = True

    return result


def audit_schema(soup, url: str) -> SchemaResult:
    """Check JSON-LD schema on homepage. Returns SchemaResult."""
    result = SchemaResult()

    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    if not scripts:
        return result

    for script in scripts:
        try:
            # script.string può essere None se il tag ha nodi figli multipli
            raw = script.string
            if not raw:
                raw = script.get_text()
            if not raw or not raw.strip():
                continue
            data = json.loads(raw)
            schemas = data if isinstance(data, list) else [data]

            for schema in schemas:
                schema_type = schema.get("@type", "unknown")
                if isinstance(schema_type, list):
                    schema_types = schema_type
                else:
                    schema_types = [schema_type]

                # Aggiungi lo schema raw una sola volta (non per ogni tipo)
                result.raw_schemas.append(schema)

                for t in schema_types:
                    result.found_types.append(t)

                    if t == "WebSite":
                        result.has_website = True
                    elif t == "WebApplication":
                        result.has_webapp = True
                    elif t == "FAQPage":
                        result.has_faq = True
                    elif t in ("Article", "BlogPosting", "NewsArticle"):
                        result.has_article = True
                    elif t == "Organization":
                        result.has_organization = True

        except json.JSONDecodeError as exc:
            # Parsing fallito: logga a debug (non critico, script di terze parti) — fix #81
            logging.debug("Schema JSON non valido ignorato: %s", exc)

    return result


def audit_meta_tags(soup, url: str) -> MetaResult:
    """Check SEO/GEO meta tags. Returns MetaResult."""
    result = MetaResult()

    # Title
    title_tag = soup.find("title")
    if title_tag and title_tag.text.strip():
        result.has_title = True
        result.title_text = title_tag.text.strip()
        result.title_length = len(result.title_text)

    # Meta description
    desc = soup.find("meta", attrs={"name": "description"})
    if desc and desc.get("content", "").strip():
        result.has_description = True
        result.description_text = desc["content"].strip()
        result.description_length = len(result.description_text)

    # Canonical
    canonical = soup.find("link", attrs={"rel": "canonical"})
    if canonical and canonical.get("href"):
        result.has_canonical = True
        result.canonical_url = canonical["href"]

    # Open Graph
    og_title = soup.find("meta", attrs={"property": "og:title"})
    og_desc = soup.find("meta", attrs={"property": "og:description"})
    og_image = soup.find("meta", attrs={"property": "og:image"})

    if og_title and og_title.get("content"):
        result.has_og_title = True

    if og_desc and og_desc.get("content"):
        result.has_og_description = True

    if og_image and og_image.get("content"):
        result.has_og_image = True

    return result


def audit_content_quality(soup, url: str) -> ContentResult:
    """Check content quality for GEO. Returns ContentResult."""
    result = ContentResult()

    # H1
    h1 = soup.find("h1")
    if h1:
        result.has_h1 = True
        result.h1_text = h1.text.strip()

    # Headings
    headings = soup.find_all(["h1", "h2", "h3", "h4"])
    result.heading_count = len(headings)

    # Fix #98: rimuovi tag script e style prima di estrarre il testo
    # per evitare falsi positivi nel word count e nell'analisi del contenuto
    import copy

    soup_clean = copy.copy(soup)
    for tag in soup_clean(["script", "style"]):
        tag.decompose()

    # Fix #107: separator=" " previene concatenazione parole di tag adiacenti
    # Esempio: <span>Hello</span><span>World</span> → "Hello World" invece di "HelloWorld"
    body_text = soup_clean.get_text(separator=" ", strip=True)
    numbers = re.findall(r"\b\d+[%\u20ac$\u00a3]|\b\d+\.\d+|\b\d{3,}\b", body_text)
    result.numbers_count = len(numbers)
    if len(numbers) >= 3:
        result.has_numbers = True

    # Word count
    words = body_text.split()
    result.word_count = len(words)

    # External links (citations)
    parsed = urlparse(url)
    base_domain = parsed.netloc
    all_links = soup.find_all("a", href=True)
    external_links = [link for link in all_links if link["href"].startswith("http") and base_domain not in link["href"]]
    result.external_links_count = len(external_links)
    if external_links:
        result.has_links = True

    return result


def compute_geo_score(robots, llms, schema, meta, content) -> int:
    """Calculate GEO score 0-100 from SCORING weights."""
    score = 0

    # robots.txt (20 punti)
    if robots.found:
        score += SCORING["robots_found"]
    if robots.citation_bots_ok:
        if robots.citation_bots_explicit:
            # #111 — Punteggio pieno solo se i citation bot sono esplicitamente consentiti
            score += SCORING["robots_citation_ok"]
        else:
            # Consentiti solo via wildcard: punteggio parziale
            score += SCORING["robots_some_allowed"]
    elif robots.bots_allowed:
        score += SCORING["robots_some_allowed"]

    # llms.txt (20 points)
    if llms.found:
        score += SCORING["llms_found"]
        if llms.has_h1:
            score += SCORING["llms_h1"]
        if llms.has_sections:
            score += SCORING["llms_sections"]
        if llms.has_links:
            score += SCORING["llms_links"]

    # Schema (25 points — fix #158: Article + Organization ora contribuiscono)
    if schema.has_website:
        score += SCORING["schema_website"]
    if schema.has_faq:
        score += SCORING["schema_faq"]
    if schema.has_webapp:
        score += SCORING["schema_webapp"]
    if schema.has_article:
        score += SCORING["schema_article"]
    if schema.has_organization:
        score += SCORING["schema_organization"]

    # Meta tags (20 points)
    if meta.has_title:
        score += SCORING["meta_title"]
    if meta.has_description:
        score += SCORING["meta_description"]
    if meta.has_canonical:
        score += SCORING["meta_canonical"]
    if meta.has_og_title and meta.has_og_description:
        score += SCORING["meta_og"]

    # Content (15 points — fix #162: word_count ora contribuisce)
    if content.has_h1:
        score += SCORING["content_h1"]
    if content.has_numbers:
        score += SCORING["content_numbers"]
    if content.has_links:
        score += SCORING["content_links"]
    if content.word_count >= CONTENT_MIN_WORDS:
        score += SCORING["content_word_count"]

    return min(score, 100)


def get_score_band(score: int) -> str:
    """Return score band name from SCORE_BANDS."""
    for band_name, (low, high) in SCORE_BANDS.items():
        if low <= score <= high:
            return band_name
    return "critical"


def build_recommendations(base_url, robots, llms, schema, meta, content) -> list:
    """Costruisce lista di raccomandazioni prioritarie in italiano."""
    recommendations = []

    if not robots.citation_bots_ok:
        recommendations.append("Update robots.txt to include all AI bots (GPTBot, ClaudeBot, PerplexityBot)")
    if not llms.found:
        recommendations.append(f"Create /llms.txt for AI indexing: geo llms --base-url {base_url}")
    if not schema.has_website:
        recommendations.append("Add WebSite JSON-LD schema to homepage")
    if not schema.has_faq:
        recommendations.append("Add FAQPage schema with site FAQs")
    if not meta.has_description:
        recommendations.append("Add optimized meta description (150-160 characters)")
    if not content.has_numbers:
        recommendations.append("Add numerical data and concrete statistics (+40% AI visibility)")
    if not content.has_links:
        recommendations.append("Cite authoritative sources with external links (increase AI credibility)")

    return recommendations


def _build_audit_result(
    base_url: str,
    robots: RobotsResult,
    llms: LlmsTxtResult,
    schema: SchemaResult,
    meta: MetaResult,
    content: ContentResult,
    http_status: int,
    page_size: int,
    soup=None,
    extra_checks: dict = None,
) -> AuditResult:
    """Costruisce AuditResult dai sub-audit (fix #97: logica comune sync/async).

    Calcola score, band e raccomandazioni, poi esegue i plugin registrati
    nel CheckRegistry (fix #104). I risultati dei plugin non influenzano
    lo score base.

    Args:
        base_url: URL normalizzato del sito.
        robots: Risultato audit robots.txt.
        llms: Risultato audit llms.txt.
        schema: Risultato audit schema JSON-LD.
        meta: Risultato audit meta tag.
        content: Risultato audit contenuto.
        http_status: Codice HTTP della homepage.
        page_size: Dimensione in byte della homepage.
        soup: BeautifulSoup della homepage (opzionale, passato ai plugin).
        extra_checks: Dizionario con risultati pre-calcolati (non usato internamente).

    Returns:
        AuditResult completo con score, band, raccomandazioni e plugin.
    """
    from geo_optimizer.core.registry import CheckRegistry

    # Calcola score e band
    score = compute_geo_score(robots, llms, schema, meta, content)
    band = get_score_band(score)

    # Raccomandazioni
    recommendations = build_recommendations(base_url, robots, llms, schema, meta, content)

    # Fix #104: esegui plugin registrati nel CheckRegistry
    # I risultati non influenzano lo score base
    plugin_results = {}
    if CheckRegistry.all():
        check_results = CheckRegistry.run_all(base_url, soup=soup)
        plugin_results = {
            r.name: {
                "score": r.score,
                "max_score": r.max_score,
                "passed": r.passed,
                "message": r.message,
                "details": r.details,
            }
            for r in check_results
        }

    # Citability Score: analisi contenuto con i 9 metodi Princeton GEO
    from geo_optimizer.core.citability import audit_citability

    citability = audit_citability(soup, base_url) if soup else CitabilityResult()

    return AuditResult(
        url=base_url,
        score=score,
        band=band,
        robots=robots,
        llms=llms,
        schema=schema,
        meta=meta,
        content=content,
        citability=citability,
        recommendations=recommendations,
        http_status=http_status,
        page_size=page_size,
        extra_checks=plugin_results,
    )


def run_full_audit(url: str, use_cache: bool = False, project_config=None) -> AuditResult:
    """Run complete audit and return AuditResult with all sub-results, score, band, and recommendations.

    Args:
        url: URL del sito da analizzare.
        use_cache: Se True, usa la cache su disco per le richieste HTTP.
        project_config: ProjectConfig opzionale — se ha extra_bots, li merge con AI_BOTS (fix #120).
    """
    from bs4 import BeautifulSoup

    # Fix #120: se il config ha extra_bots, merge con AI_BOTS per questo audit
    effective_bots = dict(AI_BOTS)
    if project_config is not None and project_config.extra_bots:
        effective_bots.update(project_config.extra_bots)

    # Normalize URL
    base_url = url.rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url

    # Fetch homepage (con cache opzionale)
    if use_cache:
        from geo_optimizer.utils.cache import FileCache

        cache = FileCache()
        cached = cache.get(base_url)
        if cached:
            # Costruisci oggetto response-like dalla cache (fix #83: usa dataclass)
            status_code, text, headers = cached
            r = CachedResponse(
                status_code=status_code,
                text=text,
                content=text.encode("utf-8"),
                headers=headers,
            )
            err = None
        else:
            r, err = fetch_url(base_url)
            if r and not err:
                cache.put(base_url, r.status_code, r.text, dict(r.headers))
    else:
        r, err = fetch_url(base_url)
    if err or not r:
        result = AuditResult(url=base_url)
        result.recommendations = [f"Unable to reach {base_url}: {err}"]
        return result

    soup = BeautifulSoup(r.text, "html.parser")

    # Run all sub-audits
    # Fix #120: passa effective_bots che include eventuali extra_bots dal project_config
    robots = audit_robots_txt(base_url, bots=effective_bots)
    llms = audit_llms_txt(base_url)
    schema = audit_schema(soup, base_url)
    meta = audit_meta_tags(soup, base_url)
    content = audit_content_quality(soup, base_url)

    # Fix #97 + #104: usa _build_audit_result per logica comune e integrazione plugin
    return _build_audit_result(
        base_url=base_url,
        robots=robots,
        llms=llms,
        schema=schema,
        meta=meta,
        content=content,
        http_status=r.status_code,
        page_size=len(r.text),
        soup=soup,
    )


async def run_full_audit_async(url: str, project_config=None) -> AuditResult:
    """Variante asincrona dell'audit completo con fetch parallelo (httpx).

    Esegue homepage, robots.txt e llms.txt in parallelo per uno
    speedup 2-3x rispetto alla versione sincrona.

    Args:
        url: URL del sito da analizzare.
        project_config: ProjectConfig opzionale — se ha extra_bots, li merge con AI_BOTS.

    Richiede: pip install geo-optimizer-skill[async]
    """
    from bs4 import BeautifulSoup

    from geo_optimizer.utils.http_async import fetch_urls_async

    # Merge extra_bots da config, come nella versione sincrona
    effective_bots = dict(AI_BOTS)
    if project_config is not None and project_config.extra_bots:
        effective_bots.update(project_config.extra_bots)

    # Normalizza URL
    base_url = url.rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url

    # Fetch parallelo: homepage + robots.txt + llms.txt
    robots_url = urljoin(base_url, "/robots.txt")
    llms_url = urljoin(base_url, "/llms.txt")

    responses = await fetch_urls_async([base_url, robots_url, llms_url])

    # Estrai risposte
    r_home, err_home = responses.get(base_url, (None, "URL non richiesto"))
    r_robots, _ = responses.get(robots_url, (None, None))
    r_llms, _ = responses.get(llms_url, (None, None))

    if err_home or not r_home:
        result = AuditResult(url=base_url)
        result.recommendations = [f"Unable to reach {base_url}: {err_home}"]
        return result

    soup = BeautifulSoup(r_home.text, "html.parser")

    # Sub-audit robots.txt (usa risposta pre-fetched con extra_bots)
    robots = _audit_robots_from_response(r_robots, bots=effective_bots)

    # Sub-audit llms.txt (usa risposta pre-fetched)
    llms = _audit_llms_from_response(r_llms)

    # Sub-audit che lavorano sul DOM (non richiedono fetch aggiuntivo)
    schema = audit_schema(soup, base_url)
    meta = audit_meta_tags(soup, base_url)
    content = audit_content_quality(soup, base_url)

    # Fix #97 + #104: usa _build_audit_result per logica comune e integrazione plugin
    return _build_audit_result(
        base_url=base_url,
        robots=robots,
        llms=llms,
        schema=schema,
        meta=meta,
        content=content,
        http_status=r_home.status_code,
        page_size=len(r_home.text),
        soup=soup,
    )


def _audit_robots_from_response(r, bots: dict = None) -> RobotsResult:
    """Analizza robots.txt da una risposta HTTP già scaricata.

    Args:
        r: Risposta HTTP (o None se fetch fallito).
        bots: Dizionario bot da verificare. Default: AI_BOTS da config.
              Permette di passare bot aggiuntivi da project_config.extra_bots.
    """
    result = RobotsResult()

    if not r or r.status_code != 200:
        return result

    effective_bots = bots if bots is not None else AI_BOTS

    result.found = True
    content = r.text
    agent_rules = parse_robots_txt(content)

    for bot, description in effective_bots.items():
        bot_status = classify_bot(bot, description, agent_rules)

        if bot_status.status == "missing":
            result.bots_missing.append(bot)
        elif bot_status.status == "blocked":
            result.bots_blocked.append(bot)
        elif bot_status.status == "partial":
            result.bots_allowed.append(bot)
            result.bots_partial.append(bot)
        else:
            result.bots_allowed.append(bot)

    result.citation_bots_ok = all(b in result.bots_allowed for b in CITATION_BOTS)

    # #111 — Distingui permesso esplicito da fallback wildcard
    citation_explicit = []
    for bot in CITATION_BOTS:
        bot_status = classify_bot(bot, "", agent_rules)
        if bot_status.status in ("allowed", "partial") and not bot_status.via_wildcard:
            citation_explicit.append(bot)
    result.citation_bots_explicit = len(citation_explicit) == len(CITATION_BOTS)

    return result


def _audit_llms_from_response(r) -> LlmsTxtResult:
    """Analizza llms.txt da una risposta HTTP già scaricata."""
    result = LlmsTxtResult()

    if not r or r.status_code != 200:
        return result

    result.found = True
    # Rimuovi BOM UTF-8 se presente (es. file generati da Yoast SEO)
    content = r.text.lstrip("\ufeff")
    lines = content.splitlines()
    result.word_count = len(content.split())

    h1_lines = [line for line in lines if line.startswith("# ")]
    if h1_lines:
        result.has_h1 = True

    blockquotes = [line for line in lines if line.startswith("> ")]
    if blockquotes:
        result.has_description = True

    h2_lines = [line for line in lines if line.startswith("## ")]
    if h2_lines:
        result.has_sections = True

    links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
    if links:
        result.has_links = True

    return result
