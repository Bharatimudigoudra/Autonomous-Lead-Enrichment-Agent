"""Turn rendered HTML into compact, LLM-friendly Markdown."""

import re

from bs4 import BeautifulSoup
from markdownify import markdownify as to_markdown


REMOVE_TAGS = [
    "script", "style", "svg", "path", "noscript", "iframe", "canvas",
    "nav", "footer", "header", "form", "button",
]


def clean_html(html: str) -> str:
    """Remove page chrome and return readable Markdown, never raw HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(REMOVE_TAGS):
        tag.decompose()

    # Remove common cookie banners, popups, and repeated navigation containers.
    for tag in soup.find_all(attrs={"class": re.compile(r"cookie|popup|modal|navbar|menu", re.I)}):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.body or soup
    markdown = to_markdown(str(main), heading_style="ATX", bullets="-")
    markdown = re.sub(r"\n[ \t]+", "\n", markdown)
    markdown = re.sub(r"[ \t]{2,}", " ", markdown)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip()


def build_llm_context(pages: dict[str, str], max_chars: int = 12_000) -> str:
    """Label each source and enforce a predictable input-size ceiling."""
    sections: list[str] = []
    remaining = max_chars
    for url, html in pages.items():
        clean = clean_html(html)
        if not clean:
            continue
        section = f"SOURCE URL: {url}\n\n{clean}\n"
        section = section[:remaining]
        sections.append(section)
        remaining -= len(section)
        if remaining <= 0:
            break
    return "\n\n---\n\n".join(sections)
