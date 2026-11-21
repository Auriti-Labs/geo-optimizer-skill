"""Verify crawler visits in a server log against the address ranges the vendors publish.

A visit that claims to be GPTBot is checked by its source address: inside a range OpenAI publishes for GPTBot it is
``verified``; outside every published range it is counted ``outside_ranges``: a spoofed name, or an address the vendor has not
listed (measured on a real log: Azure addresses claiming GPTBot sit outside OpenAI's file, and nothing independent says which). A bot whose vendor publishes no machine-readable
ranges (``CRAWLER_RANGE_SOURCES`` lists the ones that do) is reported as unverifiable, never as clean. This is an
address check, not a signature check: RFC 9421 message signatures are not recorded by standard access logs.

Range files come from a local path (offline) or, only on request, from the vendors' URLs through ``fetch_url`` (anti-SSRF
included). ``core/`` does not print.
"""

from __future__ import annotations

import ipaddress
import json
from pathlib import Path

from geo_optimizer.models.config import CRAWLER_RANGE_SOURCES, CRAWLER_RANGES_MAX_BYTES
from geo_optimizer.models.results import BotVerification, IpVerification
from geo_optimizer.utils.http import fetch_url

Network = ipaddress.IPv4Network | ipaddress.IPv6Network
Ranges = dict[str, list[Network]]  # bot name -> networks


def parse_prefixes(data: object) -> tuple[list[Network], str]:
    """The networks and the ``creationTime`` of one vendor file. Raises ``ValueError`` when the shape is wrong."""
    if not isinstance(data, dict) or not isinstance(data.get("prefixes"), list):
        raise ValueError("not a vendor range file: no 'prefixes' list")
    networks: list[Network] = []
    for item in data["prefixes"]:
        value = item.get("ipv4Prefix") or item.get("ipv6Prefix") if isinstance(item, dict) else None
        if isinstance(value, str):
            networks.append(ipaddress.ip_network(value, strict=False))
    if not networks:
        raise ValueError("no usable prefix in the file")
    return networks, str(data.get("creationTime", ""))


def _add(ranges: Ranges, sources: list[dict], name: str, where: dict, data: object) -> None:
    try:
        networks, created = parse_prefixes(data)
    except (ValueError, TypeError) as exc:
        sources.append({**where, "bots": list(CRAWLER_RANGE_SOURCES[name][1]), "error": str(exc)})
        return
    bots = CRAWLER_RANGE_SOURCES[name][1]
    for bot in bots:
        ranges.setdefault(bot, []).extend(networks)
    sources.append({**where, "bots": list(bots), "creation_time": created, "prefixes": len(networks)})


def load_ranges(path: str | Path) -> tuple[Ranges, list[dict]]:
    """Read the vendor files found in ``path`` (a directory), named as in ``CRAWLER_RANGE_SOURCES``.

    Raises ``ValueError`` when no recognised file is there."""
    folder = Path(path)
    ranges: Ranges = {}
    sources: list[dict] = []
    for name in CRAWLER_RANGE_SOURCES:
        file = folder / name
        if not file.is_file():
            continue
        if file.stat().st_size > CRAWLER_RANGES_MAX_BYTES:
            sources.append({"file": str(file), "bots": list(CRAWLER_RANGE_SOURCES[name][1]), "error": "file too large"})
            continue
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            sources.append({"file": str(file), "bots": list(CRAWLER_RANGE_SOURCES[name][1]), "error": str(exc)})
            continue
        _add(ranges, sources, name, {"file": str(file)}, data)
    if not sources:
        raise ValueError(f"no range file found in {folder}: expected {', '.join(CRAWLER_RANGE_SOURCES)}")
    return ranges, sources


def fetch_ranges() -> tuple[Ranges, list[dict]]:
    """Download the vendor files from their published URLs. A file that cannot be fetched is reported in ``sources``."""
    ranges: Ranges = {}
    sources: list[dict] = []
    for name, (url, bots) in CRAWLER_RANGE_SOURCES.items():
        response, error = fetch_url(url, max_size=CRAWLER_RANGES_MAX_BYTES)
        if error or response is None or response.status_code != 200:
            sources.append(
                {"url": url, "bots": list(bots), "error": error or f"HTTP {getattr(response, 'status_code', 0)}"}
            )
            continue
        try:
            data = json.loads(response.text)
        except ValueError as exc:
            sources.append({"url": url, "bots": list(bots), "error": f"not JSON: {exc}"})
            continue
        _add(ranges, sources, name, {"url": url}, data)
    return ranges, sources


def _address(text: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        address = ipaddress.ip_address(text.strip())
    except ValueError:
        return None
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped
    return address


def verify_visits(bot_visits: dict[str, list[dict]], ranges: Ranges, sources: list[dict]) -> IpVerification:
    """Classify every visit of every bot as verified, outside the ranges or unverifiable."""
    result = IpVerification(sources=sources)
    for bot in sorted(bot_visits):
        visits = bot_visits[bot]
        entry = BotVerification(bot=bot, hits=len(visits), ranges_available=bot in ranges)
        for visit in visits:
            address = _address(visit.get("ip", ""))
            if address is None:
                entry.no_address += 1
            elif not entry.ranges_available:
                continue
            elif any(address in network for network in ranges[bot] if network.version == address.version):
                entry.verified += 1
            else:
                entry.outside_ranges += 1
        result.bots.append(entry)
        result.verified += entry.verified
        result.outside_ranges += entry.outside_ranges
        result.unverifiable += entry.hits - entry.verified - entry.outside_ranges
    return result
