"""Normalize and tokenize search queries for hybrid retrieval (BM25 + dense).

Rules stay aligned with ``fda_regulations.tokenize`` (batch indexer).
"""

from dataclasses import dataclass

from fda_regulations.tokenize import normalize_for_retrieval, tokenize_normalized


@dataclass(frozen=True, slots=True)
class PreparedQuery:
    """Query after API-boundary preparation."""

    original: str
    """Trimmed raw query from the client (for logging)."""

    text: str
    """Unicode-normalized, case-folded string for dense encoding."""

    tokens: tuple[str, ...]
    """Word tokens for BM25; same normalization rules as ``text``."""


def prepare_search_query(raw: str) -> PreparedQuery:
    """Strip, NFKC-normalize, collapse whitespace, case-fold, and tokenize.

    ``raw`` should already be stripped and non-empty (see ``SearchRequest``).
    """
    original = raw.strip()
    if not original:
        msg = "query is empty"
        raise ValueError(msg)

    text = normalize_for_retrieval(original)
    if not text:
        msg = "query is empty after normalization"
        raise ValueError(msg)

    tokens = tokenize_normalized(text)
    if not tokens:
        msg = "query contains no searchable tokens"
        raise ValueError(msg)

    return PreparedQuery(original=original, text=text, tokens=tokens)
