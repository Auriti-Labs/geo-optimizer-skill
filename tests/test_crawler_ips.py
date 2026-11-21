"""geo logs --ip-ranges: crawler visits checked against the address ranges vendors publish (offline; fetch stubbed)."""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from geo_optimizer.cli.main import cli
from geo_optimizer.core.crawler_ips import fetch_ranges, load_ranges, parse_prefixes, verify_visits
from geo_optimizer.core.log_analyzer import _parse_line, analyze_log_file
from geo_optimizer.models.config import CRAWLER_RANGE_SOURCES

GPTBOT = {
    "creationTime": "2026-09-22T02:00:07.000000",
    "prefixes": [{"ipv4Prefix": "132.196.86.0/24"}, {"ipv6Prefix": "2001:db8::/32"}],
}
GOOGLE = {"creationTime": "2026-11-20T15:45:50.000000", "prefixes": [{"ipv4Prefix": "66.249.64.0/27"}]}


def _line(ip: str, ua: str, path: str = "/") -> str:
    return f'{ip} - - [10/Nov/2026:10:00:00 +0000] "GET {path} HTTP/1.1" 200 512 "-" "{ua}"\n'


@pytest.fixture
def ranges_dir(tmp_path):
    (tmp_path / "gptbot.json").write_text(json.dumps(GPTBOT))
    (tmp_path / "googlebot.json").write_text(json.dumps(GOOGLE))
    return tmp_path


class TestParsing:
    def test_the_combined_format_keeps_the_client_address(self):
        assert _parse_line(_line("132.196.86.5", "GPTBot/1.1"))["ip"] == "132.196.86.5"
        assert _parse_line(_line("2001:db8::1", "GPTBot/1.1"))["ip"] == "2001:db8::1"

    def test_json_lines_keep_the_address_under_the_usual_keys(self):
        for key in ("remote_addr", "client_ip", "clientIp", "c-ip"):
            line = json.dumps({key: "1.2.3.4", "user_agent": "GPTBot", "path": "/", "status": 200})
            assert _parse_line(line)["ip"] == "1.2.3.4", key

    def test_prefix_files_must_have_the_vendor_shape(self):
        nets, created = parse_prefixes(GPTBOT)
        assert len(nets) == 2 and created.startswith("2026-09-22")
        for bad in ({}, {"prefixes": "x"}, {"prefixes": []}, {"prefixes": [{"nope": 1}]}, [1]):
            with pytest.raises(ValueError):
                parse_prefixes(bad)


class TestVerification:
    def _visits(self, *pairs):
        return {bot: [{"ip": ip} for ip in ips] for bot, ips in pairs}

    def test_inside_outside_and_no_address(self, ranges_dir):
        ranges, sources = load_ranges(ranges_dir)
        v = verify_visits(
            self._visits(("GPTBot", ["132.196.86.5", "8.8.8.8", "not-an-ip", "2001:db8::7"])), ranges, sources
        )
        bot = v.bots[0]
        assert (bot.hits, bot.verified, bot.outside_ranges, bot.no_address) == (4, 2, 1, 1)
        assert (v.verified, v.outside_ranges, v.unverifiable) == (2, 1, 1)

    def test_an_ipv4_mapped_ipv6_address_is_read_as_ipv4(self, ranges_dir):
        ranges, sources = load_ranges(ranges_dir)
        v = verify_visits(self._visits(("GPTBot", ["::ffff:132.196.86.9"])), ranges, sources)
        assert v.bots[0].verified == 1

    def test_a_bot_without_published_ranges_is_unverifiable_never_clean(self, ranges_dir):
        ranges, sources = load_ranges(ranges_dir)
        v = verify_visits(self._visits(("ClaudeBot", ["1.2.3.4", "5.6.7.8"])), ranges, sources)
        bot = v.bots[0]
        assert bot.ranges_available is False and bot.verified == 0 and bot.outside_ranges == 0
        assert v.unverifiable == 2

    def test_an_address_does_not_match_a_range_of_the_other_family(self, ranges_dir):
        ranges, sources = load_ranges(ranges_dir)
        v = verify_visits(self._visits(("GPTBot", ["2001:4860::1"])), ranges, sources)
        assert v.bots[0].outside_ranges == 1


class TestLoading:
    def test_a_folder_without_a_recognised_file_is_an_error(self, tmp_path):
        (tmp_path / "other.json").write_text("{}")
        with pytest.raises(ValueError, match="no range file found"):
            load_ranges(tmp_path)

    def test_a_broken_file_is_reported_and_the_rest_still_load(self, ranges_dir):
        (ranges_dir / "bingbot.json").write_text("{not json")
        ranges, sources = load_ranges(ranges_dir)
        assert "GPTBot" in ranges and "Bingbot" not in ranges
        assert any("error" in s and "bingbot" in s["file"] for s in sources)

    def test_fetch_reports_a_file_that_cannot_be_fetched(self):
        def fake(url, **kw):
            if "openai.com/gptbot" in url:
                return Mock(status_code=200, text=json.dumps(GPTBOT)), None
            return None, "Timeout (10s)"

        with patch("geo_optimizer.core.crawler_ips.fetch_url", side_effect=fake):
            ranges, sources = fetch_ranges()
        assert list(ranges) == ["GPTBot"] and len(sources) == len(CRAWLER_RANGE_SOURCES)
        assert sum("error" in s for s in sources) == len(CRAWLER_RANGE_SOURCES) - 1


class TestAnalyzeAndCli:
    def _log(self, tmp_path):
        f = tmp_path / "access.log"
        f.write_text(
            _line("132.196.86.5", "Mozilla/5.0 (compatible; GPTBot/1.1)")
            + _line("8.8.8.8", "Mozilla/5.0 (compatible; GPTBot/1.1)")
            + _line("66.249.64.3", "Mozilla/5.0 (compatible; Googlebot/2.1)")
            + _line("1.2.3.4", "Mozilla/5.0 ClaudeBot/1.0")
            + _line("9.9.9.9", "Mozilla/5.0 (X11) Firefox/120")
        )
        return f

    def test_without_ranges_nothing_changes(self, tmp_path):
        assert analyze_log_file(self._log(tmp_path)).verification is None

    def test_with_ranges_each_bot_is_classified(self, tmp_path, ranges_dir):
        ranges, sources = load_ranges(ranges_dir)
        v = analyze_log_file(self._log(tmp_path), ranges=ranges, range_sources=sources).verification
        by = {b.bot: b for b in v.bots}
        assert (by["GPTBot"].verified, by["GPTBot"].outside_ranges) == (1, 1)
        assert by["Googlebot"].verified == 1 and by["ClaudeBot"].ranges_available is False

    def test_cli_json_has_the_verification_only_when_asked(self, tmp_path, ranges_dir):
        log = str(self._log(tmp_path))
        plain = json.loads(CliRunner().invoke(cli, ["logs", "--file", log, "--format", "json"]).output)
        assert "verification" not in plain
        asked = json.loads(
            CliRunner().invoke(cli, ["logs", "--file", log, "--format", "json", "--ip-ranges", str(ranges_dir)]).output
        )
        assert asked["verification"]["verified"] == 2 and asked["verification"]["outside_ranges"] == 1

    def test_cli_text_prints_the_table_and_the_limit(self, tmp_path, ranges_dir):
        out = CliRunner().invoke(cli, ["logs", "--file", str(self._log(tmp_path)), "--ip-ranges", str(ranges_dir)])
        assert out.exit_code == 0 and "Source address check" in out.output
        assert "no published ranges" in out.output and "RFC 9421" in out.output

    def test_cli_options_are_exclusive_and_the_folder_is_checked(self, tmp_path, ranges_dir):
        log = str(self._log(tmp_path))
        both = CliRunner().invoke(cli, ["logs", "--file", log, "--ip-ranges", str(ranges_dir), "--fetch-ip-ranges"])
        assert both.exit_code != 0 and "not both" in both.output
        empty = tmp_path / "empty"
        empty.mkdir()
        bad = CliRunner().invoke(cli, ["logs", "--file", log, "--ip-ranges", str(empty)])
        assert bad.exit_code != 0 and "no range file found" in bad.output

    def test_cli_fetch_uses_the_vendor_urls(self, tmp_path):
        with patch(
            "geo_optimizer.core.crawler_ips.fetch_url",
            return_value=(Mock(status_code=200, text=json.dumps(GPTBOT)), None),
        ) as f:
            out = CliRunner().invoke(
                cli, ["logs", "--file", str(self._log(tmp_path)), "--fetch-ip-ranges", "--format", "json"]
            )
        assert out.exit_code == 0 and f.call_count == len(CRAWLER_RANGE_SOURCES)
        assert json.loads(out.output)["verification"]["sources"][0]["url"].startswith("https://")

    def test_cli_fetch_fails_clearly_when_nothing_could_be_fetched(self, tmp_path):
        with patch("geo_optimizer.core.crawler_ips.fetch_url", return_value=(None, "Connection failed")):
            out = CliRunner().invoke(cli, ["logs", "--file", str(self._log(tmp_path)), "--fetch-ip-ranges"])
        assert out.exit_code != 0 and "No vendor range file could be fetched" in out.output
