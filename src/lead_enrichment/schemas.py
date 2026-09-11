"""Validated schemas for crawl, extraction, and output data."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ContactPoint(StrictModel):
    email: str = Field(description="A public or generic email address found in the supplied evidence.")
    source_url: str = Field(description="The supplied HTTP(S) page URL where the email was found.")

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("source_url must be an HTTP(S) URL")
        return value


class LeadershipMember(StrictModel):
    name: str = Field(description="Person's name exactly as supported by the supplied evidence.")
    title: str = Field(description="Their role or title exactly as supported by the supplied evidence.")
    linkedin_url: str | None = Field(
        description="Their LinkedIn profile URL only when present in the supplied evidence; otherwise null."
    )

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or parsed.netloc != "linkedin.com" and not parsed.netloc.endswith(
            ".linkedin.com"
        ):
            raise ValueError("linkedin_url must be an HTTP(S) LinkedIn URL")
        return value


class CompanyIntelligence(StrictModel):
    company_overview: str = Field(description="Exactly two concise sentences describing the company.")
    target_audience_or_icp: str = Field(description="The product's target audience or ideal customer profile.")
    contact_points: list[ContactPoint] = Field(description="Public/generic email addresses found in evidence.")
    leadership_team: list[LeadershipMember] = Field(
        description="Leadership or team members supported by the supplied evidence."
    )
    data_confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Evidence completeness and quality score between 0.0 and 1.0.",
    )


class CrawlPage(StrictModel):
    url: HttpUrl
    title: str
    text: str
    status_code: int | None


class PipelineError(StrictModel):
    stage: str
    message: str
    url: str | None


class TokenUsage(StrictModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)


class DomainResult(StrictModel):
    domain: str
    pages_crawled: list[HttpUrl]
    intelligence: CompanyIntelligence | None
    errors: list[PipelineError]
    token_usage: TokenUsage | None


class RunOutput(StrictModel):
    generated_at: datetime
    model: str
    results: list[DomainResult]
