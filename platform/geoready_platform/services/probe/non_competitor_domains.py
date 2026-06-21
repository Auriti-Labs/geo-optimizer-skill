"""Denylist of domains that are NOT competitors when cited by an AI answer.

WHY THIS EXISTS
---------------
v1 competitor detection treated *every* cited domain except the business's own
as a "competitor". But AI answers cite reference, review, social, directory,
marketplace, and documentation sites constantly — Wikipedia, Reddit, Yelp,
Facebook, Amazon, .gov/.edu pages. Reporting "wikipedia.org is your competitor"
destroys credibility in the single most demo-critical output. This module
filters those out so `competitor_domains` contains plausible *businesses*.

HOW IT CAN FAIL
---------------
- It is a denylist, not semantic understanding. A genuine competitor whose
  domain we haven't listed still passes through (acceptable: false positives on
  *non*-competitors are the credibility killer; a missed filter just leaves a
  real domain, which is usually fine).
- A listed platform could occasionally BE the relevant competitor (e.g. a
  business that competes with Yelp). Edge case; ignored in v1.
- Country-specific directories/socials are under-covered.

HOW IT SHOULD EVOLVE
--------------------
- Replace/augment with a category-aware allowlist of known competitors per
  vertical, and ultimately learn competitors from repeated co-occurrence across
  many probes (the dataset moat). Until then, an explicit per-entity
  competitor list (already supported in analysis) is the precise path.
"""

from __future__ import annotations

# Exact registrable domains (matched against the domain and its subdomains).
_NON_COMPETITOR_DOMAINS: frozenset[str] = frozenset(
    {
        # Reference / knowledge
        "wikipedia.org", "wikidata.org", "wikimedia.org", "britannica.com",
        "quora.com", "reddit.com", "medium.com", "substack.com",
        "stackoverflow.com", "stackexchange.com",
        # Social
        "facebook.com", "instagram.com", "twitter.com", "x.com", "linkedin.com",
        "tiktok.com", "youtube.com", "pinterest.com", "threads.net",
        "snapchat.com", "whatsapp.com", "telegram.org",
        # Reviews / directories / lead-gen (general)
        "yelp.com", "tripadvisor.com", "trustpilot.com", "g2.com", "capterra.com",
        "getapp.com", "softwareadvice.com", "bbb.org", "glassdoor.com",
        "indeed.com", "yellowpages.com", "angi.com", "angieslist.com",
        "thumbtack.com", "houzz.com", "foursquare.com", "manta.com",
        "crunchbase.com", "clutch.co", "producthunt.com", "nextdoor.com",
        "expertise.com", "threebestrated.com", "yellow.place", "cylex.com",
        # Vertical directories / aggregators (health, legal, travel, real estate, auto)
        "healthgrades.com", "zocdoc.com", "vitals.com", "webmd.com", "ratemds.com",
        "avvo.com", "findlaw.com", "justia.com", "lawyers.com", "martindale.com",
        "opentable.com", "booking.com", "expedia.com", "hotels.com", "kayak.com",
        "realtor.com", "zillow.com", "redfin.com", "trulia.com", "rightmove.co.uk",
        "cars.com", "carfax.com", "autotrader.com", "kbb.com",
        # Maps / big-tech surfaces
        "google.com", "bing.com", "duckduckgo.com", "apple.com",
        "maps.google.com", "goo.gl",
        # Marketplaces
        "amazon.com", "ebay.com", "etsy.com", "walmart.com", "alibaba.com",
        # Generic news / business press (citation sources, not competitors)
        "nytimes.com", "forbes.com", "businessinsider.com", "techcrunch.com",
        "theverge.com", "wired.com", "bloomberg.com", "cnn.com", "bbc.com",
        # Dev / docs / packages
        "github.com", "gitlab.com", "readthedocs.io", "npmjs.com", "pypi.org",
        "stackshare.io",
        # App stores
        "play.google.com", "apps.apple.com",
    }
)

# TLD suffixes that are never competitors (institutional).
_NON_COMPETITOR_TLDS: tuple[str, ...] = (".gov", ".edu", ".mil")


def is_non_competitor(domain: str) -> bool:
    """True if ``domain`` is a reference/social/directory/etc. (not a competitor)."""
    if not domain:
        return True
    d = domain.lower().strip().strip(".")
    if any(d == tld[1:] or d.endswith(tld) for tld in _NON_COMPETITOR_TLDS):
        return True
    for entry in _NON_COMPETITOR_DOMAINS:
        if d == entry or d.endswith("." + entry):
            return True
    return False


def filter_competitor_domains(domains: list[str]) -> list[str]:
    """Drop non-competitor domains, preserving order and uniqueness."""
    seen: set[str] = set()
    out: list[str] = []
    for d in domains:
        if d and d not in seen and not is_non_competitor(d):
            seen.add(d)
            out.append(d)
    return out
