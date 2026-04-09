"""BM25 token lists aligned with ``tokenize_for_retrieval``."""

from __future__ import annotations

from fda_regulations.tokenize import tokenize_for_retrieval


def bm25_token_list(text: str) -> list[str]:
    """Return token list for BM25; empty text maps to a placeholder token."""
    tokens = list(tokenize_for_retrieval(text))
    return tokens if tokens else ["__empty__"]
