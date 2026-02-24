"""
Centralized configuration for GEO Optimizer.

All shared constants (bots, schemas, scoring weights, patterns) live here
so that core modules, CLI, and tests can import from a single source.
"""

# ─── HTTP ────────────────────────────────────────────────────────────────────

USER_AGENT = "GEO-Optimizer/2.0 (https://github.com/auriti-web-design/geo-optimizer-skill)"

HEADERS = {"User-Agent": USER_AGENT}

# ─── AI bots that should be listed in robots.txt ─────────────────────────────

AI_BOTS = {
    "GPTBot": "OpenAI (ChatGPT training)",
    "OAI-SearchBot": "OpenAI (ChatGPT search citations)",
    "ChatGPT-User": "OpenAI (ChatGPT on-demand fetch)",
    "anthropic-ai": "Anthropic (Claude training)",
    "ClaudeBot": "Anthropic (Claude citations)",
    "claude-web": "Anthropic (Claude web crawl)",
    "PerplexityBot": "Perplexity AI (index builder)",
    "Perplexity-User": "Perplexity (citation fetch on-demand)",
    "Google-Extended": "Google (Gemini training)",
    "Applebot-Extended": "Apple (AI training)",
    "cohere-ai": "Cohere (language models)",
    "DuckAssistBot": "DuckDuckGo AI",
    "Bytespider": "ByteDance/TikTok AI",
    "meta-externalagent": "Meta AI (Facebook/Instagram AI)",
}

# Critical citation bots (search-oriented, not just training)
CITATION_BOTS = {"OAI-SearchBot", "ClaudeBot", "PerplexityBot"}

# ─── Schema types ────────────────────────────────────────────────────────────

VALUABLE_SCHEMAS = [
    "WebSite", "WebApplication", "FAQPage", "Article", "BlogPosting",
    "HowTo", "Recipe", "Product", "Organization", "Person", "BreadcrumbList",
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
        "logo": "{{logo_url}}",
        "sameAs": [],
    },
    "breadcrumb": {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "{{url}}"}
        ],
    },
}

# ─── llms.txt patterns ──────────────────────────────────────────────────────

CATEGORY_PATTERNS = [
    (r"/blog/", "Blog & Articles"),
    (r"/article", "Articles"),
    (r"/post/", "Posts"),
    (r"/finance/", "Finance Tools"),
    (r"/health/", "Health & Wellness"),
    (r"/math/", "Math"),
    (r"/calcul", "Calculators"),
    (r"/tool", "Tools"),
    (r"/app/", "Applications"),
    (r"/docs?/", "Documentation"),
    (r"/guide/", "Guides"),
    (r"/tutorial", "Tutorials"),
    (r"/product", "Products"),
    (r"/service", "Services"),
    (r"/about", "About"),
    (r"/contact", "Contact"),
    (r"/privacy", "Privacy & Legal"),
    (r"/terms", "Terms"),
]

SKIP_PATTERNS = [
    r"/wp-", r"/admin", r"/login", r"/logout", r"/register",
    r"/cart", r"/checkout", r"/account", r"/user/",
    r"\.(xml|json|rss|atom|pdf|jpg|png|css|js)$",
    r"/tag/", r"/category/\w+/page/", r"/page/\d+",
]

# llms.txt section ordering
SECTION_PRIORITY_ORDER = [
    "Tools", "Calculators", "Finance Tools", "Health & Wellness",
    "Math", "Applications", "Main Pages",
    "Documentation", "Guides", "Tutorials",
    "Blog & Articles", "Articles", "Posts",
    "Products", "Services",
    "About", "Contact",
    "Other",
    "Privacy & Legal", "Terms",
]

OPTIONAL_CATEGORIES = {"Privacy & Legal", "Terms", "Contact", "Other"}

# ─── Scoring weights ─────────────────────────────────────────────────────────

SCORING = {
    "robots_found": 5,
    "robots_citation_ok": 15,
    "robots_some_allowed": 8,
    "llms_found": 10,
    "llms_h1": 3,
    "llms_sections": 4,
    "llms_links": 3,
    "schema_website": 10,
    "schema_faq": 10,
    "schema_webapp": 5,
    "meta_title": 5,
    "meta_description": 8,
    "meta_canonical": 3,
    "meta_og": 4,
    "content_h1": 4,
    "content_numbers": 6,
    "content_links": 5,
}

SCORE_BANDS = {
    "excellent": (91, 100),
    "good": (71, 90),
    "foundation": (41, 70),
    "critical": (0, 40),
}
