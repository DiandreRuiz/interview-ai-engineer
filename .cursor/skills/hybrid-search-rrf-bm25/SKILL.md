---
name: hybrid-search-rrf-bm25
description: Implements sparse retrieval with Okapi BM25, combines ranked lists using reciprocal rank fusion with k about 60, and aligns tokenization with dense retrieval. Use when building hybrid RAG for fda-regulations, fusing BM25 and embedding rankings, or explaining RRF in interview prep.
---

# Hybrid search: BM25 and reciprocal rank fusion (RRF)

**References**

- Python **`rank-bm25`** (this repo: **`rank-bm25` ≥0.2.2** per `pyproject.toml`): [PyPI](https://pypi.org/project/rank-bm25/), [GitHub dorianbrown/rank_bm25](https://github.com/dorianbrown/rank_bm25)
- **RRF** (formula, **`rank_constant` default 60** in Elasticsearch): [Reciprocal rank fusion](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion) (legacy guide path: [RRF in the Elasticsearch Reference](https://www.elastic.co/guide/en/elasticsearch/reference/current/rrf.html)); original paper: [Cormack et al., SIGIR 2009](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- Project constants: [implementation-plan.md](../../../context/plans/implementation-plan.md) appendix

## Why hybrid

- **BM25** excels at **lexical** matches (CFR strings, drug names, rare tokens).
- **Dense embeddings** help **paraphrases** and topical similarity ([sentence-transformers-local](../sentence-transformers-local/SKILL.md)).
- Run both on the same **`chunk_id`** corpus, then **fuse** ranks.

## BM25 with rank-bm25

- The library expects a **tokenized** corpus: `list[list[str]]` (one token list per document).
- **Preprocessing** (lowercasing, optional stopwords) must be **consistent** between indexing and querying—and **aligned** with the tokenizer used for dense retrieval when possible (same normalization rules at minimum).

```python
from rank_bm25 import BM25Okapi

tokenized_corpus: list[list[str]] = [...]
bm25 = BM25Okapi(tokenized_corpus)
scores = bm25.get_scores(tokenized_query)
# Optional: score only a subset of doc indices — get_batch_scores(query, doc_ids)
```

- **`get_scores`** returns a **NumPy** vector over the whole corpus; use **`get_batch_scores`** when scoring a candidate subset only.
- **`rank_bm25`** depends on **NumPy**: be mindful of **array dtypes** and avoid unnecessary copies when bridging to other libraries; keep chunk text as Python `str` at boundaries.

## Reciprocal Rank Fusion (RRF)

For each document `d` appearing in retriever lists `r`, Elasticsearch defines the idea as summing **rank-based** contributions (rank starts at **1**):

\[
\text{RRF}(d) = \sum_{r} \frac{1}{k + \text{rank}_r(d)}
\]

- Documents **missing** from a retriever’s **truncated candidate list** (your per-retriever top‑N) contribute **0** for that retriever (omit that term).
- The fusion hyperparameter **`k`** (Elasticsearch **`rank_constant`**) defaults to **60** in Elastic’s RRF API; **`k ≥ 1`**. Match the value in code and [implementation-plan.md](../../../context/plans/implementation-plan.md).

```python
def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    *,
    k: int = 60,
) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ids in ranked_lists:
        for rank, chunk_id in enumerate(ids, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

## Pipeline alignment

1. Retrieve **top‑k_bm25** and **top‑k_dense** (separate `k` values allowed).
2. Fuse with RRF to a merged ordering.
3. **Extensions (not in the slim PoC):** metadata **filter/boost** (e.g. by label) or a **cross-encoder rerank** on the top‑N fused list—see [weak-supervision-taxonomy](../weak-supervision-taxonomy/SKILL.md) if adding labels.

## Why RRF instead of score normalization

BM25 scores and cosine (or dot-product) similarity scores live on **incompatible scales**. RRF uses only **ranks**, avoiding fragile hand-tuned normalization.

## Optional scale-up

For larger corpora, consider **HNSW** or dedicated vector databases; the PoC often keeps vectors **in memory**. Document the choice in the implementation plan before adding new dependencies.

## Cross-references

- Embeddings: [sentence-transformers-local](../sentence-transformers-local/SKILL.md).
- Optional weak-supervision labels (extension / interview design): [weak-supervision-taxonomy](../weak-supervision-taxonomy/SKILL.md).
