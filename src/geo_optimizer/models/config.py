"""
Centralized configuration for GEO Optimizer.

All shared constants (bots, schemas, scoring weights, patterns) live here
so that core modules, CLI, and tests can import from a single source.
"""

from __future__ import annotations

from pathlib import Path

# ─── HTTP ────────────────────────────────────────────────────────────────────

USER_AGENT = "GEO-Optimizer/2.0 (https://github.com/auriti-labs/geo-optimizer-skill)"

HEADERS = {"User-Agent": USER_AGENT}

# HTTP response size limit: 10 MB (prevents DoS from huge responses) — fix #91
MAX_RESPONSE_SIZE: int = 10 * 1024 * 1024

# Maximum number of sub-sitemaps to process in a sitemap index — fix #90
MAX_SUB_SITEMAPS: int = 10

# Total URL limit extracted from all sitemaps — fix #124 (sitemap bomb)
MAX_TOTAL_URLS: int = 10_000

# ─── Local history / tracking ────────────────────────────────────────────────

GEO_OPTIMIZER_HOME = Path.home() / ".geo-optimizer"
TRACKING_DB_PATH = GEO_OPTIMIZER_HOME / "tracking.db"
SNAPSHOTS_DB_PATH = GEO_OPTIMIZER_HOME / "snapshots.db"
DEFAULT_HISTORY_RETENTION_DAYS = 90
DEFAULT_HISTORY_LIMIT = 12
DEFAULT_SNAPSHOT_LIMIT = 20

# ─── Passive AI visibility monitoring ────────────────────────────────────────

MONITOR_SCORING = {
    "citation_bot_access": 20,
    "user_fetch_access": 10,
    "llms_readiness": 15,
    "ai_discovery_readiness": 15,
    "entity_strength": 15,
    "trust_strength": 15,
    "momentum": 10,
}

MONITOR_BANDS = {
    "strong": (80, 100),
    "visible": (60, 79),
    "emerging": (35, 59),
    "low": (0, 34),
}


# ─── AI bots — 3-tier classification (training/search/user) ──────────────────
#
# Training: crawl to train models (less critical for direct visibility)
# Search:   cite the site in AI responses (highest priority for GEO)
# User:     on-demand fetch when a user asks about a specific URL

AI_BOTS = {
    # ── OpenAI ──────────────────────────────────────────────────────────────
    "GPTBot": "OpenAI (ChatGPT training)",
    "OAI-SearchBot": "OpenAI (ChatGPT search citations)",
    "ChatGPT-User": "OpenAI (ChatGPT on-demand fetch)",
    # ── Anthropic ───────────────────────────────────────────────────────────
    "anthropic-ai": "Anthropic (Claude training)",
    "ClaudeBot": "Anthropic (Claude citations)",
    "Claude-SearchBot": "Anthropic (Claude search citations)",
    "claude-web": "Anthropic (Claude web crawl)",
    # ── Perplexity ──────────────────────────────────────────────────────────
    "PerplexityBot": "Perplexity AI (index builder)",
    "Perplexity-User": "Perplexity (citation fetch on-demand)",
    # ── Google ──────────────────────────────────────────────────────────────
    "Google-Extended": "Google (Gemini training)",
    "Google-CloudVertexBot": "Google (Vertex AI)",
    # ── Microsoft ───────────────────────────────────────────────────────────
    "Bingbot": "Microsoft (Bing/Copilot search)",
    # ── Apple ───────────────────────────────────────────────────────────────
    "Applebot-Extended": "Apple (AI training)",
    # ── Other ───────────────────────────────────────────────────────────────
    "cohere-ai": "Cohere (language models)",
    "DuckAssistBot": "DuckDuckGo AI",
    "Bytespider": "ByteDance/TikTok AI",
    "meta-externalagent": "Meta AI (Facebook/Instagram AI)",
    # ── Meta (expanded) ─────────────────────────────────────────────────────
    "Meta-ExternalFetcher": "Meta (content fetch on-demand)",
    "facebookexternalhit": "Meta (social preview + AI)",
    # ── Amazon ──────────────────────────────────────────────────────────────
    "Amazonbot": "Amazon (Alexa/search AI)",
    # ── Allen Institute ─────────────────────────────────────────────────────
    "AI2Bot": "Allen Institute (AI research)",
    "AI2Bot-Dolma": "Allen Institute (Dolma dataset)",
    # ── xAI ────────────────────────────────────────────────────────────────
    "xAI-Bot": "xAI (Grok search citations)",
    # ── Apple (general) ────────────────────────────────────────────────────
    "Applebot": "Apple (general web crawl + Siri AI)",
    # ── Huawei ─────────────────────────────────────────────────────────────
    "PetalBot": "Huawei (PetalSearch AI, EU/Asia)",
    # ── You.com ─────────────────────────────────────────────────────────────
    "YouBot": "You.com AI search",
    # ── Common Crawl ────────────────────────────────────────────────────────
    "CCBot": "Common Crawl (used by many AI labs)",
}

# 3-tier classification — bots grouped by function
BOT_TIERS = {
    "training": {
        "GPTBot",
        "anthropic-ai",
        "claude-web",
        "Google-Extended",
        "Google-CloudVertexBot",
        "Applebot-Extended",
        "Applebot",
        "cohere-ai",
        "Bytespider",
        "meta-externalagent",
        "PetalBot",
        "AI2Bot",
        "AI2Bot-Dolma",
        "CCBot",
    },
    "search": {
        "OAI-SearchBot",
        "ClaudeBot",
        "Claude-SearchBot",
        "PerplexityBot",
        "Bingbot",
        "DuckAssistBot",
        "YouBot",
        "Amazonbot",
        "xAI-Bot",
    },
    "user": {
        "ChatGPT-User",
        "Perplexity-User",
        "Meta-ExternalFetcher",
        "facebookexternalhit",
    },
}

# Critical citation bots (search-tier, directly cite sources in AI responses)
CITATION_BOTS = {"OAI-SearchBot", "ClaudeBot", "Claude-SearchBot", "PerplexityBot"}

# ─── Brand normalization ──────────────────────────────────────────────────────

# Legal suffixes stripped from brand names before comparison (#397).
# Only removed when they appear at the END of the name (after stripping punctuation/spaces).
# Lowercase, matched against the lowercased trailing token(s).
BRAND_LEGAL_SUFFIXES: frozenset = frozenset(
    {
        "inc",
        "inc.",
        "incorporated",
        "ltd",
        "ltd.",
        "limited",
        "llc",
        "l.l.c.",
        "corp",
        "corp.",
        "corporation",
        "gmbh",
        "g.m.b.h.",
        "s.r.l.",
        "srl",
        "s.p.a.",
        "spa",
        "s.a.",
        "sa",
        "ag",
        "co",
        "co.",
        "plc",
        "pty",
        "pty.",
        "bv",
        "b.v.",
        "nv",
        "n.v.",
    }
)

# ─── Schema types ────────────────────────────────────────────────────────────

# All schema.org Article subtypes that count as Article for GEO scoring
# Includes direct subclasses per schema.org hierarchy (#392)
ARTICLE_TYPES: frozenset[str] = frozenset(
    {
        "Article",
        "BlogPosting",
        "NewsArticle",
        "TechArticle",
        "ScholarlyArticle",
    }
)

VALUABLE_SCHEMAS = [
    "WebSite",
    "WebApplication",
    "FAQPage",
    "Article",
    "BlogPosting",
    "NewsArticle",
    "TechArticle",
    "ScholarlyArticle",
    "HowTo",
    "Recipe",
    "Product",
    "Organization",
    "Person",
    "BreadcrumbList",
]

# Required fields for each schema.org type (keys are lowercase)
SCHEMA_ORG_REQUIRED = {
    "website": ["@context", "@type", "url", "name"],
    "webpage": ["@context", "@type", "url", "name"],
    "organization": ["@context", "@type", "name", "url"],
    "person": ["@context", "@type", "name"],
    "faqpage": ["@context", "@type", "mainEntity"],
    "article": ["@context", "@type", "headline", "author"],
    "breadcrumblist": ["@context", "@type", "itemListElement"],
    "product": ["@context", "@type", "name", "description"],
    "localbusiness": ["@context", "@type", "name", "address"],
    "webapplication": ["@context", "@type", "name", "url"],
}

SCHEMA_TEMPLATES = {
    "website": {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "{{name}}",
        "url": "{{url}}",
        "description": "{{description}}",
        "potentialAction": {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": "{{url}}/search?q={search_term_string}",
            },
            "query-input": "required name=search_term_string",
        },
    },
    "webapp": {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": "{{name}}",
        "url": "{{url}}",
        "description": "{{description}}",
        "applicationCategory": "UtilityApplication",
        "operatingSystem": "Web",
        "browserRequirements": "Requires JavaScript",
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "author": {"@type": "Organization", "name": "{{author}}"},
    },
    "faq": {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [],
    },
    "article": {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "{{title}}",
        "description": "{{description}}",
        "url": "{{url}}",
        # image field required for Google Rich Results (#112)
        "image": "{{image_url}}",
        "datePublished": "{{date_published}}",
        "dateModified": "{{date_modified}}",
        "author": {"@type": "Person", "name": "{{author}}"},
        "publisher": {
            "@type": "Organization",
            "name": "{{publisher}}",
            "logo": {"@type": "ImageObject", "url": "{{logo_url}}"},
        },
    },
    "organization": {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "{{name}}",
        "url": "{{url}}",
        "description": "{{description}}",
        # logo must be ImageObject, not URL string (#113)
        "logo": {"@type": "ImageObject", "url": "{{logo_url}}"},
        # sameAs is the most important signal for brand_kg_readiness (3pt — #398)
        # Placeholders use authoritative domains from SAMEAS_AUTHORITATIVE_DOMAINS
        "sameAs": [
            "https://www.linkedin.com/company/YOUR_COMPANY",
            "https://github.com/YOUR_ORG",
            "https://twitter.com/YOUR_HANDLE",
        ],
    },
    "breadcrumb": {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Home", "item": "{{url}}"}],
    },
}

# ─── llms.txt patterns ──────────────────────────────────────────────────────

CATEGORY_PATTERNS = [
    (r"/blog/", "Blog & Articles"),
    (r"/article/", "Articles"),
    (r"/articles/", "Articles"),
    (r"/post/", "Posts"),
    (r"/news/", "News"),
    (r"/finance/", "Finance Tools"),
    (r"/health/", "Health & Wellness"),
    (r"/math/", "Math"),
    (r"/calcul", "Calculators"),
    (r"/tool/", "Tools"),
    (r"/tools/", "Tools"),
    (r"/app/", "Applications"),
    (r"/docs?/", "Documentation"),
    (r"/guide/", "Guides"),
    (r"/tutorial/", "Tutorials"),
    (r"/tutorials/", "Tutorials"),
    # Patterns with slash to avoid false positives (#117)
    # /product → /production-process, /service → /service-terms
    (r"/products/", "Products"),
    (r"/product/", "Products"),
    (r"/services/", "Services"),
    (r"/service/", "Services"),
    # New categories (#118)
    (r"/faq/", "FAQ"),
    (r"/faqs/", "FAQ"),
    (r"/pricing/", "Pricing"),
    (r"/price/", "Pricing"),
    (r"/portfolio/", "Portfolio"),
    (r"/case-stud", "Case Studies"),
    (r"/support/", "Support"),
    (r"/help/", "Support"),
    (r"/team/", "Team"),
    (r"/about-us(?:/|$)", "About"),
    (r"/about(?:/|$)", "About"),
    (r"/careers/", "Careers"),
    (r"/jobs/", "Careers"),
    (r"/contact", "Contact"),
    (r"/privacy", "Privacy & Legal"),
    (r"/terms", "Terms"),
]

SKIP_PATTERNS = [
    r"/wp-",
    r"/admin",
    r"/login",
    r"/logout",
    r"/register",
    r"/cart",
    r"/checkout",
    r"/account",
    r"/user/",
    r"\.(xml|json|rss|atom|pdf|jpg|png|css|js)$",
    r"/tag/",
    r"/category/\w+/page/",
    r"/page/\d+",
    # Additional skip patterns (#118)
    r"/feed/",
    r"/author/",
    r"/amp/",
    r"/api/",
    r"/wp-json/",
]

# llms.txt section ordering
SECTION_PRIORITY_ORDER = [
    "Tools",
    "Calculators",
    "Finance Tools",
    "Health & Wellness",
    "Math",
    "Applications",
    "Main Pages",
    "Documentation",
    "Guides",
    "Tutorials",
    "Blog & Articles",
    "Articles",
    "Posts",
    "News",
    "Products",
    "Services",
    "FAQ",
    "Pricing",
    "Portfolio",
    "Case Studies",
    "Support",
    "Team",
    "Careers",
    "About",
    "Contact",
    "Other",
    "Privacy & Legal",
    "Terms",
]

OPTIONAL_CATEGORIES = {"Privacy & Legal", "Terms", "Contact", "Other"}

# ─── Scoring weights ─────────────────────────────────────────────────────────

SCORING = {
    # robots.txt — 18 points (was 20)
    "robots_found": 5,
    "robots_citation_ok": 13,  # was 15
    # robots_some_allowed: removed from dict, now in ROBOTS_PARTIAL_SCORE (fix #332)
    # llms.txt — 18 points (was 20) — graduated quality + blockquote v2
    "llms_found": 5,  # was 6 — 1 point moved to llms_blockquote (#39)
    "llms_h1": 2,  # was 3
    "llms_blockquote": 1,  # #39: blockquote description present
    "llms_sections": 2,  # was 4
    "llms_links": 2,  # was 3
    "llms_depth": 2,  # NEW: word_count >= 1000
    "llms_depth_high": 2,  # NEW: word_count >= 5000
    "llms_full": 2,  # NEW: has llms-full.txt
    # Schema JSON-LD — 16 points (was 25) — any valid type + sameAs + richness
    "schema_any_valid": 2,  # any valid JSON-LD schema found (was 5, reduced for richness)
    "schema_richness": 3,  # NEW: schema with 5+ relevant attributes (Growth Marshal 2026)
    "schema_faq": 3,  # was 5 — reduced, migrated to brand_topic_authority
    "schema_article": 3,  # was 4
    "schema_organization": 3,  # was 3
    "schema_website": 2,  # was 3
    "schema_sameas": 0,  # was 3, migrated to brand KG — kept at 0 for backward compat
    # Meta tags — 14 points
    "meta_title": 5,
    "meta_description": 2,
    "meta_canonical": 3,
    "meta_og": 4,
    # Content quality — 12 points (was 15) — structure checks
    "content_h1": 2,  # was 3
    "content_numbers": 1,  # was 2
    "content_links": 1,  # was 2
    "content_word_count": 2,  # was 4
    "content_heading_hierarchy": 2,  # NEW: has H2 + H3 in correct hierarchy
    "content_lists_or_tables": 2,  # NEW: has <ul>/<ol>/<table>
    "content_front_loading": 2,  # NEW: key info in the first 30% of content
    # Signals — 6 points (NEW category)
    "signals_lang": 3,  # NEW: <html lang="...">
    "signals_rss": 2,  # was 3
    "signals_freshness": 1,  # was 2
    # AI Discovery — 6 points (geo-checklist.dev standard)
    "ai_discovery_well_known": 2,  # /.well-known/ai.txt present
    "ai_discovery_summary": 2,  # /ai/summary.json valid
    "ai_discovery_faq": 1,  # /ai/faq.json present
    "ai_discovery_service": 1,  # /ai/service.json present
    # Brand & Entity — 10 points (NEW category v4.3)
    "brand_entity_coherence": 3,  # name consistent across H1/title/og:title/schema
    "brand_kg_readiness": 3,  # sameAs pointing to Wikipedia/Wikidata/LinkedIn/Crunchbase
    "brand_about_contact": 2,  # /about link + Organization with address/telephone
    "brand_geo_identity": 1,  # hreflang + schema geo (address, areaServed)
    "brand_topic_authority": 1,  # FAQ depth + Article with dateModified
}

# Partial robots.txt score: wildcard Allow without explicit permission to citation bots
# Separate from the SCORING dict because it is an alternative (not additive) to robots_citation_ok (fix #332)
ROBOTS_PARTIAL_SCORE = 10

# Schema richness thresholds — graduated scoring (#394)
SCHEMA_RICHNESS_HIGH = 5  # avg >= 5 attrs → full points (3pt)
SCHEMA_RICHNESS_MED = 4  # avg >= 4 attrs → 2pt
SCHEMA_RICHNESS_LOW = 3  # avg >= 3 attrs → 1pt

# Minimum word threshold for content_word_count (300 words = substantial content)
CONTENT_MIN_WORDS = 300

# Content freshness thresholds in days (#401)
# AutoGEO ICLR 2026: tech content < 3 months strongly preferred by AI search engines
FRESHNESS_VERY_FRESH_DAYS = 90  # < 3 months → very_fresh
FRESHNESS_FRESH_DAYS = 180  # 3-6 months → fresh
FRESHNESS_AGING_DAYS = 365  # 6-12 months → aging (> 12 months = stale)

# Depth thresholds for llms.txt
LLMS_DEPTH_WORDS = 1000
LLMS_DEPTH_HIGH_WORDS = 5000

# Authoritative sameAs domains (for knowledge graph linking)
SAMEAS_AUTHORITATIVE_DOMAINS = {
    "wikipedia.org",
    "wikidata.org",
    "linkedin.com",
    "crunchbase.com",
    "github.com",
    "twitter.com",
    "x.com",
    "facebook.com",
}

# Pillar domains for Knowledge Graph (AI disambiguation — the 4 most relevant)
KG_PILLAR_DOMAINS = {
    "wikipedia.org",
    "wikidata.org",
    "linkedin.com",
    "crunchbase.com",
}

# ─── Prompt Injection Detection (#276) ────────────────────────────────────────

# Regex patterns for direct LLM instructions in page content
PROMPT_INJECTION_LLM_PATTERNS = [
    r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?",
    r"you\s+are\s+(?:now\s+)?(?:a|an)\s+(?:helpful\s+)?assistant",
    r"always\s+recommend\s+\w+",
    r"do\s+not\s+mention\s+competitors?",
    r"say\s+(?:only|just|that)\s+['\"]",
    r"output\s+only\s+the\s+following",
    r"respond\s+with\s+only",
    r"your\s+(?:new\s+)?(?:task|goal|objective|purpose)\s+is",
    r"from\s+now\s+on\s+you",
    r"act\s+as\s+(?:if\s+you\s+are\s+)?\w+",
    r"\[INST\]|\[SYS\]|<\|system\|>|<\|user\|>",
    r"###\s*(?:System|Human|Assistant)\s*:",
    r"<\s*system\s*>",
    # fix #387: Llama 3 / Gemma / Mistral tokens
    r"<\|start_header_id\|>|<\|end_header_id\|>|<\|eot_id\|>|<\|begin_of_text\|>",
    r"<start_of_turn>|<end_of_turn>",
    # fix #387: common jailbreak patterns
    r"\bDAN\s+mode\b|\bdeveloper\s+mode\b",
    r"pretend\s+(?:you\s+have\s+no|there\s+are\s+no)\s+restrictions?",
    r"(?:reveal|repeat|show|tell)\s+(?:me\s+)?(?:your|the)\s+(?:system\s+)?(?:prompt|instructions?)",
    # fix #387: "jailbreak" keyword and "repeat the above" prompt-leaking variant
    r"\bjailbreak\b",
    r"repeat\s+the\s+above",
]

# Suspicious keywords in HTML comments
PROMPT_INJECTION_COMMENT_KEYWORDS = ["prompt:", "instruction:", "context:", "system:", "ai:", "llm:"]

# Thresholds and limits
PROMPT_INJECTION_MAX_SAMPLES = 3
PROMPT_INJECTION_SAMPLE_MAX_LEN = 150
PROMPT_INJECTION_UNICODE_THRESHOLD = 5
PROMPT_INJECTION_COMMENT_MAX_LEN = 500
MICROFONT_SIZE_THRESHOLD_PX = 2.0

# ─── Shared thresholds (fix #388) ────────────────────────────────────────────

# Keyword stuffing threshold: single-word density above which it is considered spam
# SEMrush 2025 research: > 2.5% is a manipulation signal for AI engines
KEYWORD_STUFFING_THRESHOLD = 0.025

# URL patterns for "about" pages (fix #391)
ABOUT_LINK_PATTERNS = [
    "/about",
    "/chi-siamo",
    "/team",
    "/company",
    "/mission",
    "/our-story",
    "/who-we-are",
    "/storia",
    "/azienda",
]

# ─── Trust Stack Score (#273) ─────────────────────────────────────────────────

# Composite grading thresholds (0-25): (min_threshold, grade, trust_level)
TRUST_STACK_GRADE_BANDS = [
    (22, "A", "excellent"),
    (17, "B", "high"),
    (11, "C", "medium"),
    (6, "D", "low"),
    (0, "F", "low"),
]

# Authoritative source domains for Academic Trust
ACADEMIC_AUTHORITY_DOMAINS = [
    "ncbi.nlm.nih.gov",
    "pubmed.ncbi.nlm.nih.gov",
    "doi.org",
    "scholar.google.com",
    "arxiv.org",
    "researchgate.net",
    "nature.com",
    "science.org",
    "jstor.org",
    "ssrn.com",
]

# Recognized social domains for Social Trust
SOCIAL_PROOF_DOMAINS = [
    "twitter.com",
    "x.com",
    "instagram.com",
    "facebook.com",
    "linkedin.com",
    "youtube.com",
    "tiktok.com",
    "threads.net",
]

# Heading patterns for the References/Sources section
REFERENCES_HEADING_PATTERNS = [
    "references",
    "fonti",
    "sources",
    "bibliography",
    "note",
    "citazioni",
    "riferimenti",
    "bibliografia",
]

# Minimum statistical match count for Academic Trust
ACADEMIC_STATISTICS_MIN_MATCHES = 2

# ─── AI Discovery validation thresholds (#389) ───────────────────────────────

# Minimum length for summary.json fields
AI_DISCOVERY_SUMMARY_NAME_MIN_LEN: int = 3
AI_DISCOVERY_SUMMARY_DESC_MIN_LEN: int = 20

# Minimum length for faq.json item fields
AI_DISCOVERY_FAQ_QUESTION_MIN_LEN: int = 10
AI_DISCOVERY_FAQ_ANSWER_MIN_LEN: int = 20

# Minimum length for service.json name field
AI_DISCOVERY_SERVICE_NAME_MIN_LEN: int = 3

# ─── Score bands ─────────────────────────────────────────────────────────────

SCORE_BANDS = {
    "excellent": (86, 100),  # was (91, 100)
    "good": (68, 85),  # was (71, 90)
    "foundation": (36, 67),  # was (41, 70)
    "critical": (0, 35),  # was (0, 40)
}

# ─── Citability thresholds (#433) ───────────────────────────────────────────

# Flesch-Kincaid Grade Level formula constants (published formula, not magic numbers)
FLESCH_KINCAID_A = 0.39
FLESCH_KINCAID_B = 11.8
FLESCH_KINCAID_C = -15.59

# TTR (Type-Token Ratio) sliding window for vocabulary diversity
TTR_WINDOW_SIZE = 200
TTR_THRESHOLD = 0.40

# Front-loading: keyword density threshold in first 30% of content
FRONT_LOADING_DENSITY_THRESHOLD = 0.05
