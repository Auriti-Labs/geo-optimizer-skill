"""Tests for Server Log Analyzer (#227)."""

from __future__ import annotations

from geo_optimizer.core.log_analyzer import _match_bot, _parse_line, analyze_log_file

_COMBINED_LINES = [
    '1.2.3.4 - - [16/Apr/2026:10:00:00 +0200] "GET /blog/guide HTTP/1.1" 200 5432 "-" "Mozilla/5.0 (compatible; GPTBot/1.0)"',
    '5.6.7.8 - - [16/Apr/2026:10:01:00 +0200] "GET /docs/api HTTP/1.1" 200 3210 "-" "ClaudeBot/1.0"',
    '5.6.7.8 - - [16/Apr/2026:10:02:00 +0200] "GET /blog/guide HTTP/1.1" 200 5432 "-" "ClaudeBot/1.0"',
    '9.0.1.2 - - [16/Apr/2026:10:03:00 +0200] "GET / HTTP/1.1" 200 8000 "-" "Mozilla/5.0 (Windows NT 10.0)"',
    '3.4.5.6 - - [17/Apr/2026:10:00:00 +0200] "GET /pricing HTTP/1.1" 200 2000 "-" "PerplexityBot/1.0"',
]

_JSON_LINES = [
    '{"timestamp":"2026-04-16T10:00:00Z","method":"GET","path":"/blog","status":200,"user_agent":"GPTBot/1.0"}',
    '{"timestamp":"2026-04-16T10:01:00Z","method":"GET","path":"/about","status":200,"user_agent":"ClaudeBot/1.0"}',
]


class TestParseLine:
    def test_combined_format(self):
        entry = _parse_line(_COMBINED_LINES[0])
        assert entry is not None
        assert entry["path"] == "/blog/guide"
        assert "GPTBot" in entry["ua"]

    def test_json_format(self):
        entry = _parse_line(_JSON_LINES[0])
        assert entry is not None
        assert entry["path"] == "/blog"
        assert "GPTBot" in entry["ua"]

    def test_empty_line(self):
        assert _parse_line("") is None
        assert _parse_line("   ") is None

    def test_invalid_line(self):
        assert _parse_line("this is not a log line") is None


class TestMatchBot:
    def test_matches_gptbot(self):
        assert _match_bot("Mozilla/5.0 (compatible; GPTBot/1.0)") == "GPTBot"

    def test_matches_claudebot(self):
        assert _match_bot("ClaudeBot/1.0") == "ClaudeBot"

    def test_no_match_regular_browser(self):
        assert _match_bot("Mozilla/5.0 (Windows NT 10.0)") is None

    def test_case_insensitive(self):
        assert _match_bot("gptbot/1.0") == "GPTBot"


class TestAnalyzeLogFile:
    def test_combined_log(self, tmp_path):
        log = tmp_path / "access.log"
        log.write_text("\n".join(_COMBINED_LINES))
        result = analyze_log_file(log)
        assert result.checked is True
        assert result.total_lines == 5
        assert result.ai_requests == 4  # 3 AI bots + 1 regular
        bot_names = [b.bot_name for b in result.bots]
        assert "GPTBot" in bot_names
        assert "ClaudeBot" in bot_names

    def test_json_log(self, tmp_path):
        log = tmp_path / "access.json"
        log.write_text("\n".join(_JSON_LINES))
        result = analyze_log_file(log)
        assert result.ai_requests == 2
        assert len(result.bots) == 2

    def test_top_pages(self, tmp_path):
        log = tmp_path / "access.log"
        log.write_text("\n".join(_COMBINED_LINES))
        result = analyze_log_file(log)
        assert len(result.top_pages) > 0
        assert result.top_pages[0].total_visits >= 1

    def test_missing_file(self, tmp_path):
        result = analyze_log_file(tmp_path / "nonexistent.log")
        assert result.checked is True
        assert result.total_lines == 0

    def test_empty_file(self, tmp_path):
        log = tmp_path / "empty.log"
        log.write_text("")
        result = analyze_log_file(log)
        assert result.ai_requests == 0
        assert result.bots == []

    def test_date_range(self, tmp_path):
        log = tmp_path / "access.log"
        log.write_text("\n".join(_COMBINED_LINES))
        result = analyze_log_file(log)
        assert result.date_range_start != ""
        assert result.date_range_end != ""

    def test_bot_unique_pages(self, tmp_path):
        log = tmp_path / "access.log"
        log.write_text("\n".join(_COMBINED_LINES))
        result = analyze_log_file(log)
        claude = next(b for b in result.bots if b.bot_name == "ClaudeBot")
        assert claude.visits == 2
        assert claude.unique_pages == 2
