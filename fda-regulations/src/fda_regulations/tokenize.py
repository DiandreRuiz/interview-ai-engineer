"""Text normalization and tokenization aligned with BM25 and ``prepare_search_query``."""

from __future__ import annotations

import re
import unicodedata


def normalize_for_retrieval(text: str) -> str:
    """Apply NFKC, collapse whitespace, and casefold (input should be stripped by caller)."""
    normalized = unicodedata.normalize("NFKC", text)
    collapsed = " ".join(normalized.split())
    return collapsed.casefold()


def tokenize_normalized(normalized: str) -> tuple[str, ...]:
    """Word tokens from already case-folded text (Unicode-aware ``\\w+``)."""
    return tuple(re.findall(r"\w+", normalized, flags=re.UNICODE))


def tokenize_for_retrieval(text: str) -> tuple[str, ...]:
    """Normalize then tokenize; empty paragraphs yield ``()``."""
    if not text.strip():
        return ()
    return tokenize_normalized(normalize_for_retrieval(text))
