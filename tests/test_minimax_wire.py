"""Verify serialized MiniMax requests without network inference."""

from __future__ import annotations

import json

import pytest
import requests

from geo_optimizer.core.llm_client import query_llm


@pytest.mark.parametrize("api_format", ["openai", "anthropic"])
@pytest.mark.parametrize("host", ["api.minimax.io", "api.minimaxi.com"])
@pytest.mark.parametrize("model", ["MiniMax-M3.1-Flash", "MiniMax-M3", "MiniMax-M2.7", "custom-model"])
@pytest.mark.parametrize("thinking", ["", "adaptive", "disabled"])
def test_minimax_serialized_request_contract(monkeypatch, api_format, host, model, thinking):
    root = "v1" if api_format == "openai" else "anthropic"
    path = "chat/completions" if api_format == "openai" else "v1/messages"
    monkeypatch.setenv("MINIMAX_API_FORMAT", api_format)
    monkeypatch.setenv("MINIMAX_API_BASE_URL", f"https://{host}/{root}/")
    monkeypatch.setenv("MINIMAX_THINKING", thinking)
    monkeypatch.setenv("GEO_LLM_MODEL", model)
    captured = {}

    def send(session, request, **kwargs):
        captured["url"] = request.url
        captured["body"] = json.loads(request.body)
        captured["headers"] = request.headers
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps(
            {
                "model": model,
                "choices": [{"message": {"content": "answer", "reasoning_content": "reasoning"}}],
                "content": [{"type": "thinking", "thinking": "reasoning"}, {"type": "text", "text": "answer"}],
                "usage": {},
            }
        ).encode()
        return response

    monkeypatch.setattr(requests.Session, "send", send)
    result = query_llm("question", provider="minimax", api_key="test-key", system="system", max_tokens=2048)
    body = captured["body"]
    assert result.error is None
    assert result.text == "answer"
    assert result.model == model
    assert captured["url"] == f"https://{host}/{root}/{path}"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert body["model"] == model
    if thinking:
        expected = "adaptive" if model == "MiniMax-M3.1-Flash" else thinking
        assert body["thinking"] == {"type": expected}
    else:
        assert "thinking" not in body
    assert "reasoning_effort" not in body
    assert "service_tier" not in body
    if api_format == "openai":
        assert body["max_completion_tokens"] == 2048
        assert body["reasoning_split"] is True
    else:
        assert body["max_tokens"] == 2048
        assert "reasoning_split" not in body


@pytest.mark.parametrize("thinking", ["enabled", "none", "invalid"])
def test_minimax_rejects_invalid_thinking_before_http(monkeypatch, thinking):
    monkeypatch.setenv("MINIMAX_THINKING", thinking)
    monkeypatch.delenv("GEO_LLM_MODEL", raising=False)
    monkeypatch.setattr(requests.Session, "send", lambda *a, **kw: pytest.fail("unexpected HTTP"))
    result = query_llm("question", provider="minimax", api_key="test-key")
    assert result.error == "Invalid MINIMAX_THINKING; expected 'adaptive' or 'disabled'"
