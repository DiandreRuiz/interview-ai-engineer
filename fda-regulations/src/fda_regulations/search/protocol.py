"""Narrow contract for hybrid retrieval (API depends on this, not BM25/embeddings libs)."""

from dataclasses import dataclass
from typing import Protocol

from fda_regulations.search.query import PreparedQuery


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    chunk_id: str
    score: float
    snippet: str
    letter_id: str
    letter_url: str
    paragraph_index: int | None
    cfr_citations: tuple[str, ...]


class Retriever(Protocol):
    def search(
        self,
        query: PreparedQuery,
        *,
        top_k: int,
    ) -> list[RetrievalHit]:
        """Return ranked hits (fusion scores live in ``score``).

        Implementations should use ``query.text`` for dense encoding and
        ``query.tokens`` for BM25, per shared normalization in ``prepare_search_query``.
        """
        ...
