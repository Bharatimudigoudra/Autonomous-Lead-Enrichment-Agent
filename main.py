"""Command-line entry point for the Autonomous Lead Enrichment Agent."""

import argparse
import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

from llm_extractor import extract_lead
from models import ContactPoints, LeadEnrichment
from processor import build_llm_context
from scraper import scrape_domains


DEFAULT_DOMAINS = ["postman.com", "supabase.com", "vapi.ai"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enrich company domains from their websites.")
    parser.add_argument("domains", nargs="*", default=DEFAULT_DOMAINS)
    parser.add_argument("--output", default="output.json", help="JSON output path")
    return parser.parse_args()


async def run(domains: list[str], output_path: str) -> None:
    scrape_results = await scrape_domains(domains)
    enriched: list[LeadEnrichment] = []

    for result in scrape_results:
        print(f"[extract] {result.domain} ({len(result.pages)} pages fetched)")
        try:
            context = build_llm_context(result.pages)
            item = extract_lead(result.domain, context, result.errors)
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

    destination = Path(output_path)
    destination.write_text(
        json.dumps([item.model_dump(mode="json") for item in enriched], indent=2),
        encoding="utf-8",
    )
    print(f"Done. Wrote {len(enriched)} records to {destination.resolve()}")


def main() -> None:
    load_dotenv()
    args = parse_args()
    asyncio.run(run(args.domains, args.output))


if __name__ == "__main__":
    main()
