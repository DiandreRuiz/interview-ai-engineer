"""Normalize and tokenize search queries for hybrid retrieval (BM25 + dense).

Rules here must stay aligned with the batch indexer tokenization once chunking
and BM25 indexing exist (see ``context/plans/implementation-plan.md`` appendix).
"""

import re
import unicodedata
from dataclasses import dataclass


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

    normalized = unicodedata.normalize("NFKC", original)
    collapsed = " ".join(normalized.split())
    if not collapsed:
        msg = "query is empty after normalization"
        raise ValueError(msg)

    text = collapsed.casefold()
    tokens = tuple(re.findall(r"\w+", text, flags=re.UNICODE))
    if not tokens:
        msg = "query contains no searchable tokens"
        raise ValueError(msg)

    return PreparedQuery(original=original, text=text, tokens=tokens)
