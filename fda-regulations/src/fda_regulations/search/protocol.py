"""Narrow contract for hybrid retrieval (API depends on this, not on BM25/embeddings libs)."""

from dataclasses import dataclass
from typing import Protocol

from fda_regulations.search.query import PreparedQuery
from fda_regulations.types import ClassificationMethod


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    chunk_id: str
    score: float
    snippet: str
    letter_id: str
    letter_url: str
    paragraph_index: int | None
    taxonomy_label: str | None = None
    classification_method: ClassificationMethod | None = None


class Retriever(Protocol):
    def search(
        self,
        query: PreparedQuery,
        *,
        top_k: int,
        label_filter: str | None = None,
        label_boost: float | None = None,
    ) -> list[RetrievalHit]:
        """Return ranked hits (fusion scores live in ``score``).

        Implementations should use ``query.text`` for dense encoding and
        ``query.tokens`` for BM25, per shared normalization in ``prepare_search_query``.
        """
        ...
