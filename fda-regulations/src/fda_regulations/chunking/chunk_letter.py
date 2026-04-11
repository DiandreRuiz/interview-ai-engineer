"""Build paragraph chunks from a raw scraped letter.

For an iterable of letters, use ``raw_letters_to_chunks`` in ``fda_regulations.chunking``
(package ``__init__``), which calls ``chunk_raw_letter`` per document.
"""

from __future__ import annotations

from fda_regulations.chunking.cfr import extract_cfr_citations
from fda_regulations.chunking.models import ChunkRecord
from fda_regulations.chunking.paragraphs import extract_paragraph_texts
from fda_regulations.ingest.scrape.models import RawLetterDocument


def chunk_raw_letter(doc: RawLetterDocument) -> tuple[ChunkRecord, ...]:
    """One chunk per non-empty ``<p>`` in main content; CFR regex per chunk."""
    paragraphs = extract_paragraph_texts(doc.html)
    chunks: list[ChunkRecord] = []
    for idx, text in enumerate(paragraphs):
        cid = f"{doc.letter_id}:{idx}"
        chunks.append(
            ChunkRecord(
                chunk_id=cid,
                letter_id=doc.letter_id,
                letter_url=doc.url,
                paragraph_index=idx,
                text=text,
                cfr_citations=extract_cfr_citations(text),
                company_name=doc.company_name,
                posted_date=doc.posted_date,
                letter_issue_date=doc.letter_issue_date,
            )
        )
    return tuple(chunks)
