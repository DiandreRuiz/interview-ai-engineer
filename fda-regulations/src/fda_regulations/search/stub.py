"""Stub retriever (no index) for relaxed dev mode."""

from fda_regulations.search.protocol import RetrievalHit
from fda_regulations.search.query import PreparedQuery


class StubRetriever:
    def search(
        self,
        query: PreparedQuery,
        *,
        top_k: int,
    ) -> list[RetrievalHit]:
        _ = (query, top_k)
        return []
