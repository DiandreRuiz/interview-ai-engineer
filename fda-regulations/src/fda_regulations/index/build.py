"""Build hybrid index artifacts (BM25 corpus + dense embeddings)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from fda_regulations.chunking.models import ChunkRecord
from fda_regulations.index.manifest import HybridIndexManifest, utc_now, write_manifest


def build_hybrid_index(
    artifact_root: Path,
    chunks: Sequence[ChunkRecord],
    *,
    embedding_model_id: str,
) -> HybridIndexManifest:
    """Write ``chunks.jsonl``, ``embeddings.npy``, ``chunk_order.json``, ``index_manifest.json``."""
    root = artifact_root.expanduser().resolve()
    if not chunks:
        msg = "chunk list is empty"
        raise ValueError(msg)

    root.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    ordered: list[ChunkRecord] = []
    for c in chunks:
        if c.chunk_id in seen:
            msg = f"duplicate chunk_id: {c.chunk_id}"
            raise ValueError(msg)
        seen.add(c.chunk_id)
        ordered.append(c)

    chunks_path = root / "chunks.jsonl"
    with chunks_path.open("w", encoding="utf-8") as f:
        for c in ordered:
            f.write(c.model_dump_json())
            f.write("\n")

    texts = [c.text for c in ordered]
    model = SentenceTransformer(embedding_model_id)
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    if not isinstance(vectors, np.ndarray):
        vectors = np.asarray(vectors)
    np.save(root / "embeddings.npy", vectors)

    order_ids = [c.chunk_id for c in ordered]
    (root / "chunk_order.json").write_text(
        json.dumps(order_ids, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest = HybridIndexManifest(
        built_at_utc=utc_now(),
        embedding_model_id=embedding_model_id,
        chunk_count=len(ordered),
    )
    write_manifest(root / "index_manifest.json", manifest)
    return manifest
