r"""Small live evaluation via a non-web OpenRouter model — EVAL TOOLING ONLY.

Scope (deliberately bounded): 3 businesses x 2 prompts x 1 run = 6 calls.
Measures what a non-web model CAN validate: brand recognition, mention-based
Share-of-Model, hallucination flags, and basic response usefulness. It does NOT
measure competitor extraction (non-web models return no citations).

Safety: API key read inside the client, never printed/logged. NO fixtures are
written (everything in memory), so nothing can be committed. 20s per-call
timeout; a failed/timed-out call is recorded as unanswered and the run
continues. Engine untouched.

Run from repo root:
    $env:PYTHONPATH = "$PWD\platform;$PWD\src"
    python -m probe_eval._smoke_small
"""

from __future__ import annotations

import json
import sys

from geoready_platform.services.probe import hallucination, prompt_generator
from geoready_platform.services.probe.analysis import analyze_response
from geoready_platform.services.probe.taxonomy import CATEGORY_BY_KEY

from probe_eval import openrouter_client
from probe_eval.harness import business_by_id, score_business

MODEL = "openai/gpt-4o-mini"          # non-web (no citations) — connectivity-proven
# High-prominence brands + a DISTINCTIVE fictional business. With discovery-only
# SoM, the fictional one should score ~0 (the model won't independently name it).
BUSINESS_IDS = ["slack", "notion", "zephyrline-plumbing-austin"]
TIMEOUT_SECONDS = 20.0


def _say(msg: str) -> None:
    print(msg, flush=True)


def _two_prompts(biz: dict) -> list:
    """One share-intent prompt + one factual-intent prompt (exercises SoM + flags)."""
    allp = prompt_generator.generate_prompts(
        name=biz["name"], category=biz.get("category"), city=biz.get("city"), max_prompts=8
    )
    share = next((p for p in allp if CATEGORY_BY_KEY[p.category].counts_for_share), None)
    factual = next((p for p in allp if CATEGORY_BY_KEY[p.category].counts_for_factual), None)
    return [p for p in (share, factual) if p is not None]


def main() -> int:
    _say("starting small OpenRouter evaluation")
    if not openrouter_client.available():
        _say("ERROR: OPENROUTER_API_KEY is not set in this process environment.")
        return 2
    _say(f"selected model: {MODEL}")
    _say(f"businesses: {', '.join(BUSINESS_IDS)} | 2 prompts each | 1 run")

    report = {"model": MODEL, "businesses": {}}
    for bid in BUSINESS_IDS:
        biz = business_by_id(bid)
        if biz is None:
            _say(f"  skip: {bid} not found")
            continue
        _say(f"\n--- {biz['name']} ({biz['prominence_tier']}) ---")

        responses = []
        per_response = []
        for gp in _two_prompts(biz):
            _say(f"  request sent [{gp.category}] (timeout {int(TIMEOUT_SECONDS)}s)...")
            r = openrouter_client.run_prompt(gp.text, model=MODEL, timeout=TIMEOUT_SECONDS)
            if r.error:
                _say(f"    ERROR: {r.error}")
            else:
                _say(f"    response received ({len(r.text)} chars)")
            responses.append(
                {"category_key": gp.category, "prompt": gp.text, "text": r.text,
                 "citations": r.citations, "error": r.error}
            )
            cat = CATEGORY_BY_KEY[gp.category]
            sig = analyze_response(text=r.text, citations=r.citations, name=biz["name"],
                                   domain=biz["website"], category=biz.get("category"))
            flags = hallucination.detect_flags(
                text=r.text, category_key=gp.category, brand_mentioned=sig.brand_mentioned,
                name=biz["name"], counts_for_factual=cat.counts_for_factual,
            ) if (r.text or "").strip() else []
            per_response.append({
                "category": gp.category,
                "answered": bool((r.text or "").strip()) and not r.error,
                "brand_mentioned": sig.brand_mentioned,
                "length": len(r.text or ""),
                "flags": [f.type for f in flags],
            })

        fixture = {"business_id": bid, "taxonomy_version": prompt_generator.current_taxonomy_version(),
                   "responses": responses}
        scored = score_business(biz, fixture)
        report["businesses"][bid] = {
            "tier": biz["prominence_tier"],
            "share_of_model": scored["share_of_model"],
            "share_denominator": scored["share_denominator"],
            "recommendation_relevance": scored["recommendation_relevance"],
            "flags": scored["flags"],
            "responses": per_response,
        }

    _say("\n=== REPORT ===")
    print(json.dumps(report, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
