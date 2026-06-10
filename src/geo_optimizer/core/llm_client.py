"""
Provider-agnostic LLM query client for GEO Optimizer.

Supports OpenAI, Anthropic, Groq (optional dependencies) and Perplexity
(uses the core `requests` dependency, no extra needed).
Configuration via environment variables:
  GEO_LLM_PROVIDER  — openai | anthropic | groq | perplexity (auto-detected if not set)
  GEO_LLM_API_KEY   — API key (falls back to provider-specific env vars)
  GEO_LLM_MODEL     — model name (provider default if not set)

Requires: pip install geo-optimizer-skill[llm] (except Perplexity)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_LLM_TIMEOUT = 30  # seconds — prevent indefinite hangs on unresponsive providers

_PROVIDER_DEFAULTS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-20250514",
    "groq": "llama-3.3-70b-versatile",
    "perplexity": "sonar",
}

# Perplexity is listed last so adding its key does not silently change the
# auto-detected provider for users who already configured another one.
_PROVIDER_ENV_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
}

_PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


@dataclass
class LLMResponse:
    """Response from an LLM query."""

    text: str = ""
    model: str = ""
    provider: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    error: str | None = None
    # Source URLs returned by answer engines that ground responses in live
    # web search (Perplexity Sonar). Empty for parametric-only providers.
    citations: list[str] = field(default_factory=list)


def detect_provider() -> tuple[str | None, str | None]:
    """Auto-detect LLM provider from environment variables.

    Returns:
        (provider_name, api_key) or (None, None) if no provider configured.
    """
    explicit = os.environ.get("GEO_LLM_PROVIDER", "").lower()
    explicit_key = os.environ.get("GEO_LLM_API_KEY", "")

    if explicit and explicit_key:
        return explicit, explicit_key

    for provider, env_key in _PROVIDER_ENV_KEYS.items():
        key = os.environ.get(env_key, "")
        if key:
            return provider, key

    return None, None


def query_llm(
    prompt: str,
    *,
    system: str = "",
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    max_tokens: int = 1024,
) -> LLMResponse:
    """Send a prompt to an LLM and return the response.

    Args:
        prompt: User message to send.
        system: Optional system message.
        provider: LLM provider (auto-detected if not set).
        api_key: API key (auto-detected if not set).
        model: Model name (provider default if not set).
        max_tokens: Maximum response tokens.

    Returns:
        LLMResponse with text and metadata, or error if unavailable.
    """
    if provider is None or api_key is None:
        detected_provider, detected_key = detect_provider()
        provider = provider or detected_provider
        api_key = api_key or detected_key

    if not provider and not api_key:
        return LLMResponse(
            error="No LLM provider or API key configured. Set GEO_LLM_PROVIDER and GEO_LLM_API_KEY, or set a provider-specific key such as OPENAI_API_KEY."
        )
    if not provider:
        return LLMResponse(error="No LLM provider specified. Set GEO_LLM_PROVIDER or pass provider explicitly.")
    if not api_key:
        return LLMResponse(
            error=f"No API key provided for provider '{provider}'. Set GEO_LLM_API_KEY or the provider-specific API key."
        )

    model = model or os.environ.get("GEO_LLM_MODEL", "") or _PROVIDER_DEFAULTS.get(provider, "")

    if provider == "openai":
        return _query_openai(prompt, system=system, api_key=api_key, model=model, max_tokens=max_tokens)
    if provider == "anthropic":
        return _query_anthropic(prompt, system=system, api_key=api_key, model=model, max_tokens=max_tokens)
    if provider == "groq":
        return _query_groq(prompt, system=system, api_key=api_key, model=model, max_tokens=max_tokens)
    if provider == "perplexity":
        return _query_perplexity(prompt, system=system, api_key=api_key, model=model, max_tokens=max_tokens)

    return LLMResponse(error=f"Unknown provider: {provider}")


def _query_openai(prompt: str, *, system: str, api_key: str, model: str, max_tokens: int) -> LLMResponse:
    try:
        from openai import OpenAI
        from openai.types.chat import (
            ChatCompletionSystemMessageParam,
            ChatCompletionUserMessageParam,
        )
    except ImportError:
        return LLMResponse(error="openai not installed (pip install geo-optimizer-skill[llm])")

    try:
        client = OpenAI(api_key=api_key, timeout=_LLM_TIMEOUT)
        messages: list[ChatCompletionSystemMessageParam | ChatCompletionUserMessageParam] = []
        if system:
            messages.append(ChatCompletionSystemMessageParam(role="system", content=system))
        messages.append(ChatCompletionUserMessageParam(role="user", content=prompt))
        resp = client.chat.completions.create(model=model, messages=messages, max_tokens=max_tokens)
        choice = resp.choices[0]
        usage = resp.usage
        return LLMResponse(
            text=choice.message.content or "",
            model=resp.model,
            provider="openai",
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
        )
    except Exception as exc:
        logger.warning("OpenAI query failed: %s: %s", type(exc).__name__, exc)
        return LLMResponse(error=f"{type(exc).__name__}: {exc}", provider="openai", model=model)


def _query_anthropic(prompt: str, *, system: str, api_key: str, model: str, max_tokens: int) -> LLMResponse:
    try:
        from anthropic import Anthropic
    except ImportError:
        return LLMResponse(error="anthropic not installed (pip install geo-optimizer-skill[llm])")

    try:
        client = Anthropic(api_key=api_key, timeout=_LLM_TIMEOUT)
        kwargs: dict = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
        if system:
            kwargs["system"] = system
        resp = client.messages.create(**kwargs)
        text = resp.content[0].text if resp.content else ""
        return LLMResponse(
            text=text,
            model=resp.model,
            provider="anthropic",
            prompt_tokens=resp.usage.input_tokens if resp.usage else 0,
            completion_tokens=resp.usage.output_tokens if resp.usage else 0,
        )
    except Exception as exc:
        logger.warning("Anthropic query failed: %s: %s", type(exc).__name__, exc)
        return LLMResponse(error=f"{type(exc).__name__}: {exc}", provider="anthropic", model=model)


def _query_perplexity(prompt: str, *, system: str, api_key: str, model: str, max_tokens: int) -> LLMResponse:
    """Query Perplexity Sonar via plain HTTP (OpenAI-compatible, returns web citations)."""
    import requests

    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = requests.post(
            _PERPLEXITY_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "max_tokens": max_tokens},
            timeout=_LLM_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        usage = data.get("usage") or {}
        # Sonar exposes sources both as a flat `citations` list and as
        # structured `search_results`; merge them preserving order.
        citations = list(data.get("citations") or [])
        for result in data.get("search_results") or []:
            url = result.get("url", "")
            if url and url not in citations:
                citations.append(url)
        return LLMResponse(
            text=(choice.get("message") or {}).get("content", ""),
            model=data.get("model", model),
            provider="perplexity",
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            citations=citations,
        )
    except Exception as exc:
        logger.warning("Perplexity query failed: %s: %s", type(exc).__name__, exc)
        return LLMResponse(error=f"{type(exc).__name__}: {exc}", provider="perplexity", model=model)


def _query_groq(prompt: str, *, system: str, api_key: str, model: str, max_tokens: int) -> LLMResponse:
    try:
        from groq import Groq
        from openai.types.chat import (
            ChatCompletionSystemMessageParam,
            ChatCompletionUserMessageParam,
        )
    except ImportError:
        return LLMResponse(error="groq not installed (pip install geo-optimizer-skill[dev])")

    try:
        client = Groq(api_key=api_key, timeout=_LLM_TIMEOUT)
        messages: list[ChatCompletionSystemMessageParam | ChatCompletionUserMessageParam] = []
        if system:
            messages.append(ChatCompletionSystemMessageParam(role="system", content=system))
        messages.append(ChatCompletionUserMessageParam(role="user", content=prompt))
        resp = client.chat.completions.create(model=model, messages=messages, max_tokens=max_tokens)
        choice = resp.choices[0]
        usage = resp.usage
        return LLMResponse(
            text=choice.message.content or "",
            model=resp.model,
            provider="groq",
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
        )
    except Exception as exc:
        logger.warning("Groq query failed: %s: %s", type(exc).__name__, exc)
        return LLMResponse(error=f"{type(exc).__name__}: {exc}", provider="groq", model=model)
