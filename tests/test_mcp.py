"""
Test per geo_optimizer.mcp.server.

Verifica i 4 tool MCP e le 2 resource. Tutto mockato — zero chiamate HTTP.
Richiede: pip install geo-optimizer-skill[mcp]
"""

import json
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import pytest

# Skip se mcp non installato
pytest.importorskip("mcp", reason="mcp non installato (pip install geo-optimizer-skill[mcp])")

from geo_optimizer.mcp.server import (
    geo_audit,
    geo_factual_accuracy,
    geo_fix,
    geo_gap_analysis,
    geo_llms_generate,
    geo_schema_validate,
    get_ai_bots,
    get_score_bands,
)
from geo_optimizer.models.results import (
    AuditResult,
    ContentResult,
    FactualAccuracyResult,
    FixItem,
    FixPlan,
    GapAction,
    GapAnalysisResult,
    LlmsTxtResult,
    MetaResult,
    RobotsResult,
    SchemaResult,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(autouse=True)
def _mock_mcp_url_validation(monkeypatch):
    """Rende deterministica la validazione URL nei test MCP offline."""

    def _fake_validate(url):
        host = (urlparse(url).hostname or "").lower()
        if host.endswith("example.com"):
            return True, None
        if host in {"localhost", "169.254.169.254", "192.168.0.1", "10.0.0.1"}:
            return False, "blocked for test"
        return True, None

    monkeypatch.setattr("geo_optimizer.utils.validators.validate_public_url", _fake_validate)


def _mock_audit_result():
    """Crea un AuditResult mock per i test."""
    return AuditResult(
        url="https://example.com",
        score=65,
        band="foundation",
        robots=RobotsResult(
            found=True,
            bots_allowed=["GPTBot"],
            bots_missing=["ClaudeBot"],
            citation_bots_ok=False,
        ),
        llms=LlmsTxtResult(found=False),
        schema=SchemaResult(found_types=["WebSite"], has_website=True),
        meta=MetaResult(
            has_title=True,
            has_description=True,
            has_canonical=False,
            title_text="Example",
        ),
        content=ContentResult(has_h1=True, word_count=500),
        recommendations=["Aggiungi llms.txt"],
        http_status=200,
        page_size=12000,
    )


def _mock_fix_plan():
    """Crea un FixPlan mock per i test."""
    return FixPlan(
        url="https://example.com",
        score_before=65,
        score_estimated_after=85,
        fixes=[
            FixItem(
                category="robots",
                description="Aggiunge 1 bot AI mancante",
                content="User-agent: ClaudeBot\nAllow: /\n",
                file_name="robots.txt",
                action="append",
            ),
        ],
        skipped=["schema: già presente"],
    )


# ============================================================================
# TEST: geo_audit
# ============================================================================


class TestGeoAuditTool:
    """Test per il tool MCP geo_audit."""

    @patch("geo_optimizer.core.audit.run_full_audit")
    def test_audit_ritorna_json_valido(self, mock_audit):
        """geo_audit ritorna JSON con score e dettagli."""
        mock_audit.return_value = _mock_audit_result()

        result = geo_audit("https://example.com")
        data = json.loads(result)

        assert data["score"] == 65
        assert data["band"] == "foundation"
        assert data["url"] == "https://example.com"
        assert data["robots"]["found"] is True

    def test_audit_url_non_sicuro(self):
        """geo_audit blocca URL verso reti private."""
        result = geo_audit("http://169.254.169.254/metadata")
        data = json.loads(result)

        assert "error" in data
        assert "Unsafe URL" in data["error"]

    @patch("geo_optimizer.core.audit.run_full_audit")
    def test_audit_normalizza_url(self, mock_audit):
        """geo_audit aggiunge https:// se mancante."""
        mock_audit.return_value = _mock_audit_result()

        geo_audit("example.com")
        call_url = mock_audit.call_args[0][0]
        assert call_url.startswith("https://")

    @patch("geo_optimizer.core.audit.run_full_audit")
    def test_audit_receipt_default_disabled(self, mock_audit):
        """geo_audit does not include receipt block by default."""
        mock_audit.return_value = _mock_audit_result()
        result = geo_audit("https://example.com")
        data = json.loads(result)
        assert "receipt" not in data

    @patch("geo_optimizer.core.audit.run_full_audit")
    def test_audit_include_receipt_enabled(self, mock_audit):
        """geo_audit includes receipt with stages and metrics when requested (#557)."""

        def _fake_run(url, score_version=2, on_step=None):
            if on_step:
                on_step("Fetching page, robots.txt, llms.txt and AI files")
                on_step("Analyzing schema, meta tags and content")
            res = _mock_audit_result()
            res.audit_duration_ms = 350
            return res

        mock_audit.side_effect = _fake_run
        result = geo_audit("https://example.com", include_receipt=True)
        data = json.loads(result)
        assert "receipt" in data
        assert data["receipt"]["url"] == "https://example.com"
        assert data["receipt"]["stages_completed"] == [
            "Fetching page, robots.txt, llms.txt and AI files",
            "Analyzing schema, meta tags and content",
        ]
        assert data["receipt"]["stages_failed"] == []
        assert data["receipt"]["duration_ms"] == 350
        assert data["receipt"]["terminal_error"] is None
        assert data["receipt"]["attempts"] == 1

    @pytest.mark.parametrize(
        ("error", "http_status", "expected_code"),
        [
            ("Connection failed", 0, "connection_failed"),
            ("HTTP 403", 403, "http_error"),
            ("Timeout (10s) dopo retry esponenziale", 0, "timeout"),
            ("Response too large: 12000000 bytes (max: 5000000)", 0, "too_large"),
        ],
    )
    @patch("geo_optimizer.core.audit.run_full_audit")
    def test_audit_include_receipt_on_early_error(self, mock_audit, error, http_status, expected_code):
        """An unreachable or erroring homepage fails the fetch stage with a normalized code (#557)."""
        from geo_optimizer.models.config import AUDIT_STEPS

        def _early_return(url, score_version=2, on_step=None):
            if on_step:
                on_step(AUDIT_STEPS[0])
            res = _mock_audit_result()
            res.error = error
            res.http_status = http_status
            return res

        mock_audit.side_effect = _early_return
        data = json.loads(geo_audit("https://example.com", include_receipt=True))
        assert data["receipt"]["stages_completed"] == []
        assert data["receipt"]["stages_failed"] == [AUDIT_STEPS[0]]
        assert data["receipt"]["terminal_error"] == expected_code
        assert data["receipt"]["attempts"] == 1
        assert "attempts" not in data

    def test_audit_include_receipt_on_unsafe_url(self):
        """geo_audit retains partial receipt on unsafe URL errors (#557)."""
        result = geo_audit("http://169.254.169.254/metadata", include_receipt=True)
        data = json.loads(result)
        assert "error" in data
        assert "receipt" in data
        assert data["receipt"]["stages_failed"] == ["validate_url"]
        assert data["receipt"]["terminal_error"] == "unsafe_url"
        assert data["receipt"]["attempts"] == 1
        assert "attempts" not in data

    def test_audit_include_receipt_on_invalid_score_version(self):
        """Invalid score_version records normalized 'invalid_argument' error in receipt (#557)."""
        result = geo_audit("https://example.com", score_version=99, include_receipt=True)
        data = json.loads(result)
        assert "error" in data
        assert data["error"] == "score_version must be 1, 2, 3 or 4"
        assert "receipt" in data
        assert data["receipt"]["stages_failed"] == ["validate_score_version"]
        assert data["receipt"]["terminal_error"] == "invalid_argument"
        assert data["receipt"]["attempts"] == 1
        assert "attempts" not in data

    @patch("geo_optimizer.core.audit.run_full_audit")
    def test_audit_include_receipt_on_exception(self, mock_audit):
        """The stage running when run_full_audit raises is failed, not completed (#557).

        on_step fires when a stage starts: stage 0 finished, stage 1 raised.
        """
        from geo_optimizer.models.config import AUDIT_STEPS

        def _raising_run(url, score_version=2, on_step=None):
            if on_step:
                on_step(AUDIT_STEPS[0])
                on_step(AUDIT_STEPS[1])
            raise RuntimeError("Network failure during audit")

        mock_audit.side_effect = _raising_run
        result = geo_audit("https://example.com", include_receipt=True)
        data = json.loads(result)
        assert "error" in data
        assert data["error"] == "Internal error during operation"
        assert "receipt" in data
        assert data["receipt"]["url"] == "https://example.com"
        assert data["receipt"]["stages_completed"] == [AUDIT_STEPS[0]]
        assert data["receipt"]["stages_failed"] == [AUDIT_STEPS[1]]
        assert data["receipt"]["terminal_error"] == "internal"
        assert data["receipt"]["attempts"] == 1
        assert "attempts" not in data

    @pytest.mark.parametrize(
        ("err", "expected"),
        [
            (None, None),
            ("", None),
            ("Timeout (10s) dopo retry esponenziale", "timeout"),
            ("Connection failed", "connection_failed"),
            ("HTTP 500", "http_error"),
            ("Too many redirects (max: 5)", "http_error"),
            ("Response too large: 6000000 bytes", "too_large"),
            ("Unsafe URL: private IP", "unsafe_url"),
            ("Unsafe URL: Scheme http not allowed", "unsafe_url"),
            ("Redirect to unsafe URL: private IP", "unsafe_url"),
            ("score_version must be 1, 2, 3 or 4", "invalid_argument"),
            ("score_version must be 1, 2 or 3", "invalid_argument"),
            ("HTTP 400: invalid argument", "http_error"),
            ("Something unexpected", "internal"),
        ],
    )
    def test_normalize_terminal_error(self, err, expected):
        from geo_optimizer.mcp.server import _normalize_terminal_error

        assert _normalize_terminal_error(err) == expected

    def test_normalize_terminal_error_precedence_http_over_invalid(self):
        """Branch order precedence: HTTP status error with invalid argument payload normalizes to http_error (#557)."""
        from geo_optimizer.mcp.server import _normalize_terminal_error

        assert _normalize_terminal_error("HTTP 400: invalid argument") == "http_error"

    @patch("geo_optimizer.core.audit.run_full_audit")
    def test_audit_include_receipt_on_immediate_exception(self, mock_audit):
        """geo_audit reports first stage as failed if exception occurs before any stage completes (#557)."""
        from geo_optimizer.models.config import AUDIT_STEPS

        mock_audit.side_effect = RuntimeError("Immediate crash")
        result = geo_audit("https://example.com", include_receipt=True)
        data = json.loads(result)
        assert "error" in data
        assert data["receipt"]["stages_completed"] == []
        assert data["receipt"]["stages_failed"] == [AUDIT_STEPS[0]]

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_audit_receipt_reflects_http_attempts(self, mock_fetch):
        """geo_audit receipt attempts count reflects retries from HTTP layer (#557)."""
        from urllib3.util.retry import RequestHistory, Retry

        retry = Retry()
        retry.history = (
            RequestHistory("GET", "https://example.com", None, 500, None),
            RequestHistory("GET", "https://example.com", None, 503, None),
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><head><title>Test</title></head><body>Hello world</body></html>"
        mock_resp.content = mock_resp.text.encode("utf-8")
        mock_resp.headers = {"Content-Type": "text/html"}
        mock_resp.raw.retries = retry

        mock_fetch.return_value = (mock_resp, None)
        data = json.loads(geo_audit("https://example.com", include_receipt=True))
        assert "receipt" in data
        assert data["receipt"]["attempts"] == 3
        assert "attempts" not in data

    def test_get_response_attempts_helper(self):
        """get_response_attempts safely extracts retry history count (#557)."""
        from unittest.mock import Mock

        from geo_optimizer.utils.http import get_response_attempts

        class FakeRetries:
            def __init__(self, count):
                self.history = tuple(range(count))

        assert get_response_attempts(None) == 1
        assert get_response_attempts(MagicMock(raw=None)) == 1

        mock_resp = MagicMock()
        mock_resp.raw.retries = FakeRetries(0)
        assert get_response_attempts(mock_resp) == 1

        mock_resp.raw.retries = FakeRetries(3)
        assert get_response_attempts(mock_resp) == 4

        # Standard Mock whose child attributes are also Mocks must return 1 and not raise TypeError
        plain_mock = Mock()
        assert get_response_attempts(plain_mock) == 1

    def test_get_response_attempts_with_real_urllib3_retry(self):
        """get_response_attempts correctly inspects real urllib3 Retry history (#557)."""
        from urllib3.util.retry import RequestHistory, Retry

        from geo_optimizer.utils.http import get_response_attempts

        retry = Retry()
        retry.history = (
            RequestHistory("GET", "https://example.com", None, 500, None),
            RequestHistory("GET", "https://example.com", None, 503, None),
        )
        resp = MagicMock()
        resp.raw.retries = retry
        assert get_response_attempts(resp) == 3

    @patch("geo_optimizer.utils.validators.resolve_and_validate_url", return_value=(True, None, ["93.184.216.34"]))
    @patch("geo_optimizer.utils.http.create_session_with_retry")
    @patch("time.sleep")
    def test_audit_receipt_reflects_timeout_retries(self, mock_sleep, mock_create, mock_resolve):
        """geo_audit receipt reflects observed attempts when fetch exhausts retries on timeout (#557)."""
        import requests

        mock_session = MagicMock()
        mock_session.get.side_effect = requests.exceptions.Timeout("Connection timed out")
        mock_create.return_value = mock_session

        data = json.loads(geo_audit("https://example.com", include_receipt=True))
        assert "receipt" in data
        assert data["receipt"]["attempts"] == 4
        assert mock_session.get.call_count == 4
        assert "attempts" not in data

    @patch("geo_optimizer.core.audit.fetch_url")
    def test_audit_receipt_default_excludes_attempts(self, mock_fetch):
        """Default output (include_receipt=False) never leaks attempts (#557)."""
        from urllib3.util.retry import RequestHistory, Retry

        retry = Retry()
        retry.history = (
            RequestHistory("GET", "https://example.com", None, 500, None),
            RequestHistory("GET", "https://example.com", None, 503, None),
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><head><title>Test</title></head><body>Hello</body></html>"
        mock_resp.content = mock_resp.text.encode("utf-8")
        mock_resp.headers = {"Content-Type": "text/html"}
        mock_resp.raw.retries = retry
        mock_fetch.return_value = (mock_resp, None)

        data = json.loads(geo_audit("https://example.com", include_receipt=False))
        assert "attempts" not in data
        assert "receipt" not in data

    @patch("geo_optimizer.utils.cache.FileCache.get")
    def test_audit_receipt_cache_hit_resets_attempts_to_one(self, mock_cache_get):
        """A cached homepage returns attempts=1 even if a previous fetch had retries in the same context (#557)."""
        from dataclasses import asdict

        from geo_optimizer.core.audit import get_audit_telemetry, run_full_audit
        from geo_optimizer.utils.http import _last_request_attempts

        # Simulate previous request leaving 4 attempts in context
        _last_request_attempts.set(4)

        # Mock cache hit for homepage
        mock_cache_get.return_value = (
            200,
            "<html><head><title>Test</title></head><body>Cached content</body></html>",
            {"Content-Type": "text/html"},
        )

        with patch("geo_optimizer.core.audit.fetch_url") as mock_fetch:
            mock_resp = MagicMock(status_code=200, text="Not cached", headers={})
            mock_fetch.return_value = (mock_resp, None)
            result = run_full_audit("https://example.com", use_cache=True)

            telemetry = get_audit_telemetry()
            assert telemetry["attempts"] == 1
            # AuditResult itself never has attempts field (#557)
            assert not hasattr(result, "attempts")
            assert "attempts" not in asdict(result)

    def test_get_response_attempts_with_cached_response(self):
        """get_response_attempts returns 1 for CachedResponse (#557)."""
        from geo_optimizer.models.results import CachedResponse
        from geo_optimizer.utils.http import _last_request_attempts, get_response_attempts

        _last_request_attempts.set(4)
        cached = CachedResponse(status_code=200, text="ok", content=b"ok", headers={})
        assert get_response_attempts(cached) == 1


# ============================================================================
# TEST: geo_fix
# ============================================================================


class TestGeoFixTool:
    """Test per il tool MCP geo_fix."""

    @patch("geo_optimizer.core.fixer.run_all_fixes")
    def test_fix_ritorna_piano(self, mock_fixes):
        """geo_fix ritorna FixPlan serializzato."""
        mock_fixes.return_value = _mock_fix_plan()

        result = geo_fix("https://example.com")
        data = json.loads(result)

        assert data["score_before"] == 65
        assert data["score_estimated_after"] == 85
        assert len(data["fixes"]) == 1
        assert data["fixes"][0]["category"] == "robots"

    @patch("geo_optimizer.core.fixer.run_all_fixes")
    def test_fix_con_filtro_only(self, mock_fixes):
        """geo_fix con only filtra le categorie."""
        mock_fixes.return_value = _mock_fix_plan()

        geo_fix("https://example.com", only="robots,llms")
        call_kwargs = mock_fixes.call_args[1]
        assert call_kwargs["only"] == {"robots", "llms"}

    def test_fix_url_non_sicuro(self):
        """geo_fix blocca URL locali."""
        result = geo_fix("http://localhost:8080")
        data = json.loads(result)
        assert "error" in data


class TestGeoGapAnalysisTool:
    """Test per il tool MCP geo_gap_analysis."""

    @patch("geo_optimizer.utils.validators.validate_public_url", return_value=(True, None))
    @patch("geo_optimizer.core.gap_analysis.run_gap_analysis")
    def test_gap_analysis_ritorna_json_valido(self, mock_gap_analysis, _mock_validate):
        """geo_gap_analysis serializza una gap analysis con piano d'azione."""
        mock_gap_analysis.return_value = GapAnalysisResult(
            weaker_url="https://weaker.example.com",
            stronger_url="https://stronger.example.com",
            weaker_score=55,
            stronger_score=82,
            score_gap=27,
            weaker_band="foundation",
            stronger_band="good",
            action_plan=[
                GapAction(
                    category="llms",
                    title="Publish llms.txt",
                    rationale="The stronger site has llms.txt and the weaker site does not.",
                    impact_points=5,
                    priority="high",
                    command="geo llms --base-url https://weaker.example.com",
                )
            ],
        )

        result = geo_gap_analysis("https://weaker.example.com", "https://stronger.example.com")
        data = json.loads(result)

        assert data["score_gap"] == 27
        assert data["weaker_url"] == "https://weaker.example.com"
        assert data["action_plan"][0]["title"] == "Publish llms.txt"

    def test_gap_analysis_blocca_url_non_sicuro(self):
        """geo_gap_analysis rifiuta URL verso reti private."""
        result = geo_gap_analysis("http://192.168.0.1", "https://example.com")
        data = json.loads(result)

        assert "error" in data


class TestGeoFactualAccuracyTool:
    """Test per il tool MCP geo_factual_accuracy."""

    @patch("geo_optimizer.core.factual_accuracy.run_factual_accuracy_audit")
    def test_factual_accuracy_ritorna_json_valido(self, mock_factual):
        """geo_factual_accuracy serializza il risultato dell'audit fattuale."""
        mock_factual.return_value = FactualAccuracyResult(
            checked=True,
            claims_found=4,
            claims_sourced=2,
            claims_unsourced=1,
            unsourced_claims=["Studies show 42% of users prefer GEO."],
            inconsistencies=["Conflicting numeric claims for 'conversion rate': 42%, 45%"],
            broken_source_links=["https://broken.example.com/report"],
            source_links_checked=2,
            severity="high",
        )

        result = geo_factual_accuracy("https://example.com/blog/post")
        data = json.loads(result)

        assert data["checked"] is True
        assert data["claims_found"] == 4
        assert data["severity"] == "high"
        assert data["broken_source_links"] == ["https://broken.example.com/report"]

    def test_factual_accuracy_blocca_url_non_sicuro(self):
        """geo_factual_accuracy rifiuta URL verso reti private."""
        result = geo_factual_accuracy("http://10.0.0.1/internal")
        data = json.loads(result)

        assert "error" in data
        assert "Unsafe URL" in data["error"]


# ============================================================================
# TEST: geo_llms_generate
# ============================================================================


class TestGeoLlmsGenerateTool:
    """Test per il tool MCP geo_llms_generate."""

    @patch("geo_optimizer.core.llms_generator.generate_llms_txt", return_value="# Example\n> Sito web")
    @patch("geo_optimizer.core.llms_generator.fetch_sitemap", return_value=[])
    @patch("geo_optimizer.core.llms_generator.discover_sitemap", return_value=None)
    def test_genera_llms_txt(self, mock_discover, mock_fetch, mock_gen):
        """geo_llms_generate ritorna contenuto llms.txt."""
        result = geo_llms_generate("https://example.com")

        assert "Example" in result
        assert len(result) > 0

    def test_llms_url_non_sicuro(self):
        """geo_llms_generate blocca URL privati."""
        result = geo_llms_generate("http://10.0.0.1")

        assert "Unsafe URL" in result


# ============================================================================
# TEST: geo_schema_validate
# ============================================================================


class TestGeoSchemaValidateTool:
    """Test per il tool MCP geo_schema_validate."""

    def test_schema_valido(self):
        """Schema WebSite completo viene validato correttamente."""
        schema = json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "url": "https://example.com",
                "name": "Example",
            }
        )
        result = geo_schema_validate(schema, "website")
        data = json.loads(result)

        assert data["valid"] is True

    def test_schema_non_valido(self):
        """Schema incompleto viene rilevato."""
        schema = json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "WebSite",
            }
        )
        result = geo_schema_validate(schema, "website")
        data = json.loads(result)

        assert data["valid"] is False
        assert data["error"] is not None

    def test_json_malformato(self):
        """JSON non valido viene gestito senza crash."""
        result = geo_schema_validate("{invalid json}", "website")
        data = json.loads(result)

        assert data["valid"] is False


# ============================================================================
# TEST: Resources
# ============================================================================


class TestMcpResources:
    """Test per le resource MCP."""

    def test_ai_bots_resource(self):
        """Resource ai-bots ritorna lista bot."""
        result = get_ai_bots()
        data = json.loads(result)

        assert "ai_bots" in data
        assert "GPTBot" in data["ai_bots"]
        assert data["total"] == len(data["ai_bots"])  # v4.0: bot count dinamico
        assert "tiers" in data
        assert "search" in data["tiers"]
        assert "training" in data["tiers"]
        assert "user" in data["tiers"]

    def test_score_bands_resource(self):
        """Resource score-bands ritorna fasce punteggio."""
        result = get_score_bands()
        data = json.loads(result)

        assert "critical" in data or isinstance(data, dict)


# ============================================================================
# TEST: geo_citability
# ============================================================================


class TestGeoCitabilityTool:
    """Test per il tool MCP geo_citability."""

    @patch("geo_optimizer.utils.http.fetch_url")
    @patch("geo_optimizer.core.citability.audit_citability")
    def test_citability_happy_path_ritorna_json(self, mock_citability, mock_fetch):
        """geo_citability con fetch OK e citability audit ritorna JSON valido."""
        from unittest.mock import MagicMock

        from geo_optimizer.models.results import CitabilityResult, MethodScore

        # Arrange: risposta HTTP mock
        mock_resp = MagicMock()
        mock_resp.text = "<html><body><h1>Titolo</h1><p>Contenuto con citazione (Fonte: esempio.com).</p></body></html>"
        mock_fetch.return_value = (mock_resp, None)

        # Arrange: risultato citability mock
        mock_result = CitabilityResult(
            methods=[
                MethodScore(
                    name="cite_sources",
                    label="Cite Sources",
                    detected=True,
                    score=8,
                    max_score=10,
                    impact="+27%",
                )
            ],
            total_score=72,
            grade="high",
            top_improvements=[],
        )
        mock_citability.return_value = mock_result

        from geo_optimizer.mcp.server import geo_citability

        # Act
        result = geo_citability("https://example.com")
        data = json.loads(result)

        # Assert
        assert "total_score" in data
        assert data["total_score"] == 72
        assert data["grade"] == "high"
        assert len(data["methods"]) == 1

    @patch("geo_optimizer.utils.http.fetch_url")
    def test_citability_fetch_errore_ritorna_errore(self, mock_fetch):
        """geo_citability con fetch_url che ritorna errore restituisce messaggio di errore."""
        # Arrange
        mock_fetch.return_value = (None, "Connection refused")

        from geo_optimizer.mcp.server import geo_citability

        # Act
        result = geo_citability("https://example.com")
        data = json.loads(result)

        # Assert
        assert "error" in data
        assert "Connection refused" in data["error"] or "example.com" in data["error"]

    def test_citability_url_non_sicuro_ritorna_errore(self):
        """geo_citability blocca URL verso reti private."""
        from geo_optimizer.mcp.server import geo_citability

        # Act
        result = geo_citability("http://192.168.0.1")
        data = json.loads(result)

        # Assert
        assert "error" in data
        assert "Unsafe URL" in data["error"]

    @patch("geo_optimizer.utils.http.fetch_url")
    @patch("geo_optimizer.core.citability.audit_citability")
    def test_citability_eccezione_ritorna_errore(self, mock_citability, mock_fetch):
        """geo_citability gestisce eccezioni impreviste durante l'analisi."""
        from unittest.mock import MagicMock

        # Arrange
        mock_resp = MagicMock()
        mock_resp.text = "<html><body>test</body></html>"
        mock_fetch.return_value = (mock_resp, None)
        mock_citability.side_effect = RuntimeError("Errore imprevisto")

        from geo_optimizer.mcp.server import geo_citability

        # Act
        result = geo_citability("https://example.com")
        data = json.loads(result)

        # Assert
        assert "error" in data


# ============================================================================
# TEST: exception paths per geo_audit, geo_fix, geo_llms_generate
# ============================================================================


class TestExceptionPaths:
    """Verifica i percorsi di eccezione nei tool MCP."""

    @patch("geo_optimizer.core.audit.run_full_audit")
    def test_geo_audit_eccezione_ritorna_json_errore(self, mock_audit):
        """geo_audit gestisce eccezioni impreviste ritornando messaggio generico (fix #314).

        Il dettaglio dell'errore NON deve essere esposto al client per ragioni di sicurezza.
        L'errore reale viene loggato internamente.
        """
        # Arrange
        mock_audit.side_effect = RuntimeError("DB unavailable")

        # Act
        result = geo_audit("https://example.com")
        data = json.loads(result)

        # Assert — generic message to client, without internal detail (fix #314)
        assert "error" in data
        assert "DB unavailable" not in data["error"]
        assert "internal" in data["error"].lower() or "error" in data["error"].lower()
        assert data["url"] == "https://example.com"

    @patch("geo_optimizer.core.fixer.run_all_fixes")
    def test_geo_fix_eccezione_ritorna_json_errore(self, mock_fixes):
        """geo_fix gestisce eccezioni impreviste ritornando messaggio generico (fix #314).

        Il dettaglio dell'errore NON deve essere esposto al client per ragioni di sicurezza.
        L'errore reale viene loggato internamente.
        """
        # Arrange
        mock_fixes.side_effect = RuntimeError("Fixer crashed")

        # Act
        result = geo_fix("https://example.com")
        data = json.loads(result)

        # Assert — generic message to client, without internal detail (fix #314)
        assert "error" in data
        assert "Fixer crashed" not in data["error"]
        assert "internal" in data["error"].lower() or "error" in data["error"].lower()

    def test_geo_fix_categoria_non_valida_ritorna_errore(self):
        """geo_fix con categoria 'only' non valida ritorna errore senza crash."""
        # Act
        result = geo_fix("https://example.com", only="robots,invalid_cat")
        data = json.loads(result)

        # Assert
        assert "error" in data
        assert "invalid_cat" in data["error"]

    @patch("geo_optimizer.core.llms_generator.discover_sitemap")
    def test_geo_llms_generate_eccezione_ritorna_errore(self, mock_discover):
        """geo_llms_generate gestisce eccezioni impreviste ritornando messaggio di errore."""
        # Arrange
        mock_discover.side_effect = RuntimeError("Sitemap parse error")

        # Act
        result = geo_llms_generate("https://example.com")

        # Assert: fix #329 — ritorna JSON con errore generico (no info leak)
        parsed = json.loads(result)
        assert "error" in parsed
        assert "Sitemap parse error" not in result  # l'eccezione interna NON viene esposta
