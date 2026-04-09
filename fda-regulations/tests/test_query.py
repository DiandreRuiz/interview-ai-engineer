"""Search query normalization (shared with future BM25 + dense indexing)."""

import pytest

from fda_regulations.search.query import prepare_search_query


def test_prepare_trims_and_casefolds() -> None:
    p = prepare_search_query("  Sterility   Assurance  ")
    assert p.original == "Sterility   Assurance"
    assert p.text == "sterility assurance"
    assert p.tokens == ("sterility", "assurance")


def test_prepare_nfkc_fullwidth() -> None:
    p = prepare_search_query("ＣＦＲ 211")
    assert p.text == "cfr 211"
    assert p.tokens == ("cfr", "211")


def test_prepare_empty_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        prepare_search_query("")


def test_prepare_whitespace_only_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        prepare_search_query("   ")


def test_prepare_no_word_tokens_raises() -> None:
    with pytest.raises(ValueError, match="no searchable tokens"):
        prepare_search_query("…")
