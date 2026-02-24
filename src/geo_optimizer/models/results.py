"""
Dataclasses for GEO Optimizer results.

All audit functions return these structures instead of printing.
The CLI layer is responsible for formatting and display.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


# ─── Robots.txt ──────────────────────────────────────────────────────────────

@dataclass
class RobotsResult:
    found: bool = False
    bots_allowed: List[str] = field(default_factory=list)
    bots_missing: List[str] = field(default_factory=list)
    bots_blocked: List[str] = field(default_factory=list)
    citation_bots_ok: bool = False


# ─── llms.txt ────────────────────────────────────────────────────────────────

@dataclass
class LlmsTxtResult:
    found: bool = False
    has_h1: bool = False
    has_description: bool = False
    has_sections: bool = False
    has_links: bool = False
    word_count: int = 0


# ─── Schema JSON-LD ──────────────────────────────────────────────────────────

@dataclass
class SchemaResult:
    found_types: List[str] = field(default_factory=list)
    has_website: bool = False
    has_webapp: bool = False
    has_faq: bool = False
    raw_schemas: List[dict] = field(default_factory=list)


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
    recommendations: List[str] = field(default_factory=list)
    http_status: int = 0
    page_size: int = 0


# ─── Schema analysis ─────────────────────────────────────────────────────────

@dataclass
class SchemaAnalysis:
    found_schemas: List[Dict] = field(default_factory=list)
    found_types: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    extracted_faqs: List[Dict[str, str]] = field(default_factory=list)
    duplicates: Dict[str, int] = field(default_factory=dict)
    has_head: bool = False
    total_scripts: int = 0


# ─── llms.txt generation ─────────────────────────────────────────────────────

@dataclass
class SitemapUrl:
    url: str
    lastmod: Optional[str] = None
    priority: float = 0.5
    title: Optional[str] = None
