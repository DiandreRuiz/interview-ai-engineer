"""BM25 + dense embeddings + RRF at query time."""

from __future__ import annotations

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from fda_regulations.chunking.models import ChunkRecord
from fda_regulations.index.manifest import HybridIndexManifest
from fda_regulations.index.rrf import reciprocal_rank_fusion
from fda_regulations.search.protocol import RetrievalHit
from fda_regulations.search.query import PreparedQuery


def _snippet(text: str, limit: int = 280) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1] + "…"


class HybridRetriever:
    """Sparse + dense retrieval merged with RRF (loads ST model for query encoding)."""

    def __init__(
        self,
        *,
        chunks_by_id: dict[str, ChunkRecord],
        chunk_ids_in_order: list[str],
        embeddings: np.ndarray,
        bm25: BM25Okapi,
        manifest: HybridIndexManifest,
        rrf_k: float,
        top_k_sparse: int,
        top_k_dense: int,
    ) -> None:
        self._chunks = chunks_by_id
        self._order = chunk_ids_in_order
        self._embeddings = embeddings
        self._bm25 = bm25
        self._model = SentenceTransformer(manifest.embedding_model_id)
        self._rrf_k = rrf_k
        self._top_k_sparse = top_k_sparse
        self._top_k_dense = top_k_dense

    def search(
        self,
        query: PreparedQuery,
        *,
        top_k: int,
    ) -> list[RetrievalHit]:
        q_tokens = list(query.tokens)
        sparse_scores = self._bm25.get_scores(q_tokens)
        sparse_order = np.argsort(sparse_scores)[::-1][: self._top_k_sparse]
        sparse_ids = [self._order[int(i)] for i in sparse_order]

        q_emb = self._model.encode(
            query.text,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        if isinstance(q_emb, np.ndarray) and q_emb.ndim == 2 and q_emb.shape[0] == 1:
            q_emb = q_emb.flatten()
        sims = self._embeddings @ q_emb
        dense_order = np.argsort(sims)[::-1][: self._top_k_dense]
        dense_ids = [self._order[int(i)] for i in dense_order]

        fused = reciprocal_rank_fusion([sparse_ids, dense_ids], k=self._rrf_k)
        ranked = sorted(fused.items(), key=lambda x: x[1], reverse=True)

        hits: list[RetrievalHit] = []
        for chunk_id, score in ranked:
            ch = self._chunks[chunk_id]
            hits.append(
                RetrievalHit(
                    chunk_id=chunk_id,
                    score=float(score),
                    snippet=_snippet(ch.text),
                    letter_id=ch.letter_id,
                    letter_url=ch.letter_url,
                    paragraph_index=ch.paragraph_index,
                    cfr_citations=ch.cfr_citations,
                )
            )
            if len(hits) >= top_k:
                break
        return hits
