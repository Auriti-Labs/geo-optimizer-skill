"""Regressione: retry llms.txt fuori dall'event loop e autore G-BYLINE via @id.

- run_full_audit_async eseguiva il retry browser-like di llms.txt (fetch_url
  sincrono) direttamente nell'event loop: negli audit batch bloccava tutti gli
  audit concorrenti e il timeout per URL.
- check_byline non risolveva l'autore dichiarato come riferimento @id (Yoast,
  RankMath), quindi segnalava "No author found" su pagine con autore.
"""

from __future__ import annotations

import asyncio
import json
import threading
from unittest.mock import AsyncMock, Mock, patch

import pytest
from bs4 import BeautifulSoup

from geo_optimizer.core.audit_google_ai import check_byline
from geo_optimizer.models.results import CdnAiCrawlerResult
from geo_optimizer.utils.jsonld import iter_jsonld_objects

pytest.importorskip("httpx", reason="il percorso async richiede httpx")

_URL = "https://example.com"
_HTML = '<html lang="en"><head><title>Acme</title></head><body><h1>Acme</h1></body></html>'


def test_async_audit_runs_llms_cdn_retry_off_the_event_loop():
    from geo_optimizer.core.audit import run_full_audit_async

    home = Mock(status_code=200, text=_HTML, content=_HTML.encode(), headers={}, url=_URL)
    blocked_llms = Mock(status_code=403, text="", content=b"", headers={})
    responses = {_URL: (home, None), f"{_URL}/llms.txt": (blocked_llms, None)}
    retry_threads: list[bool] = []

    def _retry_fetch(url, *args, **kwargs):
        # True se il retry gira nel thread dell'event loop (asyncio.run usa il main thread)
        retry_threads.append(threading.current_thread() is threading.main_thread())
        return None, "still blocked"

    with (
        patch("geo_optimizer.utils.http_async.fetch_urls_async", new=AsyncMock(return_value=responses)),
        patch("geo_optimizer.core.audit.check_markdown_negotiation_async", new=AsyncMock(return_value=False)),
        patch("geo_optimizer.core.audit.audit_cdn_ai_crawler", return_value=CdnAiCrawlerResult()),
        patch("geo_optimizer.core.audit_llms.fetch_url", side_effect=_retry_fetch),
    ):
        result = asyncio.run(run_full_audit_async(_URL))

    assert result.llms.blocked_by_cdn is True
    assert retry_threads, "the browser-like retry should have run"
    assert not any(retry_threads), "the llms.txt CDN retry ran on the event loop thread"


def _schemas(jsonld: dict) -> list[dict]:
    soup = BeautifulSoup(f'<script type="application/ld+json">{json.dumps(jsonld)}</script>', "html.parser")
    return list(iter_jsonld_objects(soup))


def test_byline_resolves_author_declared_by_id_reference():
    """Forma Yoast: l'Article punta all'autore con @id, il nodo Person sta nel @graph."""
    person_id = "https://example.com/#/schema/person/abc123"
    jsonld = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Article", "@id": "https://example.com/post/#article", "author": {"@id": person_id}},
            {"@type": "Person", "@id": person_id, "name": "Jo Rossi"},
        ],
    }

    check = check_byline(BeautifulSoup(_HTML, "html.parser"), _schemas(jsonld))

    assert check.status == "pass"


def test_byline_unresolvable_id_reference_still_warns():
    jsonld = {"@context": "https://schema.org", "@type": "Article", "author": {"@id": "https://example.com/#nobody"}}

    check = check_byline(BeautifulSoup(_HTML, "html.parser"), _schemas(jsonld))

    assert check.status == "warn"


def test_byline_inline_author_name_unchanged():
    jsonld = {"@context": "https://schema.org", "@type": "Article", "author": {"@type": "Person", "name": "Jo"}}

    check = check_byline(BeautifulSoup(_HTML, "html.parser"), _schemas(jsonld))

    assert check.status == "pass"


@pytest.mark.parametrize("target_type", ["WebSite", "ImageObject", "Article"])
def test_byline_id_reference_to_non_author_node_warns(target_type):
    """Un @id verso WebSite, ImageObject o l'articolo stesso non dichiara un autore."""
    node_id = "https://example.com/#node"
    jsonld = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Article", "@id": "https://example.com/post/#article", "author": {"@id": node_id}},
            {"@type": target_type, "@id": node_id, "name": "Something"},
        ],
    }

    check = check_byline(BeautifulSoup(_HTML, "html.parser"), _schemas(jsonld))

    assert check.status == "warn"


def test_byline_id_reference_to_organization_passes():
    org_id = "https://example.com/#organization"
    jsonld = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Article", "author": [{"@id": org_id}]},
            {"@type": "NewsMediaOrganization", "@id": org_id, "name": "Acme News"},
        ],
    }

    check = check_byline(BeautifulSoup(_HTML, "html.parser"), _schemas(jsonld))

    assert check.status == "pass"
