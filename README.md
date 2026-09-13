# Autonomous Lead Enrichment Agent

A small Python command-line project that visits company websites, cleans their rendered content, and asks Groq to return validated lead data.

## What it does

1. Opens each homepage with headless Chromium through Playwright.
2. Discovers relevant same-site links and also tries `/about`, `/team`, `/company`, `/contact`, and `/pricing`.
3. Removes scripts, CSS, SVG, navigation, footers, forms, cookie popups, and other page chrome.
4. Converts only the useful page body to clean Markdown. Raw HTML is never sent to Groq.
5. Calls `llama-3.3-70b-versatile` with JSON mode and validates the result with Pydantic.
6. Writes one JSON record per domain, including scrape errors and token usage.

A bad page or domain is recorded in `errors`; it does not crash the full run.

## Bonus: LinkedIn search enrichment (Tavily)

After extraction, search_enrichment.py checks each leader for a missing LinkedIn URL. If TAVILY_API_KEY is set in .env, it searches LinkedIn through the Tavily API (queries like "name role company LinkedIn") and fills in the first linkedin.com/in/ match. If the key is missing or the search fails, the step is skipped and the pipeline still completes - resilience by design.

## Windows setup (PowerShell in VS Code)

Install Python 3.11 or newer, open this folder in VS Code, then run:

```powershell
conda create -n GenAI python=3.11 -y
conda activate GenAI
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
```

Then create a file named `.env` and add:

```text
GROQ_API_KEY=your_real_key_here
TAVILY_API_KEY=your_key to .env
```

Get a key from the 'Groq console' and 'tavily.com'. Do not commit or share `.env`.

## Run

Run the three assignment domains:

```powershell
python main.py
```

This writes `output.json`.

Choose domains or an output filename:

```powershell
python main.py stripe.com notion.so --output my_leads.json
```

## Files

- `main.py`: reads command-line arguments, runs the pipeline, catches per-domain failures, and saves JSON.
- `scraper.py`: uses Playwright to render the homepage and useful subpages.
- `processor.py`: removes noisy HTML and converts the useful content to Markdown.
- `llm_extractor.py`: calls Groq in JSON mode and validates the response.
- `models.py`: defines the required data shape and confidence limits.
- `requirements.txt`: pins the Python packages.
- `.env`: shows the required environment variable without exposing a key.
- `search_enrichment.py`: uses Tavily search to fill in LinkedIn profile URLs for leaders the website didn't link.

## Design choices and limitations

- The scraper processes domains one at a time. This is slower than a complex parallel crawler, but easier to explain and gentler on websites.
- It keeps the homepage plus at most five subpages and caps cleaned input at 60,000 characters to control token use.
- Token counts are recorded from Groq. Exact currency cost is not calculated because free-tier limits and prices can change.
- `vapi.ai` and similar sites are JavaScript-heavy. Playwright renders JavaScript, waits briefly for network idle, and continues after a bounded wait if background requests never stop.
- Bot protection can still block an automated browser. The domain gets an error record instead of stopping the run.
- Public emails, leaders, and LinkedIn links are included only when the supplied page text supports them. Missing facts remain empty rather than being guessed.
- The model is asked for exactly two overview sentences. Pydantic validates types and ranges, while the prompt controls the sentence count.

## 2-3 minute walkthrough outline

1. Show `main.py`: domains come in, scraping runs, every result is cleaned and extracted, then JSON is saved.
2. Show `scraper.py`: a real headless browser loads JavaScript pages and finds relevant links.
3. Show `processor.py`: noisy tags are removed before Markdown conversion, so Groq never receives raw HTML.
4. Show `models.py` and `llm_extractor.py`: Groq returns JSON, Pydantic checks the structure, and usage tokens are saved.
5. Run `python main.py postman.com` and open `output.json`. Point out `source_urls`, `errors`, confidence, and token usage.
