"""
Server log analyzer for AI crawler activity (#227).

Parses Apache/Nginx combined log format and JSON logs to detect
AI bot visits, aggregate statistics, and identify top crawled pages.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from geo_optimizer.models.config import AI_BOTS
from geo_optimizer.models.results import BotStats, CrawledPage, LogAnalysisResult

# Apache/Nginx combined log format:
# 1.2.3.4 - - [16/Apr/2026:10:00:00 +0200] "GET /path HTTP/1.1" 200 1234 "-" "UserAgent"
_COMBINED_RE = re.compile(
    r'^[\d.:a-fA-F]+\s+\S+\s+\S+\s+\[([^\]]+)\]\s+"(\S+)\s+(\S+)\s+[^"]*"\s+(\d+)\s+\S+\s+"[^"]*"\s+"([^"]*)"'
)

_TOP_PAGES_LIMIT = 10
_DEFAULT_MAX_LINES = 1_000_000

# Build lowercase UA fragments for matching
_BOT_UA_FRAGMENTS: dict[str, str] = {}
for bot_name in AI_BOTS:
    _BOT_UA_FRAGMENTS[bot_name.lower()] = bot_name


def analyze_log_file(file_path: str | Path, *, max_lines: int = _DEFAULT_MAX_LINES) -> LogAnalysisResult:
    """Analyze a server log file for AI crawler activity.

    Supports Apache/Nginx combined format and JSON lines format.

    Args:
        file_path: Path to the log file.

    Returns:
        LogAnalysisResult with bot stats and top crawled pages.
    """
    path = Path(file_path)
    if not path.is_file():
        return LogAnalysisResult(checked=True, log_file=str(path))

    bot_visits: dict[str, list[dict]] = defaultdict(list)
    total_lines = 0
    dates: list[str] = []

    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            total_lines += 1
            if total_lines > max_lines:
                break
            entry = _parse_line(line)
            if not entry:
                continue
            bot = _match_bot(entry["ua"])
            if bot:
                bot_visits[bot].append(entry)
                if entry["date"]:
                    dates.append(entry["date"])

    ai_requests = sum(len(v) for v in bot_visits.values())

    bots = _aggregate_bots(bot_visits)
    top_pages = _aggregate_pages(bot_visits)

    dates.sort()
    return LogAnalysisResult(
        checked=True,
        log_file=str(path),
        total_lines=total_lines,
        ai_requests=ai_requests,
        date_range_start=dates[0] if dates else "",
        date_range_end=dates[-1] if dates else "",
        bots=bots,
        top_pages=top_pages,
    )


def _parse_line(line: str) -> dict | None:
    """Parse a single log line (combined or JSON format)."""
    line = line.strip()
    if not line:
        return None

    # Try JSON first
    if line.startswith("{"):
        return _parse_json_line(line)

    # Try combined format
    m = _COMBINED_RE.match(line)
    if m:
        return {
            "date": m.group(1),
            "method": m.group(2),
            "path": m.group(3),
            "status": m.group(4),
            "ua": m.group(5),
        }
    return None


def _parse_json_line(line: str) -> dict | None:
    """Parse a JSON log line (CloudFront, Vercel, etc.)."""
    try:
        obj = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None
    ua = obj.get("user_agent") or obj.get("userAgent") or obj.get("http_user_agent") or ""
    path = obj.get("path") or obj.get("uri") or obj.get("url") or ""
    date = obj.get("timestamp") or obj.get("time") or obj.get("date") or ""
    return {
        "date": str(date),
        "method": obj.get("method", ""),
        "path": str(path),
        "status": str(obj.get("status", "")),
        "ua": str(ua),
    }


def _match_bot(ua: str) -> str | None:
    """Match a user-agent string against known AI bots."""
    ua_lower = ua.lower()
    for fragment, name in _BOT_UA_FRAGMENTS.items():
        if fragment in ua_lower:
            return name
    return None


def _aggregate_bots(bot_visits: dict[str, list[dict]]) -> list[BotStats]:
    """Aggregate per-bot statistics."""
    stats: list[BotStats] = []
    for bot_name, visits in sorted(bot_visits.items(), key=lambda x: len(x[1]), reverse=True):
        pages = {v["path"] for v in visits}
        dates = sorted(v["date"] for v in visits if v["date"])
        stats.append(
            BotStats(
                bot_name=bot_name,
                visits=len(visits),
                unique_pages=len(pages),
                first_seen=dates[0] if dates else "",
                last_seen=dates[-1] if dates else "",
            )
        )
    return stats


def _aggregate_pages(bot_visits: dict[str, list[dict]]) -> list[CrawledPage]:
    """Aggregate top crawled pages across all bots."""
    page_counter: Counter = Counter()
    page_bots: dict[str, set[str]] = defaultdict(set)

    for bot_name, visits in bot_visits.items():
        for v in visits:
            page_counter[v["path"]] += 1
            page_bots[v["path"]].add(bot_name)

    return [
        CrawledPage(path=path, total_visits=count, bots=sorted(page_bots[path]))
        for path, count in page_counter.most_common(_TOP_PAGES_LIMIT)
    ]
