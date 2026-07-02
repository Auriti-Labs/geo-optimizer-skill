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
from urllib.parse import urlsplit

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
# slug → file .astro (anche in sottocartella, es. guides/)
KEY_PAGES = {
    "/": "index.astro",
    "/research/": "research.astro",
    "/roadmap/": "roadmap.astro",
    "/manifesto/": "manifesto.astro",
    "/compare/": "compare.astro",
    # Guide content migrated to Sanity CMS — no static .astro source files.
    # Metadata quality is enforced by Sanity schema validation (required fields).
}

# robots.txt: fonte di verità per la policy di crawl (vedi report/[id].astro).
_ROBOTS = _FRONTEND / "public" / "robots.txt"


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
    parsed = urlsplit(url)
    last_segment = parsed.path.rstrip("/").split("/")[-1].lower()
    return "/assets/" in parsed.path or last_segment.endswith(_ASSET_EXTENSIONS)


def _page_url_has_trailing_slash(url: str) -> bool:
    """Valuta lo slash finale sul path, ignorando query string e fragment."""
    parsed = urlsplit(url)
    return parsed.path.endswith("/")


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
            assert _page_url_has_trailing_slash(url), f"{relpath}: URL di pagina senza trailing slash: {url}"

    def test_pagine_con_jsonld_espongono_url_di_pagina(self):
        """Anti-silent-pass: ogni pagina con un blocco JSON-LD deve esporre la
        propria identità di pagina in modo estraibile — via prop canonical sul
        <Shell> oppure via URL nei JSON-LD/const. Così un'estrazione che non matcha
        nulla fallisce in modo esplicito invece di passare a vuoto.

        Nota: alcune pagine (es. homepage) hanno solo schema di entità/FAQ senza
        un URL di pagina nel JSON-LD; lì la canonical del <Shell> è la fonte valida.

        Route dinamiche ([slug].astro, [id].astro) sono escluse: i loro URL sono
        calcolati a runtime da parametri — non estraibili staticamente dal sorgente.
        """
        mancanti: list[str] = []
        for relpath in _ALL_PAGES:
            # Skip dynamic routes — canonical is a template literal, not a static string.
            if "[" in relpath:
                continue
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


# ── Helper robots.txt ────────────────────────────────────────────────────────────
def _robots_group(agent: str) -> list[str]:
    """Ritorna le direttive (Allow/Disallow) del gruppo `User-agent: <agent>`.

    robots.txt è una sequenza di gruppi introdotti da `User-agent:`. Estrae solo
    le righe del gruppo richiesto, così i test non confondono le regole di un bot
    con quelle del wildcard `*`.
    """
    if not _ROBOTS.exists():
        return []
    directives: list[str] = []
    in_group = False
    for raw in _ROBOTS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            in_group = value == agent
            continue
        if in_group and key in ("allow", "disallow"):
            directives.append(f"{key}:{value}")
    return directives


# ── Test policy robots.txt (crawl) ───────────────────────────────────────────────
class TestRobotsPolicy:
    """La policy di crawl deve esporre solo la demo pubblica di /report/, tenendo
    privati i report con token e gli endpoint API."""

    pytestmark = pytest.mark.skipif(not _ROBOTS.exists(), reason="robots.txt assente")

    def test_demo_report_e_consentito_al_wildcard(self):
        directives = _robots_group("*")
        assert "allow:/report/demo" in directives, "Manca Allow: /report/demo per *"
        assert "allow:/report/demo/" in directives, "Manca Allow: /report/demo/ per *"

    def test_report_resta_disallow(self):
        # I report con token (es. /report/<hash>) non devono essere crawlabili.
        assert "disallow:/report/" in _robots_group("*"), "Manca Disallow: /report/"

    def test_api_resta_disallow(self):
        assert "disallow:/api/" in _robots_group("*"), "Manca Disallow: /api/"

    def test_allow_demo_precede_disallow_report(self):
        # Per i matcher robots (longest-match) l'ordine non è vincolante, ma teniamo
        # Allow più specifico prima del Disallow generico per chiarezza e per i
        # crawler che applicano la prima regola corrispondente.
        directives = _robots_group("*")
        assert directives.index("allow:/report/demo") < directives.index("disallow:/report/"), (
            "Allow: /report/demo deve precedere Disallow: /report/"
        )

    def test_sitemap_dichiarata(self):
        content = _ROBOTS.read_text(encoding="utf-8")
        assert "Sitemap: https://geoready.dev/sitemap.xml" in content, (
            "Riferimento alla sitemap mancante in robots.txt"
        )


# ── Test link interni verso le guide ─────────────────────────────────────────────
# Guide target del recovery indicizzazione.
_TARGET_GUIDES = (
    "/guides/ai-visibility-checklist/",
    "/guides/geo-vs-seo/",
    "/guides/llms-txt-wordpress/",
)
_GUIDES_HUB = _PAGES_DIR / "guides" / "index.astro"
_HOMEPAGE = _PAGES_DIR / "index.astro"
_RESEARCH = _PAGES_DIR / "research.astro"


def _hrefs(source: str) -> list[str]:
    """Tutti gli href interni (path assoluti) presenti nel sorgente.

    Cattura sia l'attributo letterale `href="/..."` sia la forma a oggetto dati
    `href: '/...'` / `href: "/..."` (usata, es., dall'array `guides` dell'hub che
    poi rende i link via `href={g.href}`).
    """
    attr = re.findall(r'href="(/[^"]*)"', source)
    data = re.findall(r"""href:\s*['"](/[^'"]*)['"]""", source)
    return attr + data


class TestGuideInternalLinks:
    """Le 3 guide non indicizzate devono ricevere link editoriali dalle pagine forti
    e nessun link non-slash deve essere introdotto (coerenza con il canonical)."""

    def test_hub_usa_sanity_per_i_link_guide(self):
        # Guide links are now Sanity-driven (getArticlesByCategory) — not hardcoded.
        # Verify the hub imports and calls the Sanity helper instead of checking
        # for static hrefs that no longer exist in source.
        source = _GUIDES_HUB.read_text(encoding="utf-8")
        assert "getArticlesByCategory" in source, (
            "guides/index.astro deve usare getArticlesByCategory per generare i link"
        )
        assert "a.slug.current" in source, (
            "guides/index.astro deve rendere gli href da a.slug.current (Sanity)"
        )

    def test_homepage_linka_hub_guide(self):
        hrefs = _hrefs(_HOMEPAGE.read_text(encoding="utf-8"))
        assert "/guides/" in hrefs, "Homepage non linka l'hub /guides/"

    def test_research_linka_almeno_una_guida_target(self):
        hrefs = set(_hrefs(_RESEARCH.read_text(encoding="utf-8")))
        assert hrefs & set(_TARGET_GUIDES), (
            "La pagina research non linka nessuna guida target"
        )

    @pytest.mark.parametrize("relpath", _ALL_PAGES)
    def test_nessun_link_guide_senza_slash(self, relpath: str):
        # Un link /guides/<slug> senza slash finale invierebbe il segnale di
        # duplicato che il canonical (slash) corregge → vietato introdurlo.
        source = (_PAGES_DIR / relpath).read_text(encoding="utf-8")
        for href in _hrefs(source):
            path = href.split("#")[0].split("?")[0]
            if path.startswith("/guides/") and len(path) > len("/guides/"):
                assert path.endswith("/"), f"{relpath}: link guide senza slash: {href}"

    @pytest.mark.parametrize("relpath", _ALL_PAGES)
    def test_link_demo_report_con_slash(self, relpath: str):
        # /report/demo è indicizzabile e canonicalizzato con slash: i link devono
        # puntare a /report/demo/ per non generare una variante non-slash.
        source = (_PAGES_DIR / relpath).read_text(encoding="utf-8")
        for href in _hrefs(source):
            path = href.split("#")[0].split("?")[0]
            if path == "/report/demo":
                pytest.fail(f"{relpath}: link a /report/demo senza slash (usare /report/demo/)")


# ── Test SEO del report demo ─────────────────────────────────────────────────────
class TestDemoReportSeo:
    """La demo pubblica deve essere indicizzabile con canonical slash; i report con
    token devono restare noindex."""

    _REPORT_PAGE = _PAGES_DIR / "report" / "[id].astro"
    pytestmark = pytest.mark.skipif(
        not (_PAGES_DIR / "report" / "[id].astro").exists(),
        reason="pagina report/[id].astro assente",
    )

    def test_demo_e_indicizzabile(self):
        source = self._REPORT_PAGE.read_text(encoding="utf-8")
        assert "isDemo ? 'index, follow'" in source, (
            "La demo deve usare robots 'index, follow'"
        )
        assert "'noindex, nofollow'" in source, (
            "I report con token devono restare 'noindex, nofollow'"
        )

    def test_demo_canonical_con_slash(self):
        source = self._REPORT_PAGE.read_text(encoding="utf-8")
        assert "https://geoready.dev/report/demo/" in source, (
            "Il canonical della demo deve essere /report/demo/ (con slash)"
        )

    def test_demo_island_inizializza_con_mock(self):
        """L'isola del report deve inizializzare lo stato dai dati mock per la demo,
        così l'HTML statico (SSG) contiene il contenuto del report e non un guscio
        vuoto: una pagina index,follow senza contenuto crawlabile finirebbe in
        'Crawled - currently not indexed'."""
        container = _FRONTEND / "src" / "components" / "report" / "AuditReportContainer.tsx"
        if not container.exists():
            pytest.skip("AuditReportContainer.tsx assente")
        source = container.read_text(encoding="utf-8")
        # L'initializer di useState deve gestire il ramo demo (non solo useEffect).
        assert re.search(
            r"useState<State>\(\s*\(\)\s*=>", source
        ), "useState della demo deve usare un initializer lazy con i dati mock"


# ── Test contenuto crawlabile della demo (build artefatti) ───────────────────────
_DIST = _FRONTEND / "dist"
_DEMO_HTML = _DIST / "report" / "demo" / "index.html"


@pytest.mark.skipif(
    not _DEMO_HTML.exists(),
    reason="build assente (dist/report/demo/index.html) — eseguire `npm run build`",
)
class TestDemoBuiltContent:
    """Se la build è presente, l'HTML statico della demo deve contenere il corpo
    del report (non lo spinner di loading)."""

    def test_html_demo_contiene_corpo_report(self):
        html = _DEMO_HTML.read_text(encoding="utf-8")
        for marker in ("Category Breakdown", "Technical Signals", "Recommendations"):
            assert marker in html, f"HTML demo senza sezione '{marker}' (shell vuoto?)"

    def test_html_demo_non_e_solo_spinner(self):
        html = _DEMO_HTML.read_text(encoding="utf-8")
        assert "Running audit" not in html, (
            "HTML demo mostra solo lo spinner 'Running audit' — contenuto non server-rendered"
        )
