from __future__ import annotations

from geo_optimizer.models.results import CdnAiCrawlerResult, RobotsResult

# The 4 user agents that decide block_pattern. Googlebot and Applebot are also
# requested, but a site that blocks AI bots while serving Google is the normal case.
AI_UA_BOTS = ("GPTBot", "OAI-SearchBot", "PerplexityBot", "Claude-SearchBot")


def _http_blocked(entry: dict) -> bool:
    """A bot counts as blocked at HTTP level on a block status/size or a challenge page."""
    return bool(entry["blocked"] or entry["challenge_detected"])


def classify_block_pattern(bot_results: list[dict]) -> str:
    """Return "none", "targeted" or "blanket" from the per-bot HTTP results of the AI UAs."""
    blocked = [_http_blocked(b) for b in bot_results if b["bot"] in AI_UA_BOTS]
    if not blocked or not any(blocked):
        return "none"
    return "blanket" if all(blocked) and len(blocked) == len(AI_UA_BOTS) else "targeted"


def merge_block_mechanisms(robots: RobotsResult, cdn: CdnAiCrawlerResult) -> list[dict[str, str]]:
    """List every blocked bot with the mechanism that blocks it.

    robots_txt: Disallow in robots.txt only; http: refused by the HTTP check only;
    both: blocked by each. Bots allowed by both checks are not listed.
    """
    by_robots = list(robots.bots_blocked)
    by_http = [b["bot"] for b in cdn.bot_results if _http_blocked(b)] if cdn.checked else []
    blocks = []
    for bot in dict.fromkeys(by_robots + by_http):  # order-preserving union
        in_robots, in_http = bot in by_robots, bot in by_http
        mechanism = "both" if in_robots and in_http else "robots_txt" if in_robots else "http"
        blocks.append({"bot": bot, "mechanism": mechanism})
    return blocks


def audit_cdn_ai_crawler(base_url: str) -> CdnAiCrawlerResult:
    """Check if CDN/WAF blocks AI crawler user-agents (#225).

    Simulates requests with the AI bot User-Agents that actually drive AI
    citations (GPTBot, OAI-SearchBot, PerplexityBot, Claude-SearchBot,
    Googlebot, Applebot) and compares response status/size to a normal
    browser request. #512: bot roster matches CITATION_BOTS plus GPTBot
    (kept for training-block visibility, per-vendor precedent).

    Based on OtterlyAI Citation Report 2026: 73% of sites have technical
    barriers blocking AI crawlers. CDN restrictions are barrier #2.

    Args:
        base_url: Base URL of the site (normalized).

    Returns:
        CdnAiCrawlerResult with per-bot comparison data.
    """
    from geo_optimizer.models.results import CdnAiCrawlerResult

    result = CdnAiCrawlerResult()

    # AI bots to test (most impactful for citations)
    test_bots = {
        "GPTBot": (
            "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GPTBot/1.2; +https://openai.com/gptbot)"
        ),
        "OAI-SearchBot": (
            "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; OAI-SearchBot/1.0; "
            "+https://openai.com/searchbot)"
        ),
        "PerplexityBot": (
            "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; PerplexityBot/1.0; "
            "+https://perplexity.ai/perplexitybot)"
        ),
        "Claude-SearchBot": (
            "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Claude-SearchBot/1.0; "
            "+https://www.anthropic.com/claude-searchbot)"
        ),
        "Googlebot": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Applebot": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/13.1.1 Safari/605.1.15 (Applebot/0.1; +http://www.apple.com/go/applebot)"
        ),
    }

    browser_ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # Challenge page indicators (Cloudflare, AWS WAF, etc.)
    challenge_indicators = [
        "cf-browser-verification",
        "challenge-platform",
        "just a moment",
        "checking your browser",
        "ray id",
        "access denied",
        "bot detection",
        "captcha",
        "blocked",
        "forbidden",
    ]

    # CDN detection headers
    cdn_header_map = {
        "cf-ray": "cloudflare",
        "cf-cache-status": "cloudflare",
        "x-amz-cf-id": "aws-cloudfront",
        "x-amz-request-id": "aws",
        "x-akamai-transformed": "akamai",
        "x-cdn": "",  # generic CDN
        "x-served-by": "",  # Fastly/Varnish
        "x-vercel-id": "vercel",
        "server": "",  # check value
    }

    from geo_optimizer.utils.http import _stream_response, create_session_with_retry
    from geo_optimizer.utils.validators import resolve_and_validate_url

    # Fix #283: SSRF validation before CDN requests
    # Fix #305: DNS pinning with pinned session (eliminates TOCTOU)
    is_safe, reason, pinned_ips = resolve_and_validate_url(base_url)
    if not is_safe:
        result.error = f"Unsafe URL: {reason}"
        return result

    # Session with DNS pinning — all requests use pre-validated IPs
    session = create_session_with_retry(total_retries=1, pinned_ips=pinned_ips)

    def _get_capped(user_agent: str):
        """GET base_url streaming the body; returns None once it exceeds 5 MB (fix #348)."""
        r = session.get(base_url, headers={"User-Agent": user_agent}, timeout=10, allow_redirects=False, stream=True)
        try:
            content, err = _stream_response(r, 5 * 1024 * 1024)
        except Exception:
            r.close()  # e.g. ReadTimeout mid-body: release the connection, then let the caller handle it
            raise
        if err:
            r.close()
            return None
        r._content = content  # noqa: SLF001 — lets r.text decode the already-read body
        return r

    try:
        # Step 1: Browser request (baseline)
        try:
            browser_r = _get_capped(browser_ua)
            if browser_r is None:
                result.error = "Response too large for CDN check"
                return result
            result.browser_status = browser_r.status_code
            result.browser_content_length = len(browser_r.text)

            # Detect CDN from headers
            resp_headers = {k.lower(): v for k, v in browser_r.headers.items()}
            for header_key, cdn_name in cdn_header_map.items():
                if header_key in resp_headers:
                    result.cdn_headers[header_key] = resp_headers[header_key]
                    if cdn_name and not result.cdn_detected:
                        result.cdn_detected = cdn_name
            # Check server header for CDN names
            server_val = resp_headers.get("server", "").lower()
            if "cloudflare" in server_val:
                result.cdn_detected = "cloudflare"
            elif "akamaighost" in server_val or "akamai" in server_val:
                result.cdn_detected = "akamai"

        except Exception:
            # Not reachable even as a browser — skip check
            return result

        # Step 2: AI bot requests
        for bot_name, bot_ua in test_bots.items():
            bot_entry = {
                "bot": bot_name,
                "status": 0,
                "content_length": 0,
                "blocked": False,
                "challenge_detected": False,
            }
            try:
                bot_r = _get_capped(bot_ua)
                if bot_r is None:
                    result.error = "Response too large for CDN check"
                    return result
                bot_entry["status"] = bot_r.status_code
                bot_entry["content_length"] = len(bot_r.text)

                # Check 1: HTTP error status
                if bot_r.status_code in (403, 429, 451, 503):
                    bot_entry["blocked"] = True

                # Check 2: Challenge/captcha page detection
                body_lower = bot_r.text[:5000].lower()
                if any(indicator in body_lower for indicator in challenge_indicators):
                    bot_entry["challenge_detected"] = True

                # Check 3: Content-length mismatch (>70% difference → probable block)
                if (
                    result.browser_content_length > 0
                    and bot_entry["content_length"] > 0
                    and result.browser_status == 200
                    and bot_r.status_code == 200
                ):
                    ratio = bot_entry["content_length"] / result.browser_content_length
                    if ratio < 0.3:
                        # Bot receives <30% of the content → likely a block page
                        bot_entry["blocked"] = True

            except Exception:
                bot_entry["blocked"] = True

            result.bot_results.append(bot_entry)

        result.checked = True
        result.any_blocked = any(_http_blocked(b) for b in result.bot_results)
        result.block_pattern = classify_block_pattern(result.bot_results)

    except Exception:
        pass

    return result
