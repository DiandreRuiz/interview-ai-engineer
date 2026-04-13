"""On-disk index manifest (artifact contract)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict


class HybridIndexManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    index_backend: Literal["hybrid_bm25_dense"] = "hybrid_bm25_dense"
    built_at_utc: datetime
    embedding_model_id: str
    chunk_count: int
    chunks_relpath: str = "chunks.jsonl"
    embeddings_relpath: str = "embeddings.npy"
    chunk_order_relpath: str = "chunk_order.json"


def write_manifest(path: Path, manifest: HybridIndexManifest) -> None:
    path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_hybrid_manifest(path: Path) -> HybridIndexManifest:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return HybridIndexManifest.model_validate(raw)


def utc_now() -> datetime:
    return datetime.now(UTC)
