"""
Centralized configuration for GEO Optimizer.

All shared constants (bots, schemas, scoring weights, patterns) live here
so that core modules, CLI, and tests can import from a single source.
"""

# ─── HTTP ────────────────────────────────────────────────────────────────────

USER_AGENT = "GEO-Optimizer/2.0 (https://github.com/auriti-labs/geo-optimizer-skill)"

HEADERS = {"User-Agent": USER_AGENT}

# HTTP response size limit: 10 MB (prevents DoS from huge responses) — fix #91
MAX_RESPONSE_SIZE: int = 10 * 1024 * 1024

# Maximum number of sub-sitemaps to process in a sitemap index — fix #90
MAX_SUB_SITEMAPS: int = 10

# Total URL limit extracted from all sitemaps — fix #124 (sitemap bomb)
MAX_TOTAL_URLS: int = 10_000


# ─── AI bots — 3-tier classification (training/search/user) ──────────────────
#
# Training: crawl per addestrare modelli (meno critico per visibilità diretta)
# Search:   citano il sito nelle risposte AI (massima priorità per GEO)
# User:     fetch on-demand quando un utente chiede di un URL specifico

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
        "cohere-ai",
        "Bytespider",
        "meta-externalagent",
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

# ─── Schema types ────────────────────────────────────────────────────────────

VALUABLE_SCHEMAS = [
    "WebSite",
    "WebApplication",
    "FAQPage",
    "Article",
    "BlogPosting",
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
        "sameAs": [],
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
    # robots.txt — 18 punti (era 20)
    "robots_found": 5,
    "robots_citation_ok": 13,  # era 15
    "robots_some_allowed": 10,  # era 8 — wildcard Allow ora vale di più
    # llms.txt — 18 punti (era 20) — qualità graduata + blockquote v2
    "llms_found": 5,  # era 6 — 1 punto spostato a llms_blockquote (#39)
    "llms_h1": 2,  # era 3
    "llms_blockquote": 1,  # #39: blockquote description presente
    "llms_sections": 2,  # era 4
    "llms_links": 2,  # era 3
    "llms_depth": 2,  # NUOVO: word_count >= 1000
    "llms_depth_high": 2,  # NUOVO: word_count >= 5000
    "llms_full": 2,  # NUOVO: has llms-full.txt
    # Schema JSON-LD — 22 punti (era 25) — qualsiasi tipo valido + sameAs + richness
    "schema_any_valid": 2,  # qualsiasi JSON-LD schema valido trovato (era 5, ridotto per richness)
    "schema_richness": 3,  # NUOVO: schema con 5+ attributi rilevanti (Growth Marshal 2026)
    "schema_faq": 3,  # era 5 — ridotto, migrato a brand_topic_authority
    "schema_article": 3,  # era 4
    "schema_organization": 3,  # era 3
    "schema_website": 2,  # era 3
    "schema_sameas": 0,  # era 3, migrato a brand KG — mantenuto a 0 per retrocompat
    # Meta tags — 14 punti
    "meta_title": 5,
    "meta_description": 2,
    "meta_canonical": 3,
    "meta_og": 4,
    # Content quality — 14 punti (era 15) — controlli struttura
    "content_h1": 2,  # era 3
    "content_numbers": 1,  # era 2
    "content_links": 1,  # era 2
    "content_word_count": 2,  # era 4
    "content_heading_hierarchy": 2,  # NUOVO: ha H2 + H3 in gerarchia corretta
    "content_lists_or_tables": 2,  # NUOVO: ha <ul>/<ol>/<table>
    "content_front_loading": 2,  # NUOVO: info chiave nel primo 30% del contenuto
    # Signals — 8 punti (NUOVA categoria)
    "signals_lang": 3,  # NUOVO: <html lang="...">
    "signals_rss": 2,  # era 3
    "signals_freshness": 1,  # era 2
    # AI Discovery — 6 punti (geo-checklist.dev standard)
    "ai_discovery_well_known": 2,  # /.well-known/ai.txt presente
    "ai_discovery_summary": 2,  # /ai/summary.json valido
    "ai_discovery_faq": 1,  # /ai/faq.json presente
    "ai_discovery_service": 1,  # /ai/service.json presente
    # Brand & Entity — 10 punti (NUOVA categoria v4.3)
    "brand_entity_coherence": 3,  # nome coerente tra H1/title/og:title/schema
    "brand_kg_readiness": 3,  # sameAs verso Wikipedia/Wikidata/LinkedIn/Crunchbase
    "brand_about_contact": 2,  # link /about + Organization con address/telephone
    "brand_geo_identity": 1,  # hreflang + schema geo (address, areaServed)
    "brand_topic_authority": 1,  # FAQ depth + Article con dateModified
}

# Minimum word threshold for content_word_count (300 parole = contenuto sostanziale)
CONTENT_MIN_WORDS = 300

# Soglie profondità llms.txt
LLMS_DEPTH_WORDS = 1000
LLMS_DEPTH_HIGH_WORDS = 5000

# Domini autorevoli sameAs (per collegamento knowledge graph)
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

# Domini pillar per Knowledge Graph (disambiguazione AI — i 4 più rilevanti)
KG_PILLAR_DOMAINS = {
    "wikipedia.org",
    "wikidata.org",
    "linkedin.com",
    "crunchbase.com",
}

SCORE_BANDS = {
    "excellent": (86, 100),  # era (91, 100)
    "good": (68, 85),  # era (71, 90)
    "foundation": (36, 67),  # era (41, 70)
    "critical": (0, 35),  # era (0, 40)
}
