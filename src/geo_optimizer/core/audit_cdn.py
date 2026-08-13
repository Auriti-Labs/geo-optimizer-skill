from __future__ import annotations

from geo_optimizer.models.results import CdnAiCrawlerResult


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

    from geo_optimizer.utils.http import create_session_with_retry
    from geo_optimizer.utils.validators import resolve_and_validate_url

    # Fix #283: SSRF validation before CDN requests
    # Fix #305: DNS pinning with pinned session (eliminates TOCTOU)
    is_safe, reason, pinned_ips = resolve_and_validate_url(base_url)
    if not is_safe:
        result.error = f"Unsafe URL: {reason}"
        return result

    # Session with DNS pinning — all requests use pre-validated IPs
    session = create_session_with_retry(total_retries=1, pinned_ips=pinned_ips)

    try:
        # Step 1: Browser request (baseline)
        try:
            browser_r = session.get(
                base_url,
                headers={"User-Agent": browser_ua},
                timeout=10,
                allow_redirects=False,
            )
            result.browser_status = browser_r.status_code
            # Fix #348: size check to avoid OOM on oversized responses
            if len(browser_r.content) > 5 * 1024 * 1024:  # 5 MB
                result.error = "Response too large for CDN check"
                return result
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
                bot_r = session.get(
                    base_url,
                    headers={"User-Agent": bot_ua},
                    timeout=10,
                    allow_redirects=False,
                )
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
        result.any_blocked = any(b["blocked"] or b["challenge_detected"] for b in result.bot_results)

    except Exception:
        pass

    return result
