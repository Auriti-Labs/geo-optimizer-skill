"""Shared JSON-LD walker: script extraction, `@graph` unpacking, DoS guard.

Consolidates three previously-independent implementations of the same logic
(citability.py's twelve walkers, audit_schema.py, schema_injector.py), each
covering a different subset of edge cases. That duplication is the exact
root cause behind several past bugs in this project: fix #326 taught three
of citability.py's twelve call sites to unpack `@graph`, the 4.16.3
"twelve-walker" fix caught the other nine, and 4.16.4 found schema_injector.py
as a fourth, separately-written gap. Each fix closed one file at a time
because the parsing lived in that many places. One shared walker, used by
every call site, closes the class of bug rather than the latest instance.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from geo_optimizer.models.config import SCHEMA_JSONLD_MAX_BYTES

if TYPE_CHECKING:
    from bs4 import BeautifulSoup

_logger = logging.getLogger(__name__)


def iter_jsonld_objects(
    soup: BeautifulSoup,
    *,
    max_bytes: int = SCHEMA_JSONLD_MAX_BYTES,
    on_parse_error: Callable[[Exception], None] | None = None,
):
    """Yield every JSON-LD object on the page, with `@graph` containers unpacked.

    Behaviour, combined from the safest parts of the three implementations
    this replaces:
    - `@graph` is unpacked at any nesting depth, not just one level.
    - `@context`/`@id` from a `@graph` root are propagated to child items
      that don't declare their own, so a child stays a valid, self-describing
      JSON-LD node once yielded on its own instead of losing its context.
    - A size guard skips oversized `<script>` bodies (DoS, fix #182).
    - Malformed JSON is skipped without discarding the rest of the page's
      valid schemas — one bad script tag doesn't cost every other one.

    Args:
        soup: BeautifulSoup of the HTML page.
        max_bytes: Skip script bodies larger than this (bytes).
        on_parse_error: Optional callback invoked once per script that fails
            to parse, for callers that surface a count (e.g. fix #399's
            "N JSON-LD scripts have parse errors" recommendation).

    Yields:
        dict: One JSON-LD object at a time, in document order.
    """
    for script in soup.find_all("script", type="application/ld+json"):
        # script.string is None when the tag has multiple child nodes.
        raw = script.string
        if not raw:
            raw = script.get_text()
        if not raw or not raw.strip():
            continue
        if len(raw) > max_bytes:
            _logger.debug("JSON-LD script too large (%d bytes), skipping", len(raw))
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            if on_parse_error is not None:
                on_parse_error(exc)
            continue

        queue = list(data) if isinstance(data, list) else [data]
        while queue:
            item = queue.pop(0)
            if not isinstance(item, dict):
                continue
            graph = item.get("@graph")
            if graph is not None:
                root_context = item.get("@context")
                root_id = item.get("@id")
                raw_items = graph if isinstance(graph, list) else [graph]
                children = []
                for child in raw_items:
                    if isinstance(child, dict) and root_context and "@context" not in child:
                        child = {**child, "@context": root_context}
                        if root_id and "@id" not in child:
                            child["@id"] = root_id
                    children.append(child)
                # Prepend so the graph's own members keep document order ahead
                # of whatever follows this container.
                queue = children + queue
                continue
            yield item


# ─── Lettura difensiva dei campi schema.org ──────────────────────────────────
# Il JSON-LD arriva da pagine di terzi: lo stesso campo puo' essere stringa,
# lista o oggetto (schema.org lo consente) oppure semplicemente sbagliato
# (numero, null, booleano). Un campo malformato in un solo schema faceva
# sollevare AttributeError/TypeError e fallire l'intero audit (errore 500 sul web).


def schema_types(value: object) -> list[str]:
    """Normalizza un valore ``@type`` in una lista di stringhe.

    Args:
        value: Il valore di ``@type`` (stringa, lista o altro).

    Returns:
        Le sole stringhe non vuote, nell'ordine originale. ``[]`` per valori
        di altro tipo (numero, null, oggetto).
    """
    items = value if isinstance(value, list) else [value]
    return [item for item in items if isinstance(item, str) and item]


def first_object(value: object) -> dict:
    """Restituisce il primo oggetto di un campo che puo' essere oggetto o lista.

    Usato per campi come ``offers`` o ``aggregateRating``: schema.org accetta
    un singolo oggetto o una lista di oggetti.

    Args:
        value: Il valore del campo.

    Returns:
        Il dict stesso, il primo dict della lista, oppure ``{}``.
    """
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return next((item for item in value if isinstance(item, dict)), {})
    return {}


def string_list(value: object) -> list[str]:
    """Normalizza un campo stringa-o-lista (es. ``sameAs``) in una lista di stringhe.

    Args:
        value: Il valore del campo.

    Returns:
        Le sole stringhe non vuote; ``[]`` per valori di altro tipo.
    """
    items = value if isinstance(value, list) else [value]
    return [item for item in items if isinstance(item, str) and item.strip()]
