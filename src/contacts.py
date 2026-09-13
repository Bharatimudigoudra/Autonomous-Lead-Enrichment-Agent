"""Deterministic contact discovery: read emails and LinkedIn links straight
from the raw HTML we already fetched.

This runs alongside the LLM pass on purpose. Emails and profile links are
verbatim facts on the page, so we read them directly instead of asking a
model to recall them. The LLM handles judgment (overview, audience,
leadership); this module handles contact data, with junk filtered out.
"""

import re

from pydantic import HttpUrl, TypeAdapter

from src.models import LeadEnrichment, LeadershipPerson

_HTTP_URL = TypeAdapter(HttpUrl)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
LINKEDIN_PROFILE_RE = re.compile(
    r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/in/[A-Za-z0-9\-_%]+/?"
)

# Technically valid addresses that are useless as sales contact points.
JUNK_LOCAL_PARTS = {
    "abuse", "privacy", "legal", "dmca", "security", "noreply", "no-reply",
    "donotreply", "do-not-reply", "postmaster", "webmaster", "unsubscribe",
    "mailer-daemon", "compliance", "copyright", "spam",
}
# Regex can catch emails inside image filenames and asset URLs.
ASSET_TLDS = {"png", "jpg", "jpeg", "gif", "svg", "webp", "css", "js", "ico"}


def find_emails(pages: dict[str, str]) -> list[str]:
    """Collect de-junked public emails from every fetched page, in order."""
    found: list[str] = []
    for html in pages.values():
        # Strip obfuscation like "hello [at] company [dot] com" lightly.
        text = html.replace(" [at] ", "@").replace(" [dot] ", ".")
        # Decode \uXXXX escapes from JSON-embedded script content, so a
        # sequence like \u003e becomes ">" and breaks the match cleanly.
        text = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text)
        for match in EMAIL_RE.findall(text):
            email = match.lower().strip(".")
            local, _, host = email.partition("@")
            tld = host.rsplit(".", 1)[-1]
            if local in JUNK_LOCAL_PARTS or tld in ASSET_TLDS:
                continue
            if email not in found:
                found.append(email)
    return found


def find_linkedin_profiles(pages: dict[str, str]) -> list[str]:
    """Collect personal LinkedIn profile URLs (/in/...) from every page."""
    profiles: list[str] = []
    for html in pages.values():
        for match in LINKEDIN_PROFILE_RE.findall(html):
            url = match.rstrip("/")
            if url not in profiles:
                profiles.append(url)
    return profiles


def _profile_matches_person(person: LeadershipPerson, profile_url: str) -> bool:
    """A profile belongs to a leader if the URL slug contains their surname."""
    slug = profile_url.rsplit("/in/", 1)[-1].replace("-", "").replace("_", "").lower()
    name_parts = person.name.lower().split()
    if not name_parts:
        return False
    # Require the last name; first name alone is too collision-prone.
    return name_parts[-1] in slug


def enrich_contacts(item: LeadEnrichment, pages: dict[str, str]) -> LeadEnrichment:
    """Merge deterministic contact facts into the LLM-produced record."""
    emails = find_emails(pages)
    item.contact_points.public_emails = list(
        dict.fromkeys([*item.contact_points.public_emails, *emails])
    )

    profiles = find_linkedin_profiles(pages)
    for person in item.key_leadership:
        if person.linkedin_url is not None:
            # The model sometimes pairs a name with the wrong profile link.
            # A URL whose slug lacks the person's surname is not evidence.
            if _profile_matches_person(person, str(person.linkedin_url)):
                continue
            person.linkedin_url = None
        # Fall through and try the page's own links, then Tavily backfills.
        for profile in profiles:
            if _profile_matches_person(person, profile):
                person.linkedin_url = _HTTP_URL.validate_python(profile)
                break
    return item
