"""Placeholder retriever until BM25 + dense + RRF adapter loads real indexes."""

from fda_regulations.search.protocol import RetrievalHit


class StubRetriever:
    """Returns no hits; used for tests and pre-index local dev."""

    def search(
        self,
        query: str,
        *,
        top_k: int,
        label_filter: str | None = None,
        label_boost: float | None = None,
    ) -> list[RetrievalHit]:
        _ = (query, top_k, label_filter, label_boost)
        return []
