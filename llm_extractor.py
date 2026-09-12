"""Ask Groq for structured facts and validate them with Pydantic."""

import json
import os

from groq import Groq
from pydantic import ValidationError

from models import LeadEnrichment


MODEL = "openai/gpt-oss-120b"


SYSTEM_PROMPT = """You extract B2B company facts from cleaned website text.
Return one valid JSON object only. Do not use outside knowledge and do not guess.
Use this exact shape:
{
  "domain": "string",
  "company_overview": "exactly two short sentences",
  "target_audience": ["specific audience or ICP"],
  "contact_points": {"public_emails": ["emails visibly present in sources"]},
  "key_leadership": [
    {"name": "string", "role": "string", "linkedin_url": "URL or null"}
  ],
  "data_confidence_score": 0.0,
  "source_urls": ["URLs supplied in the text"],
  "errors": [],
  "token_usage": {}
}
Only include leadership and LinkedIn URLs explicitly supported by the supplied pages.
Use empty lists when data is missing. Confidence should reflect source coverage and clarity.
"""


def extract_lead(domain: str, cleaned_context: str, scrape_errors: list[str]) -> LeadEnrichment:
    """Call Groq once for a domain, then validate the returned JSON."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to your .env file.")
    if not cleaned_context.strip():
        raise RuntimeError(f"No readable website content was collected for {domain}.")

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Domain: {domain}\n\nCLEANED WEBSITE SOURCES:\n{cleaned_context}",
            },
        ],
    )
    raw = response.choices[0].message.content or "{}"
    try:
        item = LeadEnrichment.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise RuntimeError(f"Groq returned invalid structured data for {domain}: {exc}") from exc

    item.domain = domain
    item.errors = list(dict.fromkeys([*item.errors, *scrape_errors]))
    usage = response.usage
    if usage:
        item.token_usage = {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        }
    return item
