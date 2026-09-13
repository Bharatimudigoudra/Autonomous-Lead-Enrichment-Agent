# Autonomous Lead Enrichment Agent

Turns a list of company domains into structured, validated lead records:
company overview, target audience, public contact emails, key leadership with
LinkedIn profiles, a data-confidence score, source URLs, per-domain errors,
and token usage for every domain.

## Project structure

```
autonomous-lead-enrichment-agent/
├── main.py                      # entry point: takes domain list, runs the pipeline
├── src/
│   ├── __init__.py
│   ├── crawler.py               # Playwright browsing + subpage discovery
│   ├── cleaner.py               # HTML -> markdown, boilerplate stripping
│   ├── extractor.py             # LLM structured extraction (Groq JSON mode + Pydantic)
│   ├── models.py                # Pydantic schemas (spec-exact field names)
│   ├── contacts.py              # deterministic email/LinkedIn regex pass over raw HTML
│   ├── search.py                # Tavily LinkedIn backfill (bonus)
│   └── cost.py                  # token + $ cost tracking per run
├── tests/                       # pytest suite (13 tests)
├── output/
│   └── sample_output.json       # real run on the 3 target domains
├── json_to_csv.py               # converts output.json to a flat CSV
├── .env.example                 # GROQ_API_KEY / TAVILY_API_KEY (+ optional price vars)
├── .gitignore
├── pytest.ini
├── requirements.txt
└── README.md
```

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # then fill in your keys
```

Required environment variables (see `.env.example`):

- `GROQ_API_KEY` - free key from console.groq.com
- `TAVILY_API_KEY` - optional; enables the LinkedIn backfill bonus
- `GROQ_PRICE_PER_1M_PROMPT` / `GROQ_PRICE_PER_1M_COMPLETION` - optional;
  when set, the run summary also prints an estimated dollar cost

## Run

```bash
python main.py                                  # default 3 domains
python main.py stripe.com notion.so             # any domains
python main.py vapi.ai --output my_leads.json
python json_to_csv.py output.json               # optional CSV export
pytest -q                                       # run the test suite
```

## Design choices

- **Playwright, not requests**: most company sites render content with
  JavaScript, so a real headless browser is used. Each domain gets its own
  browser context for isolation.
- **Small LLM context**: the crawler keeps at most 6 pages per domain and the
  cleaner strips scripts, nav, footers and cookie banners before capping the
  context at 12k characters - this keeps token usage (and cost) predictable.
- **Deterministic contacts, LLM for judgment**: emails and LinkedIn links are
  verbatim facts on the page, so `contacts.py` reads them directly with regex
  and filters junk (`abuse@`, `privacy@`, asset-file false positives). The LLM
  is only asked for judgment work - overview, audience, leadership names -
  which removes a whole class of hallucinated contact data.
- **Validated output**: every LLM response is parsed as strict JSON and
  validated with Pydantic (confidence bounded 0-1, normalized emails). A bad
  response or a crashed domain produces a fallback record with
  `data_confidence_score: 0.0` and the reason in `errors` - one broken site
  never stops the batch.
- **Honest provenance**: each record carries the exact `source_urls` it was
  built from, the fetch `errors` encountered, and real `token_usage` from the
  API response. Cost in dollars is only reported when prices are configured -
  never invented.
- **Bonus: Tavily LinkedIn backfill**: when leadership names exist but the
  site doesn't link their profiles, `search.py` searches LinkedIn via Tavily
  and fills the URLs (validated as proper URLs before saving).

## Limitations

- JavaScript-heavy sites that block headless browsers return few or no pages;
  those domains land in `errors` with a low confidence score.
- Leadership extraction depends on companies actually publishing team info;
  many don't, so `key_leadership` is legitimately empty for some domains.
- The regex email pass can only find addresses companies chose to publish.
