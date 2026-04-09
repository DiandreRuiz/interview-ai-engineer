"""Integration tests for chunk_raw_letter (HTML → ChunkRecord)."""

from fda_regulations.chunking import chunk_raw_letter
from fda_regulations.ingest.scrape.models import RawLetterDocument, utc_now


def test_chunk_raw_letter_paragraphs_and_cfr() -> None:
    html = """
    <html><body><article id="main-content">
    <p>First paragraph about 21 CFR Part 211.</p>
    <p></p>
    <p>Second paragraph.</p>
    </article></body></html>
    """
    doc = RawLetterDocument(
        letter_id="test-co",
        url="https://www.fda.gov/warning-letters/test-co",
        html=html,
        fetched_at_utc=utc_now(),
        company_name="Test Co",
        posted_date="01/15/2026",
        letter_issue_date="01/10/2026",
    )
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
