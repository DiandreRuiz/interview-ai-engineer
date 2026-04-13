"""Load hybrid retriever from artifact root."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from fda_regulations.chunking.models import ChunkRecord
from fda_regulations.config import Settings
from fda_regulations.index.manifest import read_hybrid_manifest
from fda_regulations.index.retriever import HybridRetriever
from fda_regulations.tokenize import bm25_token_list


def _read_chunks_jsonl(path: Path) -> dict[str, ChunkRecord]:
    by_id: dict[str, ChunkRecord] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = ChunkRecord.model_validate_json(line)
            by_id[rec.chunk_id] = rec
    if not by_id:
        msg = f"No chunks in {path}"
        raise ValueError(msg)
    return by_id


def load_hybrid_retriever(root: Path, settings: Settings) -> HybridRetriever:
    """Load BM25 + dense index and embedding model."""
    root = root.expanduser().resolve()
    manifest_path = root / "index_manifest.json"
    manifest = read_hybrid_manifest(manifest_path)

    chunks_path = root / manifest.chunks_relpath
    order_path = root / manifest.chunk_order_relpath
    emb_path = root / manifest.embeddings_relpath

    chunks_by_id = _read_chunks_jsonl(chunks_path)
    order: list[str] = json.loads(order_path.read_text(encoding="utf-8"))
    embeddings = np.load(emb_path)

    if len(order) != manifest.chunk_count:
        msg = "chunk_order length does not match manifest.chunk_count"
        raise ValueError(msg)
    if embeddings.shape[0] != len(order):
        msg = "embeddings row count does not match chunk_order"
        raise ValueError(msg)
    for cid in order:
        if cid not in chunks_by_id:
            msg = f"chunk_order references missing chunk_id: {cid}"
            raise ValueError(msg)

    corpus_tokens = [bm25_token_list(chunks_by_id[cid].text) for cid in order]
    bm25 = BM25Okapi(corpus_tokens)

    return HybridRetriever(
        chunks_by_id=chunks_by_id,
        chunk_ids_in_order=order,
        embeddings=embeddings,
        bm25=bm25,
        manifest=manifest,
        rrf_k=float(settings.rrf_k),
        top_k_sparse=settings.search_top_k_sparse,
        top_k_dense=settings.search_top_k_dense,
    )


def is_hybrid_index_manifest(data: dict[str, object]) -> bool:
    """True if JSON manifest describes a loadable hybrid index."""
    return (
        data.get("schema_version") == 1
        and data.get("index_backend") == "hybrid_bm25_dense"
        and isinstance(data.get("embedding_model_id"), str)
        and data["embedding_model_id"] != ""
    )
