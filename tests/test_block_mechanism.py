"""block_pattern (CDN check) and per-bot mechanism (robots.txt vs HTTP)."""

from geo_optimizer.core.audit_cdn import classify_block_pattern, merge_block_mechanisms
from geo_optimizer.models.results import CdnAiCrawlerResult, RobotsResult

AI = ("GPTBot", "OAI-SearchBot", "PerplexityBot", "Claude-SearchBot")


def _entry(bot: str, blocked: bool = False, challenge: bool = False) -> dict:
    return {
        "bot": bot,
        "status": 403 if blocked else 200,
        "content_length": 1,
        "blocked": blocked,
        "challenge_detected": challenge,
    }


class TestBlockPattern:
    def test_none_when_all_pass(self) -> None:
        assert classify_block_pattern([_entry(b) for b in AI]) == "none"

    def test_targeted_when_some_blocked(self) -> None:
        assert classify_block_pattern([_entry("GPTBot", blocked=True)] + [_entry(b) for b in AI[1:]]) == "targeted"

    def test_blanket_when_all_four_blocked(self) -> None:
        assert classify_block_pattern([_entry(b, blocked=True) for b in AI]) == "blanket"

    def test_challenge_page_counts_as_blocked(self) -> None:
        assert classify_block_pattern([_entry(b, challenge=True) for b in AI]) == "blanket"

    def test_googlebot_does_not_decide_the_pattern(self) -> None:
        results = [_entry(b) for b in AI] + [_entry("Googlebot", blocked=True)]
        assert classify_block_pattern(results) == "none"

    def test_missing_ai_results_are_never_blanket(self) -> None:
        assert classify_block_pattern([_entry("GPTBot", blocked=True)]) == "targeted"
        assert classify_block_pattern([]) == "none"


class TestMechanism:
    def _cdn(self, blocked: list[str], checked: bool = True) -> CdnAiCrawlerResult:
        return CdnAiCrawlerResult(checked=checked, bot_results=[_entry(b, blocked=b in blocked) for b in AI])

    def test_each_mechanism(self) -> None:
        robots = RobotsResult(found=True, bots_blocked=["GPTBot", "ClaudeBot"])
        blocks = merge_block_mechanisms(robots, self._cdn(["GPTBot", "PerplexityBot"]))
        assert {b["bot"]: b["mechanism"] for b in blocks} == {
            "GPTBot": "both",
            "ClaudeBot": "robots_txt",
            "PerplexityBot": "http",
        }

    def test_allowed_bots_are_not_listed(self) -> None:
        assert merge_block_mechanisms(RobotsResult(found=True), self._cdn([])) == []

    def test_unchecked_http_contributes_nothing(self) -> None:
        robots = RobotsResult(found=True, bots_blocked=["GPTBot"])
        assert merge_block_mechanisms(robots, self._cdn(["GPTBot"], checked=False)) == [
            {"bot": "GPTBot", "mechanism": "robots_txt"}
        ]
