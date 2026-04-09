"""Shared retrieval tokenization."""

from fda_regulations.search.query import prepare_search_query
from fda_regulations.tokenize import normalize_for_retrieval, tokenize_for_retrieval


def test_tokenize_matches_prepare_search_query_tokens() -> None:
    raw = "  Sterility   Assurance  "
    p = prepare_search_query(raw)
    norm = normalize_for_retrieval(raw.strip())
    assert p.text == norm
    assert p.tokens == tokenize_for_retrieval(raw.strip())
