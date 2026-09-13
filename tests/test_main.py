"""Resilience: one bad domain must never crash the whole run."""
import asyncio
import json

import src.graph as graph_module
from src.crawler import ScrapeResult
from scripts.json_export import next_available_path


def test_run_records_failure_and_continues(monkeypatch, tmp_path):
    good = ScrapeResult(domain="good.com", pages={"https://good.com/": "<html>ok</html>"})
    bad = ScrapeResult(domain="bad.com", pages={"https://bad.com/": "<html>ok</html>"})

    async def fake_scrape(domains):
        return [good, bad]

    def fake_extract(domain, context, errors):
        if domain == "bad.com":
            raise RuntimeError("Groq exploded")
        from src.models import LeadEnrichment
        return LeadEnrichment(domain=domain, company_overview="a. b.", data_confidence_score=0.5)

    monkeypatch.setattr(graph_module, "scrape_domains", fake_scrape)
    monkeypatch.setattr(graph_module, "extract_lead", fake_extract)
    monkeypatch.setattr(graph_module, "enrich_contacts", lambda item, pages: item)
    monkeypatch.setattr(graph_module, "fill_linkedin_urls", lambda item: item)
    monkeypatch.setattr(graph_module, "build_llm_context", lambda pages: "ctx")

    out = tmp_path / "output.json"
    agent = graph_module.build_graph()
    asyncio.run(agent.ainvoke({
        "domains": ["good.com", "bad.com"],
        "output_path": str(out),
        "output_format": "json",
    }))

    records = json.loads(out.read_text())
    assert len(records) == 2
    assert records[0]["domain"] == "good.com"
    assert records[1]["domain"] == "bad.com"
    assert records[1]["data_confidence_score"] == 0.0
    assert any("Extraction error" in e for e in records[1]["errors"])


def test_next_available_path_never_overwrites(tmp_path):
    target = tmp_path / "output" / "output.json"
    first = next_available_path(target)
    assert first.name == "output.json"  # folder created, name unchanged
    first.write_text("[]")
    second = next_available_path(target)
    assert second.name == "output_1.json"
    second.write_text("[]")
    third = next_available_path(target)
    assert third.name == "output_2.json"
