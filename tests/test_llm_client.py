"""Tests for geo_optimizer.core.llm_client.

Provider-agnostic LLM client per OpenAI, Anthropic, Groq.
Tutto mockato — zero chiamate reali.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import Mock, patch

import pytest

import geo_optimizer.core.llm_client as llm_client


@pytest.fixture(autouse=True)
def _mock_openai_module(monkeypatch) -> None:
    """Mock openai completo."""
    fake = types.ModuleType("openai")
    fake.__path__ = ["/fake/openai"]

    class _OpenAI:
        def __init__(self, api_key: str, timeout: int) -> None:
            self.api_key = api_key
            self.timeout = timeout

        class chat:
            class completions:
                @staticmethod
                def create(model: str, messages: list, max_tokens: int) -> Mock:
                    mock_resp = Mock()
                    choice = Mock()
                    choice.message = Mock()
                    choice.message.configure_mock(content="OpenAI response")
                    mock_resp.choices = [choice]
                    mock_resp.model = model
                    mock_resp.usage = Mock(prompt_tokens=10, completion_tokens=5)
                    return mock_resp

    fake.OpenAI = _OpenAI
    fake.types = types.ModuleType("openai.types")
    fake.types.chat = types.ModuleType("openai.types.chat")
    fake.types.chat.ChatCompletionSystemMessageParam = Mock
    fake.types.chat.ChatCompletionUserMessageParam = Mock

    monkeypatch.setitem(sys.modules, "openai", fake)
    monkeypatch.setitem(sys.modules, "openai.types", fake.types)
    monkeypatch.setitem(sys.modules, "openai.types.chat", fake.types.chat)


@pytest.fixture(autouse=True)
def _mock_anthropic_module(monkeypatch) -> None:
    """Mock anthropic."""
    fake = types.ModuleType("anthropic")

    class _Anthropic:
        def __init__(self, api_key: str, timeout: int) -> None:
            self.api_key = api_key
            self.timeout = timeout

        class messages:
            @staticmethod
            def create(**kwargs) -> Mock:
                mock_resp = Mock()
                mock_resp.content = [Mock(text="Anthropic response")]
                mock_resp.model = kwargs.get("model", "claude-sonnet-4-20250514")
                mock_resp.usage = Mock(input_tokens=10, output_tokens=5)
                return mock_resp

    fake.Anthropic = _Anthropic
    monkeypatch.setitem(sys.modules, "anthropic", fake)


@pytest.fixture(autouse=True)
def _mock_groq_module(monkeypatch) -> None:
    """Mock groq (usa openai.types.chat come _query_groq)."""
    fake = types.ModuleType("groq")

    class _Groq:
        def __init__(self, api_key: str, timeout: int) -> None:
            self.api_key = api_key
            self.timeout = timeout

        class chat:
            class completions:
                @staticmethod
                def create(model: str, messages: list, max_tokens: int) -> Mock:
                    mock_resp = Mock()
                    choice = Mock()
                    choice.message = Mock()
                    choice.message.configure_mock(content="Groq response")
                    mock_resp.choices = [choice]
                    mock_resp.model = model
                    mock_resp.usage = Mock(prompt_tokens=10, completion_tokens=5)
                    return mock_resp

    fake.Groq = _Groq
    fake.types = types.ModuleType("groq.types")
    fake.types.chat = types.ModuleType("groq.types.chat")

    monkeypatch.setitem(sys.modules, "groq", fake)
    monkeypatch.setitem(sys.modules, "groq.types", fake.types)
    monkeypatch.setitem(sys.modules, "groq.types.chat", fake.types.chat)


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch) -> None:
    """Isola environment."""
    monkeypatch.delenv("GEO_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("GEO_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.delenv("MINIMAX_API_FORMAT", raising=False)
    monkeypatch.delenv("MINIMAX_API_BASE_URL", raising=False)
    monkeypatch.delenv("MINIMAX_THINKING", raising=False)
    monkeypatch.setenv("GEO_LLM_MODEL", "test-model")


# ─── Tests ────────────────────────────────────────────────────────────────────


class TestDetectProvider:
    """Test detect_provider()."""

    def test_detect_provider_openai_env(self, _mock_env, monkeypatch) -> None:
        """detect_provider con OPENAI_API_KEY (linee 54-63)."""
        monkeypatch.setenv("OPENAI_API_KEY", "env_key")
        provider, api_key = llm_client.detect_provider()
        assert provider == "openai"
        assert api_key == "env_key"

    def test_detect_provider_with_GEO_LLM_PROVIDER(self, _mock_env, monkeypatch) -> None:
        """detect_provider con GEO_LLM_PROVIDER + GEO_LLM_API_KEY (linee 57-58)."""
        monkeypatch.setenv("GEO_LLM_PROVIDER", "openai")
        monkeypatch.setenv("GEO_LLM_API_KEY", "explicit_key")
        provider, api_key = llm_client.detect_provider()
        assert provider == "openai"
        assert api_key == "explicit_key"

    def test_detect_provider_minimax_env(self, _mock_env, monkeypatch) -> None:
        """Detect MiniMax from MINIMAX_API_KEY."""
        monkeypatch.setenv("MINIMAX_API_KEY", "env_key")
        provider, api_key = llm_client.detect_provider()
        assert provider == "minimax"
        assert api_key == "env_key"


class TestQueryLLM:
    """Test query_llm()."""

    def test_query_llm_no_provider_and_no_key(self, _mock_env) -> None:
        """query_llm senza provider e senza API key (linee 95-98)."""
        resp = llm_client.query_llm("test")
        assert resp.error is not None
        assert "No LLM provider or API key configured" in resp.error

    def test_query_llm_no_provider_only(self, _mock_env) -> None:
        """query_llm con API key presente ma provider mancante (linee 99-100)."""
        resp = llm_client.query_llm("test", provider="", api_key="fake_key")
        assert resp.error is not None
        assert "No LLM provider specified" in resp.error

    def test_query_llm_no_api_key_only(self, _mock_env, monkeypatch) -> None:
        """query_llm con provider presente ma API key mancante (linee 101-102)."""
        monkeypatch.setenv("GEO_LLM_PROVIDER", "openai")
        resp = llm_client.query_llm("test", provider="openai", api_key="")
        assert resp.error is not None
        assert "No API key provided for provider 'openai'" in resp.error

    def test_query_llm_openai_import_error(self, _mock_env, monkeypatch) -> None:
        """query_llm con OpenAI non installato (ImportError 117-118)."""
        sys.modules.pop("openai", None)
        monkeypatch.setenv("OPENAI_API_KEY", "fake_key")
        resp = llm_client.query_llm("test", provider="openai", api_key="fake_key")
        assert resp.error is not None
        assert "openai not installed" in resp.error

    def test_query_llm_groq_import_error(self, _mock_env, monkeypatch) -> None:
        """query_llm con Groq non installato (ImportError 181-182)."""
        sys.modules.pop("groq", None)
        monkeypatch.setenv("GROQ_API_KEY", "fake_key")
        resp = llm_client.query_llm("test", provider="groq", api_key="fake_key")
        assert resp.error is not None
        assert "groq not installed" in resp.error
        assert "[dev]" in resp.error, "Groq ImportError message should reference geo-optimizer-skill[dev]"

    def test_query_llm_openai_success_with_system(self, _mock_env, monkeypatch) -> None:
        """OpenAI success con system param (linee 90-107, 120-135, 124)."""
        monkeypatch.setenv("OPENAI_API_KEY", "fake_key")
        resp = llm_client.query_llm("test", provider="openai", api_key="fake_key", system="system prompt")
        assert resp.text == "OpenAI response"
        assert resp.provider == "openai"

    def test_query_llm_anthropic_success_with_system(self, _mock_env, monkeypatch) -> None:
        """Anthropic success con system param (linee 102-103, 147-163, 151)."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake_key")
        resp = llm_client.query_llm("test", provider="anthropic", api_key="fake_key", system="system prompt")
        assert resp.text == "Anthropic response"
        assert resp.provider == "anthropic"

    def test_query_llm_groq_success(self, _mock_env, monkeypatch) -> None:
        """Groq success con system param (linee 104-105, 167-194, 104-107, 180)."""
        monkeypatch.setenv("GROQ_API_KEY", "groq_key")
        resp = llm_client.query_llm("test", provider="groq", api_key="groq_key", system="system prompt")
        assert resp.text == "Groq response"
        assert resp.provider == "groq"


class TestQueryMinimax:
    """Test MiniMax provider over plain HTTP."""

    def test_query_llm_minimax_success(self, _mock_env, monkeypatch) -> None:
        """Use the default model and current chat completion token field."""
        captured: dict = {}

        def _fake_post(url, headers, json, timeout):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            resp = Mock()
            resp.raise_for_status = Mock()
            resp.json = Mock(
                return_value={
                    "model": json["model"],
                    "choices": [{"message": {"content": "MiniMax response"}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                }
            )
            return resp

        monkeypatch.delenv("GEO_LLM_MODEL")
        monkeypatch.setattr("requests.post", _fake_post)
        resp = llm_client.query_llm("test", provider="minimax", api_key="fake_key", system="system prompt")
        assert resp.text == "MiniMax response"
        assert resp.provider == "minimax"
        assert resp.model == "MiniMax-M3"
        assert resp.prompt_tokens == 10
        assert resp.completion_tokens == 5
        assert captured["url"] == "https://api.minimax.io/v1/chat/completions"
        assert captured["headers"]["Authorization"] == "Bearer fake_key"
        assert captured["json"]["model"] == "MiniMax-M3"
        assert captured["json"]["messages"][0]["role"] == "system"
        assert captured["json"]["max_completion_tokens"] == 1024
        assert captured["json"]["reasoning_split"] is True
        assert "max_tokens" not in captured["json"]

    def test_query_llm_minimax_second_model_and_region(self, _mock_env, monkeypatch) -> None:
        """Pass the second supported model through a regional API root."""
        captured: dict = {}

        def _fake_post(url, headers, json, timeout):
            captured["url"] = url
            captured["json"] = json
            resp = Mock()
            resp.raise_for_status = Mock()
            resp.json = Mock(
                return_value={
                    "model": json["model"],
                    "choices": [{"message": {"content": "Regional response"}}],
                    "usage": {},
                }
            )
            return resp

        monkeypatch.setenv("MINIMAX_API_BASE_URL", "https://api.minimaxi.com/v1/")
        monkeypatch.setattr("requests.post", _fake_post)

        resp = llm_client.query_llm(
            "test",
            provider="minimax",
            api_key="fake_key",
            model="MiniMax-M2.7",
        )

        assert resp.text == "Regional response"
        assert resp.model == "MiniMax-M2.7"
        assert captured["url"] == "https://api.minimaxi.com/v1/chat/completions"
        assert captured["json"]["model"] == "MiniMax-M2.7"
        assert "thinking" not in captured["json"]

    def test_query_llm_minimax_anthropic_format(self, _mock_env, monkeypatch) -> None:
        """Build and parse the supported messages wire format."""
        captured: dict = {}

        def _fake_post(url, headers, json, timeout):
            captured["url"] = url
            captured["json"] = json
            resp = Mock()
            resp.raise_for_status = Mock()
            resp.json = Mock(
                return_value={
                    "model": "MiniMax-M3",
                    "content": [
                        {"type": "thinking", "thinking": "reasoning"},
                        {"type": "text", "text": "Messages response"},
                    ],
                    "usage": {"input_tokens": 12, "output_tokens": 7},
                }
            )
            return resp

        monkeypatch.setenv("MINIMAX_API_FORMAT", "anthropic")
        monkeypatch.setenv("MINIMAX_THINKING", "disabled")
        monkeypatch.setattr("requests.post", _fake_post)

        resp = llm_client.query_llm(
            "test",
            provider="minimax",
            api_key="fake_key",
            model="MiniMax-M3",
            system="system prompt",
        )

        assert resp.text == "Messages response"
        assert resp.prompt_tokens == 12
        assert resp.completion_tokens == 7
        assert captured["url"] == "https://api.minimax.io/anthropic/v1/messages"
        assert captured["json"]["system"] == "system prompt"
        assert captured["json"]["max_tokens"] == 1024
        assert "max_completion_tokens" not in captured["json"]
        assert captured["json"]["thinking"] == {"type": "disabled"}

        monkeypatch.setenv("MINIMAX_API_BASE_URL", "https://api.minimaxi.com/anthropic/")
        llm_client.query_llm("test", provider="minimax", api_key="fake_key")
        assert captured["url"] == "https://api.minimaxi.com/anthropic/v1/messages"

    def test_query_llm_minimax_rejects_invalid_format(self, _mock_env, monkeypatch) -> None:
        """Reject unsupported wire formats before sending a request."""
        monkeypatch.setenv("MINIMAX_API_FORMAT", "invalid")

        with patch("requests.post") as mock_post:
            resp = llm_client.query_llm("test", provider="minimax", api_key="fake_key")

        assert resp.error == "Invalid MINIMAX_API_FORMAT; expected 'openai' or 'anthropic'"
        assert resp.provider == "minimax"
        mock_post.assert_not_called()

    def test_query_llm_minimax_http_error(self, _mock_env) -> None:
        """Return HTTP errors in LLMResponse.error."""
        import requests as requests_mod

        with patch("requests.post", side_effect=requests_mod.ConnectionError("down")):
            resp = llm_client.query_llm("test", provider="minimax", api_key="fake_key")

        assert resp.error is not None
        assert resp.provider == "minimax"
