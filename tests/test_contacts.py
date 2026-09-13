from src.contacts import enrich_contacts, find_emails, find_linkedin_profiles
from src.models import LeadEnrichment, LeadershipPerson


def test_find_emails_filters_junk(sample_pages):
    emails = find_emails(sample_pages)
    assert "hello@exampleco.com" in emails
    assert "abuse@exampleco.com" not in emails
    assert "privacy@exampleco.com" not in emails


def test_find_linkedin_profiles(sample_pages):
    profiles = find_linkedin_profiles(sample_pages)
    assert profiles == ["https://www.linkedin.com/in/janedoe"]


def test_enrich_contacts_fills_email_and_matches_leader(sample_pages):
    item = LeadEnrichment(
        domain="example.com",
        company_overview="a. b.",
        data_confidence_score=0.5,
        key_leadership=[LeadershipPerson(name="Jane Doe", role="CEO")],
    )
    out = enrich_contacts(item, sample_pages)
    assert "hello@exampleco.com" in out.contact_points.public_emails
    assert str(out.key_leadership[0].linkedin_url).rstrip("/") == "https://www.linkedin.com/in/janedoe"


def test_enrich_contacts_does_not_guess_wrong_leader(sample_pages):
    item = LeadEnrichment(
        domain="example.com",
        company_overview="a. b.",
        data_confidence_score=0.5,
        key_leadership=[LeadershipPerson(name="John Smith", role="CTO")],
    )
    out = enrich_contacts(item, sample_pages)
    assert out.key_leadership[0].linkedin_url is None
