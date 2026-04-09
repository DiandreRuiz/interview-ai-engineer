"""Corpus → chunks via raw_letters_to_chunks."""

from fda_regulations.chunk_pipeline import raw_letters_to_chunks
from fda_regulations.ingest.scrape.models import RawLetterDocument, utc_now


def test_pipeline_chunks_letter_html() -> None:
    html = """
    <html><body><article id="main-content">
    <p>Violations of 21 CFR Part 211.42 were observed.</p>
    </article></body></html>
    """
    doc = RawLetterDocument(
        letter_id="co-1",
        url="https://www.fda.gov/warning-letters/co-1",
        html=html,
        fetched_at_utc=utc_now(),
    )
    chunks = raw_letters_to_chunks((doc,))
    assert len(chunks) == 1
    assert "211" in "".join(chunks[0].cfr_citations).lower()
