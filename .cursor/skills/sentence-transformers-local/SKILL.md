---
name: sentence-transformers-local
description: Runs sentence-transformers locally on CPU or Apple Silicon for dense embeddings, batching encode calls, cosine similarity search, and optional MPS. Use when implementing the dense side of hybrid RAG without pay-per-token APIs on fda-regulations.
---

# Sentence-Transformers — local embeddings

**Canonical documentation**

- [Sentence-Transformers usage](https://sbert.net/docs/sentence_transformer/usage/usage.html)
- [Semantic search examples](https://sbert.net/docs/sentence_transformer/usage/semantic_textual_similarity.html) (patterns for encode + similarity)
- **PyTorch MPS** (optional Apple GPU): [PyTorch MPS backend](https://pytorch.org/docs/stable/notes/mps.html)

The assignment discourages **pay-per-token** APIs; use **local** embedding models on **CPU** (or **MPS** on Apple Silicon if you explicitly enable it and test).

## Installation

- Add **`sentence-transformers`** via uv ([uv-packaging](../uv-packaging/SKILL.md)); it typically pulls **PyTorch**—choose wheels appropriate for your target (macOS ARM vs Linux container).
- In **Docker**, prefer **CPU** wheels unless you standardize on GPU images; the PoC targets **M-class Mac** locally and containerized runs on typical CI.

## Model selection (PoC)

- Prefer **small** models (e.g. **MiniLM** family or similar) for speed and memory; trade quality for latency on large corpora.
- **Pin** the model name in config or constants so results are reproducible.

## Encoding

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
embeddings = model.encode(
    texts,
    batch_size=32,
    show_progress_bar=False,
    normalize_embeddings=True,  # if using cosine as dot product
)
```

- Tune **`batch_size`** for RAM; large batches help throughput until memory-bound.
- **`normalize_embeddings=True`** simplifies cosine similarity to **dot product** against normalized vectors.

## NumPy and copies

- `encode` often returns **NumPy** `ndarray`; when bridging to BM25 or pure Python structures, convert intentionally (`tolist()` only when needed). Keep **float32** consistently to save memory.

## Caching embeddings

For a **static** PoC corpus, **precompute** embeddings at index time and store alongside **`chunk_id`**; avoid re-encoding the full corpus on every query.

## Apple Silicon (optional)

- If you enable **MPS**, set device consistently and verify parity with CPU for determinism tests. Many PoCs stay **CPU-only** for simpler Docker parity.

## Cross-references

- Fuse with BM25: [hybrid-search-rrf-bm25](../hybrid-search-rrf-bm25/SKILL.md).
- Chunk text input: [html-parsing-ingest](../html-parsing-ingest/SKILL.md).
