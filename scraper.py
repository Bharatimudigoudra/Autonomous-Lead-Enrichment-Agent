"""Fetch company pages in a real headless browser."""

import asyncio
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from playwright.async_api import Browser, Page, TimeoutError as PlaywrightTimeoutError


PAGE_HINTS = ("about", "team", "company", "contact", "pricing", "leadership")
DIRECT_PATHS = ("/about", "/team", "/company", "/contact", "/pricing")


@dataclass
class ScrapeResult:
    domain: str
    pages: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


async def _fetch(page: Page, url: str, timeout_ms: int) -> tuple[str | None, str | None]:
    """Return rendered HTML, or an error string instead of raising."""
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        if response and response.status >= 400:
            return None, f"{url}: HTTP {response.status}"
        # Give client-side JavaScript a short, bounded chance to render.
        try:
            await page.wait_for_load_state("networkidle", timeout=5_000)
        except PlaywrightTimeoutError:
            pass
        html = await page.content()
        if len(html) < 200:
            return None, f"{url}: page returned too little content"
        return html, None
    except PlaywrightTimeoutError:
        return None, f"{url}: timed out"
    except Exception as exc:  # one broken site must not stop other domains
        return None, f"{url}: {type(exc).__name__}: {exc}"


async def scrape_domain(browser: Browser, domain: str, timeout_ms: int = 20_000) -> ScrapeResult:
    """Fetch the homepage and a small set of relevant same-domain pages."""
    domain = domain.strip().lower().removeprefix("https://").removeprefix("http://").strip("/")
    result = ScrapeResult(domain=domain)
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
        ),
        viewport={"width": 1440, "height": 1000},
    )
    page = await context.new_page()
    try:
        homepage = f"https://{domain}/"
        html, error = await _fetch(page, homepage, timeout_ms)
        if error:
            # Some older sites still only answer over HTTP.
            homepage = f"http://{domain}/"
            html, second_error = await _fetch(page, homepage, timeout_ms)
            if second_error:
                result.errors.extend([error, second_error])
                return result
        assert html is not None
        final_home_url = page.url
        result.pages[final_home_url] = html

        # Discover useful links from the rendered homepage.
        discovered = await page.locator("a[href]").evaluate_all(
            "els => els.map(a => ({href: a.href, text: (a.innerText || '').trim()}))"
        )
        home_host = urlparse(final_home_url).netloc.removeprefix("www.")
        candidates: list[str] = []
        for item in discovered:
            href = item.get("href", "")
            label = f"{href} {item.get('text', '')}".lower()
            parsed = urlparse(href)
            same_site = parsed.netloc.removeprefix("www.") == home_host
            if same_site and any(hint in label for hint in PAGE_HINTS):
                candidates.append(href.split("#")[0])

        # Direct paths are useful when the homepage menu hides links behind scripts.
        candidates.extend(urljoin(final_home_url, path) for path in DIRECT_PATHS)
        unique_candidates = list(dict.fromkeys(candidates))[:10]

        # Keep at most five useful subpages so LLM input stays small and cheap.
        for url in unique_candidates:
            if len(result.pages) >= 6:
                break
            sub_html, sub_error = await _fetch(page, url, timeout_ms)
            if sub_error:
                result.errors.append(sub_error)
            elif sub_html is not None:
                result.pages[page.url] = sub_html
    finally:
        await context.close()
    return result


async def scrape_domains(domains: list[str]) -> list[ScrapeResult]:
    """Use one browser process but isolate every company in its own context."""
    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            results = []
            for domain in domains:
                print(f"[scrape] {domain}")
                results.append(await scrape_domain(browser, domain))
            return results
        finally:
            await browser.close()
