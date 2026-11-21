"""Nearest block ancestor of a text node, resolved once per tag.

Walking up from every text node to its block ancestor costs the depth of inline nesting per node: 20000 nested
``<span>`` elements with text took 30 seconds. Each tag's answer is cached, so a chain is climbed once and the cost is
proportional to the size of the markup.
"""

from __future__ import annotations

from bs4.element import Tag


class BlockResolver:
    """``resolve(node)`` returns ``(owner, linked)``: the nearest ancestor of a text node whose tag is in
    ``block_tags`` (or ``body``), and whether an ``<a>`` lies between the node and that owner."""

    def __init__(self, body: Tag, block_tags: frozenset[str]) -> None:
        self._body = body
        self._blocks = block_tags
        self._cache: dict[int, tuple[Tag | None, bool]] = {}

    def resolve(self, node) -> tuple[Tag | None, bool]:
        path: list[Tag] = []
        tag = node.parent
        owner: Tag | None
        linked_above = False
        while True:
            if tag is None:
                owner = None
                break
            if tag is self._body or tag.name in self._blocks:
                owner = tag
                break
            cached = self._cache.get(id(tag))
            if cached is not None:
                owner, linked_above = cached
                break
            path.append(tag)
            tag = tag.parent
        for t in reversed(path):  # from the tag nearest the owner down to the node's parent
            linked_above = linked_above or t.name == "a"
            self._cache[id(t)] = (owner, linked_above)
        return owner, linked_above
