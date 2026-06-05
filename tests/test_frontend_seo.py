"""
Test di regressione SEO per il sito marketing geoready.dev (frontend Astro SSG).

Questi test leggono i file sorgente versionati — NON richiedono `npm run build`:
- frontend/public/sitemap.xml (sitemap statica, fonte di verità)
- frontend/src/pages/**/*.astro (prop Shell: title/description/canonical + JSON-LD url)

Obiettivo: impedire regressioni su host canonico, trailing slash, duplicati e
metadati vuoti dopo il recovery SEO. Nessuna chiamata di rete.

Note di robustezza (post review):
- _extract_shell_prop è ancorato al tag <Shell ...> e risolve sia letterali
  ("...") sia binding a espressione ({var}) tramite le const del frontmatter,
  così un refactor a binding non produce falsi negativi silenziosi.
- _extract_page_schema_urls raccoglie sia gli URL letterali nei blocchi JSON-LD
  sia le const canonical/canonicalUrl (usate dalle guide via "@id": canonical),
  così la verifica del trailing slash copre anche le pagine in sottocartella.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

# ── Percorsi ──────────────────────────────────────────────────────────────────
_FRONTEND = Path(__file__).parent.parent / "frontend"
_SITEMAP = _FRONTEND / "public" / "sitemap.xml"
_PAGES_DIR = _FRONTEND / "src" / "pages"

# Host canonico pubblico unico (vedi nginx-geoready.conf: www e http → 301 qui)
CANONICAL_HOST = "https://geoready.dev"
_SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# Estensioni di asset/file: questi URL non sono "pagine" e non richiedono lo slash.
_ASSET_EXTENSIONS = (".png", ".jpg", ".jpeg", ".svg", ".ico", ".xml", ".pdf", ".json", ".webp", ".txt")

# Pagine ad alta priorità: devono avere title + description + canonical corretti.
# slug → file .astro
KEY_PAGES = {
    "/": "index.astro",
    "/research/": "research.astro",
    "/roadmap/": "roadmap.astro",
    "/manifesto/": "manifesto.astro",
    "/compare/": "compare.astro",
}


# ── Helper di parsing ───────────────────────────────────────────────────────────
def _read_sitemap_locs() -> list[str]:
    """Estrae tutti i <loc> dalla sitemap statica."""
    tree = ET.parse(_SITEMAP)
    return [el.text.strip() for el in tree.getroot().iterfind(".//sm:loc", _SITEMAP_NS) if el.text]


def _resolve_consts(astro_source: str) -> dict[str, str]:
    """Mappa `const NAME = '...'` del frontmatter (anche su riga successiva)."""
    consts: dict[str, str] = {}
    for name, value in re.findall(
        r"const\s+(\w+)\s*=\s*[\"']([^\"']*)[\"']", astro_source
    ):
        consts[name] = value
    return consts


def _find_shell_tag(astro_source: str) -> str | None:
    """Ritorna il contenuto degli attributi del tag <Shell ...> di apertura."""
    match = re.search(r"<Shell\b(.*?)>", astro_source, re.DOTALL)
    return match.group(1) if match else None


def _extract_shell_prop(astro_source: str, prop: str) -> str | None:
    """Estrae il valore di una prop passata al componente <Shell ...>.

    Gestisce letterali doppi/singoli (prop="..." / prop='...') e binding a
    espressione (prop={var}) risolvendo la const corrispondente. Ancorato al tag
    <Shell> per non catturare attributi omonimi altrove (es. <div title="...">).
    """
    attrs = _find_shell_tag(astro_source)
    if attrs is None:
        return None
    # Letterale: prop="..." oppure prop='...'  (\b evita match dentro 'subtitle')
    literal = re.search(rf'\b{prop}\s*=\s*"([^"]*)"', attrs) or re.search(
        rf"\b{prop}\s*=\s*'([^']*)'", attrs
    )
    if literal:
        return literal.group(1)
    # Espressione: prop={varName} → risolvi la const del frontmatter
    expr = re.search(rf"\b{prop}\s*=\s*\{{(\w+)\}}", attrs)
    if expr:
        return _resolve_consts(astro_source).get(expr.group(1))
    return None


def _extract_page_schema_urls(astro_source: str) -> list[str]:
    """URL "di pagina" che puntano a geoready.dev, da JSON-LD e const canonical.

    Copre due forme reali:
    - letterale nei blocchi JSON-LD:  "url"/"@id": "https://geoready.dev/..."
    - binding via const (guide):       const canonical = 'https://geoready.dev/.../'
                                        poi "@id": canonical
    """
    urls = re.findall(r'"(?:url|@id)":\s*"(https://geoready\.dev[^"]*)"', astro_source)
    for name, value in _resolve_consts(astro_source).items():
        if name.lower() in ("canonical", "canonicalurl") and value.startswith(CANONICAL_HOST):
            urls.append(value)
    return urls


def _is_asset_url(url: str) -> bool:
    last_segment = url.rstrip("/").split("/")[-1].lower()
    return "/assets/" in url or last_segment.endswith(_ASSET_EXTENSIONS)


# ── Skip se il sorgente non è presente (es. checkout parziale) ──────────────────
pytestmark = pytest.mark.skipif(
    not _SITEMAP.exists() or not _PAGES_DIR.exists(),
    reason="frontend sources assenti (sitemap.xml o src/pages/)",
)

_ALL_PAGES = sorted(str(p.relative_to(_PAGES_DIR)) for p in _PAGES_DIR.rglob("*.astro"))


# ── Test sitemap ────────────────────────────────────────────────────────────────
class TestSitemapCanonical:
    """La sitemap deve esporre SOLO URL canonici finali."""

    def test_sitemap_contiene_solo_host_canonico(self):
        for loc in _read_sitemap_locs():
            assert loc.startswith(CANONICAL_HOST + "/"), f"URL non canonico in sitemap: {loc}"

    def test_sitemap_non_contiene_www(self):
        for loc in _read_sitemap_locs():
            assert "://www." not in loc, f"URL www nella sitemap: {loc}"

    def test_sitemap_non_contiene_app_subdomain(self):
        # app.geoready.dev è il SaaS, non il sito marketing: non deve comparire qui.
        for loc in _read_sitemap_locs():
            assert "app.geoready.dev" not in loc, f"URL app.geoready.dev nella sitemap: {loc}"

    def test_sitemap_solo_https(self):
        for loc in _read_sitemap_locs():
            assert loc.startswith("https://"), f"URL non-HTTPS nella sitemap: {loc}"

    def test_sitemap_url_con_trailing_slash(self):
        # trailingSlash:'always' in astro.config → ogni URL finisce con /
        for loc in _read_sitemap_locs():
            assert loc.endswith("/"), f"URL senza trailing slash nella sitemap: {loc}"

    def test_sitemap_nessun_duplicato(self):
        locs = _read_sitemap_locs()
        duplicati = [u for u in set(locs) if locs.count(u) > 1]
        assert not duplicati, f"URL duplicati nella sitemap: {duplicati}"

    def test_sitemap_nessuna_variante_non_slash(self):
        # Per ogni URL non deve esistere anche la variante senza slash finale.
        locs = set(_read_sitemap_locs())
        for loc in locs:
            if loc != CANONICAL_HOST + "/":
                assert loc.rstrip("/") not in locs, f"Variante non-slash duplicata: {loc}"


# ── Test metadati pagine chiave ─────────────────────────────────────────────────
class TestKeyPagesMetadata:
    """Le pagine ad alta priorità devono avere metadati non vuoti e canonici corretti."""

    @pytest.mark.parametrize("slug,filename", KEY_PAGES.items())
    def test_pagina_ha_title_non_vuoto(self, slug: str, filename: str):
        source = (_PAGES_DIR / filename).read_text(encoding="utf-8")
        title = _extract_shell_prop(source, "title")
        assert title and title.strip(), f"{filename}: title mancante o vuoto"

    @pytest.mark.parametrize("slug,filename", KEY_PAGES.items())
    def test_pagina_title_entro_limite_seo(self, slug: str, filename: str):
        # Limite pratico ~60 char per evitare il troncamento del title in SERP.
        source = (_PAGES_DIR / filename).read_text(encoding="utf-8")
        title = _extract_shell_prop(source, "title") or ""
        assert len(title) <= 60, f"{filename}: title {len(title)} char (>60, rischio troncamento)"

    @pytest.mark.parametrize("slug,filename", KEY_PAGES.items())
    def test_pagina_ha_description_non_vuota(self, slug: str, filename: str):
        source = (_PAGES_DIR / filename).read_text(encoding="utf-8")
        description = _extract_shell_prop(source, "description")
        assert description and description.strip(), f"{filename}: description mancante o vuota"

    @pytest.mark.parametrize("slug,filename", KEY_PAGES.items())
    def test_pagina_canonical_corretto(self, slug: str, filename: str):
        source = (_PAGES_DIR / filename).read_text(encoding="utf-8")
        canonical = _extract_shell_prop(source, "canonical")
        # Guardia anti-falso-positivo: la prop deve essere effettivamente trovata.
        assert canonical is not None, f"{filename}: canonical non trovato sul tag <Shell>"
        assert canonical == CANONICAL_HOST + slug, (
            f"{filename}: canonical atteso {CANONICAL_HOST + slug}, trovato {canonical}"
        )

    @pytest.mark.parametrize("slug,filename", KEY_PAGES.items())
    def test_description_entro_limite_seo(self, slug: str, filename: str):
        # Range pratico 50–160 char: sotto è troppo magra, sopra si tronca in SERP.
        source = (_PAGES_DIR / filename).read_text(encoding="utf-8")
        description = _extract_shell_prop(source, "description") or ""
        assert 50 <= len(description) <= 160, (
            f"{filename}: description {len(description)} char (fuori range 50–160)"
        )


# ── Test coerenza canonical ↔ JSON-LD ───────────────────────────────────────────
class TestSchemaCanonicalConsistency:
    """Gli URL "di pagina" nei JSON-LD (e nelle const canonical) devono usare il
    trailing slash come il canonical.

    Una variante senza slash invia un segnale di duplicato che confligge con il
    canonical (root cause del recovery SEO). Copre anche le guide in sottocartella.
    """

    @pytest.mark.parametrize("relpath", _ALL_PAGES)
    def test_page_url_con_trailing_slash(self, relpath: str):
        source = (_PAGES_DIR / relpath).read_text(encoding="utf-8")
        for url in _extract_page_schema_urls(source):
            if url == CANONICAL_HOST or _is_asset_url(url):
                continue
            assert url.endswith("/"), f"{relpath}: URL di pagina senza trailing slash: {url}"

    def test_pagine_con_jsonld_espongono_url_di_pagina(self):
        """Anti-silent-pass: ogni pagina con un blocco JSON-LD deve esporre la
        propria identità di pagina in modo estraibile — via prop canonical sul
        <Shell> oppure via URL nei JSON-LD/const. Così un'estrazione che non matcha
        nulla fallisce in modo esplicito invece di passare a vuoto.

        Nota: alcune pagine (es. homepage) hanno solo schema di entità/FAQ senza
        un URL di pagina nel JSON-LD; lì la canonical del <Shell> è la fonte valida.
        """
        mancanti: list[str] = []
        for relpath in _ALL_PAGES:
            source = (_PAGES_DIR / relpath).read_text(encoding="utf-8")
            if "application/ld+json" not in source:
                continue
            page_urls = [u for u in _extract_page_schema_urls(source) if not _is_asset_url(u)]
            shell_canonical = _extract_shell_prop(source, "canonical")
            if not page_urls and not shell_canonical:
                mancanti.append(relpath)
        assert not mancanti, (
            "Pagine con JSON-LD ma nessun URL di pagina né canonical estraibile "
            f"(possibile silent-pass o canonical mancante): {mancanti}"
        )
