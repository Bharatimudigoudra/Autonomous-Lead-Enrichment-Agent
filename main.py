"""Command-line entry point for the Autonomous Lead Enrichment Agent."""

import argparse
import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

from src.extractor import extract_lead
from src.models import ContactPoints, LeadEnrichment
from src.cleaner import build_llm_context
from src.crawler import scrape_domains
from src.contacts import enrich_contacts
from src.cost import summarize_cost
from src.search import fill_linkedin_urls


DEFAULT_DOMAINS = ["postman.com", "supabase.com", "vapi.ai"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enrich company domains from their websites.")
    parser.add_argument("domains", nargs="*", default=DEFAULT_DOMAINS)
    parser.add_argument(
        "--output",
        default="output/output.json",
        help="JSON output path (existing files are never overwritten; "
        "output_1.json, output_2.json, ... are created instead)",
    )
    return parser.parse_args()


def _next_available_path(path: Path) -> Path:
    """Never overwrite an existing run: output.json -> output_1.json -> ..."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        return path
    counter = 1
    while True:
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


async def run(domains: list[str], output_path: str) -> None:
    scrape_results = await scrape_domains(domains)
    enriched: list[LeadEnrichment] = []

    for result in scrape_results:
        print(f"[extract] {result.domain} ({len(result.pages)} pages fetched)")
        try:
            context = build_llm_context(result.pages)
            item = extract_lead(result.domain, context, result.errors)
            item = enrich_contacts(item, result.pages)
            item = fill_linkedin_urls(item)
        except Exception as exc:
            # Record a failed domain and continue processing the rest.
            item = LeadEnrichment(
                domain=result.domain,
                company_overview="Enrichment could not be completed. See the errors field for details.",
                target_audience=[],
                contact_points=ContactPoints(),
                key_leadership=[],
                data_confidence_score=0.0,
                source_urls=list(result.pages),
                errors=[*result.errors, f"Extraction error: {type(exc).__name__}: {exc}"],
            )
        enriched.append(item)

    raw = Path(output_path)
    if raw.parent == Path("."):
        # A bare filename (e.g. --output my_leads.json) belongs in output/.
        raw = Path("output") / raw
    destination = _next_available_path(raw)
    destination.write_text(
        json.dumps([item.model_dump(mode="json") for item in enriched], indent=2),
        encoding="utf-8",
    )
    cost = summarize_cost(enriched)
    print(f"Done. Wrote {len(enriched)} records to {destination.resolve()}")
    token_line = (
        f"[cost] {cost['total_tokens']} tokens "
        f"({cost['prompt_tokens']} prompt + {cost['completion_tokens']} completion)"
    )
    if "estimated_cost_usd" in cost:
        token_line += f" - about ${cost['estimated_cost_usd']:.4f}"
    print(token_line)


def main() -> None:
    load_dotenv()
    args = parse_args()
    asyncio.run(run(args.domains, args.output))


if __name__ == "__main__":
    main()
