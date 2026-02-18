#!/usr/bin/env python3
"""
Generate llms.txt — Genera file llms.txt da sitemap XML
Generative Engine Optimization (GEO) Skill

Autore: Juan Auriti (juancamilo.auriti@gmail.com)
Skill: geo-optimizer (OpenClaw)

Uso:
    python generate_llms_txt.py --base-url https://calcfast.online
    python generate_llms_txt.py --base-url https://example.com --output ./public/llms.txt
    python generate_llms_txt.py --base-url https://example.com --sitemap https://example.com/sitemap-0.xml
    python generate_llms_txt.py --base-url https://example.com --site-name "MioSito" --description "Descrizione"
"""

import argparse
import sys
import re
from urllib.parse import urljoin, urlparse
from datetime import datetime
from collections import defaultdict

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("❌ Dipendenze mancanti. Installa: pip install requests beautifulsoup4")
    sys.exit(1)

HEADERS = {
    "User-Agent": "GEO-Optimizer/1.0 (https://github.com/auriti-web-design/geo-optimizer-skill)"
}

# Mappatura categorie — pattern URL → nome sezione
CATEGORY_PATTERNS = [
    (r"/blog/", "Blog & Articoli"),
    (r"/article", "Articoli"),
    (r"/post/", "Post"),
    (r"/finance/", "Strumenti Finanziari"),
    (r"/health/", "Salute & Benessere"),
    (r"/math/", "Matematica"),
    (r"/calcul", "Calcolatori"),
    (r"/tool", "Strumenti"),
    (r"/app/", "Applicazioni"),
    (r"/docs?/", "Documentazione"),
    (r"/guide/", "Guide"),
    (r"/tutorial", "Tutorial"),
    (r"/product", "Prodotti"),
    (r"/service", "Servizi"),
    (r"/about", "Chi Siamo"),
    (r"/contact", "Contatti"),
    (r"/privacy", "Privacy & Legal"),
    (r"/terms", "Termini"),
]

SKIP_PATTERNS = [
    r"/wp-", r"/admin", r"/login", r"/logout", r"/register",
    r"/cart", r"/checkout", r"/account", r"/user/",
    r"\.(xml|json|rss|atom|pdf|jpg|png|css|js)$",
    r"/tag/", r"/category/\w+/page/", r"/page/\d+",
]


def fetch_sitemap(sitemap_url: str) -> list:
    """Scarica e parsa un sitemap XML, inclusi sitemap index."""
    urls = []
    print(f"⏳ Scarico sitemap: {sitemap_url}")

    try:
        r = requests.get(sitemap_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"❌ Errore sitemap: {e}")
        return urls

    soup = BeautifulSoup(r.content, "xml")

    # Sitemap index (contiene altri sitemap)
    sitemap_tags = soup.find_all("sitemap")
    if sitemap_tags:
        print(f"   Sitemap index trovato: {len(sitemap_tags)} sitemap")
        for sitemap in sitemap_tags[:10]:  # Limita a 10 sotto-sitemap
            loc = sitemap.find("loc")
            if loc:
                sub_urls = fetch_sitemap(loc.text.strip())
                urls.extend(sub_urls)
        return urls

    # Sitemap normale
    url_tags = soup.find_all("url")
    print(f"   URL trovati: {len(url_tags)}")

    for url_tag in url_tags:
        loc = url_tag.find("loc")
        if not loc:
            continue

        url_data = {
            "url": loc.text.strip(),
            "lastmod": None,
            "priority": 0.5,
            "title": None,
        }

        lastmod = url_tag.find("lastmod")
        if lastmod:
            url_data["lastmod"] = lastmod.text.strip()

        priority = url_tag.find("priority")
        if priority:
            try:
                url_data["priority"] = float(priority.text.strip())
            except ValueError:
                pass

        urls.append(url_data)

    return urls


def should_skip(url: str) -> bool:
    """Controlla se l'URL va saltato."""
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False


def categorize_url(url: str, base_domain: str) -> str:
    """Assegna una categoria all'URL."""
    path = urlparse(url).path.lower()

    for pattern, category in CATEGORY_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            return category

    # Root/homepage
    if path in ["/", ""]:
        return "_homepage"

    # Pagine di primo livello senza categoria
    parts = [p for p in path.split("/") if p]
    if len(parts) == 1:
        return "Pagine Principali"

    return "Altro"


def fetch_page_title(url: str) -> str:
    """Cerca di ottenere il titolo della pagina (con timeout breve)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.find("title")
        if title:
            return title.text.strip()
        h1 = soup.find("h1")
        if h1:
            return h1.text.strip()
    except Exception:
        pass
    return None


def url_to_label(url: str, base_domain: str) -> str:
    """Genera un label leggibile dall'URL."""
    path = urlparse(url).path
    # Rimuovi slash iniziale e finale
    path = path.strip("/")
    if not path:
        return "Homepage"
    # Prendi ultimo segmento e pulisci
    parts = path.split("/")
    last = parts[-1]
    # Converti slug in titolo
    label = last.replace("-", " ").replace("_", " ").title()
    # Se è solo numeri, usa il percorso completo
    if label.isdigit():
        label = "/".join(parts[-2:]).replace("-", " ").replace("_", " ").title()
    return label or path


def generate_llms_txt(
    base_url: str,
    urls: list,
    site_name: str = None,
    description: str = None,
    fetch_titles: bool = False,
    max_urls_per_section: int = 20,
) -> str:
    """Genera il contenuto di llms.txt."""
    parsed = urlparse(base_url)
    domain = parsed.netloc

    if not site_name:
        site_name = domain.replace("www.", "").split(".")[0].title()

    if not description:
        description = f"Sito web {site_name} disponibile su {base_url}"

    # Filtra e categorizza URL
    categorized = defaultdict(list)
    seen = set()

    for url_data in sorted(urls, key=lambda x: -x.get("priority", 0.5)):
        url = url_data["url"]

        # Normalizza URL
        if not url.startswith("http"):
            url = urljoin(base_url, url)

        # Salta URL esterni al dominio
        if domain not in urlparse(url).netloc:
            continue

        # Salta URL da ignorare
        if should_skip(url):
            continue

        # Deduplicazione
        if url in seen:
            continue
        seen.add(url)

        category = categorize_url(url, domain)

        # Genera label
        label = url_data.get("title") or url_to_label(url, domain)

        categorized[category].append({
            "url": url,
            "label": label,
            "priority": url_data.get("priority", 0.5),
        })

    # Costruisci llms.txt
    lines = []

    # Header obbligatorio
    lines.append(f"# {site_name}")
    lines.append("")
    lines.append(f"> {description}")
    lines.append("")

    # Info aggiuntive
    lines.append(f"Sito generato automaticamente da GEO Optimizer il {datetime.now().strftime('%Y-%m-%d')}.")
    lines.append(f"URL base: {base_url}")
    lines.append("")

    # Homepage prima (se presente)
    if "_homepage" in categorized:
        for item in categorized["_homepage"][:1]:
            lines.append(f"La homepage principale è disponibile su: [{site_name}]({item['url']})")
        lines.append("")

    # Ordine categorie per importanza
    priority_order = [
        "Strumenti", "Calcolatori", "Strumenti Finanziari", "Salute & Benessere",
        "Matematica", "Applicazioni", "Pagine Principali",
        "Documentazione", "Guide", "Tutorial",
        "Blog & Articoli", "Articoli", "Post",
        "Prodotti", "Servizi",
        "Chi Siamo", "Contatti",
        "Altro",
        "Privacy & Legal", "Termini",
    ]

    # Sezioni principali
    important_categories = [c for c in priority_order if c in categorized and c != "_homepage"]
    remaining = [c for c in categorized if c not in priority_order and c != "_homepage"]

    all_categories = important_categories + sorted(remaining)

    # Separa le sezioni "Optional" (secondarie)
    main_categories = []
    optional_categories = []

    for cat in all_categories:
        items = categorized[cat]
        # Categorie secondarie vanno in Optional
        if cat in ["Privacy & Legal", "Termini", "Contatti", "Altro"]:
            optional_categories.append(cat)
        else:
            main_categories.append(cat)

    # Sezioni principali
    for category in main_categories:
        items = categorized[category][:max_urls_per_section]
        if not items:
            continue

        lines.append(f"## {category}")
        lines.append("")
        for item in items:
            lines.append(f"- [{item['label']}]({item['url']})")
        lines.append("")

    # Sezione Optional (può essere saltata da LLM con contesto breve)
    if optional_categories:
        lines.append("## Optional")
        lines.append("")
        for category in optional_categories:
            items = categorized[category][:5]
            for item in items:
                lines.append(f"- [{item['label']}]({item['url']}): {category}")
        lines.append("")

    return "\n".join(lines)


def discover_sitemap(base_url: str) -> str:
    """Cerca il sitemap del sito."""
    common_paths = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap-index.xml",
        "/sitemaps/sitemap.xml",
        "/wp-sitemap.xml",
        "/sitemap-0.xml",
    ]

    # Prima controlla robots.txt per Sitemap:
    robots_url = urljoin(base_url, "/robots.txt")
    try:
        r = requests.get(robots_url, headers=HEADERS, timeout=5)
        for line in r.text.splitlines():
            if line.lower().startswith("sitemap:"):
                sitemap_url = line.split(":", 1)[1].strip()
                print(f"   Sitemap trovato in robots.txt: {sitemap_url}")
                return sitemap_url
    except Exception:
        pass

    # Prova i path comuni
    for path in common_paths:
        url = urljoin(base_url, path)
        try:
            r = requests.head(url, headers=HEADERS, timeout=5)
            if r.status_code == 200:
                print(f"   Sitemap trovato: {url}")
                return url
        except Exception:
            continue

    print("   ⚠️  Nessun sitemap trovato automaticamente")
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Genera llms.txt da sitemap XML per GEO optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python generate_llms_txt.py --base-url https://calcfast.online
  python generate_llms_txt.py --base-url https://example.com --output ./public/llms.txt
  python generate_llms_txt.py --base-url https://example.com --site-name "MioSito" \\
      --description "Calcolatori online gratuiti per finanza e matematica"
  python generate_llms_txt.py --base-url https://example.com \\
      --sitemap https://example.com/sitemap-index.xml --fetch-titles
        """
    )
    parser.add_argument("--base-url", required=True, help="URL base del sito (es: https://example.com)")
    parser.add_argument("--output", default=None, help="File di output (default: stdout)")
    parser.add_argument("--sitemap", default=None, help="URL del sitemap (auto-detect se non specificato)")
    parser.add_argument("--site-name", default=None, help="Nome del sito")
    parser.add_argument("--description", default=None, help="Descrizione del sito (blockquote)")
    parser.add_argument("--fetch-titles", action="store_true", help="Scarica i titoli dalle pagine (lento)")
    parser.add_argument("--max-per-section", type=int, default=20, help="Max URL per sezione (default: 20)")

    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url

    print(f"\n🌐 GEO llms.txt Generator")
    print(f"   Sito: {base_url}")

    # Auto-detect sitemap
    sitemap_url = args.sitemap
    if not sitemap_url:
        print("\n🔍 Cerco sitemap...")
        sitemap_url = discover_sitemap(base_url)

    if not sitemap_url:
        print("❌ Nessun sitemap trovato. Specifica --sitemap manualmente.")
        # Crea un llms.txt minimale
        minimal_content = f"# {args.site_name or base_url.split('//')[1].split('.')[0].title()}\n\n"
        minimal_content += f"> {args.description or 'Sito web disponibile su ' + base_url}\n\n"
        minimal_content += "## Pagine Principali\n\n"
        minimal_content += f"- [Homepage]({base_url})\n"
        if args.output:
            with open(args.output, "w") as f:
                f.write(minimal_content)
            print(f"✅ llms.txt minimale scritto su: {args.output}")
        else:
            print("\n--- llms.txt ---")
            print(minimal_content)
        return

    # Fetch URLs da sitemap
    print("\n📥 Scarico URLs dal sitemap...")
    urls = fetch_sitemap(sitemap_url)

    if not urls:
        print("❌ Nessun URL trovato nel sitemap")
        sys.exit(1)

    print(f"   Totale URL: {len(urls)}")

    # Genera llms.txt
    print("\n📝 Genero llms.txt...")
    content = generate_llms_txt(
        base_url=base_url,
        urls=urls,
        site_name=args.site_name,
        description=args.description,
        fetch_titles=args.fetch_titles,
        max_urls_per_section=args.max_per_section,
    )

    # Output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\n✅ llms.txt scritto su: {args.output}")
        print(f"   Dimensione: {len(content)} bytes")
        print(f"   Righe: {len(content.splitlines())}")
        print(f"\n   Carica il file in: {base_url}/llms.txt")
    else:
        print("\n" + "─" * 50)
        print(content)
        print("─" * 50)
        print(f"\n✅ Salva con: --output /percorso/public/llms.txt")


if __name__ == "__main__":
    main()
