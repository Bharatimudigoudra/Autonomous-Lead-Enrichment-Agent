"""LangGraph agent graph: the model-driven flow that enriches company domains.

The pipeline is defined as a state graph instead of a fixed script:
  crawl -> extract -> (retry failed domains once) -> write output

The retry decision is made by a conditional edge, not by hardcoded
control flow in main.py - this is the agentic orchestration layer.
"""

import json
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from src.extractor import extract_lead
from src.models import ContactPoints, LeadEnrichment
from src.cleaner import build_llm_context
from src.crawler import scrape_domains
from src.contacts import enrich_contacts
from src.search import fill_linkedin_urls
from scripts.csv_export import write_csv
from scripts.json_export import next_available_path, write_json


class AgentState(TypedDict):
    domains: list[str]
    scrape_results: list[Any]
    enriched: list[LeadEnrichment]
    failed_domains: list[str]
    attempts: dict[str, int]
    output_path: str
    output_format: str


async def crawl_node(state: AgentState) -> AgentState:
    """Fetch and render each domain's pages (Playwright, dynamic navigation)."""
    state["scrape_results"] = await scrape_domains(state["domains"])
    state.setdefault("enriched", [])
    state.setdefault("failed_domains", [])
    state.setdefault("attempts", {})
    return state


def _enrich_one(result: Any) -> LeadEnrichment:
    context = build_llm_context(result.pages)
    item = extract_lead(result.domain, context, result.errors)
    item = enrich_contacts(item, result.pages)
    return fill_linkedin_urls(item)


def extract_node(state: AgentState) -> AgentState:
    """Run LLM extraction + contact enrichment for every unprocessed domain.

    Domains that failed a previous pass keep a placeholder record; those are
    re-processed here until they succeed or exhaust their retry attempts.
    """
    done = {item.domain for item in state["enriched"] if item.domain not in state["failed_domains"]}
    state["enriched"] = [i for i in state["enriched"] if i.domain not in state["failed_domains"]]
    for result in state["scrape_results"]:
        if result.domain in done:
            continue
        state["attempts"][result.domain] = state["attempts"].get(result.domain, 0) + 1
        print(f"[extract] {result.domain} ({len(result.pages)} pages fetched)")
        try:
            state["enriched"].append(_enrich_one(result))
            if result.domain in state["failed_domains"]:
                state["failed_domains"].remove(result.domain)
        except Exception as exc:
            state["failed_domains"].append(result.domain)
            state["enriched"].append(
                LeadEnrichment(
                    domain=result.domain,
                    company_overview="Enrichment could not be completed. See the errors field for details.",
                    target_audience=[],
                    contact_points=ContactPoints(),
                    key_leadership=[],
                    data_confidence_score=0.0,
                    source_urls=list(result.pages),
                    errors=[*result.errors, f"Extraction error: {type(exc).__name__}: {exc}"],
                )
            )
    return state


def should_retry(state: AgentState) -> str:
    """Conditional edge (pure - no state changes): retry failures once, then write."""
    retryable = [d for d in state["failed_domains"] if state["attempts"].get(d, 0) < 2]
    return "extract" if retryable else "write"


def write_node(state: AgentState) -> AgentState:
    """Write the enriched records to JSON (and/or CSV) without overwriting a past run."""
    raw = Path(state["output_path"])
    if raw.parent == Path("."):
        raw = Path("output") / raw
    records = [i.model_dump(mode="json") for i in state["enriched"]]
    fmt = state.get("output_format", "both")
    destination = None
    if fmt in ("json", "both"):
        destination = write_json(records, raw)
        print(f"Done. Wrote {len(records)} records to {destination.resolve()}")
    if fmt in ("csv", "both"):
        base = destination if destination is not None else next_available_path(raw.with_suffix(".csv"))
        csv_destination = base.with_suffix(".csv")
        write_csv(records, csv_destination)
        print(f"Done. Wrote {len(records)} records to {csv_destination.resolve()}")
    return state


def build_graph() -> Any:
    graph = StateGraph(AgentState)
    graph.add_node("crawl", crawl_node)
    graph.add_node("extract", extract_node)
    graph.add_node("write", write_node)
    graph.set_entry_point("crawl")
    graph.add_edge("crawl", "extract")
    graph.add_conditional_edges("extract", should_retry, {"extract": "extract", "write": "write"})
    graph.add_edge("write", END)
    return graph.compile()
