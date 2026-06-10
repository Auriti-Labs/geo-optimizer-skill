"""
GEO Citations — one-shot AI citation check (`geo citations`).

Asks real AI answer engines the questions your customers ask, then checks
whether the brand is mentioned and whether the domain is cited as a source.
Perplexity Sonar is the preferred provider because it grounds answers in
live web search and returns the actual source URLs; parametric providers
(OpenAI, Anthropic, Groq) can only reveal brand knowledge, not citations.

Bring-your-own-API-key: set PERPLEXITY_API_KEY (or OPENAI_API_KEY, ...).
"""

from __future__ import annotations

import re
from collections import Counter
from urllib.parse import urlparse

from geo_optimizer.core.llm_client import _PROVIDER_ENV_KEYS, detect_provider, query_llm
from geo_optimizer.models.results import CitationCheckEntry, CitationCheckResult

_QUERY_TEMPLATES = [
    "What is the best tool for {topic}?",
    "What do you recommend for {topic}?",
    "Compare the top options for {topic}.",
]

_SNIPPET_LEN = 200

# Verdict thresholds on domain_citation_rate / brand_mention_rate
_STRONG_CITATION_RATE = 0.5


def normalize_domain(value: str) -> str:
    """Normalize a domain or URL to a bare lowercase hostname without www."""
    value = value.strip().lower()
    if "://" in value:
        value = urlparse(value).netloc or value
    value = value.split("/")[0].split(":")[0]
    return value.removeprefix("www.")


def _domains_in_text(text: str) -> list[str]:
    """Extract unique domains from URLs mentioned in answer text."""
    found: list[str] = []
    for match in re.findall(r"https?://[^\s)\]>\"']+", text):
        domain = normalize_domain(match)
        if domain and domain not in found:
            found.append(domain)
    return found


def _verdict(domain_citation_rate: float, brand_mention_rate: float) -> str:
    if domain_citation_rate >= _STRONG_CITATION_RATE:
        return "strong"
    if domain_citation_rate > 0:
        return "cited"
    if brand_mention_rate > 0:
        return "mentioned_only"
    return "invisible"


def resolve_provider(provider: str | None = None) -> tuple[str | None, str | None]:
    """Resolve the provider/key pair for a citation check.

    Explicit provider wins (key from its env var); otherwise prefer
    Perplexity when its key is set (real web citations), falling back to
    the standard auto-detection chain.
    """
    import os

    if provider:
        key = os.environ.get("GEO_LLM_API_KEY", "") or os.environ.get(_PROVIDER_ENV_KEYS.get(provider, ""), "")
        return (provider, key) if key else (provider, None)

    perplexity_key = os.environ.get("PERPLEXITY_API_KEY", "")
    if perplexity_key:
        return "perplexity", perplexity_key
    return detect_provider()


def run_citation_check(
    brand: str,
    domain: str,
    *,
    topic: str = "",
    queries: list[str] | None = None,
    provider: str | None = None,
    api_key: str | None = None,
) -> CitationCheckResult:
    """Ask an AI answer engine customer-style questions and check brand/domain visibility.

    Args:
        brand: Brand name to look for in answers.
        domain: Your domain (e.g. example.com) to look for among cited sources.
        topic: Topic context for the default query templates (defaults to brand).
        queries: Custom queries; overrides the default templates.
        provider: LLM provider (resolved via resolve_provider if not set).
        api_key: API key (resolved from environment if not set).

    Returns:
        CitationCheckResult with per-query entries and aggregate rates.
    """
    domain = normalize_domain(domain)
    topic = topic or brand
    query_list = list(queries) if queries else [t.format(topic=topic) for t in _QUERY_TEMPLATES]

    if provider is None or api_key is None:
        resolved_provider, resolved_key = resolve_provider(provider)
        provider = provider or resolved_provider
        api_key = api_key or resolved_key
    if not provider or not api_key:
        return CitationCheckResult(
            checked=True,
            skipped_reason=(
                "No AI provider configured. Set PERPLEXITY_API_KEY (recommended: real web citations) "
                "or OPENAI_API_KEY / ANTHROPIC_API_KEY / GROQ_API_KEY."
            ),
            brand=brand,
            domain=domain,
        )

    brand_pattern = re.compile(re.escape(brand), re.IGNORECASE)
    entries: list[CitationCheckEntry] = []
    other_domains: Counter[str] = Counter()
    answered = 0
    mentioned_count = 0
    cited_count = 0

    for query_text in query_list:
        response = query_llm(query_text, provider=provider, api_key=api_key)
        if response.error:
            entries.append(CitationCheckEntry(query=query_text, platform=provider, error=response.error))
            continue

        answered += 1
        source_domains = [normalize_domain(url) for url in response.citations]
        text_domains = _domains_in_text(response.text)
        all_domains = source_domains + [d for d in text_domains if d not in source_domains]

        brand_mentioned = bool(brand_pattern.search(response.text))
        domain_cited = domain in all_domains
        mentioned_count += brand_mentioned
        cited_count += domain_cited
        for d in all_domains:
            if d != domain:
                other_domains[d] += 1

        entries.append(
            CitationCheckEntry(
                query=query_text,
                platform=provider,
                model=response.model,
                brand_mentioned=brand_mentioned,
                domain_cited=domain_cited,
                cited_sources=list(response.citations),
                snippet=response.text[:_SNIPPET_LEN],
            )
        )

    if answered == 0:
        first_error = next((e.error for e in entries if e.error), "all queries failed")
        return CitationCheckResult(
            checked=True,
            skipped_reason=f"Provider '{provider}' returned no answers ({first_error})",
            brand=brand,
            domain=domain,
            entries=entries,
        )

    mention_rate = round(mentioned_count / answered, 2)
    citation_rate = round(cited_count / answered, 2)

    return CitationCheckResult(
        checked=True,
        brand=brand,
        domain=domain,
        entries=entries,
        queries_run=answered,
        brand_mention_rate=mention_rate,
        domain_citation_rate=citation_rate,
        top_cited_domains=other_domains.most_common(5),
        verdict=_verdict(citation_rate, mention_rate),
    )
