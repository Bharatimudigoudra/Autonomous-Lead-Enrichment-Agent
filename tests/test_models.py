import pytest
from pydantic import ValidationError

from src.models import ContactPoints, LeadEnrichment


def test_confidence_must_stay_within_bounds():
    with pytest.raises(ValidationError):
        LeadEnrichment(domain="x.com", company_overview="a. b.", data_confidence_score=1.5)


def test_emails_are_lowercased_and_deduplicated():
    points = ContactPoints(public_emails=["Hello@X.com", "hello@x.com", "TEAM@x.com"])
    assert points.public_emails == ["hello@x.com", "team@x.com"]
