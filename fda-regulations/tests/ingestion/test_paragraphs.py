"""Unit tests for paragraph extraction from letter HTML.

Covers basic ``<p>`` extraction, fallback selectors, empty-paragraph skipping,
and the heading-merge pass (short ``<p>`` elements prepended to the next
substantive paragraph).
"""

import pytest

from fda_regulations.chunking.paragraphs import (
    HEADING_MERGE_THRESHOLD,
    _merge_short_paragraphs,
    extract_paragraph_texts,
)


# -- Basic extraction --------------------------------------------------------

def test_extract_from_article_main_content() -> None:
    long_a = "A" * HEADING_MERGE_THRESHOLD
    long_b = "B" * HEADING_MERGE_THRESHOLD
    html = f"""
    <html><body><article id="main-content">
    <p>{long_a}</p>
    <p>{long_b}</p>
    </article></body></html>
    """
    assert extract_paragraph_texts(html) == [long_a, long_b]


def test_extract_falls_back_to_id_main_content_div() -> None:
    long_text = "X" * HEADING_MERGE_THRESHOLD
    html = f"""
    <html><body><div id="main-content">
    <p>{long_text}</p>
    </div></body></html>
    """
    assert extract_paragraph_texts(html) == [long_text]


def test_extract_prefers_article_main_content_over_div_with_same_id() -> None:
    long_text = "Z" * HEADING_MERGE_THRESHOLD
    html = f"""
    <html><body>
    <div id="main-content"><p>{long_text} div</p></div>
    <article id="main-content"><p>{long_text} article</p></article>
    </body></html>
    """
    out = extract_paragraph_texts(html)
    assert out == [f"{long_text} article"]


def test_extract_strips_script_and_style() -> None:
    long_text = "Visible " * 15  # well over threshold
    html = f"""
    <article id="main-content">
    <script>alert(1)</script>
    <style>.x{{}}</style>
    <p>{long_text}</p>
    </article>
    """
    paras = extract_paragraph_texts(html)
    assert paras == [long_text.strip()]
    assert "alert" not in paras[0]


def test_extract_skips_empty_paragraphs() -> None:
    long_a = "Real " * 20
    long_b = "Also real " * 20
    html = f"""
    <article id="main-content">
    <p>{long_a}</p>
    <p>   </p>
    <p></p>
    <p>{long_b}</p>
    </article>
    """
    assert extract_paragraph_texts(html) == [long_a.strip(), long_b.strip()]


def test_extract_returns_empty_when_no_main_region() -> None:
    assert extract_paragraph_texts("<html><body><p>Orphan</p></body></html>") == []


# -- Heading-merge via _merge_short_paragraphs --------------------------------

class TestMergeShortParagraphs:
    """Direct tests of the merge helper, independent of HTML parsing."""

    def test_no_short_paragraphs_unchanged(self) -> None:
        paras = ["Long paragraph one." * 5, "Long paragraph two." * 5]
        assert _merge_short_paragraphs(paras, 50) == paras

    def test_single_heading_merged_into_next(self) -> None:
        result = _merge_short_paragraphs(["HEADING", "Body text that is long enough to exceed the threshold."], 50)
        assert len(result) == 1
        assert result[0] == "HEADING\nBody text that is long enough to exceed the threshold."

    def test_consecutive_headings_all_merged(self) -> None:
        result = _merge_short_paragraphs(
            ["WARNING LETTER", "CGMP Violations", "Body text that is definitely long enough to exceed the threshold easily."],
            50,
        )
        assert len(result) == 1
        assert result[0].startswith("WARNING LETTER\nCGMP Violations\n")

    def test_trailing_short_paragraph_emitted_as_is(self) -> None:
        result = _merge_short_paragraphs(
            ["Body text that is definitely long enough to exceed the threshold easily.", "Sincerely,"],
            50,
        )
        assert len(result) == 2
        assert result[1] == "Sincerely,"

    def test_alternating_short_long(self) -> None:
        short = "Heading"
        long = "Substantive paragraph with enough content to exceed threshold."
        result = _merge_short_paragraphs([short, long, short, long], 50)
        assert len(result) == 2
        assert result[0] == f"{short}\n{long}"
        assert result[1] == f"{short}\n{long}"

    def test_all_short_emitted_individually(self) -> None:
        result = _merge_short_paragraphs(["A", "B", "C"], 50)
        assert result == ["A", "B", "C"]

    def test_empty_list(self) -> None:
        assert _merge_short_paragraphs([], 50) == []

    def test_single_long_paragraph(self) -> None:
        long = "X" * 100
        assert _merge_short_paragraphs([long], 50) == [long]

    def test_single_short_paragraph(self) -> None:
        assert _merge_short_paragraphs(["Short"], 50) == ["Short"]


# -- Heading-merge via full HTML pipeline ------------------------------------

def test_heading_merge_in_html_pipeline() -> None:
    """A short heading <p> followed by a long <p> produces one merged chunk."""
    long_body = "This paragraph describes a specific CGMP violation in detail. " * 3
    html = f"""
    <article id="main-content">
    <p>CGMP Violations</p>
    <p>{long_body}</p>
    </article>
    """
    result = extract_paragraph_texts(html)
    assert len(result) == 1
    assert result[0].startswith("CGMP Violations\n")
    assert long_body.strip() in result[0]


def test_heading_merge_multiple_sections() -> None:
    """Multiple heading+body pairs each produce one merged chunk."""
    body_a = "First violation involves sterility assurance across all production lines. " * 2
    body_b = "Second violation involves failure to maintain adequate laboratory records. " * 2
    html = f"""
    <article id="main-content">
    <p>CGMP Violations</p>
    <p>{body_a}</p>
    <p>Data Integrity</p>
    <p>{body_b}</p>
    </article>
    """
    result = extract_paragraph_texts(html)
    assert len(result) == 2
    assert result[0].startswith("CGMP Violations\n")
    assert result[1].startswith("Data Integrity\n")
