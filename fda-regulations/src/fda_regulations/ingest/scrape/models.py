"""Pydantic models for listing rows and fetched letter HTML."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class LetterListEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    letter_id: str = Field(description="Slug from the letter URL path.")
    url: str
    company_name: str | None = None
    posted_date: str | None = Field(default=None, description="As shown on the listing table.")
    letter_issue_date: str | None = Field(
        default=None,
        description="As shown on the listing table.",
    )


class RawLetterDocument(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    letter_id: str
    url: str
    html: str
    fetched_at_utc: datetime
    company_name: str | None = None
    posted_date: str | None = None
    letter_issue_date: str | None = None


class IngestResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    documents: tuple[RawLetterDocument, ...]
    listing_pages_fetched: int = Field(
        description="Count of listing-related HTTP GETs (hub shell + each DataTables AJAX batch).",
    )
    listing_rows_seen: int
    fetch_errors: tuple[str, ...]


def utc_now() -> datetime:
    return datetime.now(UTC)
