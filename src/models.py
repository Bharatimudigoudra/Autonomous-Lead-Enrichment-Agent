"""Pydantic models for validated lead-enrichment output."""

from pydantic import BaseModel, Field, HttpUrl, field_validator


class LeadershipPerson(BaseModel):
    name: str = Field(min_length=1)
    role: str = Field(min_length=1)
    linkedin_url: HttpUrl | None = None


class ContactPoints(BaseModel):
    public_emails: list[str] = Field(default_factory=list)

    @field_validator("public_emails")
    @classmethod
    def normalize_emails(cls, values: list[str]) -> list[str]:
        """Lowercase and de-duplicate emails while keeping their order."""
        clean: list[str] = []
        for value in values:
            email = value.strip().lower()
            if "@" in email and email not in clean:
                clean.append(email)
        return clean


class LeadEnrichment(BaseModel):
    domain: str
    company_overview: str = Field(
        description="A concise overview of the company in exactly two sentences."
    )
    target_audience: list[str] = Field(default_factory=list)
    contact_points: ContactPoints = Field(default_factory=ContactPoints)
    key_leadership: list[LeadershipPerson] = Field(default_factory=list)
    data_confidence_score: float = Field(ge=0.0, le=1.0)
    source_urls: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    token_usage: dict[str, int] = Field(default_factory=dict)
