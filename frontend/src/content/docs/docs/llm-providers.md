---
title: "geo citations: LLM Providers & API Setup"
description: "Configure API keys and regional endpoints for geo citations. Supported providers, model capabilities, wire formats and rate limits."
order: 17
---

`geo citations` asks a real AI answer engine the questions your customers ask, then checks
whether your brand is mentioned and your domain is cited as a source. It needs an API key for
whichever provider you want to query. This page covers provider-specific setup that doesn't fit
in the [README Quick Start](https://github.com/Auriti-Labs/geo-optimizer-skill#quick-start): wire formats, regional endpoints, and
model capabilities.

Perplexity is the recommended default (`PERPLEXITY_API_KEY`) because Perplexity Sonar returns
real web citation URLs, not just parametric knowledge. OpenAI, Anthropic, and Groq reveal what
the model already knows about your brand from training data, which is a different (and weaker)
signal — see the README's [Additional tools](https://github.com/Auriti-Labs/geo-optimizer-skill#additional-tools) section for the
distinction.

---

## MiniMax

MiniMax supports either wire format (OpenAI-compatible or Anthropic-compatible) and both a
global and a China API root:

```bash
export MINIMAX_API_KEY="your-api-key"
export MINIMAX_API_FORMAT="openai"  # or "anthropic"
export MINIMAX_API_BASE_URL="https://api.minimax.io/v1"
geo citations --provider minimax --brand "YourBrand" --domain yoursite.com
```

For the China endpoint, use `https://api.minimaxi.com/v1` with the `openai` format, or
`https://api.minimaxi.com/anthropic` with the `anthropic` format. The global messages-format root
is `https://api.minimax.io/anthropic`. The default model is `MiniMax-M3.1-Flash`.
`MINIMAX_THINKING` accepts `adaptive` or `disabled`; Flash normalizes either explicit
setting to `adaptive`, while M3 preserves the selected mode. Leaving it unset preserves
the API defaults: Flash adaptive; M3 adaptive on OpenAI and disabled on Anthropic.
Effort is not configured by this client, so Flash uses the API default (`max`).

Set `GEO_LLM_MODEL` to select M3 or an explicit custom/legacy model ID:

| Model | Context window | API input modalities | Thinking |
|-------|----------------|----------------------|----------|
| `MiniMax-M3.1-Flash` (default) | 1,000,000 tokens | Text, image, video | `adaptive` only |
| `MiniMax-M3` | 1,000,000 tokens | Text, image, video | `adaptive` or `disabled` |

`geo citations` currently sends text prompts only. The modalities column lists what each model's
API accepts; `query_llm` currently types text and image content parts, so video input needs a
schema addition before it can be passed. See the
[official MiniMax pricing page](https://platform.minimax.io/docs/pricing/overview) for current
rates.

---

## Gemini

Gemini is checked directly against the Gemini API, not just simulated via crawler user-agents:

```bash
export GEMINI_API_KEY="your-api-key"
geo citations --provider gemini --brand "YourBrand" --domain yoursite.com
```

Set `GEO_LLM_MODEL` to pick a specific model (default: `gemini-3.7-flash`). This calls
`generativelanguage.googleapis.com` directly, not Vertex AI, so no extra dependency is needed.

---

## DeepSeek

DeepSeek covers citation checks against the Chinese AI answer-engine ecosystem, which
Western-only providers miss entirely:

```bash
export DEEPSEEK_API_KEY="your-api-key"
geo citations --provider deepseek --brand "YourBrand" --domain yoursite.com
```

Fully OpenAI-compatible wire format against `api.deepseek.com`. Default model
`deepseek-v4-flash`; set `GEO_LLM_MODEL=deepseek-v4-pro` for the higher-capability tier.

---

## SerpBase (Google SERP + AI Overview)

Google AI Overviews isn't an LLM you can query — it's a SERP feature — so `--provider serpbase`
takes a different path from every other provider on this page: instead of asking a model a
question, it runs a real Google search via [serpbase.dev](https://serpbase.dev/docs) and checks
whether your brand appears in the organic results or the AI Overview block (when Google renders
one for the query), and whether your domain is among the cited sources.

```bash
export SERPBASE_API_KEY="your-api-key"
geo citations --provider serpbase --brand "YourBrand" --domain yoursite.com
```

Bring-your-own-key, pay-as-you-go: 100 free searches, then $0.30/1k
([pricing](https://serpbase.dev)). Never auto-detected — `SERPBASE_API_KEY` alone does nothing
unless `--provider serpbase` is passed explicitly, since it's a different kind of check (SERP
observation, not an LLM answer) and a paid one past the free tier.

Two things this provider does differently from the rest:

- **`--runs` is ignored.** A Google SERP isn't resampled the way a non-deterministic LLM answer
  is — asking again immediately would mostly return the same page, just at the cost of another
  API call. Every check is a single live snapshot per query.
- **The AI Overview block isn't always present.** Google only renders one for some queries, and
  serpbase's docs don't publish its internal field schema, so `ai_overview` is parsed
  defensively — a query without one still runs the citation check against the organic results,
  it just won't have an AI Overview signal to add. How often it actually surfaces is logged
  (`serpbase: AI Overview present in N/M queries`) rather than promised.
