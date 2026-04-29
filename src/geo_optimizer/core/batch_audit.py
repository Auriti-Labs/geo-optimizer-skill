"""Orchestrazione batch per audit GEO su URL estratti da sitemap."""

from __future__ import annotations

import asyncio
from collections import Counter

from geo_optimizer.core.audit import run_full_audit, run_full_audit_async
from geo_optimizer.core.llms_generator import fetch_sitemap
from geo_optimizer.core.scoring import get_score_band
from geo_optimizer.models.config import AUDIT_TIMEOUT_SECONDS
from geo_optimizer.models.results import AuditResult, BatchAuditPageResult, BatchAuditResult

_DEFAULT_BATCH_MAX_URLS = 50
_DEFAULT_BATCH_CONCURRENCY = 5
_TOP_PAGE_LIMIT = 5


def run_batch_audit(
    sitemap_url: str,
    *,
    use_cache: bool = False,
    project_config=None,
    max_urls: int = _DEFAULT_BATCH_MAX_URLS,
    concurrency: int = _DEFAULT_BATCH_CONCURRENCY,
) -> BatchAuditResult:
    """Esegue un audit batch sincrono partendo da una sitemap XML."""
    return asyncio.run(
        run_batch_audit_async(
            sitemap_url,
            use_cache=use_cache,
            project_config=project_config,
            max_urls=max_urls,
            concurrency=concurrency,
        )
    )


async def run_batch_audit_async(
    sitemap_url: str,
    *,
    use_cache: bool = False,
    project_config=None,
    max_urls: int = _DEFAULT_BATCH_MAX_URLS,
    concurrency: int = _DEFAULT_BATCH_CONCURRENCY,
) -> BatchAuditResult:
    """Esegue audit concorrenti sugli URL contenuti in una sitemap."""
    if max_urls <= 0:
        raise ValueError("max_urls must be greater than 0")
    if concurrency <= 0:
        raise ValueError("concurrency must be greater than 0")

    sitemap_entries = await asyncio.to_thread(fetch_sitemap, sitemap_url)
    if not sitemap_entries:
        raise ValueError("No URLs found in sitemap")

    selected_urls = _select_urls(sitemap_entries, max_urls=max_urls)
    if not selected_urls:
        raise ValueError("No URLs found in sitemap")

    page_results = await _audit_urls(
        selected_urls,
        use_cache=use_cache,
        project_config=project_config,
        concurrency=concurrency,
    )
    return _aggregate_batch_result(
        sitemap_url=sitemap_url,
        discovered_urls=len(sitemap_entries),
        page_results=page_results,
    )


def _select_urls(sitemap_entries, *, max_urls: int) -> list[str]:
    """Deduplica gli URL della sitemap preservando l'ordine originale."""
    seen: set[str] = set()
    selected: list[str] = []
    for entry in sitemap_entries:
        if entry.url in seen:
            continue
        seen.add(entry.url)
        selected.append(entry.url)
        if len(selected) >= max_urls:
            break
    return selected


async def _audit_urls(
    urls: list[str],
    *,
    use_cache: bool,
    project_config,
    concurrency: int,
) -> list[BatchAuditPageResult]:
    """Esegue gli audit delle pagine con un limite di concorrenza."""
    semaphore = asyncio.Semaphore(concurrency)

    async def _worker(url: str) -> BatchAuditPageResult:
        async with semaphore:
            # Fix H-2: per-URL timeout prevents a single hanging URL from blocking the batch
            try:
                return await asyncio.wait_for(
                    _audit_single_url(url, use_cache=use_cache, project_config=project_config),
                    timeout=AUDIT_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                result = AuditResult(url=url, error=f"Timeout ({AUDIT_TIMEOUT_SECONDS}s)", band="critical")
                return _summarize_audit_result(result)

    return await asyncio.gather(*(_worker(url) for url in urls))


async def _audit_single_url(url: str, *, use_cache: bool, project_config) -> BatchAuditPageResult:
    """Esegue un audit singolo e lo converte in un risultato batch sintetico."""
    try:
        if use_cache or not _async_runtime_available():
            result = await asyncio.to_thread(run_full_audit, url, use_cache=use_cache, project_config=project_config)
        else:
            result = await run_full_audit_async(url, project_config=project_config)
    except Exception as exc:  # pragma: no cover - rete/eccezioni inattese
        result = AuditResult(url=url, error=f"{type(exc).__name__}: {exc}", band="critical")
    return _summarize_audit_result(result)


def _async_runtime_available() -> bool:
    """Verifica se il path async è disponibile per gli audit batch."""
    try:
        import httpx  # noqa: F401

        return True
    except ImportError:
        return False


def _summarize_audit_result(result: AuditResult) -> BatchAuditPageResult:
    """Riduce un AuditResult alla sintesi usata nel report batch."""
    return BatchAuditPageResult(
        url=result.url,
        score=result.score,
        band=result.band,
        http_status=result.http_status,
        error=result.error,
        score_breakdown=dict(result.score_breakdown),
        recommendations_count=len(result.recommendations),
    )


def _aggregate_batch_result(
    *,
    sitemap_url: str,
    discovered_urls: int,
    page_results: list[BatchAuditPageResult],
) -> BatchAuditResult:
    """Calcola medie e classifiche a partire dai risultati pagina."""
    successful_pages = [page for page in page_results if not page.error]
    failed_pages = [page for page in page_results if page.error]

    average_score = 0.0
    average_band = "critical"
    band_counts: dict[str, int] = {}
    average_score_breakdown: dict[str, float] = {}

    if successful_pages:
        average_score = round(sum(page.score for page in successful_pages) / len(successful_pages), 2)
        average_band = get_score_band(int(round(average_score)))
        band_counts = dict(Counter(page.band for page in successful_pages))
        average_score_breakdown = _average_breakdowns(successful_pages)

    ranked_pages = sorted(successful_pages, key=lambda page: page.score, reverse=True)

    return BatchAuditResult(
        sitemap_url=sitemap_url,
        discovered_urls=discovered_urls,
        audited_urls=len(page_results),
        successful_urls=len(successful_pages),
        failed_urls=len(failed_pages),
        average_score=average_score,
        average_band=average_band,
        band_counts=band_counts,
        average_score_breakdown=average_score_breakdown,
        pages=page_results,
        top_pages=ranked_pages[:_TOP_PAGE_LIMIT],
        worst_pages=list(reversed(ranked_pages[-_TOP_PAGE_LIMIT:])),
    )


def _average_breakdowns(page_results: list[BatchAuditPageResult]) -> dict[str, float]:
    """Calcola la media dei punteggi per categoria sulle pagine valide."""
    category_totals: dict[str, float] = {}
    for page in page_results:
        for category, score in page.score_breakdown.items():
            category_totals[category] = category_totals.get(category, 0.0) + score

    total_pages = len(page_results)
    return {category: round(total / total_pages, 2) for category, total in sorted(category_totals.items())}
