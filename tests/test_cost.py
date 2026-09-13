from src.cost import summarize_cost
from src.models import LeadEnrichment


def _record(prompt: int, completion: int) -> LeadEnrichment:
    return LeadEnrichment(
        domain="x.com",
        company_overview="a. b.",
        data_confidence_score=0.5,
        token_usage={"prompt_tokens": prompt, "completion_tokens": completion,
                     "total_tokens": prompt + completion},
    )


def test_token_totals_without_prices(monkeypatch):
    monkeypatch.delenv("GROQ_PRICE_PER_1M_PROMPT", raising=False)
    monkeypatch.delenv("GROQ_PRICE_PER_1M_COMPLETION", raising=False)
    summary = summarize_cost([_record(100, 50), _record(200, 100)])
    assert summary["total_tokens"] == 450
    assert "estimated_cost_usd" not in summary  # never invent a dollar figure


def test_dollar_estimate_with_prices(monkeypatch):
    monkeypatch.setenv("GROQ_PRICE_PER_1M_PROMPT", "1.0")
    monkeypatch.setenv("GROQ_PRICE_PER_1M_COMPLETION", "2.0")
    summary = summarize_cost([_record(1_000_000, 1_000_000)])
    assert summary["estimated_cost_usd"] == 3.0
