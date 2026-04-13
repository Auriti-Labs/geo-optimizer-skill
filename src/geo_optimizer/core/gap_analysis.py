"""Gap analysis interpretativa tra due audit GEO."""

from __future__ import annotations

from geo_optimizer.core.audit import run_full_audit
from geo_optimizer.core.diffing import build_audit_diff
from geo_optimizer.models.config import SCORING
from geo_optimizer.models.results import AuditResult, GapAction, GapAnalysisResult


def run_gap_analysis(url1: str, url2: str) -> GapAnalysisResult:
    """Esegue due audit e restituisce una gap analysis ordinata per impatto."""
    result1 = run_full_audit(url1)
    result2 = run_full_audit(url2)
    return build_gap_analysis(result1, result2)


def build_gap_analysis(result1: AuditResult, result2: AuditResult) -> GapAnalysisResult:
    """Costruisce la gap analysis a partire da due `AuditResult`."""
    weaker, stronger = _sort_by_score(result1, result2)
    diff = build_audit_diff(weaker, stronger)
    strengths = [item for item in diff.regressed_categories if item.delta < 0]
    action_plan = _build_action_plan(weaker, stronger)
    action_plan.sort(key=lambda item: item.impact_points, reverse=True)

    return GapAnalysisResult(
        weaker_url=weaker.url,
        stronger_url=stronger.url,
        weaker_score=weaker.score,
        stronger_score=stronger.score,
        score_gap=stronger.score - weaker.score,
        weaker_band=weaker.band,
        stronger_band=stronger.band,
        category_deltas=diff.improved_categories,
        action_plan=action_plan,
        strengths=strengths,
    )


def _sort_by_score(result1: AuditResult, result2: AuditResult) -> tuple[AuditResult, AuditResult]:
    """Restituisce `(weaker, stronger)` usando il punteggio GEO come discriminante."""
    if result1.score <= result2.score:
        return result1, result2
    return result2, result1


def _build_action_plan(weaker: AuditResult, stronger: AuditResult) -> list[GapAction]:
    """Genera azioni concrete quando il sito debole manca segnali presenti nel forte."""
    actions: list[GapAction] = []
    weaker_url = weaker.url.rstrip("/")

    def add_action(category: str, title: str, rationale: str, impact_points: int, command: str = "") -> None:
        if impact_points <= 0:
            return
        priority = _priority_for_impact(impact_points)
        actions.append(
            GapAction(
                category=category,
                title=title,
                rationale=rationale,
                impact_points=impact_points,
                priority=priority,
                command=command,
            )
        )

    if stronger.robots.found and not weaker.robots.found:
        add_action(
            "robots",
            "Create robots.txt for AI crawlers",
            "The stronger site exposes a robots.txt file while the weaker site has none.",
            SCORING["robots_found"],
            f"geo fix --url {weaker_url} --only robots",
        )
    if stronger.robots.citation_bots_ok and not weaker.robots.citation_bots_ok:
        add_action(
            "robots",
            "Allow critical citation bots",
            "Citation bots are correctly configured on the stronger site and missing or blocked on the weaker site.",
            SCORING["robots_citation_ok"],
            f"geo fix --url {weaker_url} --only robots",
        )

    if stronger.llms.found and not weaker.llms.found:
        add_action(
            "llms",
            "Publish llms.txt",
            "The stronger site exposes llms.txt and the weaker site does not.",
            SCORING["llms_found"],
            f"geo llms --base-url {weaker_url}",
        )
    if stronger.llms.has_sections and not weaker.llms.has_sections:
        add_action(
            "llms",
            "Add H2 sections to llms.txt",
            "Sectioned llms.txt helps AI systems navigate the site structure more clearly.",
            SCORING["llms_sections"],
            f"geo fix --url {weaker_url} --only llms",
        )
    if stronger.llms.has_links and not weaker.llms.has_links:
        add_action(
            "llms",
            "Add key links to llms.txt",
            "The stronger site exposes navigable markdown links in llms.txt while the weaker site does not.",
            SCORING["llms_links"],
            f"geo fix --url {weaker_url} --only llms",
        )

    if stronger.schema.has_faq and not weaker.schema.has_faq:
        add_action(
            "schema",
            "Add FAQPage schema",
            "The stronger site exposes FAQ structured data that the weaker site is missing.",
            SCORING["schema_faq"],
            f"geo schema --type faq --url {weaker_url}",
        )
    if stronger.schema.has_organization and not weaker.schema.has_organization:
        add_action(
            "schema",
            "Add Organization schema",
            "The stronger site has organization-level entity markup and the weaker site does not.",
            SCORING["schema_organization"],
            f"geo schema --type organization --url {weaker_url}",
        )
    if stronger.schema.has_article and not weaker.schema.has_article:
        add_action(
            "schema",
            "Add Article schema",
            "The stronger site marks content as Article/BlogPosting and the weaker site does not.",
            SCORING["schema_article"],
            f"geo schema --type article --url {weaker_url}",
        )
    if stronger.schema.has_website and not weaker.schema.has_website:
        add_action(
            "schema",
            "Add WebSite schema",
            "The stronger site exposes baseline WebSite markup and the weaker site is missing it.",
            SCORING["schema_website"],
            f"geo schema --type website --url {weaker_url}",
        )

    if stronger.meta.has_title and not weaker.meta.has_title:
        add_action(
            "meta",
            "Add a title tag",
            "The stronger site has a title tag and the weaker site does not.",
            SCORING["meta_title"],
            f"geo fix --url {weaker_url} --only meta",
        )
    if (
        stronger.meta.has_og_title
        and stronger.meta.has_og_description
        and not (weaker.meta.has_og_title and weaker.meta.has_og_description)
    ):
        add_action(
            "meta",
            "Complete Open Graph metadata",
            "The stronger site exposes more complete OG metadata than the weaker site.",
            SCORING["meta_og"],
            f"geo fix --url {weaker_url} --only meta",
        )
    if stronger.meta.has_canonical and not weaker.meta.has_canonical:
        add_action(
            "meta",
            "Add canonical URL",
            "Canonical alignment is present on the stronger site and missing on the weaker site.",
            SCORING["meta_canonical"],
            f"geo fix --url {weaker_url} --only meta",
        )

    if stronger.ai_discovery.has_well_known_ai and not weaker.ai_discovery.has_well_known_ai:
        add_action(
            "ai_discovery",
            "Create /.well-known/ai.txt",
            "The stronger site exposes AI discovery entry points that the weaker site lacks.",
            SCORING["ai_discovery_well_known"],
            f"geo fix --url {weaker_url} --only ai_discovery",
        )
    if stronger.ai_discovery.has_summary and not weaker.ai_discovery.has_summary:
        add_action(
            "ai_discovery",
            "Publish /ai/summary.json",
            "The stronger site exposes machine-readable summary metadata that the weaker site is missing.",
            SCORING["ai_discovery_summary"],
            f"geo fix --url {weaker_url} --only ai_discovery",
        )
    if stronger.ai_discovery.has_faq and not weaker.ai_discovery.has_faq:
        add_action(
            "ai_discovery",
            "Publish /ai/faq.json",
            "The stronger site exposes structured AI FAQs and the weaker site does not.",
            SCORING["ai_discovery_faq"],
            f"geo fix --url {weaker_url} --only ai_discovery",
        )

    if stronger.signals.has_lang and not weaker.signals.has_lang:
        add_action(
            "signals",
            'Add `<html lang="...">`',
            "The stronger site has an explicit language signal and the weaker site does not.",
            SCORING["signals_lang"],
        )
    if stronger.signals.has_rss and not weaker.signals.has_rss:
        add_action(
            "signals",
            "Add RSS/Atom feed",
            "The stronger site exposes an RSS/Atom feed, improving machine-readable discovery.",
            SCORING["signals_rss"],
        )

    if stronger.content.has_front_loading and not weaker.content.has_front_loading:
        add_action(
            "content",
            "Front-load key answers earlier",
            "The stronger site surfaces key information earlier in the content than the weaker site.",
            SCORING["content_front_loading"],
        )
    if stronger.content.has_heading_hierarchy and not weaker.content.has_heading_hierarchy:
        add_action(
            "content",
            "Improve H2/H3 hierarchy",
            "The stronger site has clearer section hierarchy for extraction and chunking.",
            SCORING["content_heading_hierarchy"],
        )
    if stronger.content.has_links and not weaker.content.has_links:
        add_action(
            "content",
            "Add authoritative outbound citations",
            "The stronger site links to external sources while the weaker site does not.",
            SCORING["content_links"],
        )

    if stronger.brand_entity.kg_pillar_count > weaker.brand_entity.kg_pillar_count:
        add_action(
            "brand_entity",
            "Expand sameAs Knowledge Graph links",
            "The stronger site connects its entity to more authoritative profiles.",
            SCORING["brand_kg_readiness"],
            f"geo schema --type organization --url {weaker_url}",
        )
    if stronger.brand_entity.has_about_link and not weaker.brand_entity.has_about_link:
        add_action(
            "brand_entity",
            "Expose an About page",
            "The stronger site has a visible about/company page and the weaker site does not.",
            1,
        )

    return _dedupe_actions(actions)


def _dedupe_actions(actions: list[GapAction]) -> list[GapAction]:
    """Deduplica azioni uguali conservando la prima occorrenza."""
    seen: set[tuple[str, str]] = set()
    deduped: list[GapAction] = []
    for action in actions:
        key = (action.category, action.title)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(action)
    return deduped


def _priority_for_impact(impact_points: int) -> str:
    """Converte l'impatto stimato in priorità qualitativa."""
    if impact_points >= 5:
        return "high"
    if impact_points >= 3:
        return "medium"
    return "low"
