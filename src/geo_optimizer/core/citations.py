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

import logging
import re
from collections import Counter
from urllib.parse import urlparse

from geo_optimizer.core.llm_client import _PROVIDER_ENV_KEYS, detect_provider, query_llm
from geo_optimizer.models.results import CitationCheckEntry, CitationCheckResult
from geo_optimizer.utils.brand_match import brand_pattern

logger = logging.getLogger(__name__)

_QUERY_TEMPLATES = [
    "What is the best tool for {topic}?",
    "What do you recommend for {topic}?",
    "Compare the top options for {topic}.",
]

_SNIPPET_LEN = 200

# Verdict thresholds on domain_citation_rate / brand_mention_rate
_STRONG_CITATION_RATE = 0.5

# A verdict is "stable" when a 95% confidence interval on the citation rate is
# narrow enough that its two ends map to the same verdict. Research on AI-search
# visibility (Schulte et al. 2026, arXiv:2604.07585) shows a single sample is a
# noisy estimate — the same query re-run returns different sources.
_CI_Z = 1.96


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


def _wilson_interval(successes: int, n: int, z: float = _CI_Z) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion, rounded to 2 dp.

    Preferred over the normal approximation because it stays inside [0, 1] and
    behaves sensibly for the small sample sizes a citation check produces.
    """
    if n <= 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return (round(max(0.0, center - margin), 2), round(min(1.0, center + margin), 2))


def resolve_provider(provider: str | None = None) -> tuple[str | None, str | None]:
    """Resolve the provider/key pair for a citation check.

    Explicit provider wins (key from its env var); otherwise prefer
    Perplexity when its key is set (real web citations), falling back to
    the standard auto-detection chain.

    "serpbase" (Google SERP + AI Overview observation, #527) is resolved
    only when explicitly requested — it is never part of the default
    auto-detection chain, since it observes Google directly rather than
    asking an LLM, and is a paid API past its 100 free searches.
    """
    import os

    if provider == "serpbase":
        return "serpbase", os.environ.get("SERPBASE_API_KEY") or None

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
    runs: int = 1,
) -> CitationCheckResult:
    """Ask an AI answer engine customer-style questions and check brand/domain visibility.

    Args:
        brand: Brand name to look for in answers.
        domain: Your domain (e.g. example.com) to look for among cited sources.
        topic: Topic context for the default query templates (defaults to brand).
        queries: Custom queries; overrides the default templates.
        provider: LLM provider (resolved via resolve_provider if not set).
        api_key: API key (resolved from environment if not set).
        runs: How many times to ask each query. AI answers are non-deterministic,
            so >1 turns each rate into a sampled estimate with a confidence
            interval instead of a single coin flip. Costs runs x queries calls.

    Returns:
        CitationCheckResult with per-query entries and aggregate rates.
    """
    domain = normalize_domain(domain)
    topic = topic or brand
    runs = max(1, int(runs))
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
                "or OPENAI_API_KEY / ANTHROPIC_API_KEY / GROQ_API_KEY / MINIMAX_API_KEY / "
                "GEMINI_API_KEY / DEEPSEEK_API_KEY / SERPBASE_API_KEY (Google SERP + AI Overview)."
            ),
            brand=brand,
            domain=domain,
        )

    brand_matcher = brand_pattern(brand)

    if provider == "serpbase":
        return _run_serpbase_citation_check(brand, domain, query_list, api_key, brand_matcher)

    entries: list[CitationCheckEntry] = []
    other_domains: Counter[str] = Counter()
    queries_answered = 0
    total_answers = 0
    mentioned_count = 0
    cited_count = 0
    url_count = 0

    for query_text in query_list:
        q_answered = 0
        q_mention = 0
        q_cited = 0
        q_url = 0
        q_sources: list[str] = []
        q_model = ""
        q_snippet = ""
        q_error: str | None = None

        for _ in range(runs):
            response = query_llm(query_text, provider=provider, api_key=api_key)
            if response.error:
                q_error = q_error or response.error
                continue

            q_answered += 1
            q_model = q_model or response.model
            if not q_snippet:
                q_snippet = response.text[:_SNIPPET_LEN]

            source_domains = [normalize_domain(url) for url in response.citations]
            text_domains = _domains_in_text(response.text)

            # A URL of the domain written in the answer names the site, so it counts as a brand mention
            # (never as a citation).
            if brand_matcher.search(response.text) or domain in text_domains:
                q_mention += 1
            # A URL the model wrote is tracked apart: it is not a source the engine returned.
            if domain in source_domains:
                q_cited += 1
            if domain in text_domains:
                q_url += 1
            # Competitors are the domains the engine returned as sources, not URLs the model wrote.
            for d in source_domains:
                if d != domain:
                    other_domains[d] += 1
            for url in response.citations:
                if url not in q_sources:
                    q_sources.append(url)

        if q_answered == 0:
            entries.append(
                CitationCheckEntry(query=query_text, platform=provider, runs=runs, error=q_error or "no answer")
            )
            continue

        queries_answered += 1
        total_answers += q_answered
        mentioned_count += q_mention
        cited_count += q_cited
        url_count += q_url

        entries.append(
            CitationCheckEntry(
                query=query_text,
                platform=provider,
                model=q_model,
                runs=q_answered,
                mention_runs=q_mention,
                citation_runs=q_cited,
                brand_mentioned=q_mention > 0,
                domain_cited=q_cited > 0,
                provider_source_cited=q_cited > 0,
                url_mentioned=q_url > 0,
                cited_sources=q_sources,
                snippet=q_snippet,
            )
        )

    if total_answers == 0:
        first_error = next((e.error for e in entries if e.error), "all queries failed")
        return CitationCheckResult(
            checked=True,
            skipped_reason=f"Provider '{provider}' returned no answers ({first_error})",
            brand=brand,
            domain=domain,
            entries=entries,
            runs_per_query=runs,
        )

    mention_rate = round(mentioned_count / total_answers, 2)
    citation_rate = round(cited_count / total_answers, 2)
    citation_ci = _wilson_interval(cited_count, total_answers)
    mention_ci = _wilson_interval(mentioned_count, total_answers)
    # The verdict is trustworthy only if the confidence interval does not straddle
    # a verdict boundary (a one-run check is treated as inherently unstable).
    stable = runs > 1 and _verdict(citation_ci[0], mention_ci[0]) == _verdict(citation_ci[1], mention_ci[1])

    return CitationCheckResult(
        checked=True,
        brand=brand,
        domain=domain,
        entries=entries,
        queries_run=queries_answered,
        runs_per_query=runs,
        total_answers=total_answers,
        brand_mention_rate=mention_rate,
        domain_citation_rate=citation_rate,
        url_mention_rate=round(url_count / total_answers, 2),
        brand_mention_rate_ci=mention_ci,
        domain_citation_rate_ci=citation_ci,
        stable=stable,
        top_cited_domains=other_domains.most_common(5),
        verdict=_verdict(citation_rate, mention_rate),
    )


def _run_serpbase_citation_check(
    brand: str,
    domain: str,
    query_list: list[str],
    api_key: str,
    brand_matcher: re.Pattern,
) -> CitationCheckResult:
    """Google SERP-based citation check via serpbase.dev (#527).

    Observes the organic results and AI Overview (when Google renders one)
    directly, instead of asking an LLM. Each query is a single live SERP
    snapshot: `--runs` sampling doesn't apply here the way it does to a
    non-deterministic LLM answer — resampling the same SERP would just
    multiply paid serpbase calls for no corresponding benefit, so every
    entry reports `runs=1` and the aggregate has no confidence interval
    (`stable` stays False, same as a one-run LLM check).
    """
    from geo_optimizer.core.serp_provider import query_serpbase

    entries: list[CitationCheckEntry] = []
    other_domains: Counter[str] = Counter()
    queries_answered = 0
    mentioned_count = 0
    cited_count = 0
    organic_count = 0
    ai_overview_seen = 0

    for query_text in query_list:
        response = query_serpbase(query_text, api_key=api_key)
        if response.error:
            entries.append(CitationCheckEntry(query=query_text, platform="google_serp", runs=1, error=response.error))
            continue

        if response.ai_overview_present:
            ai_overview_seen += 1

        organic_urls = [r.url for r in response.organic if r.url]
        # Ranking in the organic list is not an AI citation: only AI Overview sources count as cited.
        organic = domain in {normalize_domain(u) for u in organic_urls}

        haystack = " ".join([f"{r.title} {r.snippet}" for r in response.organic] + [response.ai_overview_text])
        mentioned = bool(brand_matcher.search(haystack))
        cited = domain in {normalize_domain(u) for u in response.ai_overview_sources if u}

        queries_answered += 1
        mentioned_count += int(mentioned)
        cited_count += int(cited)
        organic_count += int(organic)
        # Only AI Overview sources count as "cited instead of you"; organic rankers are not citations.
        for d in dict.fromkeys(normalize_domain(u) for u in response.ai_overview_sources if u):
            if d != domain:
                other_domains[d] += 1

        snippet = response.ai_overview_text[:_SNIPPET_LEN] or (
            response.organic[0].snippet[:_SNIPPET_LEN] if response.organic else ""
        )
        entries.append(
            CitationCheckEntry(
                query=query_text,
                platform="google_serp",
                model="ai_overview" if response.ai_overview_present else "",
                runs=1,
                mention_runs=int(mentioned),
                citation_runs=int(cited),
                brand_mentioned=mentioned,
                domain_cited=cited,
                ai_overview_source_cited=cited,
                organic_result_present=organic,
                cited_sources=list(response.ai_overview_sources)[:10],
                snippet=snippet,
            )
        )

    # Coverage-measurement hook (#527): how often the ai_overview block
    # actually surfaces is undocumented and query-dependent, so this is
    # logged rather than asserted or exposed as a scoring signal.
    if query_list:
        logger.info("serpbase: AI Overview present in %d/%d queries", ai_overview_seen, len(query_list))

    if queries_answered == 0:
        first_error = next((e.error for e in entries if e.error), "all queries failed")
        return CitationCheckResult(
            checked=True,
            skipped_reason=f"Provider 'google_serp' returned no answers ({first_error})",
            brand=brand,
            domain=domain,
            entries=entries,
            runs_per_query=1,
        )

    mention_rate = round(mentioned_count / queries_answered, 2)
    citation_rate = round(cited_count / queries_answered, 2)

    return CitationCheckResult(
        checked=True,
        brand=brand,
        domain=domain,
        entries=entries,
        queries_run=queries_answered,
        runs_per_query=1,
        total_answers=queries_answered,
        brand_mention_rate=mention_rate,
        domain_citation_rate=citation_rate,
        organic_presence_rate=round(organic_count / queries_answered, 2),
        brand_mention_rate_ci=(mention_rate, mention_rate),
        domain_citation_rate_ci=(citation_rate, citation_rate),
        stable=False,
        top_cited_domains=other_domains.most_common(5),
        verdict=_verdict(citation_rate, mention_rate),
    )
