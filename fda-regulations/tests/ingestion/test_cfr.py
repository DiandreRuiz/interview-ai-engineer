"""Unit tests for 21 CFR citation regex extraction."""

import pytest

from fda_regulations.chunking.cfr import extract_cfr_citations


@pytest.mark.parametrize(
    ("text", "expected_substrings"),
    [
        ("Under 21 CFR Part 211.42 we cite quality.", ("211.42",)),
        ("Reference 21 CFR 820.30 for design controls.", ("820.30",)),
        ("See 21 C.F.R. § 820.30(a).", ("820.30",)),
        ("21 CFR Section 211.100 applies.", ("211.100",)),
        ("Mixed 21 CFR 211.1 and 21 CFR Part 820.", ("211.1", "820")),
    ],
)
def test_extract_cfr_positive_cases(text: str, expected_substrings: tuple[str, ...]) -> None:
    cites = extract_cfr_citations(text)
    joined = " ".join(cites)
    for part in expected_substrings:
        assert part in joined


def test_extract_cfr_dedupes_same_cite_case_insensitive() -> None:
    text = "21 CFR Part 211.42 then again 21 cfr part 211.42."
    cites = extract_cfr_citations(text)
    assert len(cites) == 1
    assert "211.42" in cites[0]


def test_extract_cfr_preserves_first_spelling_order() -> None:
    text = "First 21 cfr 211.100 and later 21 CFR 211.200."
    cites = extract_cfr_citations(text)
    assert len(cites) == 2
    assert cites[0].casefold().startswith("21 cfr")
    assert "211.200" in cites[1]


def test_extract_cfr_empty_and_no_match() -> None:
    assert extract_cfr_citations("") == ()
    assert extract_cfr_citations("No regulation numbers here.") == ()


def test_extract_cfr_does_not_match_other_title_or_bare_prefix() -> None:
    assert extract_cfr_citations("Under 20 CFR 211.1 we would not match title 21 rule.") == ()
    assert extract_cfr_citations("Mention 21 CFR without a section number.") == ()


def test_extract_cfr_unique_count_matches_casefold_set() -> None:
    text = "See 21 CFR Part 211.42 and 21 CFR 820.30. Also 21 cfr 211.100 for detail."
    cites = extract_cfr_citations(text)
    assert len(cites) == len({c.casefold() for c in cites})
    assert len(cites) == 3
