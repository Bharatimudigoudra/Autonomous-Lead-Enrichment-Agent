"""Resilience: one bad domain must never crash the whole run."""
import asyncio
import json

from src.crawler import ScrapeResult
import main


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

    monkeypatch.setattr(main, "scrape_domains", fake_scrape)
    monkeypatch.setattr(main, "extract_lead", fake_extract)
    monkeypatch.setattr(main, "enrich_contacts", lambda item, pages: item)
    monkeypatch.setattr(main, "fill_linkedin_urls", lambda item: item)
    monkeypatch.setattr(main, "build_llm_context", lambda pages: "ctx")

    out = tmp_path / "output.json"
    asyncio.run(main.run(["good.com", "bad.com"], str(out)))
    records = json.loads(out.read_text())
    assert len(records) == 2
    assert records[0]["domain"] == "good.com"
    assert records[1]["domain"] == "bad.com"
    assert records[1]["data_confidence_score"] == 0.0
    assert any("Extraction error" in e for e in records[1]["errors"])


def test_next_available_path_never_overwrites(tmp_path):
    target = tmp_path / "output" / "output.json"
    first = main._next_available_path(target)
    assert first.name == "output.json"  # folder created, name unchanged
    first.write_text("[]")
    second = main._next_available_path(target)
    assert second.name == "output_1.json"
    second.write_text("[]")
    third = main._next_available_path(target)
    assert third.name == "output_2.json"
