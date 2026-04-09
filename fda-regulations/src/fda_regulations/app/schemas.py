"""HTTP request/response models (stable JSON contract for OpenAPI and clients)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ClassificationMethod = Literal["cfr_rule", "keyword", "unclassified"]


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"
    index_ready: bool = Field(
        description="True when artifacts were validated at startup (strict mode).",
    )


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=4000)
    top_k: int = Field(default=10, ge=1, le=100)
    label_filter: str | None = Field(
        default=None,
        description="If set, only return chunks with this taxonomy label.",
    )
    label_boost: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional boost weight for classified chunks (retriever-specific).",
    )


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
    taxonomy_label: str | None = None
    classification_method: ClassificationMethod | None = None


class SearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hits: list[SearchHit]
