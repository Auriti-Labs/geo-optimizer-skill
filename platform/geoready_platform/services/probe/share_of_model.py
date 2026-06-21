"""Share-of-Model v1 + competitor tally. Pure, no I/O.

Share-of-Model v1 = (# recommendation-intent answers that mention the brand) /
(# recommendation-intent answers that were answered).

v1 limitation: "recommended" is approximated by "brand mentioned in a
recommendation-class answer" — true ranked-endorsement detection is deferred.
Competitor tally aggregates competitor domains/names across all answers.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from geoready_platform.services.probe.taxonomy import CATEGORY_BY_KEY


@dataclass
class AnalyzedResponse:
    category: str
    answered: bool
    brand_mentioned: bool
    competitor_domains: list[str] = field(default_factory=list)
    competitor_names: list[str] = field(default_factory=list)


@dataclass
class ShareOfModel:
    share_of_model: float
    recommended_count: int
    share_denominator: int
    competitors: list[dict]  # [{"name": <domain-or-name>, "mentions": int}]


def _counts_for_share(category: str) -> bool:
    cat = CATEGORY_BY_KEY.get(category)
    return bool(cat and cat.counts_for_share)


def compute_share_of_model(responses: list[AnalyzedResponse]) -> ShareOfModel:
    denom = 0
    recommended = 0
    competitor_counter: Counter[str] = Counter()

    for r in responses:
        if _counts_for_share(r.category) and r.answered:
            denom += 1
            if r.brand_mentioned:
                recommended += 1
        for d in r.competitor_domains:
            competitor_counter[d] += 1
        for n in r.competitor_names:
            competitor_counter[n] += 1

    share = (recommended / denom) if denom else 0.0
    competitors = [{"name": name, "mentions": count} for name, count in competitor_counter.most_common()]
    return ShareOfModel(
        share_of_model=round(share, 4),
        recommended_count=recommended,
        share_denominator=denom,
        competitors=competitors,
    )
