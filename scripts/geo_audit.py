#!/usr/bin/env python3
"""
GEO Audit Script — Generative Engine Optimization
Controlla la configurazione GEO di un sito web.

Autore: Juan Auriti (juancamilo.auriti@gmail.com)
Skill: geo-optimizer (OpenClaw)

Uso:
    python geo_audit.py --url https://example.com
    python geo_audit.py --url https://calcfast.online --verbose
"""

import argparse
import json
import sys
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("❌ Dipendenze mancanti. Installa: pip install requests beautifulsoup4")
    sys.exit(1)

# ─── AI Bots che devono essere in robots.txt ───────────────────────────────────
AI_BOTS = {
    "GPTBot": "OpenAI (ChatGPT training)",
    "OAI-SearchBot": "OpenAI (ChatGPT search citations)",
    "ChatGPT-User": "OpenAI (ChatGPT on-demand fetch)",
    "anthropic-ai": "Anthropic (Claude training)",
    "ClaudeBot": "Anthropic (Claude citations)",
    "claude-web": "Anthropic (Claude web crawl)",
    "PerplexityBot": "Perplexity AI (index builder)",
    "Perplexity-User": "Perplexity (citation fetch)",
    "Google-Extended": "Google (Gemini training)",
    "Applebot-Extended": "Apple (AI training)",
    "cohere-ai": "Cohere (language models)",
    "DuckAssistBot": "DuckDuckGo AI",
    "Bytespider": "ByteDance/TikTok AI",
}

# Bots critici per le citazioni (search-oriented, non solo training)
CITATION_BOTS = {"OAI-SearchBot", "ClaudeBot", "PerplexityBot"}

# ─── Schema types da cercare ───────────────────────────────────────────────────
VALUABLE_SCHEMAS = [
    "WebSite", "WebApplication", "FAQPage", "Article", "BlogPosting",
    "HowTo", "Recipe", "Product", "Organization", "Person", "BreadcrumbList"
]

HEADERS = {
    "User-Agent": "GEO-Audit/1.0 (https://github.com/auriti-web-design/geo-optimizer-skill)"
}


def print_header(text: str):
    width = 60
    print("\n" + "=" * width)
    print(f"  {text}")
    print("=" * width)


def ok(msg: str):
    print(f"  ✅ {msg}")


def fail(msg: str):
    print(f"  ❌ {msg}")


def warn(msg: str):
    print(f"  ⚠️  {msg}")


def info(msg: str):
    print(f"  ℹ️  {msg}")


def fetch_url(url: str, timeout: int = 10):
    """Fetch URL, return (response, error_msg)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        return r, None
    except requests.exceptions.Timeout:
        return None, f"Timeout ({timeout}s)"
    except requests.exceptions.ConnectionError as e:
        return None, f"Connessione fallita: {e}"
    except Exception as e:
        return None, str(e)


def audit_robots_txt(base_url: str) -> dict:
    """Controlla robots.txt per AI bots."""
    print_header("1. ROBOTS.TXT — AI Bot Access")
    robots_url = urljoin(base_url, "/robots.txt")
    r, err = fetch_url(robots_url)

    results = {
        "found": False,
        "bots_allowed": [],
        "bots_missing": [],
        "bots_blocked": [],
        "citation_bots_ok": False,
    }

    if err or not r:
        fail(f"robots.txt non raggiungibile: {err}")
        return results

    if r.status_code == 404:
        fail("robots.txt non trovato (404)")
        return results

    if r.status_code != 200:
        warn(f"robots.txt status: {r.status_code}")

    results["found"] = True
    ok(f"robots.txt trovato ({r.status_code})")

    content = r.text
    # Parse robots.txt — raccogli bots per stato
    current_agents = []
    agent_rules = {}  # agent -> list of Disallow paths

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("user-agent:"):
            agent = line.split(":", 1)[1].strip()
            current_agents = [agent]
            if agent not in agent_rules:
                agent_rules[agent] = []
        elif line.lower().startswith("disallow:"):
            path = line.split(":", 1)[1].strip()
            for agent in current_agents:
                if agent in agent_rules:
                    agent_rules[agent].append(path)

    print()
    for bot, description in AI_BOTS.items():
        # Check case-insensitive
        found_agent = None
        for agent in agent_rules:
            if agent.lower() == bot.lower():
                found_agent = agent
                break

        if found_agent is None:
            results["bots_missing"].append(bot)
            if bot in CITATION_BOTS:
                fail(f"{bot} NON configurato — CRITICO per citazioni AI! ({description})")
            else:
                warn(f"{bot} non configurato ({description})")
        else:
            disallows = agent_rules[found_agent]
            if any(d in ["/", "/*"] for d in disallows):
                results["bots_blocked"].append(bot)
                if bot in CITATION_BOTS:
                    fail(f"{bot} BLOCCATO — non apparirà nelle citazioni AI!")
                else:
                    warn(f"{bot} bloccato (training disabled) — OK se intenzionale")
            elif disallows == [] or all(d == "" for d in disallows):
                results["bots_allowed"].append(bot)
                ok(f"{bot} consentito ✓ ({description})")
            else:
                results["bots_allowed"].append(bot)
                ok(f"{bot} parzialmente consentito: {disallows} ({description})")

    # Summary citation bots
    citation_ok = all(b in results["bots_allowed"] for b in CITATION_BOTS)
    results["citation_bots_ok"] = citation_ok
    print()
    if citation_ok:
        ok("Bot di CITAZIONE critici tutti configurati correttamente")
    else:
        missing_cit = [b for b in CITATION_BOTS if b not in results["bots_allowed"]]
        fail(f"Bot di CITAZIONE mancanti/bloccati: {', '.join(missing_cit)}")

    return results


def audit_llms_txt(base_url: str) -> dict:
    """Verifica presenza e qualità di llms.txt."""
    print_header("2. LLMS.TXT — AI Index File")
    llms_url = urljoin(base_url, "/llms.txt")
    r, err = fetch_url(llms_url)

    results = {
        "found": False,
        "has_h1": False,
        "has_description": False,
        "has_sections": False,
        "has_links": False,
        "word_count": 0,
    }

    if err or not r:
        fail(f"llms.txt non raggiungibile: {err}")
        info("Genera con: python generate_llms_txt.py --base-url " + base_url)
        return results

    if r.status_code == 404:
        fail("llms.txt non trovato — fondamentale per AI indexing!")
        info("Genera con: python generate_llms_txt.py --base-url " + base_url)
        return results

    results["found"] = True
    content = r.text
    lines = content.splitlines()
    results["word_count"] = len(content.split())

    ok(f"llms.txt trovato ({r.status_code}, {len(content)} bytes, ~{results['word_count']} parole)")

    # Check H1 (required)
    h1_lines = [l for l in lines if l.startswith("# ")]
    if h1_lines:
        results["has_h1"] = True
        ok(f"H1 presente: {h1_lines[0]}")
    else:
        fail("H1 mancante — la spec richiede un titolo H1 obbligatorio")

    # Check blockquote description
    blockquotes = [l for l in lines if l.startswith("> ")]
    if blockquotes:
        results["has_description"] = True
        ok(f"Descrizione blockquote presente")
    else:
        warn("Descrizione blockquote mancante (consigliata)")

    # Check H2 sections
    h2_lines = [l for l in lines if l.startswith("## ")]
    if h2_lines:
        results["has_sections"] = True
        ok(f"Sezioni H2 presenti: {len(h2_lines)} ({', '.join(l[3:] for l in h2_lines[:3])}...)")
    else:
        warn("Nessuna sezione H2 — aggiungi sezioni per organizzare i link")

    # Check markdown links
    import re
    links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
    if links:
        results["has_links"] = True
        ok(f"Link trovati: {len(links)} link a pagine del sito")
    else:
        warn("Nessun link trovato — aggiungi link alle pagine principali")

    return results


def audit_schema(soup: BeautifulSoup, url: str) -> dict:
    """Controlla schema JSON-LD nella homepage."""
    print_header("3. SCHEMA JSON-LD — Structured Data")

    results = {
        "found_types": [],
        "has_website": False,
        "has_webapp": False,
        "has_faq": False,
        "raw_schemas": [],
    }

    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    if not scripts:
        fail("Nessuno schema JSON-LD trovato nella homepage")
        info("Aggiungi schema WebSite + WebApplication + FAQPage")
        return results

    ok(f"Trovati {len(scripts)} blocchi JSON-LD")

    for i, script in enumerate(scripts):
        try:
            data = json.loads(script.string)
            schemas = data if isinstance(data, list) else [data]

            for schema in schemas:
                schema_type = schema.get("@type", "unknown")
                if isinstance(schema_type, list):
                    schema_types = schema_type
                else:
                    schema_types = [schema_type]

                for t in schema_types:
                    results["found_types"].append(t)
                    results["raw_schemas"].append(schema)

                    if t == "WebSite":
                        results["has_website"] = True
                        ok(f"WebSite schema ✓ (url: {schema.get('url', 'n/a')})")
                    elif t == "WebApplication":
                        results["has_webapp"] = True
                        ok(f"WebApplication schema ✓ (name: {schema.get('name', 'n/a')})")
                    elif t == "FAQPage":
                        results["has_faq"] = True
                        entities = schema.get("mainEntity", [])
                        ok(f"FAQPage schema ✓ ({len(entities)} domande)")
                    elif t in VALUABLE_SCHEMAS:
                        ok(f"{t} schema ✓")
                    else:
                        info(f"Schema tipo: {t}")

        except json.JSONDecodeError as e:
            warn(f"JSON-LD #{i+1} non valido: {e}")

    if not results["has_website"]:
        fail("WebSite schema mancante — fondamentale per AI understanding")
    if not results["has_faq"]:
        warn("FAQPage schema mancante — molto utile per citazioni AI su domande")

    return results


def audit_meta_tags(soup: BeautifulSoup, url: str) -> dict:
    """Controlla meta tags SEO/GEO."""
    print_header("4. META TAGS — SEO & Open Graph")

    results = {
        "has_title": False,
        "has_description": False,
        "has_canonical": False,
        "has_og_title": False,
        "has_og_description": False,
        "has_og_image": False,
    }

    # Title
    title_tag = soup.find("title")
    if title_tag and title_tag.text.strip():
        results["has_title"] = True
        title_text = title_tag.text.strip()
        if len(title_text) > 60:
            warn(f"Title presente ma lungo ({len(title_text)} chars): {title_text[:60]}...")
        else:
            ok(f"Title: {title_text}")
    else:
        fail("Title mancante")

    # Meta description
    desc = soup.find("meta", attrs={"name": "description"})
    if desc and desc.get("content", "").strip():
        results["has_description"] = True
        content = desc["content"].strip()
        if len(content) < 120:
            warn(f"Meta description breve ({len(content)} chars): {content}")
        elif len(content) > 160:
            warn(f"Meta description lunga ({len(content)} chars) — potrebbe essere troncata")
        else:
            ok(f"Meta description ({len(content)} chars) ✓")
    else:
        fail("Meta description mancante — importante per snippets AI")

    # Canonical
    canonical = soup.find("link", attrs={"rel": "canonical"})
    if canonical and canonical.get("href"):
        results["has_canonical"] = True
        ok(f"Canonical: {canonical['href']}")
    else:
        warn("Canonical URL mancante")

    # Open Graph
    og_title = soup.find("meta", attrs={"property": "og:title"})
    og_desc = soup.find("meta", attrs={"property": "og:description"})
    og_image = soup.find("meta", attrs={"property": "og:image"})

    if og_title and og_title.get("content"):
        results["has_og_title"] = True
        ok(f"og:title ✓")
    else:
        warn("og:title mancante")

    if og_desc and og_desc.get("content"):
        results["has_og_description"] = True
        ok(f"og:description ✓")
    else:
        warn("og:description mancante")

    if og_image and og_image.get("content"):
        results["has_og_image"] = True
        ok(f"og:image ✓")
    else:
        warn("og:image mancante")

    return results


def audit_content_quality(soup: BeautifulSoup, url: str) -> dict:
    """Verifica qualità dei contenuti per GEO."""
    print_header("5. CONTENT QUALITY — GEO Best Practices")

    results = {
        "has_h1": False,
        "heading_count": 0,
        "has_numbers": False,
        "has_links": False,
        "word_count": 0,
    }

    # H1
    h1 = soup.find("h1")
    if h1:
        results["has_h1"] = True
        ok(f"H1: {h1.text.strip()[:60]}")
    else:
        warn("H1 mancante nella homepage")

    # Headings
    headings = soup.find_all(["h1", "h2", "h3", "h4"])
    results["heading_count"] = len(headings)
    if len(headings) >= 3:
        ok(f"Struttura heading buona: {len(headings)} headings (H1-H4)")
    elif len(headings) > 0:
        warn(f"Pochi heading: {len(headings)} — aggiungi più struttura H2/H3")

    # Check for numbers/statistics
    import re
    body_text = soup.get_text()
    numbers = re.findall(r'\b\d+[%€$£]|\b\d+\.\d+|\b\d{3,}\b', body_text)
    if len(numbers) >= 3:
        results["has_numbers"] = True
        ok(f"Dati numerici presenti: {len(numbers)} numeri/statistiche trovate ✓")
    else:
        warn("Pochi dati numerici — aggiungi statistiche concrete per +40% visibilità AI")

    # Word count
    words = body_text.split()
    results["word_count"] = len(words)
    if len(words) >= 300:
        ok(f"Contenuto sufficiente: ~{len(words)} parole")
    else:
        warn(f"Contenuto scarso: ~{len(words)} parole — aggiungi più contenuto descrittivo")

    # External links (citations)
    parsed = urlparse(url)
    base_domain = parsed.netloc
    all_links = soup.find_all("a", href=True)
    external_links = [l for l in all_links if l["href"].startswith("http") and base_domain not in l["href"]]
    if external_links:
        results["has_links"] = True
        ok(f"Link esterni (citazioni): {len(external_links)} link a fonti esterne ✓")
    else:
        warn("Nessun link a fonti esterne — cita fonti autorevoli per +40% visibilità AI")

    return results


def compute_geo_score(robots: dict, llms: dict, schema: dict, meta: dict, content: dict) -> int:
    """Calcola un punteggio GEO da 0 a 100."""
    score = 0

    # robots.txt (20 punti)
    if robots["found"]:
        score += 5
    if robots["citation_bots_ok"]:
        score += 15
    elif robots["bots_allowed"]:
        score += 8

    # llms.txt (20 punti)
    if llms["found"]:
        score += 10
        if llms["has_h1"]: score += 3
        if llms["has_sections"]: score += 4
        if llms["has_links"]: score += 3

    # Schema (25 punti)
    if schema["has_website"]: score += 10
    if schema["has_webapp"]: score += 8
    if schema["has_faq"]: score += 7

    # Meta tags (20 punti)
    if meta["has_title"]: score += 5
    if meta["has_description"]: score += 8
    if meta["has_canonical"]: score += 3
    if meta["has_og_title"] and meta["has_og_description"]: score += 4

    # Content (15 punti)
    if content["has_h1"]: score += 4
    if content["has_numbers"]: score += 6
    if content["has_links"]: score += 5

    return min(score, 100)


def main():
    parser = argparse.ArgumentParser(
        description="GEO Audit — Controlla ottimizzazione AI search di un sito",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python geo_audit.py --url https://calcfast.online
  python geo_audit.py --url https://example.com --verbose
        """
    )
    parser.add_argument("--url", required=True, help="URL del sito da auditare (es: https://example.com)")
    parser.add_argument("--verbose", action="store_true", help="Output verbose")
    args = parser.parse_args()

    # Normalizza URL
    base_url = args.url.rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url

    print("\n" + "🔍 " * 20)
    print(f"  GEO AUDIT — {base_url}")
    print(f"  Skill: geo-optimizer | Autore: Juan Auriti")
    print("🔍 " * 20)

    # Fetch homepage
    print("\n⏳ Scarico homepage...")
    r, err = fetch_url(base_url)
    if err or not r:
        print(f"\n❌ ERRORE: Impossibile raggiungere {base_url}: {err}")
        sys.exit(1)

    soup = BeautifulSoup(r.text, "html.parser")
    print(f"   Status: {r.status_code} | Size: {len(r.text):,} bytes")

    # Run audits
    robots_results = audit_robots_txt(base_url)
    llms_results = audit_llms_txt(base_url)
    schema_results = audit_schema(soup, base_url)
    meta_results = audit_meta_tags(soup, base_url)
    content_results = audit_content_quality(soup, base_url)

    # Final score
    score = compute_geo_score(robots_results, llms_results, schema_results, meta_results, content_results)

    print_header("📊 GEO SCORE FINALE")
    bar_filled = int(score / 5)
    bar_empty = 20 - bar_filled
    bar = "█" * bar_filled + "░" * bar_empty
    print(f"\n  [{bar}] {score}/100")

    if score >= 80:
        print(f"\n  🏆 ECCELLENTE — Sito ottimizzato per AI search engines!")
    elif score >= 60:
        print(f"\n  ✅ BUONO — Alcune ottimizzazioni ancora possibili")
    elif score >= 40:
        print(f"\n  ⚠️  SUFFICIENTE — Implementa le ottimizzazioni mancanti")
    else:
        print(f"\n  ❌ CRITICO — Il sito non è ottimizzato per AI search")

    print("\n  📋 PROSSIMI STEP PRIORITARI:")

    actions = []
    if not robots_results["citation_bots_ok"]:
        actions.append("1. Aggiorna robots.txt con tutti gli AI bots (spec in SKILL.md)")
    if not llms_results["found"]:
        actions.append("2. Crea /llms.txt (python generate_llms_txt.py --base-url " + base_url + ")")
    if not schema_results["has_website"]:
        actions.append("3. Aggiungi schema WebSite JSON-LD")
    if not schema_results["has_faq"]:
        actions.append("4. Aggiungi schema FAQPage con domande frequenti")
    if not meta_results["has_description"]:
        actions.append("5. Aggiungi meta description ottimizzata")
    if not content_results["has_numbers"]:
        actions.append("6. Aggiungi statistiche numeriche concrete (+40% visibilità AI)")
    if not content_results["has_links"]:
        actions.append("7. Cita fonti autorevoli con link esterni")

    if not actions:
        print("  🎉 Ottimo! Tutte le ottimizzazioni principali sono implementate.")
    else:
        for action in actions:
            print(f"  {action}")

    print("\n  Ref: SKILL.md per istruzioni dettagliate")
    print("  Ref: references/princeton-geo-methods.md per metodi avanzati")
    print()

    return score


if __name__ == "__main__":
    main()
