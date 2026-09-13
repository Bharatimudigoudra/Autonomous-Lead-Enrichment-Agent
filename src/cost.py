"""Token and dollar cost tracking per domain and per run.

Token counts come from the Groq API response (stored on each record's
token_usage field). Dollar estimates need prices, which change over time,
so they are read from environment variables instead of being hard-coded:

    GROQ_PRICE_PER_1M_PROMPT=0.15     # dollars per 1M prompt tokens
    GROQ_PRICE_PER_1M_COMPLETION=0.60 # dollars per 1M completion tokens

If prices are not set, the summary reports tokens only - never a made-up
dollar figure.
"""

import os

from src.models import LeadEnrichment


def summarize_cost(records: list[LeadEnrichment]) -> dict:
    """Total the token usage across records; add dollars when prices exist."""
    prompt = sum(r.token_usage.get("prompt_tokens", 0) for r in records)
    completion = sum(r.token_usage.get("completion_tokens", 0) for r in records)
    summary: dict = {
        "domains": len(records),
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
    }
    try:
        prompt_price = float(os.getenv("GROQ_PRICE_PER_1M_PROMPT", "0"))
        completion_price = float(os.getenv("GROQ_PRICE_PER_1M_COMPLETION", "0"))
    except ValueError:
        prompt_price = completion_price = 0.0
    if prompt_price or completion_price:
        summary["estimated_cost_usd"] = round(
            prompt * prompt_price / 1_000_000
            + completion * completion_price / 1_000_000,
            6,
        )
    return summary
