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

## Windows setup (PowerShell in VS Code)

Install Python 3.11 or newer, open this folder in VS Code, then run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
Copy-Item .env.example .env
```

Open `.env` and replace the placeholder:

```text
GROQ_API_KEY=your_real_key_here
```

Get a key from the Groq console. Do not commit or share `.env`.

If PowerShell blocks activation, either use Command Prompt with `.venv\Scripts\activate.bat`, or run the virtual environment's Python directly. Administrator rights are not needed.

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

## Generate the real `sample_output.json`

The included `sample_output.json` is deliberately marked as example-format data because no API key is stored in this project. After adding your own key, generate genuine results for the required domains with:

```powershell
python main.py postman.com supabase.com vapi.ai --output sample_output.json
```

Review the file before submitting it. Website content changes, so output can vary between runs.

## Files

- `main.py`: reads command-line arguments, runs the pipeline, catches per-domain failures, and saves JSON.
- `scraper.py`: uses Playwright to render the homepage and useful subpages.
- `processor.py`: removes noisy HTML and converts the useful content to Markdown.
- `llm_extractor.py`: calls Groq in JSON mode and validates the response.
- `models.py`: defines the required data shape and confidence limits.
- `requirements.txt`: pins the Python packages.
- `.env.example`: shows the required environment variable without exposing a key.
- `sample_output.json`: example shape only until regenerated with a real key.

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
