"""Bonus step: fill missing LinkedIn URLs for leaders using Tavily search.

If TAVILY_API_KEY is not set, this step quietly does nothing.
"""

import os

from pydantic import HttpUrl, TypeAdapter
from tavily import TavilyClient

from src.contacts import _profile_matches_person
from src.models import LeadEnrichment, LeadershipPerson

_HTTP_URL = TypeAdapter(HttpUrl)


def _search_linkedin(client: TavilyClient, person: LeadershipPerson, domain: str) -> str | None:
    """Search LinkedIn for one person. Return a profile URL or None."""
    company = domain.split(".")[0]
    query = f"{person.name} {person.role} {company} LinkedIn"
    try:
        result = client.search(query=query, include_domains=["linkedin.com"], max_results=3)
    except Exception:
        return None
    for hit in result.get("results", []):
        url = hit.get("url", "")
        if "linkedin.com/in/" not in url:
            continue
        # Search engines can return a teammate's profile for a name query.
        # Only accept a profile whose slug contains the person's surname.
        if _profile_matches_person(person, url):
            return url
    return None


def fill_linkedin_urls(item: LeadEnrichment) -> LeadEnrichment:
    """Fill linkedin_url for leaders where the website did not provide one."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or not item.key_leadership:
        return item

    client = TavilyClient(api_key=api_key)
    for person in item.key_leadership:
        if person.linkedin_url is None:
            url = _search_linkedin(client, person, item.domain)
            if url:
                # Validate into HttpUrl so the output schema stays clean.
                person.linkedin_url = _HTTP_URL.validate_python(url)
    return item
