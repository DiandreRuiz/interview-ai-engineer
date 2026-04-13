"""HTTP API models (Pydantic): request/response bodies and OpenAPI contract."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"
    index_ready: bool = Field(
        description="True when artifacts were validated at startup (strict mode).",
    )


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=4000)

    @field_validator("query")
    @classmethod
    def strip_non_empty_query(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("query must not be empty or whitespace-only")
        return stripped

    top_k: int = Field(default=10, ge=1, le=100)


class SearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    score: float = Field(description="Fused rank score (e.g. RRF).")
    snippet: str
    letter_id: str
    letter_url: str
    paragraph_index: int | None = Field(
        description="Paragraph position within the letter body when known.",
    )
    cfr_citations: tuple[str, ...] = Field(
        default=(),
        description="21 CFR citation strings extracted from the chunk text (regex metadata).",
    )


class SearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hits: list[SearchHit]
