"""
Provider-agnostic LLM query client for GEO Optimizer.

Supports OpenAI, Anthropic, and Groq via optional dependencies.
Configuration via environment variables:
  GEO_LLM_PROVIDER  — openai | anthropic | groq (auto-detected if not set)
  GEO_LLM_API_KEY   — API key (falls back to provider-specific env vars)
  GEO_LLM_MODEL     — model name (provider default if not set)

Requires: pip install geo-optimizer-skill[llm]
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_LLM_TIMEOUT = 30  # seconds — prevent indefinite hangs on unresponsive providers

_PROVIDER_DEFAULTS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-20250514",
    "groq": "llama-3.3-70b-versatile",
}

_PROVIDER_ENV_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
}


@dataclass
class LLMResponse:
    """Response from an LLM query."""

    text: str = ""
    model: str = ""
    provider: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    error: str | None = None


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

    if not provider or not api_key:
        return LLMResponse(error="No LLM provider configured. Set GEO_LLM_API_KEY or OPENAI_API_KEY.")

    model = model or os.environ.get("GEO_LLM_MODEL", "") or _PROVIDER_DEFAULTS.get(provider, "")

    if provider == "openai":
        return _query_openai(prompt, system=system, api_key=api_key, model=model, max_tokens=max_tokens)
    if provider == "anthropic":
        return _query_anthropic(prompt, system=system, api_key=api_key, model=model, max_tokens=max_tokens)
    if provider == "groq":
        return _query_groq(prompt, system=system, api_key=api_key, model=model, max_tokens=max_tokens)

    return LLMResponse(error=f"Unknown provider: {provider}")


def _query_openai(prompt: str, *, system: str, api_key: str, model: str, max_tokens: int) -> LLMResponse:
    try:
        from openai import OpenAI
    except ImportError:
        return LLMResponse(error="openai not installed (pip install geo-optimizer-skill[llm])")

    try:
        client = OpenAI(api_key=api_key, timeout=_LLM_TIMEOUT)
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
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


def _query_groq(prompt: str, *, system: str, api_key: str, model: str, max_tokens: int) -> LLMResponse:
    try:
        from groq import Groq
    except ImportError:
        return LLMResponse(error="groq not installed (pip install groq)")

    try:
        client = Groq(api_key=api_key, timeout=_LLM_TIMEOUT)
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
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
