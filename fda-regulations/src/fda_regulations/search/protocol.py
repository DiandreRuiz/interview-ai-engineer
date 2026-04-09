"""Narrow contract for hybrid retrieval (API depends on this, not on BM25/embeddings libs)."""

from dataclasses import dataclass
from typing import Literal, Protocol

ClassificationMethod = Literal["cfr_rule", "keyword", "unclassified"]


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
        query: str,
        *,
        top_k: int,
        label_filter: str | None = None,
        label_boost: float | None = None,
    ) -> list[RetrievalHit]:
        """Return ranked hits for the query (fusion scores live in `score`)."""
        ...
