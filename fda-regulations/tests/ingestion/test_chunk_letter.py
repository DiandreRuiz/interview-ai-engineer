"""Integration tests for chunk_raw_letter (HTML → ChunkRecord)."""

from fda_regulations.chunking import chunk_raw_letter
from fda_regulations.ingest.scrape.models import RawLetterDocument, utc_now


def _make_doc(html: str, letter_id: str = "test-co") -> RawLetterDocument:
    return RawLetterDocument(
        letter_id=letter_id,
        url=f"https://www.fda.gov/warning-letters/{letter_id}",
        html=html,
        fetched_at_utc=utc_now(),
        company_name="Test Co",
        posted_date="01/15/2026",
        letter_issue_date="01/10/2026",
    )


def test_chunk_raw_letter_paragraphs_and_cfr() -> None:
    html = """
    <html><body><article id="main-content">
    <p>First paragraph about 21 CFR Part 211.</p>
    <p></p>
    <p>Second paragraph.</p>
    </article></body></html>
    """
    doc = _make_doc(html)
    chunks = chunk_raw_letter(doc)
    assert len(chunks) == 2
    assert chunks[0].paragraph_index == 0
    assert chunks[1].paragraph_index == 1
    assert chunks[0].chunk_id == "test-co:0"
    assert chunks[1].chunk_id == "test-co:1"
    assert "211" in "".join(chunks[0].cfr_citations).lower()
    assert chunks[0].company_name == "Test Co"
    assert chunks[0].posted_date == "01/15/2026"
    assert chunks[0].letter_issue_date == "01/10/2026"
    assert chunks[1].cfr_citations == ()


def test_heading_merge_produces_single_chunk_with_cfr() -> None:
    """A short heading <p> is merged into the following long paragraph."""
    long_body = (
        "Your firm failed to thoroughly investigate any unexplained discrepancy "
        "or failure of a batch per 21 CFR 211.192. The investigation was incomplete."
    )
    html = f"""
    <html><body><article id="main-content">
    <p>CGMP Violations</p>
    <p>{long_body}</p>
    </article></body></html>
    """
    chunks = chunk_raw_letter(_make_doc(html))
    assert len(chunks) == 1
    assert chunks[0].text.startswith("CGMP Violations\n")
    assert long_body in chunks[0].text
    assert "211.192" in "".join(chunks[0].cfr_citations)


def test_heading_merge_trailing_short_stays_separate() -> None:
    """A short <p> at the end with no following long paragraph stays as its own chunk."""
    long_body = (
        "Your firm failed to establish and follow appropriate written procedures "
        "designed to prevent microbiological contamination of drug products."
    )
    html = f"""
    <html><body><article id="main-content">
    <p>{long_body}</p>
    <p>Sincerely, /S/</p>
    </article></body></html>
    """
    chunks = chunk_raw_letter(_make_doc(html))
    assert len(chunks) == 2
    assert chunks[0].text == long_body
    assert chunks[1].text == "Sincerely, /S/"
