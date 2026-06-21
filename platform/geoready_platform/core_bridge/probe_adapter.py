"""Probe adapter: the only probe code that touches the engine.

Reuses the engine's LLM client (`query_llm`) and provider resolver
(`resolve_provider`) — no new model-provider abstraction. Calls the provider
once per generated prompt so we capture full per-response provenance (provider,
model, raw text, citation source URLs).

Default provider is whatever the engine resolves (Perplexity when its key is
set — real web-grounded answers). Provider/key may be overridden for tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProbeResponse:
    """Normalized single-prompt probe response with provenance."""

    prompt: str
    provider: str
    model: str
    text: str
    citations: list[str] = field(default_factory=list)
    error: str | None = None


def resolve_probe_provider(provider: str | None = None) -> tuple[str | None, str | None]:
    """Resolve (provider, api_key) using the engine's resolver."""
    from geo_optimizer.core.citations import resolve_provider

    return resolve_provider(provider)


def run_prompt(prompt: str, *, provider: str, api_key: str) -> ProbeResponse:
    """Query one prompt against the AI engine and normalize the response."""
    from geo_optimizer.core.llm_client import query_llm

    resp = query_llm(prompt, provider=provider, api_key=api_key)
    return ProbeResponse(
        prompt=prompt,
        provider=resp.provider or provider,
        model=resp.model or "",
        text=resp.text or "",
        citations=list(resp.citations or []),
        error=resp.error,
    )
