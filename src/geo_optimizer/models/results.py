"""
Dataclasses for GEO Optimizer results.

All audit functions return these structures instead of printing.
The CLI layer is responsible for formatting and display.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# ─── HTTP cache ───────────────────────────────────────────────────────────────


@dataclass
class CachedResponse:
    """Synthetic HTTP response built from the on-disk cache (fix #83).

    Used by run_full_audit() when use_cache=True and the response
    is already in the FileCache, avoiding a new HTTP request.
    """

    status_code: int
    text: str
    content: bytes
    headers: dict[str, str] = field(default_factory=dict)


# ─── Robots.txt ──────────────────────────────────────────────────────────────


@dataclass
class RobotsResult:
    found: bool = False
    bots_allowed: list[str] = field(default_factory=list)
    bots_missing: list[str] = field(default_factory=list)
    bots_blocked: list[str] = field(default_factory=list)
    # Partially blocked bots (Disallow: / + specific Allows — #106)
    bots_partial: list[str] = field(default_factory=list)
    citation_bots_ok: bool = False
    # True if citation bots are explicitly allowed (not just via wildcard — #111)
    citation_bots_explicit: bool = False


# ─── llms.txt ────────────────────────────────────────────────────────────────


@dataclass
class LlmsTxtResult:
    found: bool = False
    has_h1: bool = False
    has_description: bool = False
    has_sections: bool = False
    has_links: bool = False
    word_count: int = 0
    has_full: bool = False  # /llms-full.txt present


# ─── Schema JSON-LD ──────────────────────────────────────────────────────────


@dataclass
class SchemaResult:
    found_types: list[str] = field(default_factory=list)
    has_website: bool = False
    has_webapp: bool = False
    has_faq: bool = False
    has_article: bool = False
    has_organization: bool = False
    has_howto: bool = False
    has_person: bool = False
    has_product: bool = False
    raw_schemas: list[dict] = field(default_factory=list)
    any_schema_found: bool = False  # True se QUALSIASI JSON-LD valido trovato
    has_sameas: bool = False  # proprietà sameAs trovata
    sameas_urls: list[str] = field(default_factory=list)
    has_date_modified: bool = False  # dateModified in qualsiasi schema
    # Schema richness (Growth Marshal Feb 2026): schema con 5+ attributi rilevanti
    schema_richness_score: int = 0
    avg_attributes_per_schema: float = 0.0


# ─── Meta tags ───────────────────────────────────────────────────────────────


@dataclass
class MetaResult:
    has_title: bool = False
    has_description: bool = False
    has_canonical: bool = False
    has_og_title: bool = False
    has_og_description: bool = False
    has_og_image: bool = False
    title_text: str = ""
    description_text: str = ""
    description_length: int = 0
    title_length: int = 0
    canonical_url: str = ""


# ─── Content quality ─────────────────────────────────────────────────────────


@dataclass
class ContentResult:
    has_h1: bool = False
    heading_count: int = 0
    has_numbers: bool = False
    has_links: bool = False
    word_count: int = 0
    h1_text: str = ""
    numbers_count: int = 0
    external_links_count: int = 0
    has_heading_hierarchy: bool = False  # H2+H3 presenti in gerarchia corretta
    has_lists_or_tables: bool = False  # <ul>/<ol>/<table> trovati
    has_front_loading: bool = False  # info chiave nel primo 30%


# ─── Signals tecnici (v4.0) ──────────────────────────────────────────────────


@dataclass
class SignalsResult:
    """Segnali tecnici per la scopribilità AI."""

    has_lang: bool = False
    lang_value: str = ""
    has_rss: bool = False
    rss_url: str = ""
    has_freshness: bool = False
    freshness_date: str = ""


# ─── Citability (Princeton GEO Methods) ─────────────────────────────────────


@dataclass
class MethodScore:
    """Score for a single Princeton GEO method."""

    name: str  # "cite_sources"
    label: str  # "Cite Sources"
    detected: bool = False
    score: int = 0
    max_score: int = 10
    impact: str = ""  # "+27%"
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class CitabilityResult:
    """Citability analysis result with the 9 Princeton KDD 2024 methods."""

    methods: list[MethodScore] = field(default_factory=list)
    total_score: int = 0  # 0-100 (normalized sum)
    grade: str = "low"  # low/medium/high/excellent
    top_improvements: list[str] = field(default_factory=list)


# ─── AI Discovery (geo-checklist.dev) ────────────────────────────────────────


@dataclass
class AiDiscoveryResult:
    """Result of checking AI discovery endpoints (.well-known/ai.txt, /ai/*.json)."""

    has_well_known_ai: bool = False
    has_summary: bool = False
    has_faq: bool = False
    has_service: bool = False
    summary_valid: bool = False  # ha i campi richiesti (name + description)
    faq_count: int = 0  # numero di FAQ trovate
    endpoints_found: int = 0  # conteggio totale endpoint trovati (0-4)


# ─── CDN AI Crawler Check (#225) ─────────────────────────────────────────────


@dataclass
class CdnAiCrawlerResult:
    """Result of checking if CDN blocks AI crawler user-agents.

    Simulates requests as AI bots (GPTBot, ClaudeBot, PerplexityBot) and
    compares status codes + content-length to a normal browser request.
    """

    checked: bool = False
    browser_status: int = 0
    browser_content_length: int = 0
    bot_results: list[dict] = field(default_factory=list)
    # bot_results: [{"bot": "GPTBot", "status": 200, "content_length": 12345,
    #                "blocked": False, "challenge_detected": False}]
    any_blocked: bool = False
    cdn_detected: str = ""  # "cloudflare", "akamai", "aws", "" if none
    cdn_headers: dict[str, str] = field(default_factory=dict)


# ─── JS Rendering Check (#226) ──────────────────────────────────────────────


@dataclass
class JsRenderingResult:
    """Result of checking if page content is accessible without JavaScript.

    Analyzes raw HTML (no JS execution) for content indicators:
    word count, heading count, SPA framework detection.
    """

    checked: bool = False
    raw_word_count: int = 0
    raw_heading_count: int = 0
    has_empty_root: bool = False  # <div id="root"></div> or id="app"
    has_noscript_content: bool = False
    framework_detected: str = ""  # "react", "vue", "angular", "next", ""
    js_dependent: bool = False  # True if content likely needs JS
    details: str = ""


# ─── Full audit ──────────────────────────────────────────────────────────────


@dataclass
class AuditResult:
    url: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    score: int = 0
    band: str = "critical"
    robots: RobotsResult = field(default_factory=RobotsResult)
    llms: LlmsTxtResult = field(default_factory=LlmsTxtResult)
    schema: SchemaResult = field(default_factory=SchemaResult)
    meta: MetaResult = field(default_factory=MetaResult)
    content: ContentResult = field(default_factory=ContentResult)
    recommendations: list[str] = field(default_factory=list)
    http_status: int = 0
    page_size: int = 0
    # Citability: score 0-100 based on the 9 Princeton KDD 2024 methods
    citability: CitabilityResult = field(default_factory=CitabilityResult)
    # Fix #104: CheckRegistry plugin results (do not affect the base score)
    extra_checks: dict[str, Any] = field(default_factory=dict)
    # v4.0: segnali tecnici (lang, RSS, freshness)
    signals: SignalsResult = field(default_factory=SignalsResult)
    # v4.1: AI discovery endpoints (geo-checklist.dev)
    ai_discovery: AiDiscoveryResult = field(default_factory=AiDiscoveryResult)
    # v4.0: breakdown score per categoria
    score_breakdown: dict[str, int] = field(default_factory=dict)
    # v4.0: messaggio di errore connessione (None = successo)
    error: str | None = None
    # v4.2: CDN AI Crawler check (#225)
    cdn_check: CdnAiCrawlerResult = field(default_factory=CdnAiCrawlerResult)
    # v4.2: JS Rendering check (#226)
    js_rendering: JsRenderingResult = field(default_factory=JsRenderingResult)


# ─── Schema analysis ─────────────────────────────────────────────────────────


@dataclass
class SchemaAnalysis:
    found_schemas: list[dict] = field(default_factory=list)
    found_types: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    extracted_faqs: list[dict[str, str]] = field(default_factory=list)
    duplicates: dict[str, int] = field(default_factory=dict)
    has_head: bool = False
    total_scripts: int = 0


# ─── llms.txt generation ─────────────────────────────────────────────────────


@dataclass
class SitemapUrl:
    url: str
    lastmod: str | None = None
    priority: float = 0.5
    title: str | None = None


# ─── Fix plan ───────────────────────────────────────────────────────────────


@dataclass
class FixItem:
    """Single fix generated by geo fix."""

    category: str  # "robots", "llms", "schema", "meta"
    description: str  # "Adds 5 missing AI bots to robots.txt"
    content: str  # Generated content (file text or HTML tag)
    file_name: str  # "robots.txt", "llms.txt", "schema-website.json"
    action: str  # "create", "append", "snippet"


@dataclass
class FixPlan:
    """Complete fix plan generated by geo fix."""

    url: str
    score_before: int = 0
    score_estimated_after: int = 0
    fixes: list[FixItem] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
