"""Command-line entry point for the Autonomous Lead Enrichment Agent.

Orchestration lives in src/graph.py (LangGraph). This file only parses
arguments and invokes the compiled agent graph.
"""

import argparse
import asyncio

from dotenv import load_dotenv

from src.graph import build_graph
from src.cost import summarize_cost

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
    parser.add_argument(
        "--format",
        choices=["json", "csv", "both"],
        default="both",
        help="Output format: json, csv, or both (default: both - CSV lands "
        "next to the JSON with the same name).",
    )
    return parser.parse_args()


async def run(domains: list[str], output_path: str, output_format: str) -> None:
    agent = build_graph()
    state = await agent.ainvoke(
        {"domains": domains, "output_path": output_path, "output_format": output_format}
    )
    cost = summarize_cost(state["enriched"])
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
    asyncio.run(run(args.domains, args.output, args.format))


if __name__ == "__main__":
    main()
