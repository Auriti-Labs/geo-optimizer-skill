"""BlockResolver: the cached nearest-block lookup equals the naive walk up the tree, and costs linear time."""

from __future__ import annotations

import random
import time

from bs4 import BeautifulSoup, Comment

from geo_optimizer.utils.html_blocks import BlockResolver

BLOCKS = frozenset({"p", "li", "div", "td"})
TAGS = ["div", "span", "a", "p", "b", "li", "em", "td"]


def _naive(node, body):
    owner, linked = node.parent, False
    while owner is not None and owner is not body and owner.name not in BLOCKS:
        linked = linked or owner.name == "a"
        owner = owner.parent
    return owner, linked


def _random_html(rng: random.Random, depth: int = 0) -> str:
    parts = []
    for _ in range(rng.randint(1, 3)):
        if depth < 6 and rng.random() < 0.7:
            tag = rng.choice(TAGS)
            parts.append(f"<{tag}>{_random_html(rng, depth + 1)}</{tag}>")
        else:
            parts.append(f"text{rng.randint(0, 99)} ")
    return "".join(parts)


def test_resolver_agrees_with_the_naive_walk_on_random_trees():
    rng = random.Random(7)
    checked = 0
    for _ in range(300):
        soup = BeautifulSoup(f"<body>{_random_html(rng)}</body>", "html.parser")
        body = soup.body
        resolver = BlockResolver(body, BLOCKS)
        for node in body.find_all(string=True):
            if isinstance(node, Comment):
                continue
            assert resolver.resolve(node) == _naive(node, body)
            checked += 1
    assert checked > 1000


def test_a_link_between_the_node_and_its_block_is_reported_once_per_chain():
    soup = BeautifulSoup("<body><p><a><span>x</span></a> <span>y</span></p></body>", "html.parser")
    resolver = BlockResolver(soup.body, BLOCKS)
    x, y = [n for n in soup.find_all(string=True) if n.strip()]
    assert resolver.resolve(x)[1] is True and resolver.resolve(y)[1] is False


def test_deeply_nested_inline_markup_is_linear():
    n = 20000
    soup = BeautifulSoup("<body><p>" + "<span>word " * n + "</span>" * n + "</p></body>", "html.parser")
    resolver = BlockResolver(soup.body, BLOCKS)
    started = time.perf_counter()
    for node in soup.body.find_all(string=True):
        resolver.resolve(node)
    assert time.perf_counter() - started < 3.0  # was 30 s with the naive walk
