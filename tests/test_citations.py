"""Tests for geo citations — one-shot AI citation check.

All LLM calls are mocked — zero real network calls.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

from click.testing import CliRunner

import geo_optimizer.core.citations as citations_mod
from geo_optimizer.cli.main import cli
from geo_optimizer.core.citations import normalize_domain, run_citation_check
from geo_optimizer.core.llm_client import LLMResponse


def _sonar_response(text: str, citations: list[str] | None = None) -> LLMResponse:
    return LLMResponse(text=text, model="sonar", provider="perplexity", citations=citations or [])


class TestNormalizeDomain:
    def test_bare_domain(self):
        assert normalize_domain("Example.com") == "example.com"

    def test_url_with_path(self):
        assert normalize_domain("https://www.example.com/page?q=1") == "example.com"

    def test_port_stripped(self):
        assert normalize_domain("example.com:8080") == "example.com"


class TestRunCitationCheck:
    def test_domain_cited_via_sonar_citations(self):
        with patch.object(citations_mod, "query_llm") as mock_q:
            mock_q.return_value = _sonar_response(
                "GeoReady is a popular GEO audit tool.",
                citations=["https://geoready.dev/guides/geo", "https://other.com/post"],
            )
            result = run_citation_check("GeoReady", "geoready.dev", provider="perplexity", api_key="pk-test")

        assert result.checked and result.skipped_reason is None
        assert result.queries_run == 3  # default templates
        assert result.domain_citation_rate == 1.0
        assert result.brand_mention_rate == 1.0
        assert result.verdict == "strong"
        # own domain excluded from competitor list
        assert all(d != "geoready.dev" for d, _ in result.top_cited_domains)
        assert ("other.com", 3) in result.top_cited_domains

    def test_mentioned_only_without_citation(self):
        with patch.object(citations_mod, "query_llm") as mock_q:
            mock_q.return_value = _sonar_response(
                "Acme is one option.", citations=["https://review-site.com/best-tools"]
            )
            result = run_citation_check("Acme", "acme.com", provider="perplexity", api_key="pk-test")

        assert result.domain_citation_rate == 0.0
        assert result.brand_mention_rate == 1.0
        assert result.verdict == "mentioned_only"

    def test_invisible(self):
        with patch.object(citations_mod, "query_llm") as mock_q:
            mock_q.return_value = _sonar_response("Try CompetitorX.", citations=["https://competitorx.com"])
            result = run_citation_check("Acme", "acme.com", provider="perplexity", api_key="pk-test")

        assert result.verdict == "invisible"

    def test_same_named_domain_not_counted_as_brand_mention(self):
        """A same-named but unrelated domain (geoready.app) must not inflate the
        brand mention rate for GeoReady (geoready.dev)."""
        with patch.object(citations_mod, "query_llm") as mock_q:
            mock_q.return_value = _sonar_response(
                "For this, check geoready.app — it covers the topic well.",
                citations=["https://geoready.app/post"],
            )
            result = run_citation_check("GeoReady", "geoready.dev", provider="perplexity", api_key="pk-test")

        assert result.brand_mention_rate == 0.0
        assert result.domain_citation_rate == 0.0
        assert result.verdict == "invisible"
        # the homonym is surfaced as a competitor domain, not as "you"
        assert ("geoready.app", 3) in result.top_cited_domains

    def test_brand_not_matched_inside_longer_word(self):
        """A short brand must not match as a substring of a longer word."""
        with patch.object(citations_mod, "query_llm") as mock_q:
            mock_q.return_value = _sonar_response("Acmecorp and Acmetech are unrelated firms.")
            result = run_citation_check("Acme", "acme.com", provider="perplexity", api_key="pk-test")

        assert result.brand_mention_rate == 0.0

    def test_brand_mention_at_sentence_end_still_counts(self):
        """A legitimate standalone mention ending a sentence still counts."""
        with patch.object(citations_mod, "query_llm") as mock_q:
            mock_q.return_value = _sonar_response("Many teams rely on Acme.")
            result = run_citation_check("Acme", "acme.com", provider="perplexity", api_key="pk-test")

        assert result.brand_mention_rate == 1.0

    def test_domain_cited_in_text_for_parametric_providers(self):
        """Providers without a citations list still count URLs in the answer text."""
        with patch.object(citations_mod, "query_llm") as mock_q:
            mock_q.return_value = LLMResponse(
                text="See https://www.acme.com/docs for details.", model="gpt-4o-mini", provider="openai"
            )
            result = run_citation_check("Acme", "acme.com", provider="openai", api_key="sk-test")

        assert result.domain_citation_rate == 1.0

    def test_custom_queries_override_templates(self):
        with patch.object(citations_mod, "query_llm") as mock_q:
            mock_q.return_value = _sonar_response("answer")
            result = run_citation_check(
                "Acme",
                "acme.com",
                queries=["best CRM?"],
                provider="perplexity",
                api_key="pk-test",
            )

        assert result.queries_run == 1
        assert mock_q.call_args[0][0] == "best CRM?"

    def test_no_provider_returns_skipped(self, monkeypatch):
        for var in (
            "PERPLEXITY_API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GROQ_API_KEY",
            "MINIMAX_API_KEY",
            "GEO_LLM_API_KEY",
            "GEO_LLM_PROVIDER",
        ):
            monkeypatch.delenv(var, raising=False)
        result = run_citation_check("Acme", "acme.com")
        assert result.skipped_reason is not None
        assert "MINIMAX_API_KEY" in result.skipped_reason

    def test_all_queries_error_returns_skipped(self):
        with patch.object(citations_mod, "query_llm") as mock_q:
            mock_q.return_value = LLMResponse(error="boom", provider="perplexity")
            result = run_citation_check("Acme", "acme.com", provider="perplexity", api_key="pk-test")

        assert result.skipped_reason is not None
        assert "boom" in result.skipped_reason


class TestResolveProvider:
    def test_prefers_perplexity_when_key_set(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pk-test")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("GEO_LLM_PROVIDER", raising=False)
        monkeypatch.delenv("GEO_LLM_API_KEY", raising=False)
        provider, key = citations_mod.resolve_provider()
        assert (provider, key) == ("perplexity", "pk-test")

    def test_explicit_provider_uses_its_env_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("GEO_LLM_API_KEY", raising=False)
        provider, key = citations_mod.resolve_provider("openai")
        assert (provider, key) == ("openai", "sk-test")

    def test_explicit_provider_without_key(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("GEO_LLM_API_KEY", raising=False)
        provider, key = citations_mod.resolve_provider("groq")
        assert provider == "groq" and key is None

    def test_explicit_minimax_provider_uses_its_env_key(self, monkeypatch):
        monkeypatch.setenv("MINIMAX_API_KEY", "minimax-test")
        monkeypatch.delenv("GEO_LLM_API_KEY", raising=False)
        provider, key = citations_mod.resolve_provider("minimax")
        assert (provider, key) == ("minimax", "minimax-test")


class TestCitationsCli:
    def test_cli_text_output(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pk-test")
        with patch.object(citations_mod, "query_llm") as mock_q:
            mock_q.return_value = _sonar_response("GeoReady leads the pack.", citations=["https://geoready.dev"])
            runner = CliRunner()
            result = runner.invoke(cli, ["citations", "--brand", "GeoReady", "--domain", "https://www.geoready.dev"])

        assert result.exit_code == 0
        assert "AI Citation Check" in result.output
        assert "STRONG" in result.output
        assert "geoready.dev" in result.output

    def test_cli_json_output(self, monkeypatch):
        import json

        monkeypatch.setenv("PERPLEXITY_API_KEY", "pk-test")
        with patch.object(citations_mod, "query_llm") as mock_q:
            mock_q.return_value = _sonar_response("answer", citations=["https://acme.com"])
            runner = CliRunner()
            result = runner.invoke(cli, ["citations", "--brand", "Acme", "--domain", "acme.com", "--format", "json"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["verdict"] == "strong"
        assert payload["domain"] == "acme.com"

    def test_cli_fails_without_any_key(self, monkeypatch):
        for var in (
            "PERPLEXITY_API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GROQ_API_KEY",
            "MINIMAX_API_KEY",
            "GEO_LLM_API_KEY",
            "GEO_LLM_PROVIDER",
        ):
            monkeypatch.delenv(var, raising=False)
        runner = CliRunner()
        result = runner.invoke(cli, ["citations", "--brand", "Acme", "--domain", "acme.com"])
        assert result.exit_code == 1
        assert "No AI provider configured" in result.output
        assert "MINIMAX_API_KEY" in result.output


class TestPerplexityProvider:
    def test_query_perplexity_parses_citations(self, monkeypatch):
        from geo_optimizer.core import llm_client

        fake_data = {
            "model": "sonar",
            "choices": [{"message": {"role": "assistant", "content": "Answer text"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 34},
            "citations": ["https://a.com/page"],
            "search_results": [
                {"title": "B", "url": "https://b.com/post"},
                {"title": "A", "url": "https://a.com/page"},
            ],
        }
        fake_resp = Mock(status_code=200)
        fake_resp.json.return_value = fake_data
        fake_resp.raise_for_status.return_value = None
        with patch("requests.post", return_value=fake_resp) as mock_post:
            resp = llm_client.query_llm("q", provider="perplexity", api_key="pk-test")

        assert resp.error is None
        assert resp.provider == "perplexity"
        assert resp.text == "Answer text"
        assert resp.citations == ["https://a.com/page", "https://b.com/post"]  # merged, deduped
        assert resp.prompt_tokens == 12
        sent = mock_post.call_args
        assert sent.kwargs["headers"]["Authorization"] == "Bearer pk-test"
        assert sent.kwargs["json"]["model"] == "sonar"

    def test_query_perplexity_http_error(self):
        import requests as requests_mod

        with patch("requests.post", side_effect=requests_mod.ConnectionError("down")):
            from geo_optimizer.core import llm_client

            resp = llm_client.query_llm("q", provider="perplexity", api_key="pk-test")

        assert resp.error is not None
        assert resp.provider == "perplexity"
