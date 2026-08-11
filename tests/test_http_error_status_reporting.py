"""An HTTP error is not a connection failure.

`requests.Response.__bool__` is `ok`, i.e. `status_code < 400`. So a perfectly
valid 403 carrying a full body is *falsy*, and `if err or not r` routed it down
the "no response at all" branch: the audit reported `error="Connection failed"`
and `http_status=0` for a request that had completed, and the branch immediately
below — written to name the status and point at a WAF — became unreachable for
every status >= 400.

Reported from production: https://www.netsons.com/ answers 200 to a desktop
browser and 403 to the server, and the report read "Audit failed — Connection
failed", which sends the user looking for a network problem that does not exist.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from geo_optimizer.core.audit import run_full_audit


class _FakeResponse:
    """Minimal stand-in that reproduces requests' truthiness rule."""

    def __init__(self, status_code: int, text: str = "<html><body>x</body></html>"):
        self.status_code = status_code
        self.text = text
        self.headers: dict[str, str] = {"content-type": "text/html"}
        self.encoding = "utf-8"

    @property
    def ok(self) -> bool:
        return self.status_code < 400

    def __bool__(self) -> bool:
        # This is the whole point of the test: requests does exactly this.
        return self.ok


class TestErrorStatusIsReportedAsSuch:
    @pytest.mark.parametrize("status", [403, 401, 404, 429, 500, 503])
    def test_http_error_reports_the_status_not_a_connection_failure(self, status: int):
        with patch("geo_optimizer.core.audit.fetch_url", return_value=(_FakeResponse(status), None)):
            result = run_full_audit("https://blocked.example")

        assert result.error == f"HTTP {status}", f"a {status} must be named, got {result.error!r}"
        assert result.http_status == status, "the status code must survive into the result"
        assert "Connection failed" not in (result.error or "")

    def test_the_waf_hint_is_reachable(self):
        """The recommendation behind the status branch was dead code for 4xx/5xx."""
        with patch("geo_optimizer.core.audit.fetch_url", return_value=(_FakeResponse(403), None)):
            result = run_full_audit("https://blocked.example")

        joined = " ".join(result.recommendations)
        assert "403" in joined
        assert "WAF" in joined or "Cloudflare" in joined

    def test_a_real_transport_failure_still_reports_one(self):
        """The fix must not swallow the case the branch was actually for."""
        with patch(
            "geo_optimizer.core.audit.fetch_url",
            return_value=(None, "Connection failed dopo retry esponenziale: timeout"),
        ):
            result = run_full_audit("https://unreachable.example")

        assert "Connection failed" in (result.error or "")

    def test_no_response_and_no_error_still_degrades_readably(self):
        """Defensive: if fetch_url ever returns (None, None), the message must not
        interpolate a bare None — that was the "Unable to reach X: None" the user
        saw."""
        with patch("geo_optimizer.core.audit.fetch_url", return_value=(None, None)):
            result = run_full_audit("https://nothing.example")

        assert result.error == "Connection failed"
        assert "None" not in " ".join(result.recommendations)

    @pytest.mark.parametrize("status", [200, 203])
    def test_success_statuses_are_still_audited(self, status: int):
        with patch("geo_optimizer.core.audit.fetch_url", return_value=(_FakeResponse(status), None)):
            result = run_full_audit("https://ok.example")

        assert result.error is None
