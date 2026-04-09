"""Chunk records for indexing and citations."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ChunkRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str = Field(description="Stable id, e.g. letter_id:paragraph_index.")
    letter_id: str
    letter_url: str
    paragraph_index: int = Field(ge=0)
    text: str = Field(min_length=1)
    cfr_citations: tuple[str, ...] = ()
    company_name: str | None = None
    posted_date: str | None = None
    letter_issue_date: str | None = None
