import pytest


@pytest.fixture
def sample_pages() -> dict[str, str]:
    """Minimal fetched pages the way crawler.scrape_domain returns them."""
    return {
        "https://example.com/": """
            <html><head><script>tracker()</script></head><body>
            <nav>menu links</nav>
            <main>
              <h1>ExampleCo</h1>
              <p>ExampleCo builds payment APIs for developers.</p>
              <a href="mailto:hello@example.com">Contact</a>
              <a href="https://www.linkedin.com/in/janedoe/">Jane on LinkedIn</a>
              <p>abuse@example.com privacy@example.com</p>
            </main>
            <footer>copyright</footer>
            </body></html>
        """
    }
