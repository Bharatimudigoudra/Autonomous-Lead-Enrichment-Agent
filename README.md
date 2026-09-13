# Autonomous Lead Enrichment Agent

An autonomous agent that takes any company website, crawls it like a human would, and returns a structured, validated lead records: company overview, target audience, public contact emails, key leadership with LinkedIn profiles, a data-confidence score, source URLs, per-domain errors, and token usage for every domain.

The pipeline is orchestrated with **LangGraph** - crawl, extract, self-retry and write run as explicit graph nodes, so the control flow is inspectable and easy to extend.

## Why this project

Sales and recruiting teams spend hours manually researching companies. This agent collapses that to one command: point it at a URL, get back decision-ready lead data. Built to demonstrate agentic AI skills: multi-step planning, tool use, structured LLM extraction, self-correction on failure, and observable, cost-tracked runs.

## Features

- **Dynamic web crawling** - Playwright (headless Chromium) renders JavaScript-heavy sites and navigates multi-page flows, not just static HTML
- **LangGraph orchestration** - the pipeline is an explicit state graph (crawl -> extract -> conditional retry -> write), so control flow is inspectable and extensible
- **Structured LLM extraction** - Groq-hosted open models (gpt-oss-120b) extract a typed lead record; output is validated against Pydantic models
- **Self-correction** - failed or empty extractions are retried automatically via a conditional graph edge; persistent failures are recorded honestly in an `errors` field instead of crashing the run
- **Dual output formats** - every run writes JSON and/or CSV (`--format json|csv|both`), with auto-numbered filenames to avoid overwriting
- **Cost observability** - token usage per run is logged so LLM spend is visible, not a black box

## Workflow Architecture

```
                         +-------------------+
   target URL ---------> |   CRAWL NODE      |
   (CLI arg)             |  Playwright headless browser
                         |  renders pages, follows links,
                         |  collects visible text + links
                         +---------+---------+
                                   |  state.raw_pages
                                   v
                         +-------------------+
                         |   EXTRACT NODE    |
                         |  Groq LLM (gpt-oss-120b)
                         |  structured extraction ->
                         |  validated Pydantic lead record
                         +---------+---------+
                                   |
                         +---------v---------+
                         |  ROUTER (pure)    |<------------------+
                         |  extraction ok?   |                   |
                         +--+-----------+----+                   |
                    success |           | failed / empty          |
                            |           | retries left            |
                            |           +-------------------------+
                            v                        (loop back to EXTRACT)
                         +-------------------+
                         |   WRITE NODE      |
                         |  scripts/json_export.py -> output.json
                         |  scripts/csv_export.py  -> output.csv
                         |  errors recorded if retries exhausted
                         +-------------------+
```

Each run is a single LangGraph `StateGraph` execution:

1. **crawl** - Playwright fetches and renders the target site, gathering text and candidate links
2. **extract** - the LLM converts page text into a validated `LeadRecord` (Pydantic schema)
3. **should_retry** (conditional edge) - pure routing function; on failure with retries remaining, control loops back to `extract`
4. **write** - results are exported to JSON and/or CSV; unrecoverable failures produce a placeholder record carrying the real error list

## Project Structure

```
autonomous-lead-enrichment-agent/
├── main.py                      # entry point: takes domain list, runs the pipeline
├── src/
│   ├── __init__.py
│   ├── graph.py                 # LangGraph StateGraph: crawl -> extract -> retry -> write
│   ├── crawler.py               # Playwright browsing + subpage discovery
│   ├── cleaner.py               # HTML -> markdown, boilerplate stripping
│   ├── extractor.py             # LLM structured extraction (Groq JSON mode + Pydantic)
│   ├── models.py                # Pydantic schemas (spec-exact field names)
│   ├── contacts.py              # deterministic email/LinkedIn regex pass over raw HTML
│   ├── search.py                # Tavily LinkedIn backfill (bonus)
│   └── cost.py                  # token + $ cost tracking per run
├── scripts/
│   ├── json_export.py           # JSON writer (+ auto-numbered filenames)
│   └── csv_export.py            # CSV writer (flat records)
├── tests/                       # pytest suite (13 tests)
├── output/
│   └── output.json              # real run on the 3 target domains
├── .env.example                 # GROQ_API_KEY / TAVILY_API_KEY (+ optional price vars)
├── .gitignore
├── pytest.ini
├── requirements.txt
└── README.md
```

## Setup

```bash
git clone https://github.com/Bharatimudigoudra/Autonomous-Lead-Enrichment-Agent.git
cd Autonomous-Lead-Enrichment-Agent
pip install -r requirements.txt
playwright install chromium
```

*Set your API keys*

Copy .env.example to a new file named .env and fill in the values:

- `GROQ_API_KEY` - required. Get a free key at console.groq.com
- `TAVILY_API_KEY` - optional. Enables the LinkedIn backfill bonus
- `GROQ_PRICE_PER_1M_PROMPT` / `GROQ_PRICE_PER_1M_COMPLETION` - optional. When set, the run summary also prints the estimated dollar cost


## Usage

```bash
# default 3 domains
python main.py

# try with any company domain names
python main.py zoho.com freshworks.com

# save the results with custom filename (extension added automatically) and specified format
python main.py vapi.ai --output my_file_1 --format json

# run the test suite (optional)
pytest -q
```

## Output

**JSON** - one record per run: company profile, industry, offerings, contact signals, source URLs, token usage, and an `errors` array when retries were exhausted.

**CSV** - flat row-per-record export for spreadsheets and CRM import.

## Error Handling

The agent never dies silently:

- transient extraction failures trigger an automatic retry through the graph's conditional edge
- persistent failures (rate limits, unreachable sites) are captured in the record's `errors` field with the real exception text
- token budgets are logged per run so quota exhaustion is diagnosable from the output itself

## Tech Stack

| Layer | Choice |
|---|---|
| Orchestration | LangGraph (StateGraph, conditional edges) |
| Browser | Playwright (headless Chromium) |
| LLM | Groq - openai/gpt-oss-120b |
| Validation | Pydantic |
| Language | Python 3.11+ |

## Roadmap

- [ ] Batch mode: crawl a list of URLs in one run
- [ ] Contact verification via public email patterns
- [ ] Streamlit dashboard for non-CLI users

